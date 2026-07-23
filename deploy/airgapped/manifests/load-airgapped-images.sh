#!/bin/bash
# =============================================================================
# Load Airgapped Images to Cluster Nodes
# =============================================================================
# Loads container images directly into all Kubernetes cluster nodes.
# Supports Kind clusters (via docker exec) and real nodes (via SSH).
#
# Usage:
#   ./load-airgapped-images.sh <path-to-images-directory> [options]
#
# Options:
#   --daemonset          Use DaemonSet for parallel loading (faster for many nodes)
#   --ssh                Use SSH to connect to nodes (default: docker exec for Kind)
#   --ssh-user <user>    SSH username (default: ubuntu)
#   --ssh-key <path>     Path to SSH private key
#   --ctr-path <path>    Path to ctr binary on nodes (default: /usr/local/bin/ctr)
#   --ctr-bin-path <p>   Directory containing ctr binary (default: /usr/local/bin)
#   --platform <plat>    Platform to import (default: linux/amd64)
#
# Examples:
#   # Kind cluster - sequential (simple, good for small clusters)
#   ./load-airgapped-images.sh /path/to/images
#
#   # Kind cluster - parallel via DaemonSet (faster for 5+ nodes)
#   ./load-airgapped-images.sh /srv/nfs/kubedata/images --daemonset
#
#   # Real cluster via SSH
#   ./load-airgapped-images.sh /path/to/images --ssh --ssh-user admin --ssh-key ~/.ssh/id_rsa
#
#   # ARM64 cluster
#   ./load-airgapped-images.sh /path/to/images --platform linux/arm64
#
# After running this script, deploy with the offline installer and a config that sets cluster.airgapped: true.
# =============================================================================

set -e
set -o pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    local message="$1"
    echo -e "${BLUE}[INFO]${NC} $message"
    return 0
}

log_success() {
    local message="$1"
    echo -e "${GREEN}[SUCCESS]${NC} $message"
    return 0
}

log_warning() {
    local message="$1"
    echo -e "${YELLOW}[WARNING]${NC} $message"
    return 0
}

log_error() {
    local message="$1"
    echo -e "${RED}[ERROR]${NC} $message" >&2
    return 0
}

# Defaults
IMAGES_PATH=""
USE_SSH=false
SSH_USER="ubuntu"
SSH_KEY=""
CTR_PATH="/usr/local/bin/ctr"
PLATFORM="linux/amd64"
USE_DAEMONSET=false
CTR_BIN_PATH="/usr/local/bin"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --ssh)
            USE_SSH=true
            shift
            ;;
        --ssh-user)
            SSH_USER="$2"
            shift 2
            ;;
        --ssh-key)
            SSH_KEY="$2"
            shift 2
            ;;
        --ctr-path)
            CTR_PATH="$2"
            shift 2
            ;;
        --ctr-bin-path)
            CTR_BIN_PATH="$2"
            shift 2
            ;;
        --platform)
            PLATFORM="$2"
            shift 2
            ;;
        --daemonset)
            USE_DAEMONSET=true
            shift
            ;;
        -h|--help)
            head -30 "$0" | tail -25
            exit 0
            ;;
        *)
            if [[ -z "$IMAGES_PATH" ]]; then
                IMAGES_PATH="$1"
            else
                log_error "Unknown argument: $1"
                exit 1
            fi
            shift
            ;;
    esac
done

