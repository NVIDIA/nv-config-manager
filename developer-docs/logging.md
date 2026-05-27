# NVIDIA Config Manager Logging & Observability

## Structured Logging

All NVIDIA Config Manager Python services produce structured JSON logs by default. This is
controlled by two environment variables:

| Variable    | Default | Description |
|-------------|---------|-------------|
| `LOG_FORMAT` | `json`  | Set to `text` for human-readable output during local development. |
| `LOG_LEVEL`  | `INFO`  | Standard Python level names: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. The legacy `DEBUG=1` env var is also supported. |

### Setup

Every service entry point calls `configure_logging(service="<name>")` once at
startup. This configures the **root** logger so that all loggers (including
third-party libraries like uvicorn) produce consistent output.

Individual modules obtain a logger via:

```python
from nv_config_manager.common.config import LogCategory, get_logger

logger = get_logger(__name__, category=LogCategory.RENDER)
```

`get_logger` returns a `logging.LoggerAdapter` that automatically attaches
`service` and `category` fields to every log record.

### JSON Output Format

Each JSON log line contains:

| Field       | Type   | Description |
|-------------|--------|-------------|
| `message`   | string | Log message |
| `levelname` | string | `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` |
| `name`      | string | Python logger name (e.g., `nv_config_manager.render.dispatch`) |
| `asctime`   | string | ISO 8601 timestamp |
| `module`    | string | Python module name |
| `lineno`    | int    | Source line number |
| `service`   | string | Service name set by `configure_logging()` |
| `category`  | string | Log category (see below) |
| *(custom)*  | string | Any key from `global.customLabels` (see [Custom Labels](#custom-labels)) |

Example:

```json
{
  "message": "Processing event for device abc-123",
  "levelname": "INFO",
  "name": "nv_config_manager.render.dispatch",
  "asctime": "2025-12-01 10:30:45,123",
  "module": "dispatch",
  "lineno": 142,
  "service": "render",
  "category": "render.event"
}
```

## Custom Labels

Arbitrary key-value pairs can be attached to **all logs** (as JSON fields) and
**all Prometheus metrics** (as metric labels) by setting `global.customLabels`
in the Helm chart:

```yaml
global:
  customLabels:
    production: "true"
    region: "us-east-1"
```

### How It Works

**Logs:** The Helm chart serialises `global.customLabels` into a
`NV_CONFIG_MANAGER_CUSTOM_LABELS` environment variable (JSON string) on every NVIDIA Config Manager service
container. `configure_logging()` parses it at startup and injects every KVP
into the Python log-record factory, so the fields appear in every JSON log line
alongside `service` and `category`:

```json
{
  "message": "Processing event for device abc-123",
  "levelname": "INFO",
  "service": "render",
  "category": "render.event",
  "production": "true",
  "region": "us-east-1"
}
```

**Metrics:** The same labels are added as Kubernetes pod labels on every NVIDIA Config Manager
pod. Each PodMonitor includes a `podTargetLabels` list that tells Prometheus to
copy these pod labels onto every scraped metric. This means PromQL queries can
filter or group by any custom label without changing application code.

### Constraints

Labels must be valid across Kubernetes pod labels, Prometheus metric labels,
and Python log record attributes simultaneously. The logging module enforces:

- **Key format:** must match `[a-zA-Z_][a-zA-Z0-9_]*` (no dots or hyphens --
  use underscores instead).
- **Key length:** max 63 characters.
- **Reserved keys:** `service`, `category`, `message`, `levelname`, `name`,
  `module`, `lineno`, and other standard LogRecord fields cannot be overwritten.
- **Value length:** truncated to 63 characters (Kubernetes pod label limit).

Invalid entries are skipped at startup with a warning on stderr.

### Use Cases

- **Production gating:** Set `production: "true"` to control paging rules and
  SLO inclusion in Prometheus alerting.
- **Regional filtering:** Set `region` to slice dashboards and alerts by
  deployment region.
- **Environment tagging:** Distinguish between `staging`, `canary`, and `prod`
  deployments in a shared Grafana instance.

## Log Categories

Every logger has a default `category` label. Categories follow a dotted
hierarchy so you can filter broadly (`render`) or narrowly (`render.event`).

| Category             | Description | Services |
|----------------------|-------------|----------|
| `render`             | Config rendering operations (template execution, Jinja2) | Render |
| `render.event`       | NATS event processing in the render pipeline | Render |
| `render.api`         | Render service HTTP API (admin endpoints, consumer management) | Render |
| `dhcp`               | DHCP config generation and Kea interactions | DHCP |
| `dhcp.data`          | DHCP data validation issues (bad Nautobot data) | DHCP |
| `config_store`       | Config storage and retrieval operations | Config Store |
| `config_store.api`   | Config Store HTTP API and startup | Config Store |
| `ztp`                | Zero Touch Provisioning (SFTP, sync, firmware streaming) | ZTP |
| `ztp.api`            | ZTP HTTP API (device provisioning, firmware, serial validation) | ZTP |
| `temporal.workflow`  | Temporal workflow orchestration, stages, and schedulers | Temporal |
| `temporal.activity`  | Temporal activity implementations and supporting clients | Temporal |
| `temporal.api`       | Temporal HTTP API (workflow CRUD, codec server, RBAC) | Temporal |
| `nautobot`           | Nautobot API interactions (GraphQL queries, plugin updates) | Render, DHCP, Config Store, Temporal |
| `auth`               | Authentication, authorization, and OIDC token management | All |
| `nats`               | NATS messaging infrastructure | Render, Temporal |
| `cache`              | Cache operations (Redis, device cache, refresh service) | Config Store |

### Overriding Category Per-Call

You can override the default category on individual log calls:

```python
logger.info("Cache miss for device %s", uuid, extra={"category": "cache"})
```

### Log Messages by Category

Below are representative log samples for each category. Every ERROR and WARNING
message is listed; INFO/DEBUG messages show 1-2 representative examples.

---

#### `render`

**Sample INFO messages:**

- `"Rendering configuration for %s with commit message '%s'"`
- `"Produced commit %s for %s, affected files: %s"`

---

#### `render.event`

**Sample INFO messages:**

- `"Consumer %s connected to NATS."`
- `"No event handler implemented for %s, ignoring message."`

**ERROR and WARNING messages:**

| Level   | Message |
|---------|---------|
| WARNING | `"Error during task cleanup: %s"` |
| WARNING | `"No responders available for ack (likely during shutdown), treating as success"` |
| ERROR   | `"Error acknowledging message: %s"` |
| WARNING | `"No responders available for nak (likely during shutdown), ignoring"` |
| ERROR   | `"Error nacking message: %s"` |
| ERROR   | `"Unhandled NATS error"` |
| WARNING | `"NATS connection disconnected."` |
| WARNING | `"NATS connection reconnected."` |
| ERROR   | `"NATS connection or JetStream is None, cannot run consumer"` |
| WARNING | `"Consumer %s cycle failed, recreating: %s"` |
| WARNING | `"Fetch error for consumer %s, recreating: %s"` |
| WARNING | `"Error unsubscribing: %s"` |
| ERROR   | `"Failed to ensure consumer exists: %s"` |
| ERROR   | `"Error in message handler: %s"` |
| ERROR   | `"Failed to nak message after handler error: %s"` |
| WARNING | `"Error closing NATS connection: %s"` |
| WARNING | `"Could not schedule close_connection task: %s"` |
| ERROR   | `"Error processing nautobot message"` |
| ERROR   | `"Error processing device change message: %s"` |
| ERROR   | `"Error releasing lock for %s"` |
| ERROR   | `"Error processing template change message"` |
| ERROR   | `"Error processing event: %s"` |
| ERROR   | `"Error queuing render jobs for %s update %s"` |
| WARNING | `"Failed to queue device %s: %s"` |

---

#### `render.api`

**Sample INFO messages:**

- `"Consumer %s has %s pending messages"`
- `"Successfully deleted consumer %s"`

**ERROR and WARNING messages:**

| Level   | Message |
|---------|---------|
| WARNING | `"Could not get info for consumer %s: %s"` |
| ERROR   | `"Error listing consumers: %s"` |
| ERROR   | `"Error resetting consumer %s: %s"` |
| ERROR   | `"Failed to delete consumer '%s': %s"` |
| ERROR   | `"Error processing consumer %s: %s"` |
| ERROR   | `"Error resetting all consumers: %s"` |
| ERROR   | `"Error getting consumer info for %s: %s"` |

---

#### `dhcp`

**Sample INFO messages:**

- `"Generating configuration from nautobot data."`
- `"KEA DHCP{ip_version} Configuration Refresh Complete."`

**ERROR and WARNING messages:**

| Level   | Message |
|---------|---------|
| WARNING | `"Could not fetch current Kea config, using defaults: {exc}"` |
| ERROR   | `"Error refreshing the KEA config: {exc}"` |

---

#### `dhcp.data`

**Sample INFO messages:**

_(No INFO messages -- this category surfaces only warnings and errors from bad
Nautobot data.)_

**ERROR and WARNING messages:**

| Level   | Message |
|---------|---------|
| WARNING | `"Reserved IP %s is not ZTP enabled, skipping"` |
| WARNING | `"Reserved IP %s is aggregate status mismatch, skipping"` |
| WARNING | `"Static reservation for %s is being overwritten by a generated reservation"` |
| WARNING | `"IP address conflict: automatic reservation for %s (%s) has the same IP %s as %s reservation for %s. Using automatic reservation."` |
| WARNING | `"IP address %s in subnet %s has both dhcp-pool and dhcp-reserve tags; ignoring dhcp-reserve and treating as pool only"` |
| WARNING | `"Undefined variable in option %s: %s, leaving template as is."` |
| WARNING | `"Template syntax error in option %s: %s, leaving as is."` |
| WARNING | `"Subnet conflict: auto-generated subnet %s conflicts with existing subnet. Using auto-generated subnet."` |
| ERROR   | `"Conflicting values for option '{opt}': '{value1}' vs '{value2}'"` |
| ERROR   | `"Subnet {prefix} {label} for {address} conflicts with existing option {opt}: ..."` |

---

#### `config_store`

**Sample INFO messages:**

- `"No diff for %s/%s"`

**ERROR and WARNING messages:**

| Level | Message |
|-------|---------|
| ERROR | `"Failed to enrich device %s: %s"` |

---

#### `config_store.api`

**Sample INFO messages:**

- `"Initializing Redis-based Nautobot cache service (read-only)"`
- `"API service shutting down"`

**ERROR and WARNING messages:**

| Level | Message |
|-------|---------|
| ERROR | `"Redis search failed, falling back to DB query: %s"` |
| ERROR | `"Failed to initialize Nautobot cache service: %s"` |

---

#### `ztp`

**Sample INFO messages:**

- `"Streaming file: %s"`
- `"Starting file sync process"`

**ERROR and WARNING messages:**

| Level   | Message |
|---------|---------|
| ERROR   | `"Unexpected error: {exc}"` |
| ERROR   | `"Error closing file handle: %s"` |
| ERROR   | `"Error reading from file: %s"` |
| ERROR   | `"Error loading file %s for stat: %s"` |
| ERROR   | `"S3 file not found: %s/%s/%s"` |
| ERROR   | `"Error getting S3 metadata: %s"` |
| ERROR   | `"Error loading file %s: %s"` |
| ERROR   | `"Error creating SFTP handle: %s"` |
| ERROR   | `"No channel established"` |
| WARNING | `"Socket error from %s: %s"` |
| ERROR   | `"Error handling connection: %s"` |
| ERROR   | `"Error accepting connection: %s"` |
| ERROR   | `"Server error: %s"` |
| ERROR   | `"Error during streaming: %s"` |

---

#### `ztp.api`

**ERROR and WARNING messages:**

| Level | Message |
|-------|---------|
| ERROR | `"Error invoking backup workflow: %s"` |
| ERROR | `"Serial number mismatch observed on device %s, expected: %s, observed: %s."` |

---

#### `temporal.workflow`

**Sample INFO messages:**

- `"Scheduling backups for %s"`
- `"Backup scheduling updates complete."`

**ERROR and WARNING messages:**

| Level   | Message |
|---------|---------|
| ERROR   | `"Received approve signal for non-existent stage: %s"` |
| ERROR   | `"Received reject signal for non-existent stage: %s"` |
| ERROR   | `"Received retry signal for non-existent stage: %s"` |
| WARNING | `"Ignoring retry request for non-retryable stage."` |
| WARNING | `"Ignoring retry request for non-failed stage."` |
| ERROR   | `"No RBAC configuration found for %s"` |
| ERROR   | `"Error querying desired devices from Nautobot, leaving schedules unchanged."` |

---

#### `temporal.activity`

**Sample INFO messages:**

- `"Scanning range %s-%s for Redfish hosts"`
- `"Creating eth0 interface for %s"`

**ERROR and WARNING messages:**

| Level   | Message |
|---------|---------|
| WARNING | `"Redfish vendor %s not supported for host %s, skipping"` |
| WARNING | `"Server %s has %s installed devices but %s DPUs, skipping"` |
| WARNING | `"ARP entry missing data, skipping: %s"` |
| WARNING | `"Authentication failed for %s@%s (attempt %d/%d): %s"` |
| WARNING | `"Duplicate MAC address %s on device %s: using newest entry"` |
| WARNING | `"Error querying %s, rebuilding: %s"` |
| WARNING | `"UFM authentication failed for %s (attempt %d/%d): HTTP %d"` |
| ERROR   | `"Failed to invoke backup workflow for device %s: %s"` |
| ERROR   | `"Failed to post batch. HTTP status: %d"` |
| ERROR   | `"Request failed with status %d: %s"` |
| ERROR   | `"Request error: %s"` |
| WARNING | `"Server error (500). Retry attempt %d/%d in %d seconds..."` |

---

#### `temporal.api`

**Sample INFO messages:**

- `"RBAC configuration loaded: %s workflows found"`
- `"Registered dynamic endpoint: %s -> %s"`

**ERROR and WARNING messages:**

| Level   | Message |
|---------|---------|
| ERROR   | `"Workflow %s of type %s has not implemented the %s query."` |
| ERROR   | `"Workflow %s of type %s is in a bad state and cannot accept queries."` |
| ERROR   | `"User %s with roles %s is not authorized to execute workflow %s"` |
| ERROR   | `"No RBAC configuration found for workflow %s"` |
| ERROR   | `"Workflow %s of type %s does not have %s search attributes"` |
| ERROR   | `"User %s with roles %s does not have permission to %s workflow %s of type %s"` |
| WARNING | `"Workflow %s does not use WorkflowMetadataMixin, skipping dynamic registration"` |
| WARNING | `"Workflow %s has incomplete metadata, skipping dynamic registration"` |
| WARNING | `"Workflow %s missing endpoint path or input class"` |
| ERROR   | `"Failed to register endpoint for %s: %s"` |
| ERROR   | `"Codec server failed to parse request body"` |
| ERROR   | `"Codec server decode failed"` |
| ERROR   | `"Codec server encode failed"` |

---

#### `nautobot`

**Sample INFO messages:**

- `"Fetched %d devices in current page (offset: %d)"`
- `"Found namespaces: %s"`

**ERROR and WARNING messages:**

| Level   | Message |
|---------|---------|
| WARNING | `"Device %s not found in Nautobot"` |
| ERROR   | `"Failed to get device %s: %s"` |
| ERROR   | `"Failed to parse device %s: %s"` |
| ERROR   | `"Failed to get all devices: %s"` |
| ERROR   | `"Error parsing interface %s"` |
| ERROR   | `"Failed to create VRFs"` |

---

#### `auth`

**Sample INFO messages:**

- `"Opening browser for OIDC authentication..."`
- `"Authentication successful!"`

**ERROR and WARNING messages:**

| Level   | Message |
|---------|---------|
| WARNING | `"Unexpected error validating JWT with provider %s"` |
| WARNING | `"Failed to parse mTLS certificate from header"` |
| WARNING | `"User %s denied: not in any allowed group"` |
| WARNING | `"User %s denied: missing required group (needs one of %s, has %s)"` |
| WARNING | `"Error loading cached token: %s"` |
| ERROR   | `"Token exchange failed: %s"` |

---

#### `nats`

**Sample INFO messages:**

- `"Publishing to NATS subject=%s (message_len=%d)"`
- `"Connected to NATS %s"`

**ERROR and WARNING messages:**

| Level | Message |
|-------|---------|
| ERROR | `"NATS publish failed: subject=%s server=%s error=%s"` |
| ERROR | `"NATS error: %s"` |
| ERROR | `"NATS connection failed: server=%s error=%s"` |
| ERROR | `"NVIDIA Config Manager JetStream stream not found (publish will fail): server=%s"` |

---

#### `cache`

**Sample INFO messages:**

- `"Redis connection established: %s:%d (db=%d) ssl=%s timeout=%ds"`
- `"Starting background cache refresh loop (interval=%ds)"`

**ERROR and WARNING messages:**

| Level   | Message |
|---------|---------|
| ERROR   | `"Failed to connect to Redis at %s:%d - connection timeout after %ds"` |
| ERROR   | `"Failed to connect to Redis at %s:%d - %s"` |
| ERROR   | `"Failed to get device %s from cache: %s"` |
| WARNING | `"Device %s not found in Nautobot"` |
| ERROR   | `"Failed to refresh device %s: %s"` |
| WARNING | `"No devices returned from Nautobot"` |
| ERROR   | `"Failed to cache device %s: %s"` |
| ERROR   | `"Failed to refresh all devices: %s"` |
| ERROR   | `"Failed to search devices by name: %s"` |
| ERROR   | `"Error in background refresh loop: %s"` |
| ERROR   | `"Nautobot token is not configured"` |
| ERROR   | `"Fatal error in cache refresh service: %s"` |

## Prometheus Metrics

### Render Service

Defined in `src/nv_config_manager/render/dispatch.py`:

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `nv_config_manager_event_processing_time` | Histogram | model, instance, namespace | Event processing duration |
| `nv_config_manager_events_received` | Counter | model, instance, namespace | Events received via NATS |
| `nv_config_manager_events_processed` | Counter | model, instance, namespace | Events successfully processed |
| `nv_config_manager_events_skipped` | Counter | model, instance, namespace | Events skipped (device not enabled) |
| `nv_config_manager_events_failed` | Counter | model, instance, exception_class, namespace | Events that failed processing |
| `nv_config_manager_nautobot_change_message_processing_time` | Histogram | — | Nautobot change message processing time |
| `nv_config_manager_nautobot_change_message_end_to_end_time` | Histogram | — | End-to-end latency for change messages |
| `nv_config_manager_nautobot_change_messages_received` | Counter | — | Change messages received |
| `nv_config_manager_nautobot_change_messages_processed` | Counter | — | Change messages processed |
| `nv_config_manager_nautobot_change_messages_failed` | Counter | instance, exception_class, namespace | Failed change messages |

### DHCP Service

Defined in `src/nv_config_manager/dhcp/metrics.py` (counters/histogram) and
`src/nv_config_manager/dhcp/api.py` (cache refresh gauge):

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `nv_config_manager_dhcp_config_generation_errors_total` | Counter | error_type, ip_version | Config generation errors by type |
| `nv_config_manager_dhcp_query_errors_total` | Counter | error_type | Nautobot query/data validation errors |
| `nv_config_manager_dhcp_config_generation_duration_seconds` | Histogram | ip_version | Config generation duration |
| `nv_config_manager_dhcp_cache_refresh_errors_total` | Counter | ip_version | Cache refresh failures |
| `nv_config_manager_dhcp_cache_last_refresh_timestamp_seconds` | Gauge | ip_version | Unix timestamp of last successful refresh |

#### DHCP Error Types

`nv_config_manager_dhcp_config_generation_errors_total` error_type values:
- `missing_serial` — Serial number required for client ID but not present
- `template_error` — Jinja2 template rendering error in client_id_template
- `router_override` — Attempt to override the routers option
- `no_ztp_server` — No ZTP server found in DHCP context

`nv_config_manager_dhcp_query_errors_total` error_type values:
- `gateway_outside_subnet` — Gateway IP is not within the subnet
- `no_interfaces` — Reserved IP has no interfaces assigned
- `multiple_interfaces` — Reserved IP has multiple interfaces assigned
- `missing_mac_serial` — Interface has no MAC address or serial number

## Local Observability Stack (Dev Only)

For local development on Kind (or airgapped demo boxes) the Helm chart can
bundle a self-contained metrics stack as subcharts, all installed in the
nv-config-manager release namespace. The pieces:

- **prometheus-operator-crds** — installs only the
  `monitoring.coreos.com/v1` CRDs (PodMonitor, ServiceMonitor, Probe,
  PrometheusRule, Alertmanager, AlertmanagerConfig, Prometheus,
  ThanosRuler, ScrapeConfig). No Operator pod, no admission webhooks, no
  Prometheus.
- **prometheus** — standalone Prometheus running with
  `--web.enable-remote-write-receiver`. Pure storage backend; doesn't
  scrape anything itself.
- **alloy** — DaemonSet that owns metrics scraping. Watches PodMonitor /
  ServiceMonitor / Probe CRs natively via its `prometheus.operator.*`
  components, scrapes the targets, and `prometheus.remote_write`s to
  Prometheus.

```
   prometheus-operator-crds subchart
    \-- installs PodMonitor / ServiceMonitor / Probe / etc. CRDs only.

   Alloy DaemonSet
    |-- prometheus.operator.podmonitors    \
    |-- prometheus.operator.servicemonitors  >-- watches CRs cluster-wide,
    |-- prometheus.operator.probes         /    scrapes targets directly
    |     |
    |     \-> prometheus.remote_write -> standalone Prometheus (storage)
```

### Why no Prometheus Operator pod?

The Operator's job in the standard kube-prometheus-stack model is "watch
PodMonitor/ServiceMonitor/Probe CRs and translate them into a Prometheus
scrape config Secret." Grafana Alloy includes the same translator
in-process (the `prometheus.operator.*` components), so we get the
PodMonitor user-facing API without running a separate Operator deployment.
The `prometheus-operator-crds` chart provides the CRD definitions, the
PodMonitor resources in
[`deploy/helm/templates/monitoring.yaml`](../deploy/helm/templates/monitoring.yaml)
get applied, and Alloy picks them up.

This also means Alloy clustering (gossip-based consistent-hash sharding,
the equivalent of OpenTelemetry's Target Allocator) is the path forward
if we ever need to scale this beyond a single replica. Not enabled in
local dev, but the architecture supports it.

### How are Prometheus CRDs handled?

The installer does not run a separate kube-prometheus-stack release for
the local-dev observability stack. When
`infrastructure.monitoring.observability_enabled` is true, the deployer
pre-installs the `prometheus-operator-crds` chart as
`nv-config-manager-prom-crds` in `nv-config-manager-monitoring`, then
layers `values-observability.yaml` into the main Helm release.

This still touches cluster-scoped `monitoring.coreos.com` CRDs. If another
platform release already owns those CRDs, Helm can fail with CRD ownership
errors. Use one CRD owner per cluster.

### Why is this dev-only?

- The local Prometheus uses `emptyDir` storage; restarts lose all metrics.
- The CRD install is cluster-scoped, so it must not conflict with a platform
  monitoring stack.

### Enabling

| Entry point          | How to enable                                                  |
|----------------------|----------------------------------------------------------------|
| TUI installer        | Infrastructure screen -> "Enable local observability stack (Prometheus + Alloy, dev only)". Auto-enables the chart's `monitoring.enabled` gate so PodMonitors render. |
| Installer config     | Set `infrastructure.monitoring.observability_enabled: true`; the deployer layers `values-observability.yaml` and enables `monitoring.enabled`. |
| Raw `helm`           | `helm dependency update deploy/helm && helm install ... -f deploy/helm/values-observability.yaml --set monitoring.enabled=true`. |

### Access

After `helm install` completes:

```bash
kubectl port-forward -n nv-config-manager svc/prometheus-server 9090:9090
```

Open [http://localhost:9090](http://localhost:9090) and query
`{namespace="nv-config-manager"}` to confirm Alloy is remote-writing
scraped metrics.

### Adding a new scrape target

Add a PodMonitor / ServiceMonitor / Probe to
[`deploy/helm/templates/monitoring.yaml`](../deploy/helm/templates/monitoring.yaml).
Alloy's `prometheus.operator.*` components watch those CRDs cluster-wide
and pick up new resources within seconds. No Prometheus restart, no
config reload, no Alloy config changes.

### Debugging the metrics pipeline

```bash
# Alloy's UI: see discovered components and target health
kubectl port-forward -n nv-config-manager ds/alloy 12345:12345
open http://localhost:12345

# Prometheus's own UI: confirm series are arriving via remote_write
kubectl port-forward -n nv-config-manager svc/prometheus-server 9090:9090
open http://localhost:9090/targets    # empty (Prometheus doesn't scrape)
open http://localhost:9090/graph       # query: {namespace="nv-config-manager"}
```

If metrics are empty, it's almost always one of:
1. The PodMonitor port name doesn't match a container port name in the pod spec.
2. The nv-config-manager `monitoring.enabled` gate is false (PodMonitors didn't render).
3. The pod's `/metrics` endpoint isn't exposing what the dashboard query expects.

## Grafana Dashboards

A reference Grafana dashboard ships with the Helm chart at
[`deploy/helm/dashboards/`](../deploy/helm/dashboards/):

| Dashboard | File | Description |
|-----------|------|-------------|
| NVIDIA Config Manager Overview | [`nv-config-manager-overview.json`](../deploy/helm/dashboards/nv-config-manager-overview.json) | Error logs, metrics, throughput, and logs by service |

### Importing into Grafana

1. Copy the JSON file from [`deploy/helm/dashboards/`](../deploy/helm/dashboards/)
2. In Grafana, go to **Dashboards > Import** and upload the JSON file
3. Select your **Prometheus** and **Loki** data sources from the dropdowns

### Dashboard Variables

After import, configure the variables at the top of the dashboard:

| Variable | Description | Example |
|----------|-------------|---------|
| **Prometheus** | Prometheus data source that scrapes NVIDIA Config Manager PodMonitors | `mimir-us-west-2` |
| **Loki** | Loki data source that ingests NVIDIA Config Manager pod logs | `loki-us-west-2` |
| **Log Selector** | Loki stream selector labels (varies by environment) | `namespace="nv-config-manager"` or `cluster="my-cluster", k8s_namespace_name="nv-config-manager-prod"` |
| **Namespace** | Kubernetes namespace for Prometheus metric filtering | `nv-config-manager` |

### Using the Dashboard

The overview dashboard is divided into sections:

- **Render / DHCP Error Logs** — Error and warning logs for the two most
  operationally critical services. Click any log row to expand it and view
  the full traceback in the `exc_info` field.
- **Metrics** — Render Events (processed vs failed rate), DHCP Config Age
  (seconds since last successful Kea config refresh), and HTTP Request Rate
  by handler.
- **Logs by Service** — All logs for each NVIDIA Config Manager service (Render, DHCP, KEA
  DHCP, Config Store, ZTP, Temporal). The KEA DHCP panel shows raw Kea
  server logs filtered to DHCP4/DHCP6 request activity. Click any row to
  expand and view all structured fields (`category`, `service`, `levelname`,
  `exc_info`, etc.).

  You can also use the explore button on each panel to filter logs down further as desired.

### Linking Grafana from the UI

Set `monitoring.grafanaUrl` in your Helm values to display a Grafana link on
the NVIDIA Config Manager splash page:

```yaml
monitoring:
  grafanaUrl: "https://grafana.example.com"
```

### Loki Label Expectations

The dashboard queries use selective JSON extraction (`| json service,
category, levelname, message, exc_info`) from the log body. The stream
selector labels (configured via the **Log Selector** variable) depend on your
log shipping setup. Common labels:

| Label                | Source | Description |
|----------------------|--------|-------------|
| `namespace`          | Kubernetes | Namespace (standard Promtail/Loki setups) |
| `k8s_namespace_name` | OTEL Collector | Namespace (OpenTelemetry setups) |
| `cluster`            | OTEL Collector | Cluster name (multi-cluster environments) |
