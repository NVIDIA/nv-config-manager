#!/usr/bin/env bash
# Stage 1 of the test-env promote flow: obtain a successful secret-free build
# of the vetted copy-pr-bot snapshot (pull-request/<n>) on the mirror.
#
# Resolves the snapshot's HEAD SHA, confirms the PR is still open upstream and
# warns if the snapshot lags the PR's live HEAD, then either reuses an existing
# successful build pipeline for that exact ref+SHA (unexpired artifacts) or
# API-triggers a new one on the pull-request ref and polls it to completion.
# The build pipeline runs on an UNPROTECTED ref, so it executes the untrusted
# PR code without any protected variables; no variables are passed on the
# trigger call because trigger variables would be visible to those untrusted
# jobs. Provenance is finally asserted from GitLab's own pipeline metadata.
#
# Inputs (pipeline variables): NVCM_PROMOTE_PR, NVCM_PROMOTE_ENV
#   Optional: NVCM_PROMOTE_REUSE_BUILD (default true),
#             NVCM_PROMOTE_REQUIRE_PR_HEAD (default false),
#             NVCM_PROMOTE_ALLOW_UNVERIFIED_PR_STATE (default false)
# Requires: NVCM_MIRROR_API_TOKEN (read_api; polling/job-listing endpoints are
#           not in the CI_JOB_TOKEN allowlist), NVCM_BUILD_TRIGGER_TOKEN
#           (pipeline trigger token - a job token cannot trigger a pipeline in
#           its own project), CI_JOB_TOKEN (repo clone)
# Output:   promote.env (dotenv + file artifact) - PR_NUM, PR_REF, PR_SHA,
#           PR_SHORT_SHA,
#           PROMOTE_VERSION, BUILD_PIPELINE_ID, BUILD_JOB_ID_<IMAGE> x9,
#           CHART_BUILD_JOB_ID
set -euo pipefail

: "${NVCM_PROMOTE_PR:?Set NVCM_PROMOTE_PR to the GitHub PR number}"
: "${NVCM_PROMOTE_ENV:?Set NVCM_PROMOTE_ENV to the target environment}"
: "${NVCM_MIRROR_API_TOKEN:?NVCM_MIRROR_API_TOKEN (read_api) is required}"
# NVCM_BUILD_TRIGGER_TOKEN is checked lazily at the trigger site rather than
# here: a run that reuses an existing successful build never needs it.

if ! printf '%s' "$NVCM_PROMOTE_PR" | grep -Eq '^[0-9]+$'; then
    echo "ERROR: NVCM_PROMOTE_PR must be a PR number, got '${NVCM_PROMOTE_PR}'" >&2
    exit 1
fi

github_repo="${NVCM_UPSTREAM_GITHUB_REPO:-dsx-ai-factory/nv-config-manager}"
api="${CI_API_V4_URL}/projects/${CI_PROJECT_ID}"
poll_interval="${NVCM_BUILD_POLL_INTERVAL:-30}"
poll_timeout="${NVCM_BUILD_POLL_TIMEOUT:-5400}"

# Pipeline sources that count as a deliberately triggered build. Anything else
# (a mirror push, a schedule, ...) is refused by the pr-build workflow rules in
# common.yml, so such a pipeline can be "successful" without having built
# anything. Applied both when picking a build to reuse and at the provenance
# gate below; keep the two in sync by keeping this the only copy.
allowed_build_sources='["pipeline","trigger","api","web"]'

PR_NUM="$NVCM_PROMOTE_PR"
PR_REF="pull-request/${PR_NUM}"

# The nine pr-build-image matrix entries (target|image), matching pr-build.yml.
matrix_entries="nv-config-manager|nv-config-manager
kea|nv-config-manager-kea
kea-admin|nv-config-manager-kea-admin
ui|nv-config-manager-ui
nb|nv-config-manager-nautobot
nats-ready|nv-config-manager-nats-ready
temporal-server|nv-config-manager-temporal
temporal-bootstrap|nv-config-manager-temporal-bootstrap
temporal-ui|nv-config-manager-temporal-ui"

api_get() {
    curl -fsS --max-time 30 -H "PRIVATE-TOKEN: ${NVCM_MIRROR_API_TOKEN}" "$@"
    return $?
}

