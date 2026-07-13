#!/usr/bin/env bash
# Local verification harness for PR #24 (nautobot rbac group mapping).
#
# Prereqs: a `make kind-up-sec` deploy is up. Requires: kubectl, helm, curl, jq.
# Run from the repo root.
#
# SAFETY: every kubectl/helm call is pinned to an explicit --context (default
# `kind-nv-config-manager`), NOT the ambient current-context. This matters
# because tools like Teleport/tsh continually rewrite `current-context` in a
# merged KUBECONFIG, which could otherwise point these mutating commands at a
# production cluster. Override with KUBECTX=... but it MUST be a kind-* context.
#
# Exercises the three configuration states the PR introduces:
#
#   state-a  UNCONFIGURED (default deploy): no ConfigMap/mount, sync is a no-op,
#            existing privileges are left untouched. This is the regression fix.
#   state-c  CONFIGURED: apply values-configured.yaml, log users in, confirm the
#            managed Groups + ObjectPermissions are created and applied.
#   state-b  CONFIGURED-BUT-EMPTY: set groupMapping=[], log in, confirm managed
#            Groups/ObjectPermissions are pruned (revoke-everyone).
#
#   all      Runs state-a -> state-c -> state-b in order.
#
# Individual helpers: `login <user>`, `show <user-substring>`.
set -euo pipefail

KUBECTX="${KUBECTX:-kind-nv-config-manager}"
NS="${NS:-nv-config-manager}"
RELEASE="${RELEASE:-nv-config-manager}"
CHART="${CHART:-deploy/helm}"
KEYCLOAK_NS="${KEYCLOAK_NS:-keycloak}"
KEYCLOAK_SVC="${KEYCLOAK_SVC:-keycloak}"
REALM="${REALM:-nv-config-manager}"
# The `nv-config-manager-cli` client is public with direct-access-grants
# DISABLED, so scripted password-grant token fetch is refused. The confidential
# `nv-config-manager` client has direct grants enabled and carries the audience
# mappers the Nautobot authenticator expects, so we use it for local testing.
CLI_CLIENT_ID="${CLI_CLIENT_ID:-nv-config-manager}"
CLI_CLIENT_SECRET="${CLI_CLIENT_SECRET:-nvcm-local-client-secret}"
KEYCLOAK_LOCAL_PORT="${KEYCLOAK_LOCAL_PORT:-18080}"
NB_LOCAL_PORT="${NB_LOCAL_PORT:-18443}"
VALUES_CONFIGURED="${VALUES_CONFIGURED:-scripts/rbac-local-test/values-configured.yaml}"

CONFIGMAP="${RELEASE}-nautobot-group-mapping"

log()  { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m  ✓ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m  ! %s\033[0m\n' "$*"; }

require() { command -v "$1" >/dev/null 2>&1 || { echo "missing required command: $1" >&2; exit 1; }; }
require kubectl; require helm; require curl; require jq

# Isolate from the shared kubeconfig. Tools like Teleport/tsh continually
# rewrite ~/.kube/config (flipping current-context to prod, and even briefly
# dropping the kind context mid-rewrite). Regenerate a dedicated, kind-only
# kubeconfig and point KUBECONFIG at just that file so nothing external can
# retarget our mutating commands. Set KIND_ISOLATE=0 to opt out.
KIND_CLUSTER="${KIND_CLUSTER:-nv-config-manager}"
if [[ "${KIND_ISOLATE:-1}" == "1" ]] && command -v kind >/dev/null 2>&1 \
     && kind get clusters 2>/dev/null | grep -qx "$KIND_CLUSTER"; then
  _dedicated="${DEDICATED_KUBECONFIG:-/tmp/kind-${KIND_CLUSTER}.kubeconfig}"
  if kind get kubeconfig --name "$KIND_CLUSTER" > "$_dedicated" 2>/dev/null; then
    chmod 600 "$_dedicated" 2>/dev/null || true
    export KUBECONFIG="$_dedicated"
  fi
fi

# All cluster access goes through these wrappers so the target context can never
# be silently swapped out from under us by current-context churn.
kctl() { kubectl --context "$KUBECTX" "$@"; }
hlm()  { helm --kube-context "$KUBECTX" "$@"; }

guard_context() {
  case "$KUBECTX" in
    kind-*) ;;
    *) echo "Refusing to run: KUBECTX '$KUBECTX' is not a kind-* context." >&2; exit 1 ;;
  esac
  if ! kubectl config get-contexts -o name 2>/dev/null | grep -qx "$KUBECTX"; then
    echo "Refusing to run: context '$KUBECTX' not found in kubeconfig." >&2
    exit 1
  fi
  echo "Targeting context: $KUBECTX (namespace: $NS)"
}

