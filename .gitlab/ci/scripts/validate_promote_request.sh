#!/usr/bin/env bash
# Validate how a protected test-environment promotion was started.
#
# Promotions must originate from the matching manual job on a
# pull-request/<n> pipeline for the exact vetted SHA being promoted. The checks
# use GitLab API metadata rather than trusting the variables supplied by the
# untrusted PR pipeline.
#
# Output: promote-request.env, consumed by promote_build_pipeline.sh.
set -euo pipefail

: "${CI_JOB_TOKEN:?CI_JOB_TOKEN is required}"
: "${CI_API_V4_URL:?CI_API_V4_URL is required}"
: "${CI_PROJECT_ID:?CI_PROJECT_ID is required}"
: "${NVCM_MIRROR_API_TOKEN:?NVCM_MIRROR_API_TOKEN (read_api) is required}"
: "${NVCM_PROMOTE_PR:?NVCM_PROMOTE_PR is required}"
: "${NVCM_PROMOTE_ENV:?NVCM_PROMOTE_ENV is required}"

api="${CI_API_V4_URL}/projects/${CI_PROJECT_ID}"

api_get() {
    curl -fsS --max-time 30 -H "PRIVATE-TOKEN: ${NVCM_MIRROR_API_TOKEN}" "$@"
}

fail() {
    echo "ERROR: invalid test-environment promotion request: $*" >&2
    exit 1
}

# /job is authenticated by this job's short-lived token, so its pipeline
# metadata cannot be redirected by overriding a predefined CI variable.
current_job_json="$(curl -fsS --max-time 30 -H "JOB-TOKEN: ${CI_JOB_TOKEN}" "${CI_API_V4_URL}/job")"
request_source="$(printf '%s' "$current_job_json" | jq -r '.source // empty')"
current_ref="$(printf '%s' "$current_job_json" | jq -r '.pipeline.ref // empty')"
current_user_id="$(printf '%s' "$current_job_json" | jq -r '.user.id // empty')"

project_json="$(api_get "$api")"
default_branch="$(printf '%s' "$project_json" | jq -r '.default_branch // empty')"
[[ -n "$default_branch" ]] || fail "GitLab did not report a default branch"
[[ "$current_ref" == "$default_branch" ]] \
    || fail "protected promotion runs on '${current_ref:-unknown}', expected '${default_branch}'"

[[ "$request_source" == "pipeline" ]] \
    || fail "pipeline source '${request_source:-unknown}' is not a PR promotion button"

for key in NVCM_PROMOTE_SOURCE_PIPELINE_ID NVCM_PROMOTE_SOURCE_JOB_ID \
    NVCM_PROMOTE_SOURCE_REF NVCM_PROMOTE_SOURCE_SHA; do
    [[ -n "${!key:-}" ]] || fail "${key} is required for a button-triggered promotion"
done
[[ "$NVCM_PROMOTE_SOURCE_PIPELINE_ID" =~ ^[0-9]+$ ]] \
    || fail "source pipeline id is not numeric"
[[ "$NVCM_PROMOTE_SOURCE_JOB_ID" =~ ^[0-9]+$ ]] \
    || fail "source job id is not numeric"
[[ "$NVCM_PROMOTE_PR" =~ ^[0-9]+$ ]] || fail "PR number is not numeric"
[[ "$NVCM_PROMOTE_SOURCE_REF" == "pull-request/${NVCM_PROMOTE_PR}" ]] \
    || fail "source ref '${NVCM_PROMOTE_SOURCE_REF}' does not match PR #${NVCM_PROMOTE_PR}"
[[ "$NVCM_PROMOTE_SOURCE_SHA" =~ ^[0-9a-f]{40}$ ]] \
    || fail "source SHA is not a full lowercase Git SHA"

case "$NVCM_PROMOTE_ENV" in
    test|test01) ;;
    *) fail "unsupported target environment '${NVCM_PROMOTE_ENV}'" ;;