# Show usage if no path provided
if [[ -z "$IMAGES_PATH" ]]; then
    echo "Usage: $0 <path-to-images-directory> [options]"
    echo ""
    echo "Options:"
    echo "  --daemonset          Use DaemonSet for parallel loading (faster for 5+ nodes)"
    echo "  --ssh                Use SSH to connect to nodes (default: docker exec)"
    echo "  --ssh-user <user>    SSH username (default: ubuntu)"
    echo "  --ssh-key <path>     Path to SSH private key"
    echo "  --ctr-path <path>    Path to ctr binary on nodes (default: /usr/local/bin/ctr)"
    echo "  --ctr-bin-path <p>   Directory containing ctr (for daemonset, default: /usr/local/bin)"
    echo "  --platform <plat>    Platform to import (default: linux/amd64)"
    echo ""
    echo "Examples:"
    echo "  # Sequential (simple, good for small clusters)"
    echo "  $0 /srv/nfs/kubedata/images"
    echo ""
    echo "  # Parallel via DaemonSet (faster for many nodes)"
    echo "  $0 /srv/nfs/kubedata/images --daemonset"
    exit 1
fi

if [[ ! -d "$IMAGES_PATH" ]]; then
    log_error "Images directory not found: $IMAGES_PATH"
    exit 1
fi

echo ""
echo "=============================================="
echo "  Loading Airgapped Images to Cluster Nodes"
echo "=============================================="
echo ""
log_info "Images path: $IMAGES_PATH"
log_info "Connection method: $(if $USE_SSH; then echo "SSH"; else echo "docker exec"; fi)"
log_info "Platform: $PLATFORM"

# Check for required tools
if ! command -v kubectl &> /dev/null; then
    log_error "kubectl is required but not installed"
    exit 1
fi

if $USE_SSH; then
    if ! command -v ssh &> /dev/null; then
        log_error "ssh is required but not installed"
        exit 1
    fi
    if ! command -v scp &> /dev/null; then
        log_error "scp is required but not installed"
        exit 1
    fi
else
    if ! command -v docker &> /dev/null; then
        log_error "docker is required but not installed (use --ssh for non-Kind clusters)"
        exit 1
    fi
fi

# Build SSH options
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o LogLevel=ERROR"
if [[ -n "$SSH_KEY" ]]; then
    SSH_OPTS="$SSH_OPTS -i $SSH_KEY"
fi

# Get node information
if $USE_SSH; then
    # For SSH, get node IPs - use go-template for reliable newline handling
    NODES=$(kubectl get nodes -o go-template='{{range .items}}{{.metadata.name}}:{{range .status.addresses}}{{if eq .type "InternalIP"}}{{.address}}{{end}}{{end}}{{"\n"}}{{end}}' | grep -v '^$')
else
    # For docker exec, just get node names
    NODES=$(kubectl get nodes -o jsonpath='{.items[*].metadata.name}')
fi

if [[ -z "$NODES" ]]; then
    log_error "No nodes found in cluster. Is the cluster running?"
    exit 1
fi

# Count nodes properly - for SSH mode count lines, for docker mode count words
if $USE_SSH; then
    NODE_COUNT=$(echo "$NODES" | wc -l | tr -d ' ')
else
    NODE_COUNT=$(echo "$NODES" | wc -w | tr -d ' ')
fi
log_info "Found $NODE_COUNT node(s)"

