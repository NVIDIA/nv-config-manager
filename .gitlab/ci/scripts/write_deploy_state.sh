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
#          DIGEST_<IMAGE> x9, and from test-promote-chart: BASELINE_REVISION
#          (main SHA whose baseline was validated) + ENV_BRANCH_REVISION
#          (env-branch SHA whose overrides were validated)
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
: "${ENV_BRANCH_REVISION:?ENV_BRANCH_REVISION missing (dotenv from test-promote-chart)}"
: "${DIGEST_NV_CONFIG_MANAGER:?missing dotenv from test-promote-push-images}"
: "${DIGEST_NV_CONFIG_MANAGER_UI:?missing dotenv from test-promote-push-images}"
: "${DIGEST_NV_CONFIG_MANAGER_KEA:?missing dotenv from test-promote-push-images}"
: "${DIGEST_NV_CONFIG_MANAGER_KEA_ADMIN:?missing dotenv from test-promote-push-images}"
: "${DIGEST_NV_CONFIG_MANAGER_NAUTOBOT:?missing dotenv from test-promote-push-images}"
: "${DIGEST_NV_CONFIG_MANAGER_NATS_READY:?missing dotenv from test-promote-push-images}"
: "${DIGEST_NV_CONFIG_MANAGER_TEMPORAL:?missing dotenv from test-promote-push-images}"
: "${DIGEST_NV_CONFIG_MANAGER_TEMPORAL_BOOTSTRAP:?missing dotenv from test-promote-push-images}"
: "${DIGEST_NV_CONFIG_MANAGER_TEMPORAL_UI:?missing dotenv from test-promote-push-images}"

if [ -n "${NV_CONFIG_MANAGER_VALUES_REPO_URL:-}" ]; then
    # A full URL override is used as-is (provide any auth it needs in the URL).
    values_repo_url="$NV_CONFIG_MANAGER_VALUES_REPO_URL"
    # Credential-free label for logs: strip any "userinfo@" (e.g. oauth2:token@)
    # so an override URL that embeds a token can't leak it into the job log.
    values_repo_display="$(printf '%s' "$NV_CONFIG_MANAGER_VALUES_REPO_URL" | sed -E 's#://[^/@]*@#://#')"
    # No clean project path is available from a full-URL override.
    values_repo_path=""
else
    # A path builds the authenticated GitLab URL with the push token.
    values_repo_path="${NVCM_VALUES_REPO_PATH:?Set NVCM_VALUES_REPO_PATH or NV_CONFIG_MANAGER_VALUES_REPO_URL}"
    values_repo_url="https://oauth2:${NV_CONFIG_MANAGER_VALUES_PUSH_TOKEN}@${CI_SERVER_HOST}/${values_repo_path}.git"
    values_repo_display="$values_repo_path"
fi

state_file="${NVCM_ENV_STATE_DIR}/deploy-state.yaml"
occupant="${GITLAB_USER_LOGIN:-${GITLAB_USER_NAME:-ci}}"

echo "Committing deploy-state for env '${NVCM_ENV}' to ${values_repo_display}@${NVCM_ENV_BRANCH}:${state_file}"

git clone "$values_repo_url" values-repo
cd values-repo

if git ls-remote --heads origin "${NVCM_ENV_BRANCH}" | grep -q "${NVCM_ENV_BRANCH}"; then
    git fetch origin "${NVCM_ENV_BRANCH}"
    git checkout "${NVCM_ENV_BRANCH}"
else
    echo "ERROR: env branch '${NVCM_ENV_BRANCH}' does not exist in ${values_repo_display}."
    echo "Seed it from main first (see the kiwi-argocd README migration steps)."
    exit 1
fi

if [ ! -f "$state_file" ]; then
    echo "ERROR: ${state_file} not found on ${NVCM_ENV_BRANCH}; the env is not seeded."
    exit 1
fi

# The render gate in test-promote-chart validated this env's overrides at a
# specific env-branch revision. resource_group serializes promote/rollback/
# release runs, but not human pushes to the env branch, so the overrides can
# change in between. Refuse to write deploy-state against overrides that were
# never validated - fail closed and let the operator re-run.
current_env_rev="$(git rev-parse HEAD)"
if [ "$current_env_rev" != "$ENV_BRANCH_REVISION" ]; then
    echo "ERROR: ${NVCM_ENV_BRANCH} moved since the render gate validated it."
    echo "  validated: ${ENV_BRANCH_REVISION}"
    echo "  current:   ${current_env_rev}"
    echo "Someone pushed to the env branch mid-promote, so its overrides are"
    echo "unvalidated against this chart. Re-run the promote pipeline."
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
    current_hold \
    DIGEST_NV_CONFIG_MANAGER DIGEST_NV_CONFIG_MANAGER_UI \
    DIGEST_NV_CONFIG_MANAGER_KEA DIGEST_NV_CONFIG_MANAGER_KEA_ADMIN \
    DIGEST_NV_CONFIG_MANAGER_NAUTOBOT DIGEST_NV_CONFIG_MANAGER_NATS_READY \
    DIGEST_NV_CONFIG_MANAGER_TEMPORAL DIGEST_NV_CONFIG_MANAGER_TEMPORAL_BOOTSTRAP \
    DIGEST_NV_CONFIG_MANAGER_TEMPORAL_UI
updated_at="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
export updated_at

trap 'rm -f "${state_file}.new" "${state_file}.merged"' EXIT

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
  .images.temporalServer = strenv(DIGEST_NV_CONFIG_MANAGER_TEMPORAL) |
  .images.temporalBootstrap = strenv(DIGEST_NV_CONFIG_MANAGER_TEMPORAL_BOOTSTRAP) |
  .images.temporalUi = strenv(DIGEST_NV_CONFIG_MANAGER_TEMPORAL_UI) |
  .sourceSHA = strenv(PR_SHA) |
  .pr = (strenv(PR_NUM) | tonumber) |
  .occupant = strenv(occupant) |
  .updatedAt = strenv(updated_at) |
  .hold = (strenv(current_hold) == "true")
' > "${state_file}.new"

# Keep the leading DO-NOT-HAND-EDIT comment header from the existing file.
# Assemble into a separate file: redirecting straight onto "$state_file" would
# truncate it before awk could read the header back out of it.
{
    awk '/^---$/ { next } /^#/ { print; next } { exit }' "$state_file"
    cat "${state_file}.new"
} > "${state_file}.merged"
mv "${state_file}.merged" "$state_file"
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
# Only build the web view URL from a known project path - a full-URL override
# has no clean path and could otherwise produce a malformed/credential URL.
if [ -n "$values_repo_path" ]; then
    echo "View: https://${CI_SERVER_HOST}/${values_repo_path}/-/commits/${NVCM_ENV_BRANCH}"
fi
