#!/bin/bash
# =============================================================================
# Copy Secrets from Production Vault to Local OpenBao
# =============================================================================
# This script reads secrets from a production HashiCorp Vault and copies them
# to a local OpenBao instance for ESO testing.
#
# Prerequisites:
#   - vault CLI installed (works with both Vault and OpenBao)
#   - kubectl access to the cluster with OpenBao
#   - Valid authentication to production Vault
#
# Usage:
#   ./scripts/copy-vault-secrets.sh copy <path> [<path2> ...]
#   ./scripts/copy-vault-secrets.sh generate [environment]
#   ./scripts/copy-vault-secrets.sh list [path]
#
# Examples:
#   # Copy a specific path (recursively)
#   ./scripts/copy-vault-secrets.sh copy my-engine/my-org/nv-config-manager/prod/
#
#   # Copy multiple paths
#   ./scripts/copy-vault-secrets.sh copy \
#     my-engine/my-org/nv-config-manager/dev/nautobot \
#     my-engine/my-org/nv-config-manager/dev/redis
#
#   # Generate test secrets
#   ./scripts/copy-vault-secrets.sh generate dev
#
#   # List secrets in local OpenBao
#   ./scripts/copy-vault-secrets.sh list nv-config-manager/dev
# =============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

# =============================================================================
# Configuration
# =============================================================================

# Production Vault settings (override with env vars)
PROD_VAULT_ADDR="${VAULT_ADDR:-https://prod.vault.nvidia.com}"
PROD_VAULT_NAMESPACE="${VAULT_NAMESPACE:-ngc}"

# Local OpenBao settings
LOCAL_OPENBAO_NAMESPACE="${OPENBAO_NAMESPACE:-openbao}"
LOCAL_OPENBAO_POD="${OPENBAO_POD:-openbao-0}"
LOCAL_OPENBAO_TOKEN="${OPENBAO_TOKEN:-root}"  # Dev mode token

# Tracking
COPIED_COUNT=0
FAILED_COUNT=0
SKIPPED_COUNT=0

# =============================================================================
# Functions
# =============================================================================

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v vault &> /dev/null; then
        log_error "vault CLI is not installed. Please install it first."
        echo "  brew install vault  # macOS"
        echo "  or download from https://developer.hashicorp.com/vault/downloads"
        exit 1
    fi
    
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        exit 1
    fi
    
    if ! command -v jq &> /dev/null; then
        log_error "jq is not installed. Please install it first."
        echo "  brew install jq  # macOS"
        exit 1
    fi
    
    # Check if OpenBao is running
    if ! kubectl -n "$LOCAL_OPENBAO_NAMESPACE" get pod "$LOCAL_OPENBAO_POD" &> /dev/null; then
        log_error "OpenBao pod not found. Please install OpenBao first."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

check_prod_vault_auth() {
    log_info "Checking production Vault authentication..."
    
    # Check if already logged in
    if vault token lookup &> /dev/null; then
        log_success "Already authenticated to Vault"
        return 0
    fi
    
    log_warn "Not authenticated to production Vault"
    echo ""
    echo "Please authenticate to the production Vault using one of these methods:"
    echo ""
    echo "  Option 1 - OIDC login (interactive):"
    echo "    export VAULT_ADDR='$PROD_VAULT_ADDR'"
    echo "    export VAULT_NAMESPACE='$PROD_VAULT_NAMESPACE'"
    echo "    vault login -method=oidc"
    echo ""
    echo "  Option 2 - Token (if you have one):"
    echo "    export VAULT_ADDR='$PROD_VAULT_ADDR'"
    echo "    export VAULT_NAMESPACE='$PROD_VAULT_NAMESPACE'"
    echo "    export VAULT_TOKEN='your-token-here'"
    echo ""
    echo "Then re-run this script."
    exit 1
}

# Ensure KV engine is enabled at a given mount path
ensure_kv_engine() {
    local mount_path="$1"
    
    kubectl -n "$LOCAL_OPENBAO_NAMESPACE" exec "$LOCAL_OPENBAO_POD" -- \
        env BAO_TOKEN="$LOCAL_OPENBAO_TOKEN" \
        bao secrets enable -path="$mount_path" kv-v2 2>/dev/null || true
}

