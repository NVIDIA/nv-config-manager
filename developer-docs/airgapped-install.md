# Air-Gapped Installation Guide

Air-gapped deployments use a self-contained bundle built by `deploy/airgapped/create-airgapped.sh`. The bundle includes the Helm chart, container image tarballs, dependency charts and manifests, operator version pins, image loader manifests, an OCI registry upload helper, and the offline installer package.

## Build the Bundle

On an internet-connected build host:

```bash
cd deploy/airgapped
export NGC_API_KEY="your-ngc-api-key"
./create-airgapped.sh --version v1.0.0 --arch amd64
```

Add `--include-skopeo` to copy a local Skopeo binary into the bundle. The upload helper uses bundled Skopeo automatically when it is present. Pre-release E2E tests can pass `--local-image-fallback` after tagging local images to the same source references the chart renders. Missing images fail the bundle build by default; `--allow-missing-images` is only for diagnostics because that bundle may not install offline.

Build hosts need `helm`, `jq`, `curl`, a container runtime (`docker` or `containerd`/`ctr`), and `skopeo`. Skopeo is required as the image archive fallback when Docker cannot export an architecture-specific image directly.

Default bundles exclude Grafana and Loki charts/images because their OSS distributions are AGPLv3. Pass `--include-agpl-observability` only when that license is acceptable for the target environment.

The output is written to `deploy/airgapped/output/`.

## Transfer and Extract

```bash
scp output/nv-config-manager-airgapped-v1.0.0-amd64.tar.gz <target-host>:~/
ssh <target-host>
tar -xzf nv-config-manager-airgapped-v1.0.0-amd64.tar.gz
cd nv-config-manager-airgapped-v1.0.0-amd64
```

Expected bundle layout:

```text
helm/                    # NVIDIA Config Manager Helm chart and packaged chart
charts/                  # Dependency charts
images/                  # Image tarballs and image-list.txt
manifests/               # Image loader and operator manifests
installer/               # Offline installer wheel, dependencies, and install.sh
developer-docs/          # Optional developer documentation
tools/skopeo/            # Optional bundled Skopeo binary
upload-to-registry.sh    # OCI registry image and chart upload helper
operator-versions.env    # Dependency version pins
manifest.json            # Bundle metadata
```

## Upload Images and Chart

Push the bundled image archives and packaged chart to an OCI-compliant registry reachable by the target cluster:

```bash
./upload-to-registry.sh \
  --registry registry.example.com/nv-config-manager \
  --chart-registry registry.example.com/nv-config-manager/charts \
  --username '<user>' \
  --password-stdin
```

The helper writes `image-map.tsv` with source and target image references. Use that map when setting the image registry/prefix values in `install.yaml`. Pass `--include-dependency-charts` if you also want to mirror the dependency chart tarballs under `charts/`. For local HTTP registries used in tests, pass `--plain-http` so Helm chart upload uses HTTP. When using Docker mode with an architecture-specific bundle, pass `--platform linux/amd64` or `--platform linux/arm64` so Docker pushes a single-platform manifest.

## Image Loading Alternative

If the target environment does not have a registry, preload image tarballs onto the target nodes before deploying.

For Kind or single-node test clusters:

```bash
./manifests/load-airgapped-images.sh ./images
```

For multi-node clusters with shared storage for image tarballs:

```bash
./manifests/load-airgapped-images.sh /shared/nv-config-manager/images --daemonset
```

For SSH-based loading:

```bash
./manifests/load-airgapped-images.sh /shared/nv-config-manager/images \
  --ssh \
  --ssh-user admin \
  --ssh-key ~/.ssh/id_rsa
```

## Install the Offline Installer

```bash
./installer/install.sh
./installer/nv-config-manager-installer --help
```

The bootstrap script creates a local virtual environment from bundled wheels and does not require internet access on the target host.

## Create Configuration

Launch the TUI and save a repeatable config:

```bash
./installer/nv-config-manager-installer init --config install.yaml
```

Minimum settings to confirm:

| Section | Required Choices |
| ------- | ---------------- |
| Cluster | Hostname, namespace, environment, size, `airgapped: true` |
| Services | Enabled services for the deployment |
| App Secrets | Kubernetes secrets or ESO/Vault settings |
| Container Images | OCI registry targets from `image-map.tsv`, or preloaded image references |
| Infrastructure | TLS, load balancer provider, MetalLB/Cilium/NLB addresses if used |
| OS Images | Optional ZTP image PVC or S3 settings |
| Ingest Data | Optional Nautobot jobs and post-deploy jobs |