NB_SELECTOR="app.kubernetes.io/name=${RELEASE}-nautobot,app.kubernetes.io/instance=${RELEASE}"

nb_deploy() {
  local d
  d="$(kctl -n "$NS" get deploy -l "$NB_SELECTOR" \
        -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || true)"
  [[ -z "$d" ]] && d="${RELEASE}-nautobot"
  echo "$d"
}

nb_pod() {
  kctl -n "$NS" get pod -l "$NB_SELECTOR" \
    -o jsonpath='{.items[0].metadata.name}'
}

# Reconcile only runs on JWT login, so we fetch a token then hit the Nautobot
# REST API to trigger nv_config_manager_auth.jwt_authentication + rbac.
get_token() { # $1 = username (local password == username)
  local user="$1"
  curl -s -X POST \
    "http://localhost:${KEYCLOAK_LOCAL_PORT}/realms/${REALM}/protocol/openid-connect/token" \
    -d "client_id=${CLI_CLIENT_ID}" \
    -d "client_secret=${CLI_CLIENT_SECRET}" \
    -d "grant_type=password" -d "scope=openid" \
    -d "username=${user}" -d "password=${user}" | jq -r '.access_token // empty'
}

pf_pid=""
start_pf() {
  kctl -n "$KEYCLOAK_NS" port-forward "svc/${KEYCLOAK_SVC}" "${KEYCLOAK_LOCAL_PORT}:80" >/dev/null 2>&1 &
  pf_pid+=" $!"
  local nb_svc nb_port
  nb_svc="$(kctl -n "$NS" get svc -l "$NB_SELECTOR" -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "${RELEASE}-nautobot")"
  [[ -z "$nb_svc" ]] && nb_svc="${RELEASE}-nautobot"
  nb_port="$(kctl -n "$NS" get svc "$nb_svc" -o jsonpath='{.spec.ports[0].port}' 2>/dev/null || echo 80)"
  NB_SCHEME="http"; [[ "$nb_port" == "443" ]] && NB_SCHEME="https"
  kctl -n "$NS" port-forward "svc/${nb_svc}" "${NB_LOCAL_PORT}:${nb_port}" >/dev/null 2>&1 &
  pf_pid+=" $!"
  sleep 3
}
stop_pf() { for p in $pf_pid; do kill "$p" 2>/dev/null || true; done; pf_pid=""; }
trap stop_pf EXIT

api_login() { # $1 = username -> triggers the authenticator, prints HTTP status
  local user="$1" token status
  token="$(get_token "$user")"
  if [[ -z "$token" ]]; then warn "no token for ${user} (check keycloak port-forward / client)"; return 1; fi
  status="$(curl -s -k -o /dev/null -w '%{http_code}' \
    -H "Authorization: Bearer ${token}" \
    "${NB_SCHEME}://localhost:${NB_LOCAL_PORT}/api/users/users/")"
  echo "$status"
}

