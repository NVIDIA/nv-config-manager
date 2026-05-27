# Config Store Service

Config Store is the versioned storage API for rendered, intended, and backup network configuration artifacts. It stores content in PostgreSQL and exposes both API endpoints and UI-backed browsing through the main NVIDIA Config Manager UI.

## File Types

| Type | Purpose |
| ---- | ------- |
| `rendered` | Output produced by the render service before deployment |
| `intended` | Configuration selected for a device deployment |
| `backup` | Configuration captured from a device |
| `metadata` | Supporting data used by workflows and UI views |

## API Patterns

Common operations:

```bash
# Read latest device config
curl -k https://config-store.config-manager.local/v1/configs/<device>/<path>

# Read a specific version
curl -k https://config-store.config-manager.local/v1/configs/<device>/<path>?commit=<commit-id>

# List versions
curl -k https://config-store.config-manager.local/v1/configs/<device>/<path>/versions

# Compare versions
curl -k https://config-store.config-manager.local/v1/configs/<device>/<path>/diff?from=<old>&to=<new>
```

The exact schema is documented in `docs/api-specs/config-store.openapi.json`.

## UI

The unified UI exposes configuration browsing at `/configs` on the base hostname:

```text
https://config-manager.local/configs
```

For direct local development, port-forward the UI or Config Store service as needed.

## Runtime Configuration

Config Store reads service settings from `nv-config-manager-ini`:

```ini
[config_store]
api_service = http://nv-config-manager-config-store-api:8000
api_url = https://config-store.config-manager.local

[database]
host = cluster-config-store-rw.nv-config-manager.svc.cluster.local
port = 5432
name = config_store

[redis]
host = redis.nv-config-manager.svc.cluster.local
port = 6379

[nautobot]
url = https://nautobot.config-manager.local
```

The installer renders these values from `nv-config-manager-install.yaml`, selected services, and external service settings.

## Cache Refresh

The cache refresh worker maintains device metadata used for UI enrichment and workflow links.

```bash
kubectl logs -n nv-config-manager deployment/nv-config-manager-config-store-cache -f
kubectl rollout restart deployment/nv-config-manager-config-store-cache -n nv-config-manager
```

## Development

```bash
uv run uvicorn nv_config_manager.config_store.api.main:app --reload --port 8084
uv run pytest src/tests/config_store/
```

## Related Documentation

- [Architecture](architecture.md)
- [Render](render.md)
- [Temporal](temporal.md)
- [OpenAPI specs](../docs/api-specs)

