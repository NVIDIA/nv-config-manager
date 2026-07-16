#!/usr/bin/env bash
# Guard against building or promoting a stale pull-request/<n> SHA.
#
# The mirror replicates copy-pr-bot's pull-request/<n> branches from GitHub
# with pull-mirroring lag, and a PR can gain commits (or close) between the
# moment a pipeline is scheduled and the moment its jobs run. Any job acting
# on a pull-request ref calls this to confirm the ref still exists on the
# mirror and still points at the SHA being built/promoted, with a best-effort
# cross-check against upstream GitHub.
#
# Usage: pr_ref_guard.sh [ref] [expected-sha]
#   ref          defaults to $CI_COMMIT_REF_NAME
#   expected-sha defaults to $CI_COMMIT_SHA
#
# The mirror check uses $CI_REPOSITORY_URL, which embeds CI_JOB_TOKEN. That
# token is NOT read-only, but it is the same token the runner already uses to
# check out the repo, and it carries no protected/registry credentials. The
# optional GitHub cross-check is unauthenticated and is skipped in the untrusted
# build stage (NVCM_PR_GUARD_SKIP_GITHUB=1); the authoritative freshness and
# provenance checks run in the protected promote consumer.
set -euo pipefail

ref="${1:-${CI_COMMIT_REF_NAME:?ref argument or CI_COMMIT_REF_NAME required}}"
expected="${2:-${CI_COMMIT_SHA:?expected-sha argument or CI_COMMIT_SHA required}}"
github_repo="${NVCM_UPSTREAM_GITHUB_REPO:-NVIDIA/nv-config-manager}"

echo "Checking that ${ref} still points at ${expected}..."

mirror_head="$(git ls-remote "$CI_REPOSITORY_URL" "refs/heads/${ref}" | cut -f1)"
if [ -z "$mirror_head" ]; then
    echo "ERROR: ${ref} no longer exists on the mirror (PR closed or merged?)"
    exit 1
fi
if [ "$mirror_head" != "$expected" ]; then
    echo "ERROR: stale SHA - mirror ${ref} is at ${mirror_head}, expected ${expected}."
    echo "The PR gained commits since this run was scheduled; re-run against the new HEAD."
    exit 1
fi

# GitHub cross-check: best-effort detection of the mirror lagging behind
# copy-pr-bot's pull-request/<n> branch. It does NOT compare against the PR's
# live HEAD (that divergence is surfaced in promote_build_pipeline.sh).
#
# Skipped in the untrusted build stage (NVCM_PR_GUARD_SKIP_GITHUB=1): those jobs
# run many times per pipeline, and unauthenticated GitHub calls behind a shared
# NAT quickly exhaust the 60 req/hour limit (then degrade to warn-and-succeed).
# The authoritative freshness + provenance checks run in the protected promote
# consumer, which can make authenticated calls.
if [ "${NVCM_PR_GUARD_SKIP_GITHUB:-0}" = "1" ] || [ "${NVCM_PR_GUARD_SKIP_GITHUB:-}" = "true" ]; then
    echo "OK: ${ref} is current at ${expected} (mirror check only; GitHub cross-check skipped)"
    exit 0
fi

# Unauthenticated. Inspect the HTTP status so a definitive 404 (branch gone
# upstream - the mirror copy is an orphan) fails, while inconclusive failures
# (network, rate limit, 5xx) only warn. A confirmed SHA mismatch on a 200 fails.
github_response="$(curl -sS --max-time 10 -w '\n%{http_code}' \
    "https://api.github.com/repos/${github_repo}/branches/${ref}" 2>/dev/null || true)"
github_status="$(printf '%s' "$github_response" | tail -n 1)"
github_body="$(printf '%s' "$github_response" | sed '$d')"
case "$github_status" in
    200)
        github_head="$(printf '%s' "$github_body" | grep -o '"sha": *"[0-9a-f]\{40\}"' | head -n 1 | grep -o '[0-9a-f]\{40\}' || true)"
        if [ -n "$github_head" ] && [ "$github_head" != "$expected" ]; then
            echo "ERROR: upstream GitHub ${ref} is at ${github_head}; the mirror copy is stale."
            echo "Wait for pull-mirroring to sync, then re-run."
            exit 1
        fi
        ;;
    404)
        echo "ERROR: ${ref} does not exist on GitHub (PR closed/merged or copy-pr-bot"
        echo "branch removed); the mirror copy is an orphaned stale branch. Refusing."
        exit 1
        ;;
    *)
        echo "WARN: could not verify ${ref} against GitHub (HTTP ${github_status:-000}: network, rate limit, or API error); mirror check passed."
        ;;
esac

echo "OK: ${ref} is current at ${expected}"
