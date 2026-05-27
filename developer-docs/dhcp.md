# DHCP Service

The DHCP service renders Kea configuration from Nautobot data, validates it, and applies it to the Kea DHCP server. It provides device bootstrapping support for ZTP and can run with in-memory leases or a PostgreSQL lease database.

## Data Sources

DHCP reservations are built from Nautobot device, interface, IP address, platform, location, and config context data. The rendered Kea configuration includes subnets, reservations, boot file URLs, option data, and platform-specific metadata needed by ZTP.

## Commands

```bash
# Generate and apply Kea config
uv run nv-config-manager-dhcp generate

# Run a standalone refresh loop for local debugging
uv run nv-config-manager-dhcp generate --watch --interval 300

# Validate generated config without updating Kea
uv run nv-config-manager-dhcp generate --check
```

## API

```bash
curl -k https://dhcp.config-manager.local/health
curl -k https://dhcp.config-manager.local/v1/config
curl -k -X POST https://dhcp.config-manager.local/v1/refresh
curl -k https://dhcp.config-manager.local/v1/contexts
```

The OpenAPI spec is `docs/api-specs/dhcp.openapi.json`.

## Runtime Configuration

```ini
[dhcp]
api_service = http://nv-config-manager-dhcp-api:8000
api_url = https://dhcp.config-manager.local

[kea]
control_socket = /run/kea/kea4-ctrl-socket

[database]
host = cluster-dhcp-rw.nv-config-manager.svc.cluster.local
port = 5432
name = dhcp

[nautobot]
url = https://nautobot.config-manager.local

[redis]
host = redis.nv-config-manager.svc.cluster.local
port = 6379
```

## Kea Management

```bash
kubectl logs -n nv-config-manager deployment/nv-config-manager-kea -f
kubectl logs -n nv-config-manager deployment/nv-config-manager-dhcp-api -f
kubectl exec -n nv-config-manager deploy/nv-config-manager-kea -- kea-shell -s /run/kea/kea4-ctrl-socket lease4-get-all
```

## Local Development

```bash
uv run nv-config-manager-dhcp generate --check
uv run pytest src/tests/dhcp/
uv run pytest src/tests/integration/test_dhcp.py -v
```

Deploy with DHCP enabled by setting `services.dhcp: true` in the installer config and running the installer deploy command.

## Metrics

The service emits counters and histograms for config generation, validation, API requests, Kea reloads, and failure categories. See [Logging and Observability](logging.md).