# Prints Django group + ObjectPermission state for users matching a substring.
show_users() { # $1 = username substring
  local needle="$1" pod; pod="$(nb_pod)"
  kctl -n "$NS" exec -i "$pod" -- nautobot-server nbshell <<PY
exec("""
from django.contrib.auth import get_user_model
from nautobot.users.models import ObjectPermission
U = get_user_model()
for u in U.objects.filter(username__icontains="${needle}").order_by("username"):
    groups = list(u.groups.values_list("name", flat=True))
    print(f"{u.username}: superuser={u.is_superuser} groups={groups}")
for g_name in ("nvcm-network", "nvcm-admin"):
    perms = list(
        ObjectPermission.objects.filter(name__startswith=f"{g_name}_").values_list("name", flat=True)
    )
    print(f"  managed ObjectPermissions for {g_name!r}: {perms}")
""")
PY
}

helm_upgrade() { # $@ = extra helm args
  log "helm upgrade ${RELEASE} (${*})"
  hlm upgrade "$RELEASE" "$CHART" -n "$NS" --reuse-values "$@"
  kctl -n "$NS" rollout status "deploy/$(nb_deploy)" --timeout=15m
}

state_a() {
  log "STATE A — UNCONFIGURED (regression fix: sync must be a no-op)"
  if kctl -n "$NS" get configmap "$CONFIGMAP" >/dev/null 2>&1; then
    warn "ConfigMap ${CONFIGMAP} EXISTS — expected absent in default deploy."
    warn "If you previously ran state-c/state-b, reset with: helm upgrade ... (remove groupMapping) or redeploy."
  else
    ok "ConfigMap ${CONFIGMAP} is absent (nothing rendered)."
  fi
  local pod; pod="$(nb_pod)"
  if kctl -n "$NS" get pod "$pod" -o yaml | grep -qi group-mapping; then
    warn "group-mapping volume/mount present on ${pod} — expected none."
  else
    ok "No group-mapping volume/mount on ${pod}."
  fi
  start_pf
  log "Logging in as nvcm-admin; privileges must be untouched (no revoke path)."
  echo "  HTTP status: $(api_login nvcm-admin || true)"
  show_users nvcm
  stop_pf
}

state_c() {
  log "STATE C — CONFIGURED (apply mapping, verify grants)"
  helm_upgrade -f "$VALUES_CONFIGURED"
  if kctl -n "$NS" get configmap "$CONFIGMAP" >/dev/null 2>&1; then
    ok "ConfigMap ${CONFIGMAP} now present."
  else
    warn "ConfigMap ${CONFIGMAP} still absent — override may not have applied."
  fi
  start_pf
  log "Baseline (before logins):"; show_users nvcm
  for u in nvcm-network nvcm-admin; do
    log "Login ${u} -> HTTP $(api_login "$u" || true)"
  done
  log "After logins (expect nvcm-network group + _view/_change perms; nvcm-admin superuser):"
  show_users nvcm
  stop_pf
}

state_b() {
  log "STATE B — CONFIGURED-BUT-EMPTY (groupMapping=[] -> revoke-everyone)"
  helm_upgrade --set-json 'nautobot.rbac.groupMapping=[]'
  start_pf
  for u in nvcm-network nvcm-admin; do
    log "Login ${u} -> HTTP $(api_login "$u" || true)"
  done
  log "After logins (expect managed groups/perms pruned; manual groups untouched):"
  show_users nvcm
  stop_pf
}

main() {
  guard_context
  case "${1:-all}" in
    state-a|a) state_a ;;
    state-c|c) state_c ;;
    state-b|b) state_b ;;
    login)     start_pf; echo "HTTP $(api_login "${2:?usage: login <user>}")"; stop_pf ;;
    show)      show_users "${2:?usage: show <user-substring>}" ;;
    all)       state_a; state_c; state_b ;;
    *) echo "usage: $0 {all|state-a|state-c|state-b|login <user>|show <substr>}" >&2; exit 1 ;;
  esac
}

main "$@"
