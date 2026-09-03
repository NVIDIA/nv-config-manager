#!/usr/bin/env bash
# Offline state-machine tests for wait_for_argocd.sh. They cover stale-operation
# termination, exact sync, bounded rejected syncs, and fatal HTTP responses.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
test_root="$(mktemp -d)"
trap 'rm -rf "$test_root"' EXIT
mkdir -p "${test_root}/bin" "${test_root}/project"

expected_chart='0.0.0-pr999.01234567'
expected_git='0123456789abcdef0123456789abcdef01234567'
old_git='aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
{
    printf 'ARGOCD_APPLICATION=nv-config-manager-test\n'
    printf 'ARGOCD_EXPECTED_CHART_REVISION=%s\n' "$expected_chart"
    printf 'ARGOCD_EXPECTED_GIT_REVISION=%s\n' "$expected_git"
} > "${test_root}/project/deploy.env"

cat > "${test_root}/bin/curl" <<'MOCK_CURL'
#!/usr/bin/env bash
set -euo pipefail
method=GET
body=''
url=''
output_file=/dev/stdout
write_out=''
config_file=''
while (( $# > 0 )); do
    case "$1" in
        -X)
            shift
            method="$1"
            ;;
        -H)
            shift
            if [[ "$1" == Authorization:* ]]; then
                echo 'authorization header exposed in curl argv' >&2
                exit 1
            fi
            ;;
        --config)
            shift
            config_file="$1"
            ;;
        --retry|--retry-delay|--retry-max-time|--connect-timeout|--max-time)
            shift
            ;;
        --output|-o)
            shift
            output_file="$1"
            ;;
        --write-out|-w)
            shift
            write_out="$1"
            ;;
        --data-binary)
            shift
            body="$1"
            ;;
        http://*|https://*)
            url="$1"
            ;;
    esac
    shift
done

[[ -n "$config_file" && -f "$config_file" ]]
grep -Fqx "header = \"Authorization: Bearer ${MOCK_EXPECTED_TOKEN}\"" "$config_file"

respond() {
    local status="$1" response_body="${2:-}"
    printf '%s' "$response_body" > "$output_file"
    if [[ -n "$write_out" ]]; then
        printf '%s' "$status"
    fi
}