# -----------------------------------------------------------------------------
# Resolve the current HEAD of the VETTED copy-pr-bot snapshot on the mirror
# (pull-request/<n>). This is intentionally the vetted snapshot, not the PR's
# live HEAD - the GitHub PR-HEAD comparison below surfaces any divergence.
# -----------------------------------------------------------------------------
PR_SHA="$(git ls-remote "$CI_REPOSITORY_URL" "refs/heads/${PR_REF}" | cut -f1)"
if [[ -z "$PR_SHA" ]]; then
    echo "ERROR: ${PR_REF} does not exist on the mirror." >&2
    echo "Either the PR is closed/merged, copy-pr-bot has not vetted it, or"
    echo "pull-mirroring has not replicated the branch yet."
    exit 1
fi
PR_SHORT_SHA="$(printf '%s' "$PR_SHA" | cut -c1-8)"
PROMOTE_VERSION="0.0.0-pr${PR_NUM}.${PR_SHORT_SHA}"
echo "PR #${PR_NUM}: ${PR_REF} @ ${PR_SHA}"
echo "Promote version: ${PROMOTE_VERSION}"

# Interactive-path upstream checks against GitHub's PR API. This API is
# authoritative for PR *state* and the PR's *true* HEAD - unlike the copy-pr-bot
# pull-request/<n> branch (PR_SHA above), which is a VETTED SNAPSHOT that may
# lag the PR (untrusted authors only re-copy on /ok to test).
pr_json="$(curl -fsS --max-time 10 "https://api.github.com/repos/${github_repo}/pulls/${PR_NUM}" || true)"
if [[ -n "$pr_json" ]]; then
    pr_state="$(printf '%s' "$pr_json" | jq -r '.state // empty')"
    if [[ "$pr_state" != "open" ]]; then
        echo "ERROR: upstream PR #${PR_NUM} is '${pr_state:-unknown}', not open. Refusing to promote." >&2
        exit 1
    fi
    # Surface (do NOT silently deploy) a vetted snapshot older than PR HEAD. We
    # deliberately promote the vetted snapshot, not the live PR HEAD - newer
    # commits are unvetted and must not run - but the operator must know when
    # what deploys is not their latest push.
    pr_head_sha="$(printf '%s' "$pr_json" | jq -r '.head.sha // empty')"
    if [[ -n "$pr_head_sha" && "$pr_head_sha" != "$PR_SHA" ]]; then
        echo "WARN: PR #${PR_NUM} HEAD is ${pr_head_sha}, but the vetted copy-pr-bot"
        echo "      snapshot (pull-request/${PR_NUM}) is ${PR_SHA}. Promoting the VETTED"
        echo "      snapshot; to deploy newer commits, have them re-vetted (/ok to test)."
        if [[ "${NVCM_PROMOTE_REQUIRE_PR_HEAD:-false}" = "true" ]]; then
            echo "ERROR: NVCM_PROMOTE_REQUIRE_PR_HEAD=true and the snapshot lags PR HEAD." >&2
            exit 1
        fi
    fi
elif [[ "${NVCM_PROMOTE_ALLOW_UNVERIFIED_PR_STATE:-false}" = "true" ]]; then
    echo "WARN: could not query GitHub PR state; NVCM_PROMOTE_ALLOW_UNVERIFIED_PR_STATE=true set, continuing."
else
    # Fail closed: don't promote a possibly-closed PR just because GitHub was
    # unreachable. Operator can explicitly override for a GitHub outage.
    echo "ERROR: could not confirm PR #${PR_NUM} is open (GitHub unreachable or rate-limited)." >&2
    echo "Re-run when GitHub is reachable, or set NVCM_PROMOTE_ALLOW_UNVERIFIED_PR_STATE=true to override."
    exit 1
fi
bash "$(dirname "$0")/pr_ref_guard.sh" "$PR_REF" "$PR_SHA"

# -----------------------------------------------------------------------------
# Reuse an existing successful build for this exact ref+SHA, if allowed.
# -----------------------------------------------------------------------------
BUILD_PIPELINE_ID=""
if [[ "${NVCM_PROMOTE_REUSE_BUILD:-true}" != "false" ]]; then
    # Consider several recent successes, not just the newest: a pipeline with a
    # disallowed source would be rejected by the provenance gate below, which
    # would dead-end the promote instead of falling through to a fresh trigger.
    BUILD_PIPELINE_ID="$(api_get "${api}/pipelines?ref=$(printf '%s' "$PR_REF" | sed 's|/|%2F|g')&sha=${PR_SHA}&status=success&order_by=id&sort=desc&per_page=20" \
        | jq -r --argjson allowed "$allowed_build_sources" \
            '[.[] | select(.source as $s | $allowed | index($s))] | sort_by(.id) | last | .id // empty')"
    if [[ -n "$BUILD_PIPELINE_ID" ]]; then
        echo "Found existing successful build pipeline ${BUILD_PIPELINE_ID} for ${PR_SHA}; will verify its artifacts."
    fi
