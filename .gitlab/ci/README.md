# GitLab CI Variables

The GitLab pipeline is intentionally split into local includes under
`.gitlab/ci/`. Public-safe linting and tests should run in GitHub Actions.
Internal GitLab jobs keep private details behind CI/CD variables so the checked
in pipeline does not expose registry paths, scanner
credentials, scanner policy locations, deployment targets, or downstream
repository paths.

The mirror pipeline must not create Git tags or commits in the mirrored
repository. Default-branch updates run validation only: builds, tests, and
private scans. Releases happen only when an upstream semver tag is mirrored into
GitLab. Tag pipelines build and scan the tagged commit, then publish external
artifacts using `CI_COMMIT_TAG` as the version. The bundled Nautobot apps are
published to the GitLab PyPI package registry from the mirrored tag.
Release tags must be Docker-compatible semver such as `1.2.3` or
`1.2.3-rc.1`; tags with a `v` prefix or `+build` metadata are rejected by the
release pipeline.

Configure sensitive variables as masked and protected where possible. Configure
non-secret internal names as protected variables if they should not appear in
the public repository.

## Required For Internal Build And Release

| Variable | Purpose |
| -------- | ------- |
| `NVCM_IMAGE_TARGETS` | Newline-delimited image targets, one `name\|repository_prefix\|token_variable` record per target |
| `NVCM_IMAGE_TARGET` | Optional default image target for build/publish jobs; the first `NVCM_IMAGE_TARGETS` record is used when unset |
| `NVCM_VALUES_IMAGE_TARGET` | Image target name used when publishing charts and updating downstream deployment values |
| `NVCM_IMAGE_REPOSITORY` | Legacy/default image repository prefix; when `NVCM_IMAGE_TARGETS` is set, jobs derive this from the selected image target |
| `NVCM_NGC_API_BASE` | Base registry API URL |
| `NVCM_NGC_ORG` | Registry organization used by tag existence checks |
| `NVCM_NGC_TEAM` | Registry team used by tag existence checks |
| `NVCM_CHART_TARGETS` | Newline-delimited chart targets, one `type\|repository\|token_variable\|options` record per target |
| Token variables referenced by target records | Registry credentials used for configured image and chart targets |
| `CI_PUSH_TOKEN` | Token allowed to push CI-generated commits, chart branches, and package uploads |
| `CI_PUSH_EMAIL` | Commit email used by CI-generated commits |

Image and chart target records keep each publish target on one line. Token
fields are variable names, not token values, so each target can use a
masked/protected token without embedding the secret in a list.

Example image target layout:

```text
NVCM_IMAGE_TARGETS
internal|registry.example.com/example/team|REGISTRY_TOKEN

NVCM_VALUES_IMAGE_TARGET
internal
```

Example chart target layout:

```text
NVCM_CHART_TARGETS
oci|registry.example.com/example/components|CHART_REGISTRY_TOKEN
```

Supported optional chart target options are `org`, `registry`, `username`,
and `label`.

`deploy/helm/values.yaml` uses `registry.example.com/nvidia/...` placeholders
for checked-in service image repositories. Internal publishing and deployment
jobs rewrite those repositories from `NVCM_IMAGE_TARGETS` before packaging
charts or updating downstream values.

## Runner Tags And Image Overrides

