#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
final_validator="${repo_root}/.gitlab/ci/scripts/validate_promote_request.sh"
source_validator="${repo_root}/.gitlab/ci/scripts/validate_promote_source_pipeline.sh"
webhook_fixture="${repo_root}/.gitlab/ci/scripts/tests/fixtures/push_webhook.json"
test_dir="$(mktemp -d)"
trap 'rm -rf "$test_dir"' EXIT

pr_sha="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
main_sha="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"

# The validators call only GitLab read endpoints. Return deterministic API
# metadata so the authorization boundary can be tested without network access.
curl() {
    local url="${!#}"
    case "$url" in
        */api/v4/job)
            printf '{"source":"%s","pipeline":{"id":300,"ref":"main"},"user":{"id":%s}}\n' \
                "${MOCK_CURRENT_SOURCE}" "${MOCK_CURRENT_USER_ID}"
            ;;
        */projects/7/pipelines\?ref=*)
            printf '[{"id":100,"ref":"pull-request/123","sha":"%s","source":"push"}]\n' \
                "$pr_sha"
            ;;
        */projects/7/pipelines/100)
            printf '{"ref":"pull-request/123","sha":"%s","status":"success","source":"push","user":{"id":7}}\n' \
                "$pr_sha"
            ;;
        */projects/7/repository/branches/pull-request%2F123)
            printf '{"commit":{"id":"%s"}}\n' "$pr_sha"
            ;;
        */projects/7/pipelines/200/jobs\?per_page=100)
            printf '[{"id":202,"name":"test-promote-request-validate","status":"success"}]\n'
            ;;
        */projects/7/pipelines/200)
            printf '{"ref":"main","sha":"%s","status":"running","source":"trigger"}\n' \
                "$main_sha"
            ;;
        */projects/7/pipelines/300/metadata)
            printf '{}\n'
            ;;
        */projects/7/jobs/202/artifacts/promote-request.env\?job_token=*)
            printf 'VERIFIED_PROMOTE_PR=%s\nVERIFIED_PROMOTE_PR_SHA=%s\nVERIFIED_PROMOTE_BUILD_PIPELINE_ID=100\n' \
                "${MOCK_VERIFIED_PR:-123}" "$pr_sha"
            ;;
        */projects/7/jobs/201)
            printf '{"name":"promote-to-test","status":"running","pipeline":{"id":200,"ref":"main","sha":"%s"},"user":{"id":42}}\n' \
                "$main_sha"
            ;;
        */projects/7)
            printf '{"default_branch":"main"}\n'
            ;;
        *)
            echo "unexpected curl URL: $url" >&2
            return 1
            ;;
    esac
}
export -f curl
export pr_sha main_sha

run_source_validator() (
    cd "$test_dir"
    export MOCK_CURRENT_SOURCE=trigger MOCK_CURRENT_USER_ID=7
    export CI_JOB_TOKEN=job-token CI_API_V4_URL=https://gitlab.example/api/v4 CI_PROJECT_ID=7
    export NVCM_MIRROR_API_TOKEN=read-token TRIGGER_PAYLOAD="$webhook_fixture"
    bash "$source_validator"
    grep -qx 'VERIFIED_PROMOTE_PR=123' promote-request.env
    grep -qx "VERIFIED_PROMOTE_PR_SHA=${pr_sha}" promote-request.env
    grep -qx 'VERIFIED_PROMOTE_BUILD_PIPELINE_ID=100' promote-request.env
)

run_final_validator() (
    export MOCK_CURRENT_SOURCE=pipeline MOCK_CURRENT_USER_ID=42
    export CI_JOB_TOKEN=job-token CI_API_V4_URL=https://gitlab.example/api/v4 CI_PROJECT_ID=7
    export NVCM_MIRROR_API_TOKEN=read-token
    export NVCM_PROMOTE_PR=123 NVCM_PROMOTE_PR_SHA="$pr_sha"
    export NVCM_PROMOTE_BUILD_PIPELINE_ID=100 NVCM_PROMOTE_ENV=test
    export NVCM_PROMOTE_SOURCE_PIPELINE_ID=200 NVCM_PROMOTE_SOURCE_JOB_ID=201
    export NVCM_PROMOTE_SOURCE_REF=main NVCM_PROMOTE_SOURCE_SHA="$main_sha"
    export NVCM_PROMOTE_SOURCE_ENVIRONMENT="${TEST_SOURCE_ENVIRONMENT:-test}"
    export NVCM_PROMOTE_SOURCE_ENVIRONMENT_ACTION="${TEST_SOURCE_ACTION:-prepare}"
    export MOCK_VERIFIED_PR="${TEST_VERIFIED_PR:-123}"
    bash "$final_validator"
)

assert_final_rejected() {
    local expected="$1" output
    if output="$(run_final_validator 2>&1)"; then
        echo "expected final validator to reject request" >&2
        exit 1
    fi
    grep -Fq "$expected" <<<"$output"
}

run_source_validator
run_final_validator
TEST_VERIFIED_PR=999 assert_final_rejected "verified request PR does not match"
TEST_SOURCE_ENVIRONMENT=test01 assert_final_rejected "does not match 'test'"
TEST_SOURCE_ACTION=start assert_final_rejected "action is not 'prepare'"

echo "validate promote request tests passed"
