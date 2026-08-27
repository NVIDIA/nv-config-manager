#!/usr/bin/env bash
#
# Validate the Redis exporter, PodMonitor, NetworkPolicy, and air-gap image
# discovery rendering contracts. This test intentionally lives with the Helm
# chart and runs only in CI jobs that install Helm.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHART_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
AIRGAP_VALUES="$CHART_DIR/../airgapped/values-airgapped-extract.yaml"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

assert_contains() {
    local file="$1"
    local expected="$2"
    local message="$3"
    grep -Fq -- "$expected" "$file" || fail "$message (missing: $expected)"
}

assert_not_contains() {
    local file="$1"
    local unexpected="$2"
    local message="$3"
    if grep -Fq -- "$unexpected" "$file"; then
        fail "$message (unexpected: $unexpected)"
    fi
}

assert_empty() {
    local file="$1"
    local message="$2"
    [[ ! -s "$file" ]] || fail "$message"
}

assert_not_empty() {
    local file="$1"
    local message="$2"
    [[ -s "$file" ]] || fail "$message"
}

render() {
    local output="$1"
    shift
    helm template test "$CHART_DIR" \
        --values "$CHART_DIR/values-ci.yaml" \
        "$@" > "$output"
}

extract_document() {
    local input="$1"
    local kind="$2"
    local name="$3"
    local output="$4"
    awk -v kind="$kind" -v name="$name" '
        BEGIN { RS = "---"; ORS = "" }
        $0 ~ ("\nkind: " kind "\n") && $0 ~ ("\n  name: " name "\n") { print }
    ' "$input" > "$output"
}

assert_exporter_present() {
    local rendered="$1"
    local deployment="$TMP_DIR/redis-deployment.yaml"
    extract_document "$rendered" Deployment test-nv-config-manager-redis "$deployment"
    assert_not_empty "$deployment" "Redis Deployment should render"
    assert_contains "$deployment" "        - name: redis-exporter" "Redis exporter sidecar should render"
}

assert_exporter_absent() {
    local rendered="$1"
    local deployment="$TMP_DIR/redis-deployment.yaml"
    extract_document "$rendered" Deployment test-nv-config-manager-redis "$deployment"
    assert_not_contains "$deployment" "        - name: redis-exporter" "Redis exporter sidecar should not render"
}

assert_monitor_present() {
    local rendered="$1"
    local monitor="$TMP_DIR/redis-podmonitor.yaml"
    extract_document "$rendered" PodMonitor test-nv-config-manager-redis "$monitor"
    assert_not_empty "$monitor" "Redis PodMonitor should render"
}

assert_monitor_absent() {
    local rendered="$1"
    local monitor="$TMP_DIR/redis-podmonitor.yaml"
    extract_document "$rendered" PodMonitor test-nv-config-manager-redis "$monitor"
    assert_empty "$monitor" "Redis PodMonitor should not render"
}

assert_exporter_network_port() {
    local rendered="$1"
    local port="$2"
    local policy="$TMP_DIR/namespace-isolation.yaml"
    extract_document "$rendered" NetworkPolicy namespace-isolation "$policy"
    assert_contains "$policy" "          port: $port  # bundled Redis exporter" \
        "NetworkPolicy should allow the Redis exporter port"
}

assert_no_exporter_network_port() {
    local rendered="$1"
    local policy="$TMP_DIR/namespace-isolation.yaml"
    extract_document "$rendered" NetworkPolicy namespace-isolation "$policy"
    assert_not_contains "$policy" "# bundled Redis exporter" \
        "NetworkPolicy should not include a Redis exporter rule"
}

full="$TMP_DIR/full.yaml"
render "$full" \
    --set externalServices.redis.local=true \
    --set externalServices.redis.metricsExport.enabled=true \
    --set monitoring.enabled=true \
    --set monitoring.podMonitors.enabled=true \
    --set monitoring.podMonitors.redis.enabled=true \
    --set global.customLabels.production=true