fi

# -----------------------------------------------------------------------------
# Otherwise trigger a fresh build on the pull-request ref and poll it.
# Uses a pipeline trigger token (NVCM_BUILD_TRIGGER_TOKEN): GitLab returns 422
# for a job token triggering its own project. NO variables are passed.
# -----------------------------------------------------------------------------
if [[ -z "$BUILD_PIPELINE_ID" ]]; then
    : "${NVCM_BUILD_TRIGGER_TOKEN:?NVCM_BUILD_TRIGGER_TOKEN required to trigger a build (Settings > CI/CD > Pipeline triggers)}"
    echo "Triggering build pipeline on ${PR_REF}..."
    # No `-f`: it suppresses the response body on an HTTP error and, under
    # `set -e`, aborts before the diagnostics below can run. GitLab puts the
    # actual reason (e.g. "No stages / jobs for this pipeline") in the body, so
    # capture status and body and always surface them.
    # A pipeline TRIGGER token, not CI_JOB_TOKEN: GitLab rejects a job token
    # triggering a pipeline in its own project (HTTP 422). A trigger token is
    # also the tighter credential - it can only start pipelines, nothing else.
    # Still no variables are passed, so nothing leaks into the untrusted build.
    trigger_raw="$(curl -sS --max-time 30 -X POST -w '\n%{http_code}' \
        -F "token=${NVCM_BUILD_TRIGGER_TOKEN}" \
        -F "ref=${PR_REF}" \
        "${api}/trigger/pipeline" || true)"
    trigger_http="$(printf '%s' "$trigger_raw" | tail -n 1)"
    trigger_response="$(printf '%s' "$trigger_raw" | sed '$d')"
    BUILD_PIPELINE_ID="$(printf '%s' "$trigger_response" | jq -r '.id // empty' 2>/dev/null || true)"
    if [[ -z "$BUILD_PIPELINE_ID" ]]; then
        echo "ERROR: failed to trigger build pipeline (HTTP ${trigger_http:-000}):" >&2
        printf '%s\n' "$trigger_response"
        echo ""
        echo "Common causes:"
        echo "  - 'No stages / jobs for this pipeline': nothing matched on ${PR_REF}."
        echo "    The PR branch predates the pr-build CI definitions - rebase it onto main."
        echo "  - 403/404: several possible causes - NVCM_BUILD_TRIGGER_TOKEN may be"
        echo "    invalid, revoked, or from another project, or ${PR_REF} may not"
        echo "    exist or not be accessible. Check Settings > CI/CD > Pipeline"
        echo "    triggers, and confirm the ref exists on the mirror."
        echo "  - 'Insufficient permissions': the trigger token lacks access to ${PR_REF}."
        exit 1
    fi
    echo "Build pipeline: ${CI_PROJECT_URL}/-/pipelines/${BUILD_PIPELINE_ID}"

    elapsed=0
    while :; do
        status="$(api_get "${api}/pipelines/${BUILD_PIPELINE_ID}" | jq -r '.status')"
        case "$status" in
            success)
                echo "Build pipeline ${BUILD_PIPELINE_ID} succeeded."
                break
                ;;
            failed|canceled|skipped)
                echo "ERROR: build pipeline ${BUILD_PIPELINE_ID} ended with status '${status}'." >&2
                echo "See ${CI_PROJECT_URL}/-/pipelines/${BUILD_PIPELINE_ID}"
                exit 1
                ;;
            *)
                if [[ "$elapsed" -ge "$poll_timeout" ]]; then
                    echo "ERROR: timed out after ${poll_timeout}s waiting for build pipeline ${BUILD_PIPELINE_ID} (status: ${status})." >&2
                    exit 1
                fi
                echo "Build pipeline ${BUILD_PIPELINE_ID} status: ${status} (${elapsed}s elapsed)"
                sleep "$poll_interval"
                elapsed=$((elapsed + poll_interval))
                ;;
        esac
    done
fi

