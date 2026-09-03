#!/usr/bin/env bash
# Block a test-environment promotion until ArgoCD has completed a healthy sync
# of the exact chart version and values-repository commit written by
# write_deploy_state.sh. If an older operation is still running, terminate it
# before starting one exact-revision sync.
set -euo pipefail

: "${CI_PROJECT_DIR:?CI_PROJECT_DIR is required}"
: "${NVCM_ARGOCD_SERVER:?Set NVCM_ARGOCD_SERVER to the ArgoCD API base URL}"
: "${NVCM_ARGOCD_AUTH_TOKEN:?Set NVCM_ARGOCD_AUTH_TOKEN to a protected, masked ArgoCD token}"

deploy_attest="${CI_PROJECT_DIR}/deploy.env"
[[ -f "$deploy_attest" ]] || { echo "ERROR: missing deployment attestation ${deploy_attest}" >&2; exit 1; }

attest() {
    local key="$1" val
    val="$(grep -m1 "^${key}=" "$deploy_attest" | cut -d= -f2- || true)"
    [[ -n "$val" ]] || { echo "ERROR: ${key} missing from deploy.env" >&2; exit 1; }
    printf '%s' "$val"
}

application="$(attest ARGOCD_APPLICATION)"
expected_chart_revision="$(attest ARGOCD_EXPECTED_CHART_REVISION)"
expected_git_revision="$(attest ARGOCD_EXPECTED_GIT_REVISION)"
app_namespace="${NVCM_ARGOCD_APPLICATION_NAMESPACE:-argocd}"
argocd_project="${NVCM_ARGOCD_PROJECT:-kiwi}"
poll_interval="${NVCM_ARGOCD_POLL_INTERVAL:-10}"
timeout="${NVCM_ARGOCD_SYNC_TIMEOUT:-1800}"
max_sync_attempts="${NVCM_ARGOCD_MAX_SYNC_ATTEMPTS:-2}"
max_stale_terminations="${NVCM_ARGOCD_MAX_STALE_TERMINATIONS:-2}"
request_connect_timeout="${NVCM_ARGOCD_CONNECT_TIMEOUT:-10}"
request_timeout="${NVCM_ARGOCD_REQUEST_TIMEOUT:-60}"

for numeric_value in "$poll_interval" "$timeout" "$max_sync_attempts" "$max_stale_terminations" "$request_connect_timeout" "$request_timeout"; do
    [[ "$numeric_value" =~ ^[0-9]+$ ]] || { echo "ERROR: ArgoCD timing/attempt settings must be non-negative integers" >&2; exit 1; }
done
(( poll_interval > 0 && timeout > 0 && max_sync_attempts > 0 && max_stale_terminations > 0 && request_connect_timeout > 0 && request_timeout > 0 )) || {
    echo "ERROR: ArgoCD timing, request bounds, and attempt limits must be greater than zero" >&2
    exit 1
}
if (( timeout > 1800 )); then
    echo "ERROR: NVCM_ARGOCD_SYNC_TIMEOUT must not exceed 1800 seconds so the 35-minute job retains diagnostic headroom" >&2
    exit 1
