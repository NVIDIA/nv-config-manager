#!/usr/bin/env bash
# Final stage of the test-env promote flow: commit the machine-written
# deployment state for one environment to its env branch in the downstream
# ArgoCD values repository. The ApplicationSet's git file generator reads this
# file and deploys the pinned chart version + image digests.
#
# The deploy-state file is the ONLY file this script touches - human-owned
# overrides on the env branch are never modified.
#
# Requires (dotenv from earlier stages): PROMOTE_VERSION, PR_NUM, PR_SHA,
#          DIGEST_<IMAGE> x6, BASELINE_REVISION (from test-promote-chart)
# Requires (eval of test_env_config.sh): NVCM_ENV, NVCM_ENV_BRANCH,
#          NVCM_ENV_NAMESPACE, NVCM_ENV_RELEASE_NAME, NVCM_ENV_STATE_DIR
# Requires (protected variables): NV_CONFIG_MANAGER_VALUES_PUSH_TOKEN,
#          NVCM_VALUES_REPO_PATH (or NV_CONFIG_MANAGER_VALUES_REPO_URL),
#          NVCM_CHART_REPO (Helm repo URL ArgoCD reads the chart from, e.g.
#          https://helm.ngc.nvidia.com/nvidian/cfa)
set -euo pipefail

: "${PROMOTE_VERSION:?missing dotenv from test-promote-build}"
: "${PR_NUM:?missing dotenv from test-promote-build}"
: "${PR_SHA:?missing dotenv from test-promote-build}"
: "${NVCM_ENV:?eval test_env_config.sh first}"
: "${NVCM_ENV_BRANCH:?eval test_env_config.sh first}"
: "${NVCM_ENV_NAMESPACE:?eval test_env_config.sh first}"
: "${NVCM_ENV_RELEASE_NAME:?eval test_env_config.sh first}"
: "${NVCM_ENV_STATE_DIR:?eval test_env_config.sh first}"
: "${NVCM_CHART_REPO:?Set NVCM_CHART_REPO to the Helm repo URL ArgoCD reads the chart from}"
: "${DIGEST_NV_CONFIG_MANAGER:?missing dotenv from test-promote-push-images}"
: "${DIGEST_NV_CONFIG_MANAGER_UI:?missing dotenv from test-promote-push-images}"
: "${DIGEST_NV_CONFIG_MANAGER_KEA:?missing dotenv from test-promote-push-images}"
: "${DIGEST_NV_CONFIG_MANAGER_KEA_ADMIN:?missing dotenv from test-promote-push-images}"
: "${DIGEST_NV_CONFIG_MANAGER_NAUTOBOT:?missing dotenv from test-promote-push-images}"
: "${DIGEST_NV_CONFIG_MANAGER_NATS_READY:?missing dotenv from test-promote-push-images}"

if [ -n "${NV_CONFIG_MANAGER_VALUES_REPO_URL:-}" ]; then
    # A full URL override is used as-is (provide any auth it needs in the URL).
    values_repo="$NV_CONFIG_MANAGER_VALUES_REPO_URL"
    values_repo_url="$NV_CONFIG_MANAGER_VALUES_REPO_URL"
else
    # A path builds the authenticated GitLab URL with the push token.
    values_repo="${NVCM_VALUES_REPO_PATH:?Set NVCM_VALUES_REPO_PATH or NV_CONFIG_MANAGER_VALUES_REPO_URL}"
    values_repo_url="https://oauth2:${NV_CONFIG_MANAGER_VALUES_PUSH_TOKEN}@${CI_SERVER_HOST}/${values_repo}.git"
fi

state_file="${NVCM_ENV_STATE_DIR}/deploy-state.yaml"
occupant="${GITLAB_USER_LOGIN:-${GITLAB_USER_NAME:-ci}}"

echo "Committing deploy-state for env '${NVCM_ENV}' to ${values_repo}@${NVCM_ENV_BRANCH}:${state_file}"

git clone "$values_repo_url" values-repo
cd values-repo

if git ls-remote --heads origin "${NVCM_ENV_BRANCH}" | grep -q "${NVCM_ENV_BRANCH}"; then
    git fetch origin "${NVCM_ENV_BRANCH}"
    git checkout "${NVCM_ENV_BRANCH}"
else
    echo "ERROR: env branch '${NVCM_ENV_BRANCH}' does not exist in ${values_repo}."
    echo "Seed it from main first (see the kiwi-argocd README migration steps)."
    exit 1