| Name | Purpose |
| ---- | ------- |
| `dca` | Literal GitLab runner site/pool tag used by internal jobs |
| `linux/amd64` | Literal GitLab runner architecture tag for amd64 jobs |
| `linux/arm64` | Literal GitLab runner architecture tag for native arm64 image builds |
| `docker` | Literal GitLab runner capability tag for jobs that need Docker-capable runners |
| `NVCM_CI_IMAGE_ALPINE` | Alpine CI image |
| `NVCM_CI_IMAGE_AWS_CLI` | AWS CLI CI image |
| `NVCM_CI_IMAGE_DOCKER` | Docker CLI CI image |
| `NVCM_CI_IMAGE_DOCKER_DIND` | Docker-in-Docker service image |
| `NVCM_CI_IMAGE_GO` | Go CI image |
| `NVCM_CI_IMAGE_NODE` | Node.js CI image |
| `NVCM_CI_IMAGE_PLAYWRIGHT` | Playwright CI image |
| `NVCM_CI_IMAGE_PYTHON_311_BOOKWORM` | Python 3.11 Debian CI image |
| `NVCM_CI_IMAGE_PYTHON_313` | Python 3.13 CI image |
| `NVCM_CI_IMAGE_SONAR` | Sonar scanner image |
| `NVCM_CI_IMAGE_UBUNTU` | Ubuntu CI image |

## Internal Package Mirrors

| Variable | Purpose |
| -------- | ------- |
| `NVCM_APT_MIRROR` | Optional Ubuntu package mirror URL passed into Docker builds |
| `NVCM_APT_MIRROR_DEBIAN` | Optional Debian package mirror URL passed into Docker builds |
| `NVCM_APT_MIRROR_GPG_KEY_URL` | Optional APT mirror GPG key URL |

## Security And Quality Scans

| Variable | Purpose |
| -------- | ------- |
| `FORCE_PULSE_SCAN` | Set to `true` to force image builds and Pulse scan jobs |
| `PULSE_NSPECT_ID` | Pulse project or engagement identifier |
| `SSA_CLIENT_ID` | Service account client ID used by Pulse scanner authentication |
| `SSA_CLIENT_SECRET` | Service account client secret used by Pulse scanner authentication |
| `NV_CONFIG_MANAGER_CONTAINER_SCAN_POLICY_TOKEN` | Token that can read the internal container scan policy file |
| `NVCM_CONTAINER_SCAN_POLICY_PROJECT` | URL-encoded GitLab project path for the internal scan policy project |
| `NVCM_CONTAINER_SCAN_POLICY_FILE` | URL-encoded internal scan policy file path |
| `NVCM_CONTAINER_SCAN_POLICY_REF` | Ref for the internal scan policy file, defaults to `main` |
| `SONAR_HOST_URL` | SonarQube URL |
| `SONAR_TOKEN` | Token authorized to analyze the SonarQube project and export its report |
| `NVCM_SONAR_PROJECT_KEY` | SonarQube project key; configure as a protected CI/CD variable |

SonarQube runs on every mirrored default-branch commit as an informational,
post-merge report. Both Sonar jobs intentionally use `allow_failure: true` and
do not gate upstream code. The default-branch Python test jobs run before every
scan so all configured coverage reports are available; the scanner skips an
analysis rather than replacing valid dashboard coverage with 0% if an expected
artifact is missing. Generated Go API clients under `bindings/go/` are excluded
from Sonar analysis.

Pulse scan jobs use the versioned Pulse `scan-images` CI/CD component. The
component scans each published image from the selected `NVCM_IMAGE_TARGETS`
repository for both `linux/amd64` and `linux/arm64`, mints a fresh SSA token at
scan time, and applies the configured internal policy file fetched from
`NVCM_CONTAINER_SCAN_POLICY_PROJECT`. The matrix also scans the exact pinned
upstream oauth2-proxy image shipped by the Helm chart on both architectures.

## Downstream Deployments