fi
[[ "$application" =~ ^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$ ]] || { echo "ERROR: invalid ArgoCD application name '${application}'" >&2; exit 1; }
[[ "$app_namespace" =~ ^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$ ]] || { echo "ERROR: invalid ArgoCD application namespace '${app_namespace}'" >&2; exit 1; }
[[ "$argocd_project" =~ ^[a-z0-9]([-a-z0-9.]*[a-z0-9])?$ ]] || { echo "ERROR: invalid ArgoCD project '${argocd_project}'" >&2; exit 1; }
[[ "$expected_git_revision" =~ ^[0-9a-f]{40}$ ]] || { echo "ERROR: expected Git revision is not a full SHA-1" >&2; exit 1; }
[[ "$NVCM_ARGOCD_SERVER" == https://* ]] || { echo "ERROR: NVCM_ARGOCD_SERVER must use https://" >&2; exit 1; }
[[ "$NVCM_ARGOCD_AUTH_TOKEN" =~ ^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$ ]] || {
    echo "ERROR: NVCM_ARGOCD_AUTH_TOKEN must be an ArgoCD JWT" >&2
    exit 1
}

# No individual request may outlive the overall convergence window.
if (( request_timeout > timeout )); then
    request_timeout="$timeout"
fi
if (( request_connect_timeout > request_timeout )); then
    request_connect_timeout="$request_timeout"
fi

argocd_server="${NVCM_ARGOCD_SERVER%/}"
application_url="${argocd_server}/api/v1/applications/${application}"
last_payload=""
umask 077
api_response_file="$(mktemp)"
curl_config_file="$(mktemp)"
printf 'header = "Authorization: Bearer %s"\n' "$NVCM_ARGOCD_AUTH_TOKEN" > "$curl_config_file"
unset NVCM_ARGOCD_AUTH_TOKEN
trap 'rm -f "$api_response_file" "$curl_config_file"' EXIT
readonly fatal_api_error=78

# Execute one logical API request and classify HTTP failures. GETs may use
# curl's transport retry support; mutations are never replayed inside curl
# because their outcome can be ambiguous. The outer state machine observes the
# Application again before deciding whether another bounded mutation is safe.
api_request() {
    local method="$1" suffix="$2" body="$3" output_file="$4" retry_get="$5"
    local http_code curl_status=0
    local -a curl_args=(
        --silent --show-error
        --connect-timeout "$request_connect_timeout"
        --max-time "$request_timeout"
        --output "$output_file"
        --write-out '%{http_code}'
        --config "$curl_config_file"
        -X "$method"
    )
    if [[ "$retry_get" == "true" ]]; then
        curl_args+=(--retry 3 --retry-delay 2 --retry-connrefused --retry-max-time "$request_timeout")
    fi
    if [[ -n "$body" ]]; then
        curl_args+=(-H 'Content-Type: application/json' --data-binary "$body")
    fi
    curl_args+=("${application_url}${suffix}?appNamespace=${app_namespace}&project=${argocd_project}")

    : > "$output_file"
    if http_code="$(curl "${curl_args[@]}")"; then
        curl_status=0
    else
        curl_status=$?
    fi
    if (( curl_status != 0 )); then
        echo "ArgoCD API transport failure (curl exit ${curl_status})." >&2
        return 1
    fi
    if [[ "$http_code" =~ ^2[0-9]{2}$ ]]; then
        return 0
    fi

    case "$http_code" in
        401)
            echo "ERROR: ArgoCD API returned HTTP 401; the promotion token is invalid or expired." >&2
            return "$fatal_api_error"
            ;;
        403)
            echo "ERROR: ArgoCD API returned HTTP 403; the promotion role lacks get/sync access to ${argocd_project}/${application}." >&2
            return "$fatal_api_error"
            ;;
        404)
            echo "ERROR: ArgoCD API returned HTTP 404; verify the application name, namespace, project, and get permission." >&2
            return "$fatal_api_error"
            ;;
        *)
            echo "ArgoCD API returned transient HTTP ${http_code}." >&2
            return 1
            ;;
    esac
}

api_get() {
    api_request GET '' '' "$api_response_file" true
}

api_mutate() {
    local method="$1" suffix="$2" body="${3:-}"
    api_request "$method" "$suffix" "$body" /dev/null false
}

revision_set_matches() {
    local jq_path="$1" payload="$2"
    jq -e \
        --arg chart "$expected_chart_revision" \
        --arg git "$expected_git_revision" \
        "(${jq_path} // []) as \$revisions | (\$revisions | index(\$chart)) != null and (\$revisions | index(\$git)) != null" \
        >/dev/null <<<"$payload"
}

deadline=$(( $(date +%s) + timeout ))
sync_attempts=0
stale_terminations=0
sync_budget_exhausted_reported=false
previous_summary=""
failure_reason="timed out waiting for exact-revision ArgoCD convergence for ${application}"

echo "Waiting for ArgoCD application ${app_namespace}/${application}:"
echo "  chart: ${expected_chart_revision}"
echo "  values revision: ${expected_git_revision}"