# Parse a vault path into mount and secret path
# Input: my-engine/my-org/nv-config-manager/dev/nautobot
# Output: Sets MOUNT_PATH and SECRET_PATH variables
parse_vault_path() {
    local full_path="$1"
    
    # Remove trailing slash if present
    full_path="${full_path%/}"
    
    # Common KV v2 mount patterns
    # Format: <mount>/data/<path> or <mount>/<path>
    
    # Check if path contains /data/ (explicit KV v2 path)
    if [[ "$full_path" == *"/data/"* ]]; then
        # Extract mount (everything before /data/)
        MOUNT_PATH="${full_path%%/data/*}"
        # Extract secret path (everything after /data/)
        SECRET_PATH="${full_path#*/data/}"
    else
        # Assume format: <mount>/<path>
        # e.g., nv-config-manager/dev/nautobot or my-engine/my-org/nv-config-manager/dev/nautobot
        if [[ "$full_path" == */secrets/* ]]; then
            # Mount is everything up to and including "secrets"
            MOUNT_PATH="${full_path%%/secrets/*}/secrets"
            # Secret path is everything after "secrets/"
            SECRET_PATH="${full_path#*/secrets/}"
        else
            # Fallback: first segment is mount, rest is path
            MOUNT_PATH="${full_path%%/*}"
            SECRET_PATH="${full_path#*/}"
        fi
    fi
}

# List secrets at a path (recursively)
list_secrets_recursive() {
    local mount="$1"
    local path="$2"
    local indent="${3:-}"
    
    # List at current path
    local keys
    keys=$(vault kv list -format=json "${mount}/${path}" 2>/dev/null | jq -r '.[]' 2>/dev/null) || return 0
    
    for key in $keys; do
        if [[ "$key" == */ ]]; then
            # It's a directory, recurse
            local subpath="${path}/${key%/}"
            subpath="${subpath#/}"  # Remove leading slash if present
            list_secrets_recursive "$mount" "$subpath" "$indent"
        else
            # It's a secret
            local full_secret_path="${path}/${key}"
            full_secret_path="${full_secret_path#/}"  # Remove leading slash
            echo "${mount}/${full_secret_path}"
        fi
    done
}

# Copy a single secret from prod to local
copy_single_secret() {
    local mount="$1"
    local secret_path="$2"
    
    log_info "Copying: ${mount}/${secret_path}"
    
    # Read from production Vault
    local secret_json
    if ! secret_json=$(vault kv get -format=json "${mount}/${secret_path}" 2>/dev/null); then
        log_warn "  Could not read secret (may not exist or no access)"
        ((SKIPPED_COUNT++))
        return 1
    fi
    
    # Extract just the data portion
    local secret_data
    secret_data=$(echo "$secret_json" | jq -r '.data.data // empty')
    
    if [[ -z "$secret_data" || "$secret_data" == "null" ]]; then
        log_warn "  No data in secret"
        ((SKIPPED_COUNT++))
        return 1
    fi
    
    # Ensure the KV engine is enabled at the mount path
    ensure_kv_engine "$mount"
    
    # Build the bao kv put command with all key-value pairs
    local kv_args=()
    while IFS= read -r key; do
        local value
        value=$(echo "$secret_data" | jq -r --arg k "$key" '.[$k] // empty')
        if [[ -n "$value" ]]; then
            kv_args+=("${key}=${value}")
        fi
    done < <(echo "$secret_data" | jq -r 'keys[]')
    
    # Write to local OpenBao
    if kubectl -n "$LOCAL_OPENBAO_NAMESPACE" exec "$LOCAL_OPENBAO_POD" -- \
        env BAO_TOKEN="$LOCAL_OPENBAO_TOKEN" \
        bao kv put "${mount}/${secret_path}" "${kv_args[@]}" >/dev/null 2>&1; then
        log_success "  ✓ Copied successfully"
        ((COPIED_COUNT++))
        return 0
    else
        log_error "  ✗ Failed to write to local OpenBao"
        ((FAILED_COUNT++))
        return 1
    fi
}

# Copy all secrets under a path (recursively)
copy_path_recursive() {
    local full_path="$1"
    
    parse_vault_path "$full_path"
    
    log_info "Mount: $MOUNT_PATH"
    log_info "Path: $SECRET_PATH"
    echo ""
    
    # First, try to read as a single secret
    if vault kv get -format=json "${MOUNT_PATH}/${SECRET_PATH}" &>/dev/null; then
        # It's a single secret, copy it directly
        copy_single_secret "$MOUNT_PATH" "$SECRET_PATH"
    else
        # It's a directory, list and copy recursively
        log_info "Listing secrets under: ${MOUNT_PATH}/${SECRET_PATH}"
        
        local secrets
        secrets=$(list_secrets_recursive "$MOUNT_PATH" "$SECRET_PATH")
        
        if [[ -z "$secrets" ]]; then
            log_warn "No secrets found at path: $full_path"
            log_info "Trying to list available paths..."
            vault kv list "${MOUNT_PATH}/${SECRET_PATH}" 2>/dev/null || \
                log_warn "Could not list path (may not exist or no access)"
            return 1
        fi
        
        echo ""
        log_info "Found secrets to copy:"
        echo "$secrets" | while read -r s; do echo "  - $s"; done
        echo ""
        
        # Copy each secret
        while IFS= read -r secret_full_path; do
            if [[ -n "$secret_full_path" ]]; then
                # Parse the full path again for each secret
                parse_vault_path "$secret_full_path"
                copy_single_secret "$MOUNT_PATH" "$SECRET_PATH"
            fi
        done <<< "$secrets"
    fi
}

# Main copy command
do_copy() {
    shift  # Remove 'copy' from args
    
    if [[ $# -eq 0 ]]; then
        log_error "No paths specified"
        echo ""
        echo "Usage: $0 copy <path> [<path2> ...]"
        echo ""
        echo "Examples:"
        echo "  $0 copy my-engine/my-org/nv-config-manager/prod/"
        echo "  $0 copy my-engine/my-org/nv-config-manager/dev/nautobot"
        exit 1
    fi
    
    check_prerequisites
    check_prod_vault_auth
    
    echo ""
    log_info "========================================="
    log_info "Copying secrets to local OpenBao"
    log_info "Source: $PROD_VAULT_ADDR"
    log_info "Target: $LOCAL_OPENBAO_POD in $LOCAL_OPENBAO_NAMESPACE"
    log_info "========================================="
    echo ""
    
    for path in "$@"; do
        log_info "Processing path: $path"
        echo ""
        copy_path_recursive "$path"
        echo ""
    done
    
    echo ""
    log_info "========================================="
    log_info "Summary:"
    log_success "  Copied:  $COPIED_COUNT secrets"
    if [[ $SKIPPED_COUNT -gt 0 ]]; then
        log_warn "  Skipped: $SKIPPED_COUNT secrets"
    fi
    if [[ $FAILED_COUNT -gt 0 ]]; then
        log_error "  Failed:  $FAILED_COUNT secrets"
    fi
    log_info "========================================="
}

# List secrets in local OpenBao
do_list() {
    shift  # Remove 'list' from args
    
    local path="${1:-}"
    
    if [[ -z "$path" ]]; then
        log_info "Listing all enabled secrets engines in local OpenBao:"
        kubectl -n "$LOCAL_OPENBAO_NAMESPACE" exec "$LOCAL_OPENBAO_POD" -- \
            env BAO_TOKEN="$LOCAL_OPENBAO_TOKEN" \
            bao secrets list -format=table
        return
    fi
    
    parse_vault_path "$path"
    
    log_info "Listing secrets at: ${MOUNT_PATH}/${SECRET_PATH}"
    kubectl -n "$LOCAL_OPENBAO_NAMESPACE" exec "$LOCAL_OPENBAO_POD" -- \
        env BAO_TOKEN="$LOCAL_OPENBAO_TOKEN" \
        bao kv list "${MOUNT_PATH}/${SECRET_PATH}" 2>/dev/null || \
        log_warn "No secrets found at path or path does not exist"
}

# Read a specific secret from local OpenBao
do_get() {
    shift  # Remove 'get' from args
    
    local path="${1:-}"
    
    if [[ -z "$path" ]]; then
        log_error "No path specified"
        echo "Usage: $0 get <path>"
        exit 1
    fi
    
    parse_vault_path "$path"
    
    log_info "Reading secret at: ${MOUNT_PATH}/${SECRET_PATH}"
    kubectl -n "$LOCAL_OPENBAO_NAMESPACE" exec "$LOCAL_OPENBAO_POD" -- \
        env BAO_TOKEN="$LOCAL_OPENBAO_TOKEN" \
        bao kv get "${MOUNT_PATH}/${SECRET_PATH}"
}

generate_test_secrets() {
    local environment="${1:-dev}"
    
    log_info "Generating test secrets with dummy values for local development..."
    log_info "Environment: $environment"
    echo ""
    
    local env_path="${environment}"
    
    # Ensure KV engine is enabled (uses "nv-config-manager" as default mount)
    ensure_kv_engine "nv-config-manager"
    
    # Helper function
    write_secret() {
        local path="$1"
        shift
        kubectl -n "$LOCAL_OPENBAO_NAMESPACE" exec "$LOCAL_OPENBAO_POD" -- \
            env BAO_TOKEN="$LOCAL_OPENBAO_TOKEN" \
            bao kv put "nv-config-manager/${path}" "$@" >/dev/null 2>&1
    }
    
    # Nautobot
    write_secret "${env_path}/nautobot" \
        token="test-nautobot-token-12345" \
        nats_password="test-nats-password"
    log_success "  ✓ nautobot"
    
    # Redis
    write_secret "${env_path}/redis" \
        password="test-redis-password"
    log_success "  ✓ redis"
    
    # CNPG (PostgreSQL)
    write_secret "${env_path}/cnpg" \
        temporal_user="temporal" \
        temporal_password="test-temporal-pass" \
        temporal_visibility_user="temporal_visibility" \
        temporal_visibility_password="test-visibility-pass" \
        config_store_user="config_store" \
        config_store_password="test-configstore-pass" \
        dhcp_user="dhcp" \
        dhcp_password="test-dhcp-pass" \
        nautobot_user="nautobot" \
        nautobot_password="test-nautobot-db-pass"
    log_success "  ✓ cnpg"
    
    # Network
    write_secret "${env_path}/network" \
        user="admin" \
        password="test-network-password"
    log_success "  ✓ network"
    
    # Redfish
    write_secret "${env_path}/redfish" \
        lenovo_default_user="USERID" \
        lenovo_default_password="PASSW0RD" \
        lenovo_config_manager_password="test-lenovo-nv-config-manager" \
        bluefield_default_user="admin" \
        bluefield_default_password="admin" \
        bluefield_config_manager_password="test-bluefield-nv-config-manager"
    log_success "  ✓ redfish"
    
    # BMC
    write_secret "${env_path}/bmc" \
        'bmc-creds.json={"default": {"username": "admin", "password": "admin"}}'
    log_success "  ✓ bmc"
    
    # Slack
    write_secret "${env_path}/slack" \
        token="xoxb-test-slack-token"
    log_success "  ✓ slack"
    
    # DHCP
    write_secret "${env_path}/dhcp" \
        password="test-dhcp-password"
    log_success "  ✓ dhcp"
    
    # AIR
    write_secret "${env_path}/air" \
        ssa_client_id="test-air-client-id" \
        ssa_client_secret="test-air-client-secret"
    log_success "  ✓ air"
    
    # UFM
    write_secret "${env_path}/ufm" \
        ufm_api_user="admin" \
        ufm_api_token_r1="test-ufm-token"
    log_success "  ✓ ufm"
    
    # Nautobot App
    write_secret "${env_path}/nautobot-app" \
        admin_password="admin" \
        django_secret_key="test-django-secret-key-that-is-long-enough-for-django" \
        superuser_api_token="0123456789abcdef0123456789abcdef01234567"
    log_success "  ✓ nautobot-app"
    
    echo ""
    log_success "All test secrets created at: nv-config-manager/${env_path}/"
}

show_usage() {
    echo "Usage: $0 <command> [arguments]"
    echo ""
    echo "Commands:"
    echo "  copy <path> [<path2> ...]  Copy secrets from production Vault to local OpenBao"
    echo "  generate [env]             Generate test secrets with dummy values (default: dev)"
    echo "  list [path]                List secrets in local OpenBao"
    echo "  get <path>                 Read a specific secret from local OpenBao"
    echo ""
    echo "Path format:"
    echo "  <mount>/<secret-path>      e.g., nv-config-manager/dev/nautobot"
    echo ""
    echo "Examples:"
    echo "  # Copy all secrets under a path (recursive)"
    echo "  $0 copy my-engine/my-org/nv-config-manager/prod/"
    echo ""
    echo "  # Copy specific secrets"
    echo "  $0 copy my-engine/nv-config-manager/dev/nautobot \\"
    echo "         my-engine/nv-config-manager/dev/redis"
    echo ""
    echo "  # Generate test secrets for dev environment"
    echo "  $0 generate dev"
    echo ""
    echo "  # List secrets in local OpenBao"
    echo "  $0 list nv-config-manager/dev"
    echo ""
    echo "  # Read a secret from local OpenBao"
    echo "  $0 get nv-config-manager/dev/nautobot"
    echo ""
    echo "Environment variables:"
    echo "  VAULT_ADDR         Production Vault address (default: https://prod.vault.nvidia.com)"
    echo "  VAULT_NAMESPACE    Production Vault namespace (default: ngc)"
    echo "  OPENBAO_NAMESPACE  Local OpenBao k8s namespace (default: openbao)"
    echo "  OPENBAO_POD        Local OpenBao pod name (default: openbao-0)"
    echo "  OPENBAO_TOKEN      Local OpenBao token (default: root)"
}

# =============================================================================
# Main
# =============================================================================

main() {
    local command="${1:-}"
    
    case "$command" in
        copy)
            do_copy "$@"
            ;;
        generate)
            shift
            check_prerequisites
            generate_test_secrets "${1:-dev}"
            ;;
        list)
            do_list "$@"
            ;;
        get)
            do_get "$@"
            ;;
        -h|--help|help)
            show_usage
            ;;
        *)
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