| Variable | Purpose |
| -------- | ------- |
| `NV_CONFIG_MANAGER_VALUES_PUSH_TOKEN` | Token with write access to the downstream values repository |
| `NVCM_VALUES_REPO_PATH` | Downstream values repository path |
| `NV_CONFIG_MANAGER_VALUES_REPO_URL` | Optional full downstream values repo override |
| `NVCM_TEST_NAMESPACE` | First test deployment namespace |
| `NVCM_TEST_VALUES_FILE_PATH` | Values file path for the first test environment |
| `NVCM_TEST_VALUES_BRANCH` | Values branch for the first test environment |
| `NVCM_TEST_CHART_BRANCH` | Source repo chart branch for the first test environment |
| `NVCM_TEST01_NAMESPACE` | Second test deployment namespace |
| `NVCM_TEST01_VALUES_FILE_PATH` | Values file path for the second test environment |
| `NVCM_TEST01_VALUES_BRANCH` | Values branch for the second test environment |
| `NVCM_TEST01_CHART_BRANCH` | Source repo chart branch for the second test environment |

For the `kiwi-test` migration, keep Argo CD on the existing app and branch names:

```text
NVCM_VALUES_REPO_PATH=example/nv-config-manager-values
NV_CONFIG_MANAGER_VALUES_REPO_URL=<unset>

NVCM_TEST_NAMESPACE=kiwi-test
NVCM_TEST_VALUES_FILE_PATH=cfa/values/nv-config-manager/values-aws-test.yaml
NVCM_TEST_VALUES_BRANCH=nvcm-kiwi-platform-test
NVCM_TEST_CHART_BRANCH=kiwi-test-deployment
```

The `kiwi-platform-test` ApplicationSet entry must reconcile `spec.sources`
during this cutover; do not keep `/spec/sources` in
`ignoreApplicationDifferences` while expecting the chart repo/value path change
to propagate.

The migration values file should set the old release/resource compatibility
names:

```yaml
nameOverride: kiwi-platform
fullnameOverride: kiwi-platform-test
secrets:
  vault:
    secretStoreName: vault-secretstore-kiwi
    networkSecretStoreName: vault-secretstore-kiwi-network
externalServices:
  nats:
    user: kiwi
    secretName: nats-kiwi
    externalSecretName: nats-kiwi-eso
temporal:
  configManagerWorker:
    nameSuffix: kiwi-worker
```

`kiwi-test01` is not migrated by this first cutover. Leave it on the old values
path and current appset branch names until its ApplicationSet element is pointed
at the `nv-config-manager` chart repository:

```text
NVCM_TEST01_NAMESPACE=kiwi-test01
NVCM_TEST01_VALUES_FILE_PATH=cfa/values/kiwi-platform/values-aws-test01.yaml
NVCM_TEST01_VALUES_BRANCH=kiwi-platform-test01
NVCM_TEST01_CHART_BRANCH=kiwi-test01-deployment
```

## Test-Environment Promote Pipeline (test / test01)

The GitOps promote flow (`pr-build.yml` + `promote-test-envs.yml`) replaces the
legacy `deploy-to-test*` jobs. It builds a PR once into immutable artifacts (a
versioned OCI Helm chart plus images referenced by digest) and promotes them by
committing a machine-written `deploy-state.yaml` to the environment's branch in
the downstream ArgoCD values repository. It targets ONLY the shared test
environments; production stays on the tag-driven release flow.

Security model: the image build runs in a separate pipeline on the unprotected
`pull-request/<n>` mirror ref with no secrets (no registry login; images are
handed over as job artifacts). The promote pipeline runs on protected `main`,
holds the protected variables, and only operates on the finished artifacts.
Because of that split, **every secret CI/CD variable in this project and its
groups must be flagged Protected** - unprotected variables are visible to the
untrusted `pull-request/*` builds. Never protect `pull-request/*` refs.