while (( $(date +%s) <= deadline )); do
    if api_get; then
        last_payload="$(<"$api_response_file")"
    else
        api_status=$?
        if (( api_status == fatal_api_error )); then
            exit 1
        fi
        echo "ArgoCD API query failed; retrying in ${poll_interval}s..." >&2
        sleep "$poll_interval"
        continue
    fi
    if ! jq -e 'type == "object"' >/dev/null <<<"$last_payload"; then
        echo "ArgoCD API returned malformed JSON; retrying in ${poll_interval}s..." >&2
        sleep "$poll_interval"
        continue
    fi

    sync_status="$(jq -r '.status.sync.status // "Unknown"' <<<"$last_payload")"
    health_status="$(jq -r '.status.health.status // "Unknown"' <<<"$last_payload")"
    operation_phase="$(jq -r '.status.operationState.phase // "None"' <<<"$last_payload")"
    summary="sync=${sync_status}, health=${health_status}, operation=${operation_phase}"
    if [[ "$summary" != "$previous_summary" ]]; then
        echo "  ${summary}"
        previous_summary="$summary"
    fi

    desired_matches=false
    operation_matches=false
    if revision_set_matches '.status.sync.revisions' "$last_payload"; then
        desired_matches=true
    fi
    if jq -e \
        --arg chart "$expected_chart_revision" \
        --arg git "$expected_git_revision" \
        '([.status.operationState.operation.sync.revisions[]?, .status.operationState.operation.sync.revision?] | map(select(. != null and . != ""))) as $revisions | ($revisions | index($chart)) != null and ($revisions | index($git)) != null' \
        >/dev/null <<<"$last_payload"; then
        operation_matches=true
    fi

    if [[ "$desired_matches" == true && "$operation_matches" == true \
          && "$sync_status" == "Synced" && "$health_status" == "Healthy" \
          && "$operation_phase" == "Succeeded" ]]; then
        echo "ArgoCD synced and health-checked the exact promoted revisions."
        exit 0
    fi

    operation_active=false
    case "$operation_phase" in
        Running|Pending|Progressing|Waiting|Terminating) operation_active=true ;;
    esac

    # A previous deployment can remain Running even after the ApplicationSet
    # resolves a newer env-branch revision. It can never attest this promotion,
    # so terminate only that stale operation and let the exact sync proceed.
    if [[ "$desired_matches" == true && "$operation_active" == true \
          && "$operation_phase" != "Terminating" && "$operation_matches" == false ]]; then
        if (( stale_terminations >= max_stale_terminations )); then
            failure_reason="ArgoCD repeatedly started stale operations for ${application}"
            break
        fi
        next_stale_termination=$((stale_terminations + 1))
        echo "Terminating stale ArgoCD operation (${next_stale_termination}/${max_stale_terminations})..."
        if api_mutate DELETE '/operation'; then
            stale_terminations="$next_stale_termination"
            echo "Stale ArgoCD operation terminated (${stale_terminations}/${max_stale_terminations})."
        else
            api_status=$?
            if (( api_status == fatal_api_error )); then
                exit 1
            fi
            echo "ArgoCD rejected stale-operation termination; will retry." >&2
        fi
        sleep "$poll_interval"
        continue
    fi

    # Trigger an explicit multi-source sync only after ArgoCD has resolved both
    # exact desired revisions. The revisions array preserves source order and
    # prevents a branch from moving between the gate and reconciliation.
    if [[ "$desired_matches" == true && "$operation_active" == false \
          && ( "$sync_status" != "Synced" || "$operation_matches" == false ) ]]; then
        if (( sync_attempts >= max_sync_attempts )); then
            if [[ "$sync_budget_exhausted_reported" == false ]]; then
                echo "Exact-revision sync attempt limit reached; continuing observation without further mutations."
                sync_budget_exhausted_reported=true
            fi
        else
            desired_revisions="$(jq -c '.status.sync.revisions' <<<"$last_payload")"
            source_count="$(jq -r '(.spec.sources // []) | length' <<<"$last_payload")"
            revision_count="$(jq -r '(.status.sync.revisions // []) | length' <<<"$last_payload")"
            if (( source_count != revision_count )); then
                failure_reason="ArgoCD reports ${revision_count} resolved revisions for ${source_count} configured sources; refusing a positional sync"
                break
            fi
            sync_attempts=$((sync_attempts + 1))
            desired_source_positions="$(jq -c '[.status.sync.revisions | to_entries[] | .key + 1]' <<<"$last_payload")"
            sync_prune="$(jq -c '(.spec.syncPolicy.automated.prune // false) == true' <<<"$last_payload")"
            sync_request="$(jq -cn \
                --arg name "$application" \
                --arg namespace "$app_namespace" \
                --arg project "$argocd_project" \
                --argjson prune "$sync_prune" \
                --argjson revisions "$desired_revisions" \
                --argjson sourcePositions "$desired_source_positions" \
                '{name: $name, appNamespace: $namespace, project: $project, prune: $prune, revisions: $revisions, sourcePositions: $sourcePositions}')"
            echo "Starting exact-revision ArgoCD sync (${sync_attempts}/${max_sync_attempts}, prune=${sync_prune})..."
            if api_mutate POST '/sync' "$sync_request"; then
                :
            else
                api_status=$?
                if (( api_status == fatal_api_error )); then
                    exit 1
                fi
                echo "ArgoCD did not accept sync attempt ${sync_attempts}; observing state before any retry." >&2
            fi
        fi
    fi

    sleep "$poll_interval"
done

echo "ERROR: ${failure_reason}" >&2
if [[ -n "$last_payload" ]]; then
    jq '{
      sync: .status.sync,
      health: .status.health,
      operation: {
        phase: .status.operationState.phase,
        message: .status.operationState.message,
        startedAt: .status.operationState.startedAt,
        finishedAt: .status.operationState.finishedAt,
        revisions: .status.operationState.operation.sync.revisions
      },
      conditions: (.status.conditions // []),
      unconvergedResources: [
        .status.resources[]?
        | select((.status // "Unknown") != "Synced" or ((.health.status // "Healthy") != "Healthy"))
        | {group, kind, namespace, name, status, health}
      ]
    }' <<<"$last_payload" >&2
fi
exit 1
