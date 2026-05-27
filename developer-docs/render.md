# Render Service

The Render service consumes inventory and workflow events, renders network configuration templates, writes results to Config Store, and updates Nautobot plugin state where applicable.

## Event Processing

Render consumers subscribe to configurable NATS JetStream streams and subjects for inventory changes, device changes, and workflow results. Existing stream names are preserved by configuration; do not hardcode stream or subject strings in service code.

## API

```bash
# Health
curl -k https://render.config-manager.local/health

# List consumers
curl -k https://render.config-manager.local/api/v1/admin/consumers

# Reset one consumer
curl -k -X POST https://render.config-manager.local/api/v1/admin/consumers/nautobot/reset

# Queue a render for a device
curl -k -X POST https://render.config-manager.local/api/v1/render/device/<device-id>
```

The OpenAPI spec is `docs/api-specs/render.openapi.json`.

## Runtime Configuration

```ini
[render]
api_service = http://nv-config-manager-render-api:8000
api_url = https://render.config-manager.local
use_internal = true

[nautobot]
url = https://nautobot.config-manager.local

[redis]
host = redis.nv-config-manager.svc.cluster.local
port = 6379
```

NATS stream and subject settings are rendered by Helm into the runtime config secret from chart values.

## Template Plugins

The installer can stage one or more Jinja2 template plugin directories into a PVC and mount them into the Render service. Configure this in the Template Plugins TUI section or in `content.template_plugins`.

```yaml
content:
  template_plugins:
    - path: ../nv-config-manager-templates
      storage_class: standard
      access_mode: ReadWriteOnce
```

## Local Development

```bash
uv run uvicorn nv_config_manager.render.api.main:app --reload --port 8083
uv run python -m nv_config_manager.render.consumer
uv run pytest src/tests/render/
```

Deploy with Render enabled by setting `services.render: true` in installer config.

## Metrics

Render emits metrics for queue depth, render duration, render failures, lock contention, and API request latency. See [Logging and Observability](logging.md).

## Related Documentation

- [Architecture](architecture.md)
- [Config Store](config-store.md)
- [Nautobot](nautobot.md)
- [OpenAPI specs](../docs/api-specs)