esac

source_pipeline_json="$(api_get "${api}/pipelines/${NVCM_PROMOTE_SOURCE_PIPELINE_ID}")"
source_pipeline_ref="$(printf '%s' "$source_pipeline_json" | jq -r '.ref // empty')"
source_pipeline_sha="$(printf '%s' "$source_pipeline_json" | jq -r '.sha // empty')"
source_pipeline_status="$(printf '%s' "$source_pipeline_json" | jq -r '.status // empty')"
source_pipeline_source="$(printf '%s' "$source_pipeline_json" | jq -r '.source // empty')"

[[ "$source_pipeline_ref" == "$NVCM_PROMOTE_SOURCE_REF" ]] \
    || fail "source pipeline ref is '${source_pipeline_ref}', expected '${NVCM_PROMOTE_SOURCE_REF}'"
[[ "$source_pipeline_sha" == "$NVCM_PROMOTE_SOURCE_SHA" ]] \
    || fail "source pipeline SHA does not match the button request"
case "$source_pipeline_status" in
    running|success) ;;
    *) fail "source pipeline status is '${source_pipeline_status}'" ;;
esac
[[ "$source_pipeline_source" == "push" ]] \
    || fail "source pipeline was not created by the vetted mirror sync"
source_pipeline_user_id="$(printf '%s' "$source_pipeline_json" | jq -r '.user.id // empty')"

source_job_json="$(api_get "${api}/jobs/${NVCM_PROMOTE_SOURCE_JOB_ID}")"
source_job_name="$(printf '%s' "$source_job_json" | jq -r '.name // empty')"
source_job_pipeline_id="$(printf '%s' "$source_job_json" | jq -r '.pipeline.id // empty')"
source_job_ref="$(printf '%s' "$source_job_json" | jq -r '.pipeline.ref // empty')"
source_job_sha="$(printf '%s' "$source_job_json" | jq -r '.pipeline.sha // .commit.id // empty')"
source_job_status="$(printf '%s' "$source_job_json" | jq -r '.status // empty')"
source_job_user_id="$(printf '%s' "$source_job_json" | jq -r '.user.id // empty')"

[[ "$source_job_name" == "promote-to-${NVCM_PROMOTE_ENV}" ]] \
    || fail "source job is '${source_job_name}', expected 'promote-to-${NVCM_PROMOTE_ENV}'"
[[ "$source_job_pipeline_id" == "$NVCM_PROMOTE_SOURCE_PIPELINE_ID" ]] \
    || fail "source job does not belong to source pipeline ${NVCM_PROMOTE_SOURCE_PIPELINE_ID}"
[[ "$source_job_ref" == "$NVCM_PROMOTE_SOURCE_REF" ]] \
    || fail "source job ref does not match '${NVCM_PROMOTE_SOURCE_REF}'"
[[ "$source_job_sha" == "$NVCM_PROMOTE_SOURCE_SHA" ]] \
    || fail "source job SHA does not match the button request"
case "$source_job_status" in
    running|success) ;;
    *) fail "source job status is '${source_job_status}'" ;;
esac
[[ -n "$source_pipeline_user_id" && -n "$source_job_user_id" && -n "$current_user_id" ]] \
    || fail "GitLab did not report complete pipeline/job user provenance"
[[ "$source_job_user_id" != "$source_pipeline_user_id" ]] \
    || fail "source job was not started by a human promotion action"
[[ "$current_user_id" == "$source_job_user_id" ]] \
    || fail "protected pipeline user does not match the person who pressed the button"

{
    echo "PROMOTE_REQUEST_SOURCE=button"
    echo "PROMOTE_REQUEST_BUILD_PIPELINE_ID=${NVCM_PROMOTE_SOURCE_PIPELINE_ID}"
} > promote-request.env

echo "Promotion button authorized: ${source_job_name} from ${source_pipeline_ref}@${source_pipeline_sha}."
