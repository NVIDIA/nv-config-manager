# Deploying NVIDIA Config Manager on a Remote VM

This guide describes the supported remote VM path: create a Kind cluster, deploy through `nv-config-manager-installer`, and access services through SSH forwarding, DNS, or `/etc/hosts` entries.

## Recommended VM Sizes

| Profile | Use Case | Suggested VM |
| ------- | -------- | ------------ |
| `small` | Single-user development | 8 vCPU, 24 GB RAM, 100 GB disk |
| `medium` | Shared remote development | 16 vCPU, 64 GB RAM, 250 GB disk |
| `large` | Production-like validation | 3+ nodes, 96 vCPU total, 256 GB RAM total |

Set the selected profile in `cluster.size` in the installer config.

## Prerequisites

Install Docker, kubectl, Helm, Kind, git, and uv on the VM.

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
kind version
kubectl version --client
helm version
```

## Create the Cluster

```bash
kind create cluster --name nv-config-manager --config deploy/kind-config.yaml --wait 5m
kubectl cluster-info
```

## Deploy

Use the bundled config profile or copy it and edit `cluster.hostname`, `cluster.size`, sites, secrets, image settings, and content paths.

```bash
make kind-up INSTALL_CONFIG=deploy/configs/local-superpod.yaml HELM_TIMEOUT=20m
```

Equivalent headless installer command:

```bash
cd installer
uv run nv-config-manager-installer deploy ../deploy/configs/local-superpod.yaml \
  --image-source local \
  --build-images \
  --load-kind \
  --kind-cluster nv-config-manager \
  --install-envoy-gateway \
  --install-cnpg-operator \
  --install-cert-manager \
  --helm-timeout 20m
```

## Verify

```bash
kubectl get pods -n nv-config-manager -o wide
kubectl get svc -n nv-config-manager
kubectl get gateway -n nv-config-manager
kubectl logs -n nv-config-manager deployment/nv-config-manager-render-api -f
```

## Access Options

### SSH Port Forwarding

Forward the Envoy Gateway from the VM to your workstation:

```bash
ssh -L 8443:127.0.0.1:443 <user>@<vm-ip>
```

Add local host entries pointing at `127.0.0.1` and browse with the configured base hostname, for example `config-manager.local`.

### Direct VM Access

Point DNS or `/etc/hosts` at the VM IP:

```text
<VM-IP> config-manager.local nautobot.config-manager.local render.config-manager.local ztp.config-manager.local
<VM-IP> dhcp.config-manager.local workflow.config-manager.local config-store.config-manager.local temporal.config-manager.local
```

### kubectl Port Forward

```bash
kubectl port-forward -n nv-config-manager svc/nautobot 8080:80
kubectl port-forward -n nv-config-manager svc/temporal-ui 8081:8080
```

## Multi-Node Notes

For multi-node Kind or production-like clusters, use RWX storage for shared job, template, and OS image PVCs, or set node selectors so RWO PVCs and pods land on the same node. MetalLB or a cloud load balancer is required for device-facing ZTP and DHCP access.

## Cleanup

```bash
helm uninstall nv-config-manager -n nv-config-manager
kubectl delete namespace nv-config-manager
kind delete cluster --name nv-config-manager
```

## Troubleshooting

| Symptom | Checks |
| ------- | ------ |
| Docker permission denied | Confirm the user is in the `docker` group and has a new login session |
| Pods pending | Check CPU, memory, storage class, and PVC binding events |
| Gateway unreachable | Check Envoy Gateway pods, Gateway status, and host resolution |
| Image pull failures | Confirm local image tags were built and loaded, or registry credentials are valid |
| Jobs not visible | Re-run the installer and check Nautobot pod logs after jobs PVC staging |