assert_exporter_present "$full"
deployment="$TMP_DIR/redis-deployment.yaml"
extract_document "$full" Deployment test-nv-config-manager-redis "$deployment"
assert_contains "$deployment" "        production: true" "Redis pod labels should propagate custom labels"
assert_contains "$deployment" "          image: \"docker.io/oliver006/redis_exporter:v1.90.0\"" "Exporter image should use the configured default"
assert_contains "$deployment" "          imagePullPolicy: IfNotPresent" "Exporter should use the global pull policy"
assert_contains "$deployment" "            - name: REDIS_ADDR" "Exporter should configure the Redis address"
assert_contains "$deployment" "              value: redis://localhost:6379" "Exporter should target the local Redis container"
assert_contains "$deployment" "                  name: redis-password" "Exporter should use the existing password Secret"
assert_contains "$deployment" "            - name: REDIS_EXPORTER_WEB_LISTEN_ADDRESS" "Exporter should configure its listen address"
assert_contains "$deployment" "              value: \":9121\"" "Exporter should listen on the configured port"
assert_contains "$deployment" "            - containerPort: 9121" "Exporter container port should render"
assert_contains "$deployment" "              name: redis-metrics" "Exporter port should have the stable PodMonitor name"
assert_contains "$deployment" "            allowPrivilegeEscalation: false" "Exporter should disable privilege escalation"
assert_contains "$deployment" "            runAsNonRoot: true" "Exporter should run as non-root"
assert_contains "$deployment" "            runAsUser: 1000" "Exporter should use the chart security UID"
assert_contains "$deployment" "            runAsGroup: 1000" "Exporter should use the chart security GID"
assert_contains "$deployment" "                - ALL" "Exporter should drop all capabilities"
assert_contains "$deployment" "              cpu: 10m" "Exporter CPU request should render"
assert_contains "$deployment" "              memory: 32Mi" "Exporter memory request should render"
assert_contains "$deployment" "              memory: 64Mi" "Exporter memory limit should render"

assert_monitor_present "$full"
monitor="$TMP_DIR/redis-podmonitor.yaml"
extract_document "$full" PodMonitor test-nv-config-manager-redis "$monitor"
assert_contains "$monitor" "    production: true" "PodMonitor labels should propagate custom labels"
assert_contains "$monitor" "    app.kubernetes.io/name: test-nv-config-manager-redis" "PodMonitor selector should match Redis pod labels"
assert_contains "$monitor" "  podTargetLabels:" "PodMonitor should copy custom pod labels"
assert_contains "$monitor" "    - production" "PodMonitor should copy the production label"
assert_contains "$monitor" "    - port: redis-metrics" "PodMonitor should scrape the named exporter port"
assert_contains "$monitor" "      path: /metrics" "PodMonitor should scrape the metrics path"
assert_contains "$monitor" "      interval: 30s" "PodMonitor should use the configured interval"
assert_contains "$monitor" "      scrapeTimeout: 10s" "PodMonitor should use the configured timeout"
assert_contains "$monitor" "          targetLabel: production" "PodMonitor should propagate custom metric labels"
assert_contains "$monitor" "          replacement: \"true\"" "PodMonitor should set the custom metric label value"
assert_exporter_network_port "$full" 9121

exporter_disabled="$TMP_DIR/exporter-disabled.yaml"
render "$exporter_disabled" \
    --set externalServices.redis.local=true \
    --set monitoring.enabled=true \
    --set monitoring.podMonitors.enabled=true \
    --set monitoring.podMonitors.redis.enabled=true
assert_exporter_absent "$exporter_disabled"
assert_monitor_absent "$exporter_disabled"
assert_no_exporter_network_port "$exporter_disabled"

monitor_disabled="$TMP_DIR/monitor-disabled.yaml"
render "$monitor_disabled" \
    --set externalServices.redis.local=true \
    --set externalServices.redis.metricsExport.enabled=true \
    --set monitoring.enabled=true \
    --set monitoring.podMonitors.enabled=true
assert_exporter_present "$monitor_disabled"
assert_monitor_absent "$monitor_disabled"
assert_exporter_network_port "$monitor_disabled" 9121