# Count images
IMAGE_FILES=$(ls -1 "$IMAGES_PATH"/*.tar 2>/dev/null || true)
IMAGE_COUNT=$(echo "$IMAGE_FILES" | grep -c '.tar$' || echo 0)

if [[ "$IMAGE_COUNT" -eq 0 ]]; then
    log_error "No .tar files found in $IMAGES_PATH"
    exit 1
fi

log_info "Found $IMAGE_COUNT image tarball(s) to load"

# Calculate total size
TOTAL_SIZE=$(du -sh "$IMAGES_PATH" | cut -f1)
log_info "Total images size: $TOTAL_SIZE"
log_info "Mode: $(if $USE_DAEMONSET; then echo "DaemonSet (parallel)"; else echo "Sequential"; fi)"
echo ""

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

# Function to run command on node
run_on_node() {
    local node_name="$1"
    local node_ip="$2"
    local cmd="$3"
    
    if $USE_SSH; then
        # -n prevents ssh from reading stdin (important when called in a while-read loop)
        ssh -n $SSH_OPTS "${SSH_USER}@${node_ip}" "$cmd" || return $?
    else
        docker exec "$node_name" bash -c "$cmd" || return $?
    fi
    return 0
}

# Function to copy files to node
copy_to_node() {
    local node_name="$1"
    local node_ip="$2"
    local src="$3"
    local dst="$4"
    
    if $USE_SSH; then
        scp $SSH_OPTS -r "$src" "${SSH_USER}@${node_ip}:${dst}" || return $?
    else
        docker cp "$src" "${node_name}:${dst}" || return $?
    fi
    return 0
}

# Function to detect ctr binary path on a node
detect_ctr_path() {
    local node_name="$1"
    local node_ip="$2"
    
    run_on_node "$node_name" "$node_ip" "
        if command -v ctr >/dev/null 2>&1; then
            command -v ctr
        elif ls /cm/local/apps/containerd/*/bin/ctr >/dev/null 2>&1; then
            ls /cm/local/apps/containerd/*/bin/ctr 2>/dev/null | head -1
        elif [ -x /usr/local/bin/ctr ]; then
            echo /usr/local/bin/ctr
        elif [ -x /usr/bin/ctr ]; then
            echo /usr/bin/ctr
        fi
    " || return $?
    return 0
}

# =============================================================================
# DAEMONSET MODE - Parallel loading via Kubernetes DaemonSet
# =============================================================================
if [[ "$USE_DAEMONSET" == "true" ]]; then
    log_info "Using DaemonSet for parallel image loading..."
    echo ""
    
    # Find busybox tarball (required for daemonset)
    BUSYBOX_TAR="$IMAGES_PATH/docker.io-library-busybox-1.36.tar"
    if [[ ! -f "$BUSYBOX_TAR" ]]; then
        BUSYBOX_TAR=$(find "$IMAGES_PATH" -name "*busybox*1.36*.tar" 2>/dev/null | head -1)
    fi
    
    if [[ -z "$BUSYBOX_TAR" || ! -f "$BUSYBOX_TAR" ]]; then
        log_error "busybox:1.36 tarball not found in $IMAGES_PATH"
        log_error "DaemonSet requires busybox to be pre-loaded on all nodes"
        exit 1
    fi
    
    # Find the daemonset manifest
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    DAEMONSET_MANIFEST=""
    for path in "$SCRIPT_DIR/image-loader-daemonset.yaml" \
                "$SCRIPT_DIR/../manifests/image-loader-daemonset.yaml" \
                "$(dirname "$IMAGES_PATH")/manifests/image-loader-daemonset.yaml"; do
        if [[ -f "$path" ]]; then
            DAEMONSET_MANIFEST="$path"
            break
        fi
    done
    
    if [[ -z "$DAEMONSET_MANIFEST" ]]; then
        log_error "Could not find image-loader-daemonset.yaml"
        exit 1
    fi
    
    EXPECTED_PODS=$NODE_COUNT
    
    if $USE_SSH; then
        # =================================================================
        # SSH MODE: Copy images to nodes, then use DaemonSet to import
        # =================================================================
        log_info "Mode: SSH + DaemonSet (parallel copy, parallel import)"
        echo ""
        
        # Step 1: Copy images to all nodes in parallel
        log_info "Step 1: Copying images to all nodes in parallel..."
        COPY_PIDS=()
        while IFS= read -r node_info; do
            [[ -z "$node_info" ]] && continue
            node_name=$(echo "$node_info" | cut -d: -f1)
            node_ip=$(echo "$node_info" | cut -d: -f2)
            
            (
                echo "  [$node_name] Starting copy..."
                ssh -n $SSH_OPTS "${SSH_USER}@${node_ip}" "sudo rm -rf /var/tmp/nv-config-manager-images; mkdir -p /var/tmp/nv-config-manager-images" 2>/dev/null
                scp $SSH_OPTS -r "$IMAGES_PATH/." "${SSH_USER}@${node_ip}:/var/tmp/nv-config-manager-images/" >/dev/null 2>&1
                echo "  [$node_name] Copy complete"
            ) &
            COPY_PIDS+=($!)
        done <<< "$NODES"
        
        # Wait for all copies to complete
        log_info "  Waiting for copies to complete..."
        COPY_FAILED=0
        for pid in "${COPY_PIDS[@]}"; do
            if ! wait "$pid"; then
                ((COPY_FAILED++))
            fi
        done
        
        if [[ $COPY_FAILED -gt 0 ]]; then
            log_warning "$COPY_FAILED node(s) failed to copy"
        fi
        log_success "✓ Images copied to all nodes"
        echo ""
        
        # Step 2: Pre-load busybox on all nodes
        log_info "Step 2: Pre-loading busybox:1.36 to all nodes..."
        while IFS= read -r node_info; do
            [[ -z "$node_info" ]] && continue
            node_name=$(echo "$node_info" | cut -d: -f1)
            node_ip=$(echo "$node_info" | cut -d: -f2)
            
            CTR_PATH_NODE=$(detect_ctr_path "$node_name" "$node_ip" 2>/dev/null)
            if [[ -n "$CTR_PATH_NODE" ]]; then
                echo "  [$node_name] Loading busybox..."
                ssh -n $SSH_OPTS "${SSH_USER}@${node_ip}" "sudo $CTR_PATH_NODE -n k8s.io images import --platform $PLATFORM /var/tmp/nv-config-manager-images/docker.io-library-busybox-1.36.tar" 2>/dev/null || true
            fi
        done <<< "$NODES"
        log_success "✓ busybox:1.36 loaded on all nodes"
        echo ""
        
        # Step 3: Detect ctr path for DaemonSet (use first node as reference)
        FIRST_NODE_INFO=$(echo "$NODES" | head -1)
        FIRST_NODE_NAME=$(echo "$FIRST_NODE_INFO" | cut -d: -f1)
        FIRST_NODE_IP=$(echo "$FIRST_NODE_INFO" | cut -d: -f2)
        CTR_BIN_DETECTED=$(detect_ctr_path "$FIRST_NODE_NAME" "$FIRST_NODE_IP" 2>/dev/null)
        CTR_BIN_DIR=$(dirname "$CTR_BIN_DETECTED")
        log_info "Detected ctr binary directory: $CTR_BIN_DIR"
        
        # Step 4: Deploy DaemonSet
        log_info "Step 3: Deploying image-loader DaemonSet..."
        sed -e "s|path: /mnt/nfs/nv-config-manager-airgapped-v1.0.0/images|path: /var/tmp/nv-config-manager-images|g" \
            -e "s|path: /usr/local/bin|path: ${CTR_BIN_DIR}|g" \
            "$DAEMONSET_MANIFEST" | kubectl apply -f -
    else
        # =================================================================
        # KIND MODE: Use docker commands (original behavior)
        # =================================================================
        log_info "Mode: Kind cluster (docker exec)"
        echo ""
        
        # Step 1: Load busybox to all nodes
        log_info "Step 1: Pre-loading busybox:1.36 to all nodes..."
        for node_name in $NODES; do
            log_info "  Loading busybox on $node_name..."
            docker cp "$BUSYBOX_TAR" "$node_name:/var/tmp/busybox.tar"
            docker exec "$node_name" ctr -n k8s.io images import --platform linux/amd64 /var/tmp/busybox.tar 2>/dev/null || true
            docker exec "$node_name" rm -f /var/tmp/busybox.tar
        done
        log_success "✓ busybox:1.36 loaded on all nodes"
        echo ""
        
        # Step 2: Deploy DaemonSet (images accessed via hostPath)
        log_info "Step 2: Deploying image-loader DaemonSet..."
    sed -e "s|path: /mnt/nfs/nv-config-manager-airgapped-v1.0.0/images|path: ${IMAGES_PATH}|g" \
        -e "s|path: /usr/local/bin|path: ${CTR_BIN_PATH}|g" \
        "$DAEMONSET_MANIFEST" | kubectl apply -f -
    fi

    echo ""
    log_info "Step 4: Waiting for DaemonSet pods to start..."
    sleep 5
    
    TIMEOUT=120
    ELAPSED=0
    while [[ $ELAPSED -lt $TIMEOUT ]]; do
        RUNNING=$(kubectl get pods -n nv-config-manager-airgapped -l app=nv-config-manager-image-loader --no-headers 2>/dev/null | grep -c "Running" || echo 0)
        RUNNING=$(echo "$RUNNING" | tr -d '[:space:]')
        if [[ "$RUNNING" -ge "$EXPECTED_PODS" ]]; then
            break
        fi
        echo "  Waiting for pods... ($RUNNING/$EXPECTED_PODS running)"
        sleep 5
        ELAPSED=$((ELAPSED + 5))
    done
    
    log_success "✓ All $EXPECTED_PODS pods running"
    echo ""
    
    # Wait for all pods to complete
    log_info "Step 5: Waiting for all nodes to complete image loading..."
    echo "  (All $EXPECTED_PODS nodes importing in parallel)"
    
    TIMEOUT=600
    ELAPSED=0
    COMPLETED=0
    
    while [[ $ELAPSED -lt $TIMEOUT ]]; do
        COMPLETED=0
        for pod in $(kubectl get pods -n nv-config-manager-airgapped -l app=nv-config-manager-image-loader -o jsonpath='{.items[*].metadata.name}' 2>/dev/null); do
            if kubectl logs -n nv-config-manager-airgapped "$pod" --all-containers 2>/dev/null | grep -q "All images imported successfully!"; then
                COMPLETED=$((COMPLETED + 1))
            fi
        done
        
        echo "  Progress: $COMPLETED/$EXPECTED_PODS nodes completed"
        
        if [[ "$COMPLETED" -ge "$EXPECTED_PODS" ]]; then
            echo ""
            log_success "✓ All $EXPECTED_PODS nodes completed!"
            break
        fi
        
        sleep 10
        ELAPSED=$((ELAPSED + 10))
    done
    
    if [[ $ELAPSED -ge $TIMEOUT && "$COMPLETED" -lt "$EXPECTED_PODS" ]]; then
        log_warning "Timeout waiting for all nodes. $COMPLETED/$EXPECTED_PODS completed."
        log_info "Check pod logs: kubectl logs -n nv-config-manager-airgapped -l app=nv-config-manager-image-loader --all-containers"
    fi
    
    # Cleanup
    log_info "Step 6: Cleaning up..."
    kubectl delete namespace nv-config-manager-airgapped --wait=false 2>/dev/null || true
    
    if $USE_SSH; then
        log_info "Cleaning up temp files on nodes..."
        while IFS= read -r node_info; do
            [[ -z "$node_info" ]] && continue
            node_name=$(echo "$node_info" | cut -d: -f1)
            node_ip=$(echo "$node_info" | cut -d: -f2)
            ssh -n $SSH_OPTS "${SSH_USER}@${node_ip}" "sudo rm -rf /var/tmp/nv-config-manager-images" 2>/dev/null &
        done <<< "$NODES"
        wait
    fi
    
    echo ""
    log_success "Image loading complete (parallel via DaemonSet)!"
    echo ""
    echo "Next steps:"
    echo "  Deploy with --airgapped flag:"
    echo ""
    echo "    ./installer/nvcm-installer deploy install.yaml --chart-dir helm --image-source registry \\"
    echo "      --airgapped \\"
    echo "      --auto-generate-secrets --yes"
    echo ""
    exit 0
fi

# =============================================================================
# SEQUENTIAL MODE - Load images node by node
# =============================================================================

# Load images into each node
FAILED_NODES=()

if $USE_SSH; then
    # SSH mode - parse node:ip format
    PROCESSED_COUNT=0
    log_info "Nodes to process:"
    echo "$NODES" | while IFS= read -r line; do echo "  - $line"; done
    echo ""
    
    while IFS= read -r node_info; do
        [[ -z "$node_info" ]] && continue
        node_name=$(echo "$node_info" | cut -d: -f1)
        node_ip=$(echo "$node_info" | cut -d: -f2)
        
        # Validate we got both name and IP
        if [[ -z "$node_name" || -z "$node_ip" || "$node_name" == "$node_ip" ]]; then
            log_warning "Invalid node entry: '$node_info', skipping..."
            continue
        fi
        
        echo "----------------------------------------------"
        log_info "Processing node: $node_name ($node_ip)"
        
        # Test SSH connection (-n to not consume stdin from while-read loop)
        if ! ssh -n $SSH_OPTS "${SSH_USER}@${node_ip}" "echo ok" &>/dev/null; then
            log_warning "Cannot connect to $node_name via SSH, skipping..."
            FAILED_NODES+=("$node_name")
            continue
        fi
        
        # Create temp directory on node
        log_info "Preparing temp directory on $node_name..."
        run_on_node "$node_name" "$node_ip" "sudo rm -rf /var/tmp/nv-config-manager-images; mkdir -p /var/tmp/nv-config-manager-images"
        
        # Copy images to node
        log_info "Copying images to $node_name:/var/tmp/nv-config-manager-images (this may take a while)..."
        if ! copy_to_node "$node_name" "$node_ip" "$IMAGES_PATH/." "/var/tmp/nv-config-manager-images/"; then
            log_error "Failed to copy images to $node_name"
            FAILED_NODES+=("$node_name")
            continue
        fi
        
        # Find ctr binary on the node
        # If --ctr-path was specified and differs from default, use it; otherwise auto-detect
        if [[ "$CTR_PATH" != "/usr/local/bin/ctr" ]]; then
            # User specified a custom path
            if run_on_node "$node_name" "$node_ip" "[ -x '$CTR_PATH' ]"; then
                CTR_ACTUAL="$CTR_PATH"
            else
                log_error "Specified ctr path not found on $node_name: $CTR_PATH"
                FAILED_NODES+=("$node_name")
                continue
            fi
        else
            # Auto-detect ctr
            CTR_ACTUAL=$(detect_ctr_path "$node_name" "$node_ip")
            if [[ -z "$CTR_ACTUAL" ]]; then
                log_error "ctr binary not found on $node_name (checked: PATH, /cm/local/apps/containerd/*/bin/ctr, /usr/local/bin/ctr, /usr/bin/ctr)"
                FAILED_NODES+=("$node_name")
                continue
            fi
        fi
        log_info "Using ctr at: $CTR_ACTUAL"
        
        # Import images into containerd
        log_info "Importing images into containerd on $node_name..."
        run_on_node "$node_name" "$node_ip" "
            IMPORT_OK=0
            IMPORT_FAIL=0
            for tarfile in /var/tmp/nv-config-manager-images/*.tar; do
                if [[ -f \"\$tarfile\" ]]; then
                    BASENAME=\$(basename \"\$tarfile\")
                    echo \"  Importing: \$BASENAME\"
                    OUTPUT=\$(sudo $CTR_ACTUAL -n k8s.io images import --platform $PLATFORM \"\$tarfile\" 2>&1)
                    if [[ \$? -eq 0 ]]; then
                        ((IMPORT_OK++))
                    else
                        if echo \"\$OUTPUT\" | grep -q 'already exists'; then
                            echo \"    (already exists)\"
                            ((IMPORT_OK++))
                        else
                            echo \"    ERROR: \$OUTPUT\"
                            ((IMPORT_FAIL++))
                        fi
                    fi
                fi
            done
            echo \"\"
            echo \"  Imported: \$IMPORT_OK, Failed: \$IMPORT_FAIL\"
        "
        
        # Verify nv-config-manager image was loaded (quick check for one image)
        if run_on_node "$node_name" "$node_ip" "sudo $CTR_ACTUAL -n k8s.io images list -q 2>/dev/null | grep -q 'nvcr.io/nvidian/cfa/nv-config-manager'"; then
            log_info "Verified: nv-config-manager images present"
        else
            log_warning "Verification failed: nv-config-manager images not found on $node_name!"
        fi
        
        # Cleanup (don't fail if cleanup fails)
        log_info "Cleaning up temp files on $node_name..."
        run_on_node "$node_name" "$node_ip" "sudo rm -rf /var/tmp/nv-config-manager-images" || log_warning "Cleanup failed on $node_name (non-fatal)"
        
        log_success "Completed $node_name"
        PROCESSED_COUNT=$((PROCESSED_COUNT + 1))
        echo ""
    done <<< "$NODES"
    
    log_info "Processed $PROCESSED_COUNT node(s)"
else
    # Docker exec mode (Kind clusters)
    for node_name in $NODES; do
        echo "----------------------------------------------"
        log_info "Processing node: $node_name"
        
        # Check if node container exists and is running
        if ! docker ps --format '{{.Names}}' | grep -q "^${node_name}$"; then
            log_warning "Container $node_name not found or not running, skipping..."
            FAILED_NODES+=("$node_name")
            continue
        fi
        
        # Create temp directory on node
        log_info "Preparing temp directory on $node_name..."
        docker exec "$node_name" rm -rf /var/tmp/nv-config-manager-images 2>/dev/null || true
        docker exec "$node_name" mkdir -p /var/tmp/nv-config-manager-images
        
        # Copy images to node
        log_info "Copying images to $node_name:/var/tmp/nv-config-manager-images (this may take a while)..."
        if ! docker cp "$IMAGES_PATH/." "$node_name:/var/tmp/nv-config-manager-images/"; then
            log_error "Failed to copy images to $node_name"
            FAILED_NODES+=("$node_name")
            continue
        fi
        
        # Import each image into containerd
        log_info "Importing images into containerd on $node_name..."
        docker exec "$node_name" bash -c "
            IMPORT_COUNT=0
            SKIP_COUNT=0
            
            for tarfile in /var/tmp/nv-config-manager-images/*.tar; do
                if [[ -f \"\$tarfile\" ]]; then
                    BASENAME=\$(basename \"\$tarfile\")
                    if ctr -n k8s.io images import --platform $PLATFORM \"\$tarfile\" 2>/dev/null; then
                        ((IMPORT_COUNT++))
                        echo \"  ✓ \$BASENAME\"
                    else
                        ((SKIP_COUNT++))
                        echo \"  ○ \$BASENAME (already exists or failed)\"
                    fi
                fi
            done
            
            echo \"\"
            echo \"  Imported: \$IMPORT_COUNT, Skipped/Existing: \$SKIP_COUNT\"
        "
        
        # Cleanup temp files on node
        log_info "Cleaning up temp files on $node_name..."
        docker exec "$node_name" rm -rf /var/tmp/nv-config-manager-images
        
        log_success "Completed $node_name"
        echo ""
    done
fi

# Summary
echo "=============================================="
echo "  Summary"
echo "=============================================="

if [[ ${#FAILED_NODES[@]} -gt 0 ]]; then
    log_warning "Failed nodes: ${FAILED_NODES[*]}"
fi

echo ""
log_success "Image loading complete!"
echo ""
echo "Next steps:"
echo "  Deploy with --airgapped flag (images are already loaded, no DaemonSet needed):"
echo ""
echo "    ./installer/nvcm-installer deploy install.yaml --chart-dir helm --image-source registry \\"
echo "      --airgapped \\"
echo "      --auto-generate-secrets --yes"
echo ""