state="$(cat "${MOCK_ARGO_ROOT}/state")"
automated_prune="${MOCK_AUTOMATED_PRUNE:-true}"
case "${method}:${url}" in
    GET:*/api/v1/applications/nv-config-manager-test\?appNamespace=argocd\&project=kiwi)
        get_attempts="$(cat "${MOCK_ARGO_ROOT}/get-attempts")"
        printf '%s' "$((get_attempts + 1))" > "${MOCK_ARGO_ROOT}/get-attempts"
        if [[ -n "${MOCK_GET_HTTP_STATUS:-}" ]]; then
            respond "$MOCK_GET_HTTP_STATUS" '{"message":"forced GET failure"}'
            exit 0
        fi
        if [[ "$state" == 2 && "${MOCK_CONVERGE_AFTER_REJECTED_SYNCS:-false}" == true \
              && "$(cat "${MOCK_ARGO_ROOT}/post-attempts")" -ge 2 ]]; then
            state=3
            printf '3' > "${MOCK_ARGO_ROOT}/state"
        fi
        case "$state" in
            0)
                response_body="$(jq -cn \
                    --arg chart "$MOCK_EXPECTED_CHART" --arg git "$MOCK_EXPECTED_GIT" --arg old "$MOCK_OLD_GIT" --argjson prune "$automated_prune" \
                    '{spec:{syncPolicy:{automated:{prune:$prune}}},status:{sync:{status:"OutOfSync",revisions:[$chart,$git]},health:{status:"Progressing"},operationState:{phase:"Running",operation:{sync:{revisions:["0.0.0-pr998.deadbeef",$old]}}},resources:[]}}')"
                ;;
            1)
                response_body="$(jq -cn \
                    --arg chart "$MOCK_EXPECTED_CHART" --arg git "$MOCK_EXPECTED_GIT" --arg old "$MOCK_OLD_GIT" --argjson prune "$automated_prune" \
                    '{spec:{syncPolicy:{automated:{prune:$prune}}},status:{sync:{status:"OutOfSync",revisions:[$chart,$git]},health:{status:"Progressing"},operationState:{phase:"Terminating",operation:{sync:{revisions:["0.0.0-pr998.deadbeef",$old]}}},resources:[]}}')"
                printf '2' > "${MOCK_ARGO_ROOT}/state"
                ;;
            2)
                response_body="$(jq -cn \
                    --arg chart "$MOCK_EXPECTED_CHART" --arg git "$MOCK_EXPECTED_GIT" --arg old "$MOCK_OLD_GIT" --argjson prune "$automated_prune" \
                    '{spec:{syncPolicy:{automated:{prune:$prune}}},status:{sync:{status:"OutOfSync",revisions:[$chart,$git]},health:{status:"Progressing"},operationState:{phase:"Failed",operation:{sync:{revisions:["0.0.0-pr998.deadbeef",$old]}}},resources:[]}}')"
                ;;
            3)
                response_body="$(jq -cn \
                    --arg chart "$MOCK_EXPECTED_CHART" --arg git "$MOCK_EXPECTED_GIT" --argjson prune "$automated_prune" \
                    '{spec:{syncPolicy:{automated:{prune:$prune}}},status:{sync:{status:"Synced",revisions:[$chart,$git]},health:{status:"Healthy"},operationState:{phase:"Succeeded",operation:{sync:{revisions:[$chart,$git]}}},resources:[]}}')"
                ;;
        esac
        respond 200 "$response_body"
        ;;
    DELETE:*/api/v1/applications/nv-config-manager-test/operation\?appNamespace=argocd\&project=kiwi)
        [[ "$state" == 0 ]]
        delete_attempts="$(cat "${MOCK_ARGO_ROOT}/delete-attempts")"
        delete_attempts=$((delete_attempts + 1))
        printf '%s' "$delete_attempts" > "${MOCK_ARGO_ROOT}/delete-attempts"
        if [[ "${MOCK_FAIL_FIRST_DELETE:-false}" == true && "$delete_attempts" == 1 ]]; then
            respond 409 '{"message":"transient termination conflict"}'
            exit 0
        fi
        if [[ -n "${MOCK_DELETE_HTTP_STATUS:-}" ]]; then
            respond "$MOCK_DELETE_HTTP_STATUS" '{"message":"forced termination failure"}'
            exit 0
        fi
        printf '1' > "${MOCK_ARGO_ROOT}/state"
        respond 200 '{}'
        ;;
    POST:*/api/v1/applications/nv-config-manager-test/sync\?appNamespace=argocd\&project=kiwi)
        if [[ "$state" == 1 ]]; then
            printf 'yes' > "${MOCK_ARGO_ROOT}/synced-while-terminating"
            respond 409 '{"message":"operation is terminating"}'
            exit 0
        fi
        [[ "$state" == 2 ]]
        jq -e \
            --arg chart "$MOCK_EXPECTED_CHART" --arg git "$MOCK_EXPECTED_GIT" --argjson prune "$automated_prune" \
            '.project == "kiwi" and .prune == $prune and .revisions == [$chart, $git] and .sourcePositions == [1, 2]' \
            >/dev/null <<<"$body"
        post_attempts="$(cat "${MOCK_ARGO_ROOT}/post-attempts")"
        post_attempts=$((post_attempts + 1))
        printf '%s' "$post_attempts" > "${MOCK_ARGO_ROOT}/post-attempts"
        if [[ -n "${MOCK_SYNC_HTTP_STATUS:-}" ]]; then
            respond "$MOCK_SYNC_HTTP_STATUS" '{"message":"forced sync failure"}'
            exit 0
        fi
        if [[ "${MOCK_ALWAYS_REJECT_SYNC:-false}" == "true" || "$post_attempts" == 1 ]]; then
            respond 409 '{"message":"sync conflict"}'
            exit 0
        fi
        printf '3' > "${MOCK_ARGO_ROOT}/state"
        respond 200 '{}'
        ;;
    *)
        echo "unexpected fake curl request: ${method}:${url}" >&2
        exit 1
        ;;
esac
MOCK_CURL
chmod +x "${test_root}/bin/curl"

reset_mock() {
    printf '%s' "${1:-0}" > "${test_root}/state"
    printf '0' > "${test_root}/get-attempts"
    printf '0' > "${test_root}/delete-attempts"
    printf '0' > "${test_root}/post-attempts"
    rm -f "${test_root}/synced-while-terminating"
}

export PATH="${test_root}/bin:${PATH}"
export MOCK_ARGO_ROOT="$test_root"
export MOCK_EXPECTED_CHART="$expected_chart"
export MOCK_EXPECTED_GIT="$expected_git"
export MOCK_OLD_GIT="$old_git"
export MOCK_EXPECTED_TOKEN='eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJwcm9qZWN0In0.signature_123'
export CI_PROJECT_DIR="${test_root}/project"
export NVCM_ARGOCD_SERVER='https://argocd.example.test'
export NVCM_ARGOCD_AUTH_TOKEN="$MOCK_EXPECTED_TOKEN"
export NVCM_ARGOCD_POLL_INTERVAL=0
export NVCM_ARGOCD_ALLOW_ZERO_POLL_INTERVAL_FOR_TESTS=true
export NVCM_ARGOCD_SYNC_TIMEOUT=10
export NVCM_ARGOCD_MAX_SYNC_ATTEMPTS=2

