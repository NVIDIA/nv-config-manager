# NVIDIA Config Manager Airgapped Manifests

Kubernetes manifests for air-gapped deployment support.

## Image Loader DaemonSet

The `image-loader-daemonset.yaml` runs a privileged pod on each node to import container images from tarball files directly into containerd.

### When to Use

Use this when deploying NVIDIA Config Manager to an air-gapped (offline) Kubernetes cluster that cannot pull images from the internet or NVCR.

### Prerequisites

1. Airgapped tarball extracted to a path accessible by all nodes (e.g., shared NFS mount, or copied to each node)
2. Kubernetes cluster using containerd as the container runtime
3. `kubectl` access to create DaemonSets and ConfigMaps

### Quick Start

```bash
# 1. Extract the airgapped tarball to shared storage
tar -xzf nv-config-manager-airgapped-*.tar.gz -C /shared/storage/

# 2. Edit the manifest to set the images path
# Update the hostPath.path under "- name: images" volume
vim image-loader-daemonset.yaml

# 3. Apply the DaemonSet
kubectl apply -f image-loader-daemonset.yaml

# 4. Watch pods start on each node
kubectl get pods -n nv-config-manager-airgapped -l app=nv-config-manager-image-loader -w

# 5. Check logs for import status
kubectl logs -n nv-config-manager-airgapped -l app=nv-config-manager-image-loader -f

# 6. Once all pods show "All images imported successfully!", delete the DaemonSet
kubectl delete -f image-loader-daemonset.yaml
# Or delete the entire namespace:
kubectl delete namespace nv-config-manager-airgapped
```

### Configuration

#### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CONTAINERD_SOCKET` | `/host/run/containerd/containerd.sock` | Path to containerd socket |
| `CTR_BINARY` | `/host/usr/bin/ctr` | Path to `ctr` binary |
| `IMAGES_DIR` | `/images` | Directory containing image tarballs (inside pod) |
| `NAMESPACE` | `k8s.io` | containerd namespace for imported images |

#### Volume Mounts

Update these in the manifest based on your environment:

```yaml
volumes:
- name: containerd-bin
  hostPath:
    # Standard location on most distros
    path: /usr/bin
    # Or for custom containerd installations:
    # path: /cm/local/apps/containerd/current/bin
    type: Directory
- name: images
  hostPath:
    # UPDATE THIS to your images directory
    path: /path/to/nv-config-manager-airgapped/images
    type: Directory
```

### Verifying Images

After the DaemonSet completes, verify images are available:

```bash
# SSH to a node or exec into a pod with ctr access
ctr -n k8s.io images ls | grep -E 'nv-config-manager|nautobot|temporal'
```

### Troubleshooting

#### Pods Not Starting

```bash
kubectl describe pod -n nv-config-manager-airgapped -l app=nv-config-manager-image-loader
```

Common issues:
- hostPath doesn't exist on nodes
- SELinux/AppArmor blocking access
- containerd socket in non-standard location

#### Images Not Loading

Check pod logs:
```bash
kubectl logs -n nv-config-manager-bootstrap <pod-name>
```

Common issues:
- Corrupt tarball files
- Architecture mismatch (amd64 images on arm64 nodes)
- Insufficient disk space

#### ctr Binary Not Found

Edit the manifest to set the correct path for your cluster:
```yaml
env:
- name: CTR_BINARY
  value: "/host/cm/local/apps/containerd/current/bin/ctr"  # Custom path
```

### Alternative: Direct `ctr` Import (No DaemonSet)

If you prefer to load images manually without the DaemonSet, use `ctr` directly:

**On real cluster nodes:**
```bash
# SSH to each node and import directly
ssh node1
cd /mnt/nfs/nv-config-manager-airgapped/images/
for tar in *.tar; do
  ctr -n k8s.io images import "$tar"
done
```

**On kind cluster nodes:**
```bash
# Copy images to kind node first
docker cp images/. kind-control-plane:/tmp/images/

# Import using ctr inside the kind container
docker exec kind-control-plane sh -c 'for tar in /tmp/images/*.tar; do ctr -n k8s.io images import "$tar"; done'
```

**Multi-node kind cluster:**
```bash
for node in $(kind get nodes --name my-cluster); do
  echo "Loading images on $node..."
  docker cp images/. "$node":/tmp/images/
  docker exec "$node" sh -c 'for tar in /tmp/images/*.tar; do ctr -n k8s.io images import "$tar"; done'
done
```

### ImagePullPolicy

After loading images, ensure your deployments use the correct imagePullPolicy:

```yaml
# Recommended - uses local if available
imagePullPolicy: IfNotPresent

# Or - never pull, fail if not local
imagePullPolicy: Never

# DON'T use - will try to pull from registry
imagePullPolicy: Always  # ❌
```

The NVIDIA Config Manager Helm chart defaults to `IfNotPresent` which works correctly with pre-loaded images. The installer should render `IfNotPresent` for pre-loaded air-gapped images.

### Cleanup

Images persist in containerd after deleting the DaemonSet. To remove:

```bash
# Delete DaemonSet
kubectl delete -f image-loader-daemonset.yaml

# Or delete namespace (also removes ConfigMap)
kubectl delete namespace nv-config-manager-airgapped
```

To remove loaded images from containerd (on each node):
```bash
# List NVIDIA Config Manager images
ctr -n k8s.io images ls | grep nv-config-manager

# Remove specific image
ctr -n k8s.io images rm <image-ref>
```

