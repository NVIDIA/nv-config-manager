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
# Uses only $CI_REPOSITORY_URL (embeds the read-only job token, available on
# unprotected refs) and unauthenticated GitHub API access - no secrets.
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

# Best-effort mirror-lag check: compare the mirror's copy to GitHub's copy of
# the SAME vetted copy-pr-bot branch (pull-request/<n>). This catches the mirror
# lagging behind copy-pr-bot; it intentionally does NOT compare against the PR's
# live HEAD (that divergence is surfaced in promote_build_pipeline.sh, and
# building unvetted PR-HEAD commits is deliberately out of scope). Unauthenticated.
# Inspect the HTTP status so a definitive 404 (branch gone upstream - the mirror
# copy is an orphan) fails, while inconclusive failures (network, rate limit,
# 5xx) only warn. A confirmed SHA mismatch on a 200 fails.
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