if NVCM_ARGOCD_SERVER='http://argocd.example.test' bash "${script_dir}/wait_for_argocd.sh" >/dev/null 2>&1; then
    echo 'ERROR: health gate accepted a non-HTTPS ArgoCD server' >&2
    exit 1
fi
if NVCM_ARGOCD_ALLOW_ZERO_POLL_INTERVAL_FOR_TESTS=false bash "${script_dir}/wait_for_argocd.sh" >/dev/null 2>&1; then
    echo 'ERROR: health gate accepted a zero poll interval outside test mode' >&2
    exit 1
fi

# Authentication, authorization, and addressing failures are configuration
# errors, not convergence delays: each must stop after the first response.
for fatal_get_status in 401 404; do
    reset_mock 0
    if fatal_output="$(MOCK_GET_HTTP_STATUS="$fatal_get_status" bash "${script_dir}/wait_for_argocd.sh" 2>&1)"; then
        echo "ERROR: health gate accepted fatal GET HTTP ${fatal_get_status}" >&2
        exit 1
    fi
    grep -q "HTTP ${fatal_get_status}" <<<"$fatal_output"
    [[ "$(cat "${test_root}/get-attempts")" == 1 ]]
done

reset_mock 2
if fatal_output="$(MOCK_SYNC_HTTP_STATUS=403 bash "${script_dir}/wait_for_argocd.sh" 2>&1)"; then
    echo 'ERROR: health gate accepted a forbidden sync response' >&2
    exit 1
fi
grep -q 'HTTP 403' <<<"$fatal_output"
[[ "$(cat "${test_root}/post-attempts")" == 1 ]]

# Every rejected POST consumes an attempt. Once the configured limit is
# reached, keep observing without sending a third mutation. Convergence by an
# ArgoCD-owned operation must still satisfy the gate.
reset_mock 2
MOCK_ALWAYS_REJECT_SYNC=true MOCK_CONVERGE_AFTER_REJECTED_SYNCS=true \
    bash "${script_dir}/wait_for_argocd.sh" >/dev/null
[[ "$(cat "${test_root}/post-attempts")" == 2 ]]

# Without external convergence, exhausting the sync mutation budget keeps
# polling until the convergence deadline and still sends no third mutation.
reset_mock 2
if bounded_output="$(NVCM_ARGOCD_SYNC_TIMEOUT=2 NVCM_ARGOCD_POLL_INTERVAL=1 MOCK_ALWAYS_REJECT_SYNC=true bash "${script_dir}/wait_for_argocd.sh" 2>&1)"; then
    echo 'ERROR: health gate unexpectedly converged while syncs were rejected' >&2
    exit 1
fi
grep -q 'continuing observation without further mutations' <<<"$bounded_output"
grep -q 'timed out waiting for exact-revision ArgoCD convergence' <<<"$bounded_output"
[[ "$(cat "${test_root}/post-attempts")" == 2 ]]

# A rejected DELETE does not consume the successful-termination budget. With a
# limit of one, the next termination succeeds and the gate still converges.
reset_mock 0
NVCM_ARGOCD_MAX_STALE_TERMINATIONS=1 MOCK_FAIL_FIRST_DELETE=true \
    bash "${script_dir}/wait_for_argocd.sh" >/dev/null
[[ "$(cat "${test_root}/state")" == 3 ]]
[[ "$(cat "${test_root}/delete-attempts")" == 2 ]]

# The explicit sync must follow the Application's pruning policy rather than
# broadening it. This mock Application disables pruning and verifies the POST.
reset_mock 2
MOCK_AUTOMATED_PRUNE=false bash "${script_dir}/wait_for_argocd.sh" >/dev/null
[[ "$(cat "${test_root}/state")" == 3 ]]
[[ "$(cat "${test_root}/post-attempts")" == 2 ]]

# Full success path: stale Running -> Terminating -> Failed, one rejected
# exact sync, one accepted exact sync, then exact Healthy/Synced convergence.
reset_mock 0
bash "${script_dir}/wait_for_argocd.sh"
[[ "$(cat "${test_root}/state")" == 3 ]]
[[ "$(cat "${test_root}/delete-attempts")" == 1 ]]
[[ "$(cat "${test_root}/post-attempts")" == 2 ]]
[[ ! -f "${test_root}/synced-while-terminating" ]]
echo 'ArgoCD exact-revision health gate state-machine tests passed.'