| Variable | Purpose |
| -------- | ------- |
| `NVCM_MIRROR_API_TOKEN` | Project access token (Reporter, `read_api`) used to poll build pipelines and list jobs; protected + masked |
| `NVCM_BUILD_TRIGGER_TOKEN` | Starts the secret-free build on `pull-request/<n>`. Two steps: create a token under **Settings → CI/CD → Pipeline triggers**, then store its value as this variable under **Settings → CI/CD → Variables** with protected + masked set, expand off. A job token cannot trigger a pipeline in its own project (GitLab returns HTTP 422), and a trigger token can only start pipelines, nothing else |
| `NVCM_TEST_ENV_TARGETS` | One record per env: `env\|env_branch\|namespace\|release_name\|baseline_values\|state_dir` (see `scripts/test_env_config.sh`) |
| `NVCM_CHART_REPO` | Helm repo URL ArgoCD reads the promoted chart from, e.g. `https://helm.ngc.nvidia.com/nvidian/cfa` (must match the `ngc` target in `NVCM_CHART_TARGETS`); written into deploy-state as `chartRepo` |
| `NVCM_UPSTREAM_GITHUB_REPO` | Optional override for the upstream GitHub repo checked by the stale-HEAD guard (default `NVIDIA/nv-config-manager`) |
| `NVCM_BUILD_POLL_INTERVAL` / `NVCM_BUILD_POLL_TIMEOUT` | Optional build-pipeline poll tuning (seconds; defaults 30 / 5400) |

Runbooks (run pipeline on the default branch):

- **Deploy a PR**: set `NVCM_PROMOTE_PR=<PR number>` and
  `NVCM_PROMOTE_ENV=test|test01`. The pipeline resolves the **vetted copy-pr-bot
  snapshot** (`pull-request/<n>`) from the mirror, reuses or triggers the
  no-secrets build, pushes images (capturing digests), publishes the chart as
  `0.0.0-pr<n>.<sha>`, validates the render against the env's baseline +
  overrides, and commits the deploy-state. Set `NVCM_PROMOTE_REUSE_BUILD=false`
  to force a rebuild.
  - What deploys is the *vetted snapshot*, which can lag the PR's live HEAD
    (untrusted authors re-copy only on `/ok to test`). If they differ, the run
    warns and proceeds; to deploy newer commits, re-vet them first. Set
    `NVCM_PROMOTE_REQUIRE_PR_HEAD=true` to hard-fail instead when the snapshot
    lags PR HEAD.
  - The run refuses a closed PR, and **fails closed if GitHub can't be reached**
    to confirm the PR is open. Set `NVCM_PROMOTE_ALLOW_UNVERIFIED_PR_STATE=true`
    to override during a GitHub outage.
- **Rollback**: set only `NVCM_PROMOTE_ENV`, start `test-rollback-env`. Without
  `NVCM_ROLLBACK_TO` it lists recent deploy-states and fails; re-run with
  `NVCM_ROLLBACK_TO=<env-branch commit sha>` to restore that exact snapshot
  (chart version + digests + pinned baseline revision).
- **Free a slot**: set only `NVCM_PROMOTE_ENV`, start `test-release-env`. It
  resets the env's deploy-state and overrides to the canonicals on the values
  repo's `main`.

Project settings required (GitLab UI):

- Maximum artifacts size ≥ 1.5 GB (the build hands images over as artifacts).
- Pull mirroring must replicate `pull-request/*` branches.
- Only `main` and release-tag patterns protected; `pull-request/*` unprotected.
- The **values repo** (`NVCM_VALUES_REPO_PATH`) must allow this project in its
  inbound **job token allowlist**. `test-promote-chart` reads the baseline and
  overrides with `CI_JOB_TOKEN` rather than the push token, since it only reads;
  without the allowlist entry that clone fails with an auth error. Only the
  deploy-state / rollback / release jobs use
  `NV_CONFIG_MANAGER_VALUES_PUSH_TOKEN`, and only they write.

## Air-Gapped Bundles

| Variable | Purpose |
| -------- | ------- |
| `AWS_ACCESS_KEY_ID` | AWS access key for air-gapped bundle uploads |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key for air-gapped bundle uploads |
| `NVCM_AIRGAPPED_S3_BUCKET` | S3 bucket for air-gapped bundles |
| `NVCM_AIRGAPPED_S3_REGION` | AWS region for air-gapped bundle uploads |