## Deploy

```bash
./installer/nv-config-manager-installer deploy install.yaml \
  --chart-dir helm \
  --image-source registry \
  --install-envoy-gateway \
  --install-cert-manager \
  --install-cnpg-operator \
  --helm-timeout 30m
```

When `cluster.airgapped` is true, the installer resolves operator manifests and dependency charts from the local bundle instead of the network. Images must already be present on the target nodes or be reachable from the configured OCI registry.

## Validate an Air-Gapped Bundle

Use this flow to test the same installer registry override path that production uses. Do not configure source-registry mirrors or manual Helm image values for this validation; the goal is to prove that `upload-to-registry.sh` plus `images.registry` is sufficient.

Build a bundle for the local machine architecture:

```bash
cd deploy/airgapped
./create-airgapped.sh \
  --version e2e \
  --arch amd64 \
  --include-skopeo \
  --local-image-fallback
```

Start a local registry and upload the extracted bundle:

```bash
docker run -d --restart=always -p 5001:5000 --name nvcm-airgap-registry registry:2
tar -xzf output/nv-config-manager-airgapped-e2e-amd64.tar.gz -C /tmp
cd /tmp/nv-config-manager-airgapped-e2e-amd64
./upload-to-registry.sh \
  --registry localhost:5001/nv-config-manager \
  --chart-registry localhost:5001/nv-config-manager/charts \
  --mode docker \
  --platform linux/amd64 \
  --skip-login \
  --include-dependency-charts \
  --plain-http \
  --map-file image-map.tsv
```

If the test cluster is Kind, configure containerd on the Kind nodes to allow `localhost:5001` as an HTTP registry. Then use an installer config with:

```yaml
cluster:
  airgapped: true
images:
  source: registry
  registry: localhost:5001/nv-config-manager
```

Deploy with the bundled chart and installer-managed dependencies:

```bash
./installer/nv-config-manager-installer deploy install.yaml \
  --chart-dir helm \
  --image-source registry \
  --install-envoy-gateway \
  --install-cert-manager \
  --install-cnpg-operator \
  --helm-timeout 30m
```

Validation passes when pods do not enter `ImagePullBackOff`, no workload tries to pull from public source registries, operator installs use local bundle artifacts, and `kubectl get pods -n nv-config-manager` reports ready workloads.

## Verify

```bash
kubectl get pods -n nv-config-manager -o wide
kubectl get svc -n nv-config-manager
kubectl get gateway -n nv-config-manager
kubectl get secret nautobot-admin -n nv-config-manager -o jsonpath='{.data.password}' | base64 -d && echo
```

Configure DNS or `/etc/hosts` for the selected base hostname and service subdomains:

```text
<GATEWAY-IP> config-manager.example.com nautobot.config-manager.example.com render.config-manager.example.com ztp.config-manager.example.com
<GATEWAY-IP> dhcp.config-manager.example.com workflow.config-manager.example.com temporal.config-manager.example.com config-store.config-manager.example.com
```

## Updating

Re-run the installer with the same config after changing values, staged content, or images:

```bash
./installer/nv-config-manager-installer deploy install.yaml --chart-dir helm --image-source registry --helm-timeout 30m
```

The deployer detects existing releases and restarts services only when relevant staged content changes.

## Uninstall

```bash
helm uninstall nv-config-manager -n nv-config-manager
kubectl delete namespace nv-config-manager
```

Operators such as Envoy Gateway, cert-manager, and CloudNativePG are cluster-level dependencies. Remove them only if they are not shared with other applications.

## Troubleshooting

| Symptom | Checks |
| ------- | ------ |
| ImagePullBackOff | Confirm image names and tags match `image-map.tsv`, registry credentials, or node containerd stores |
| Operator install fails offline | Confirm `manifests/`, `charts/`, and `operator-versions.env` are present in the bundle |
| Chart upload fails | Confirm Helm can authenticate to the target OCI chart namespace |
| LoadBalancer pending | Check MetalLB/Cilium/NLB configuration and address pools |
| ESO secrets not syncing | Check SecretStore, ExternalSecret status, Vault/OpenBao path mappings, and auth token secrets |
| Helm timeout | Increase `--helm-timeout`, inspect pod events, and verify storage class availability |
