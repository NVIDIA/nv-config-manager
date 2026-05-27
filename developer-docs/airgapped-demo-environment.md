# Air-Gapped Demo Environment

This guide is a compact demo flow for proving an offline install. It assumes a prepared Kubernetes or Kind cluster and uses the offline installer from the air-gapped bundle.

## Prepare the Demo Host

Install cluster prerequisites on the demo VM before disconnecting it from the network:

```bash
./deploy/scripts/setup-vm-prereqs.sh \
  --cluster-name nv-config-manager-demo \
  --keycloak-hostname keycloak.config-manager.demo \
  --spiffe-trust-domain config-manager.demo
```

Optional components, such as SPIRE, Keycloak, OpenBao, External Secrets Operator, MetalLB, and NFS, can be installed by the setup script depending on demo scope.

## Transfer the Bundle

```bash
scp deploy/airgapped/output/nv-config-manager-airgapped-v1.0.0-amd64.tar.gz demo-host:~/
ssh demo-host
tar -xzf nv-config-manager-airgapped-v1.0.0-amd64.tar.gz
cd nv-config-manager-airgapped-v1.0.0-amd64
```

## Simulate Network Isolation

If the demo requires proof that the install is offline, block outbound internet after the bundle and prerequisites are present. Keep SSH access open and leave access to the internal OCI registry open.

```bash
sudo iptables -I OUTPUT -p tcp --dport 443 -j REJECT
sudo iptables -I OUTPUT -p tcp --dport 80 -j REJECT
```

Remove these rules after the demo or before troubleshooting external dependencies.

## Upload Images and Chart

If the demo environment has an internal OCI registry, push the images and packaged chart there:

```bash
./upload-to-registry.sh \
  --registry registry.config-manager.demo/nv-config-manager \
  --chart-registry registry.config-manager.demo/nv-config-manager/charts \
  --username '<user>' \
  --password-stdin
```

The command writes `image-map.tsv`; use the target image references from that file in `demo-install.yaml`.

## Image Loading Alternative

For a Kind demo or any demo without a registry, preload images directly onto the cluster nodes:

```bash
./manifests/load-airgapped-images.sh ./images --daemonset
```

For a small Kind demo, sequential loading is also acceptable:

```bash
./manifests/load-airgapped-images.sh ./images
```

## Install and Configure

```bash
./installer/install.sh
./installer/nv-config-manager-installer init --config demo-install.yaml
```

Recommended demo settings:

| Section | Value |
| ------- | ----- |
| Cluster hostname | `config-manager.demo` |
| Namespace | `nv-config-manager` |
| Airgapped | enabled |
| Size | `small` or `medium` |
| Mock devices | enabled for local demos |
| Services | all enabled unless the demo is scoped |
| Images | OCI registry targets from `image-map.tsv`, or preloaded image references |
| Ingest data | include mock topology jobs when showing end-to-end workflows |

## Deploy

```bash
./installer/nv-config-manager-installer deploy demo-install.yaml \
  --chart-dir helm \
  --image-source registry \
  --install-envoy-gateway \
  --install-cert-manager \
  --install-cnpg-operator \
  --helm-timeout 30m
```

## Access

Add host entries pointing at the gateway IP or local forwarded address:

```text
127.0.0.1 config-manager.demo nautobot.config-manager.demo render.config-manager.demo ztp.config-manager.demo dhcp.config-manager.demo workflow.config-manager.demo temporal.config-manager.demo config-store.config-manager.demo
```

Verify:

```bash
kubectl get pods -n nv-config-manager
kubectl get svc -n nv-config-manager
curl -k https://nautobot.config-manager.demo/health
```

## Demo Talking Points

- The bundle contains images, chart source, a packaged chart, dependency charts, operator manifests, a registry upload helper, and an offline installer.
- The installer config is repeatable and can be checked into a secure internal GitOps workflow after secrets are removed or externalized.
- Existing stream names and subjects are configuration, not code assumptions.
- Re-runs only restart services when relevant staged content changes.

## Troubleshooting

| Symptom | Checks |
| ------- | ------ |
| Images not loading | Confirm image tarballs exist and the node runtime is containerd or Docker as expected |
| ImagePullBackOff | Compare pod image names with `image-map.tsv` or `images/image-list.txt` |
| Chart upload fails | Confirm Helm can authenticate to the target OCI chart namespace |
| Gateway not reachable | Check Envoy Gateway status and host mappings |
| Jobs not running | Check `content.run_after_deploy` in the installer config and Nautobot logs |
| Storage pending | Confirm the storage class supports the configured access mode |