fully_enabled="$TMP_DIR/fully-enabled.yaml"
render "$fully_enabled" \
    --set externalServices.redis.local=true \
    --set externalServices.redis.metricsExport.enabled=true \
    --set monitoring.enabled=true \
    --set monitoring.podMonitors.enabled=true \
    --set monitoring.podMonitors.redis.enabled=true
assert_exporter_present "$fully_enabled"
assert_monitor_present "$fully_enabled"
assert_exporter_network_port "$fully_enabled" 9121

monitoring_disabled="$TMP_DIR/monitoring-disabled.yaml"
render "$monitoring_disabled" \
    --set externalServices.redis.local=true \
    --set externalServices.redis.metricsExport.enabled=true \
    --set monitoring.enabled=false \
    --set monitoring.podMonitors.enabled=true \
    --set monitoring.podMonitors.redis.enabled=true
assert_exporter_present "$monitoring_disabled"
assert_monitor_absent "$monitoring_disabled"
assert_no_exporter_network_port "$monitoring_disabled"

pod_monitors_disabled="$TMP_DIR/pod-monitors-disabled.yaml"
render "$pod_monitors_disabled" \
    --set externalServices.redis.local=true \
    --set externalServices.redis.metricsExport.enabled=true \
    --set monitoring.enabled=true \
    --set monitoring.podMonitors.enabled=false \
    --set monitoring.podMonitors.redis.enabled=true
assert_exporter_present "$pod_monitors_disabled"
assert_monitor_absent "$pod_monitors_disabled"
assert_exporter_network_port "$pod_monitors_disabled" 9121

local_redis_disabled="$TMP_DIR/local-redis-disabled.yaml"
render "$local_redis_disabled" \
    --set externalServices.redis.local=false \
    --set externalServices.redis.host=redis.example.com \
    --set externalServices.redis.metricsExport.enabled=true \
    --set monitoring.enabled=true \
    --set monitoring.podMonitors.enabled=true \
    --set monitoring.podMonitors.redis.enabled=true
assert_exporter_absent "$local_redis_disabled"
assert_monitor_absent "$local_redis_disabled"
assert_no_exporter_network_port "$local_redis_disabled"

custom_port="$TMP_DIR/custom-port.yaml"
render "$custom_port" \
    --set externalServices.redis.local=true \
    --set externalServices.redis.metricsExport.enabled=true \
    --set externalServices.redis.metricsExport.port=19121 \
    --set monitoring.enabled=true \
    --set monitoring.podMonitors.enabled=true \
    --set monitoring.podMonitors.redis.enabled=true
assert_exporter_present "$custom_port"
extract_document "$custom_port" Deployment test-nv-config-manager-redis "$deployment"
assert_contains "$deployment" "              value: \":19121\"" "Exporter should honor a custom listen port"
assert_contains "$deployment" "            - containerPort: 19121" "Exporter should expose a custom container port"
assert_monitor_present "$custom_port"
assert_exporter_network_port "$custom_port" 19121
policy="$TMP_DIR/namespace-isolation.yaml"
extract_document "$custom_port" NetworkPolicy namespace-isolation "$policy"
assert_not_contains "$policy" "          port: 9121  # bundled Redis exporter" \
    "NetworkPolicy should not retain the default exporter port after an override"

airgap="$TMP_DIR/airgap.yaml"
helm template test "$CHART_DIR" --values "$AIRGAP_VALUES" > "$airgap"
airgap_images="$TMP_DIR/airgap-images.txt"
grep -iE '^[[:space:]]*image:' "$airgap" \
    | sed -E 's/^[[:space:]]*image:[[:space:]]*//' \
    | sed -E 's/^["'\'']|["'\'']$//g' \
    | sort -u > "$airgap_images"
assert_contains "$airgap_images" "docker.io/oliver006/redis_exporter:v1.90.0" \
    "Air-gap bundle discovery should include the Redis exporter image"

echo "Redis metrics render assertions passed"