# -----------------------------------------------------------------------------
# Trusted provenance gate. GitLab records the exact commit and ref a pipeline
# ran on; assert the build pipeline ran on the PR HEAD we resolved and guarded.
# This is the ONLY provenance check that matters: it uses GitLab metadata, not
# any file the untrusted build produced (which the PR author fully controls).
# -----------------------------------------------------------------------------
build_pipeline_json="$(api_get "${api}/pipelines/${BUILD_PIPELINE_ID}")"
build_sha="$(printf '%s' "$build_pipeline_json" | jq -r '.sha')"
build_ref="$(printf '%s' "$build_pipeline_json" | jq -r '.ref')"
build_status="$(printf '%s' "$build_pipeline_json" | jq -r '.status')"
build_source="$(printf '%s' "$build_pipeline_json" | jq -r '.source')"
if [[ "$build_sha" != "$PR_SHA" || "$build_ref" != "$PR_REF" || "$build_status" != "success" ]]; then
    echo "ERROR: build pipeline ${BUILD_PIPELINE_ID} provenance mismatch." >&2
    echo "  got ref=${build_ref} sha=${build_sha} status=${build_status}"
    echo "  expected ref=${PR_REF} sha=${PR_SHA} status=success"
    echo "Re-run with NVCM_PROMOTE_REUSE_BUILD=false to force a fresh build."
    exit 1
fi
if ! printf '%s' "$allowed_build_sources" \
    | jq -e --arg s "$build_source" 'index($s) != null' >/dev/null; then
    echo "ERROR: build pipeline ${BUILD_PIPELINE_ID} has disallowed source '${build_source}'." >&2
    echo "Expected a deliberately triggered pipeline ($(printf '%s' "$allowed_build_sources" | jq -r 'join(", ")'))."
    exit 1
fi
echo "Provenance OK: successful ${build_source} pipeline ${BUILD_PIPELINE_ID} ran on ${PR_REF}@${PR_SHA}"

# -----------------------------------------------------------------------------
# Collect the six pr-build-image job ids and confirm artifacts are usable.
# -----------------------------------------------------------------------------
jobs_json="$(api_get "${api}/pipelines/${BUILD_PIPELINE_ID}/jobs?per_page=100")"

{
    echo "PR_NUM=${PR_NUM}"
    echo "PR_REF=${PR_REF}"
    echo "PR_SHA=${PR_SHA}"
    echo "PR_SHORT_SHA=${PR_SHORT_SHA}"
    echo "PROMOTE_VERSION=${PROMOTE_VERSION}"
    echo "BUILD_PIPELINE_ID=${BUILD_PIPELINE_ID}"
} > promote.env

now_epoch="$(date -u +%s)"
while IFS='|' read -r target image; do
    job_name="pr-build-image: [${target}, ${image}]"
    job_json="$(printf '%s' "$jobs_json" | jq -c --arg name "$job_name" '[.[] | select(.name == $name and .status == "success")] | sort_by(.id) | last // empty')"
    if [[ -z "$job_json" || "$job_json" = "null" ]]; then
        echo "ERROR: no successful '${job_name}' job in pipeline ${BUILD_PIPELINE_ID}." >&2
        exit 1
    fi
    job_id="$(printf '%s' "$job_json" | jq -r '.id')"
    expires_at="$(printf '%s' "$job_json" | jq -r '.artifacts_expire_at // empty')"
    if [[ -n "$expires_at" ]]; then
        expire_epoch="$(date -u -d "$expires_at" +%s 2>/dev/null || date -u -D "%Y-%m-%dT%H:%M:%S" -d "${expires_at%%.*}" +%s 2>/dev/null || echo 0)"
        if [[ "$expire_epoch" != "0" && "$expire_epoch" -le "$now_epoch" ]]; then
            echo "ERROR: artifacts of job ${job_id} (${job_name}) have expired." >&2
            echo "Re-run with NVCM_PROMOTE_REUSE_BUILD=false to force a fresh build."
            exit 1
        fi
    fi
    key="$(printf '%s' "$image" | tr 'a-z-' 'A-Z_')"
    echo "BUILD_JOB_ID_${key}=${job_id}" >> promote.env
    echo "  ${job_name} -> job ${job_id}"
done <<EOF
${matrix_entries}
EOF

# The chart is packaged (secret-free) alongside the images; capture its job id
# so the promote pipeline can download the .tgz and publish it without ever
# rebuilding from PR source.
chart_job_id="$(printf '%s' "$jobs_json" | jq -r '[.[] | select(.name == "pr-build-chart" and .status == "success")] | sort_by(.id) | last | .id // empty')"
if [[ -z "$chart_job_id" ]]; then
    echo "ERROR: no successful 'pr-build-chart' job in pipeline ${BUILD_PIPELINE_ID}." >&2
    exit 1
fi
echo "CHART_BUILD_JOB_ID=${chart_job_id}" >> promote.env
echo "  pr-build-chart -> job ${chart_job_id}"

echo "Build stage resolved:"
cat promote.env