fi

if [ ! -f "$state_file" ]; then
    echo "ERROR: ${state_file} not found on ${NVCM_ENV_BRANCH}; the env is not seeded."
    exit 1
fi

# Honor a manual hold: an occupant who set hold: true is protecting the slot.
current_hold=$(yq -r '.hold // false' "$state_file")
current_occupant=$(yq -r '.occupant // "none"' "$state_file")
if [ "$current_hold" = "true" ] && [ "$current_occupant" != "$occupant" ]; then
    echo "ERROR: ${NVCM_ENV} is on hold by '${current_occupant}' (deploy-state hold: true)."
    echo "Coordinate with them or have them release the hold before promoting."
    exit 1
fi

# Baseline pin: the kiwi-argocd main SHA whose baseline values the render gate
# validated against, captured in test-promote-chart and passed via dotenv.
# Consuming that exact SHA - rather than re-resolving origin/main here - keeps
# the deployed baseline identical to the one that was validated even if main
# moved in between. Pinning (vs tracking main) also makes rollback exact.
baseline_rev="${BASELINE_REVISION:?BASELINE_REVISION missing (dotenv from test-promote-chart)}"

export NVCM_ENV NVCM_ENV_NAMESPACE NVCM_ENV_BRANCH NVCM_ENV_RELEASE_NAME \
    NVCM_CHART_REPO PROMOTE_VERSION PR_SHA PR_NUM occupant baseline_rev \
    DIGEST_NV_CONFIG_MANAGER DIGEST_NV_CONFIG_MANAGER_UI \
    DIGEST_NV_CONFIG_MANAGER_KEA DIGEST_NV_CONFIG_MANAGER_KEA_ADMIN \
    DIGEST_NV_CONFIG_MANAGER_NAUTOBOT DIGEST_NV_CONFIG_MANAGER_NATS_READY
updated_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
export updated_at

yq -n '
  .env = strenv(NVCM_ENV) |
  .namespace = strenv(NVCM_ENV_NAMESPACE) |
  .envBranch = strenv(NVCM_ENV_BRANCH) |
  .releaseName = strenv(NVCM_ENV_RELEASE_NAME) |
  .chartRepo = strenv(NVCM_CHART_REPO) |
  .chartVersion = strenv(PROMOTE_VERSION) |
  .baselineRevision = strenv(baseline_rev) |
  .images.nvConfigManager = strenv(DIGEST_NV_CONFIG_MANAGER) |
  .images.nvConfigManagerUi = strenv(DIGEST_NV_CONFIG_MANAGER_UI) |
  .images.kea = strenv(DIGEST_NV_CONFIG_MANAGER_KEA) |
  .images.keaAdmin = strenv(DIGEST_NV_CONFIG_MANAGER_KEA_ADMIN) |
  .images.nautobot = strenv(DIGEST_NV_CONFIG_MANAGER_NAUTOBOT) |
  .images.natsReady = strenv(DIGEST_NV_CONFIG_MANAGER_NATS_READY) |
  .sourceSHA = strenv(PR_SHA) |
  .pr = (strenv(PR_NUM) | tonumber) |
  .occupant = strenv(occupant) |
  .updatedAt = strenv(updated_at) |
  .hold = false
' > "${state_file}.new"

# Keep the leading DO-NOT-HAND-EDIT comment header from the existing file.
{
    awk '/^---$/ { next } /^#/ { print; next } { exit }' "$state_file"
    cat "${state_file}.new"
} > "$state_file"
rm -f "${state_file}.new"

if git diff --quiet "$state_file"; then
    echo "No deploy-state changes; ${NVCM_ENV} is already at ${PROMOTE_VERSION}."
    exit 0
fi

echo "Deploy-state diff:"
git diff "$state_file"

git add "$state_file"
git commit -m "[nvcm CI] Promote PR #${PR_NUM} (${PROMOTE_VERSION}) to ${NVCM_ENV}

Source commit: ${PR_SHA}
Baseline: ${baseline_rev}
Triggered by: ${occupant}
Pipeline: ${CI_PIPELINE_URL}"
git push origin "HEAD:refs/heads/${NVCM_ENV_BRANCH}"

echo ""
echo "Deploy-state committed. ArgoCD will sync ${NVCM_ENV} to chart ${PROMOTE_VERSION} with digest-pinned images."
echo "View: https://${CI_SERVER_HOST}/${values_repo}/-/commits/${NVCM_ENV_BRANCH}"
