# Temporal Workflows Service

The Temporal service provides workflow APIs, workers, scheduling, approval gates, and operational automation for managed network devices.

## Workflow Categories

| Category | Examples |
| -------- | -------- |
| Device operations | Backup, render, deploy, password rotation |
| Validation | Cable validation, BGP validation, fabric health checks |
| Upgrade | Firmware and NOS upgrade workflows |
| Simulation | AIR-backed environment workflows |
| Administration | RBAC-aware workflow discovery and approval handling |

## API

```bash
curl -k https://workflow.config-manager.local/health
curl -k https://workflow.config-manager.local/whoami
curl -k https://workflow.config-manager.local/v1/workflow/types
curl -k https://workflow.config-manager.local/v1/workflows
curl -k https://workflow.config-manager.local/v1/parameter/site
curl -k 'https://workflow.config-manager.local/v1/parameter/device?limit=50'
```

The OpenAPI spec is `docs/api-specs/temporal.openapi.json`.

## CLI

The workflow CLI uses the shared OIDC helper for SSO deployments and can also target local deployments through `--base-hostname`.

```bash
uv run workflow-cli login -H config-manager.local -k
uv run workflow-cli types -H config-manager.local -k
uv run workflow-cli backup -H config-manager.local --device-name switch001.example.com -k
```

## Runtime Configuration

```ini
[temporal]
grpc_service = temporal-frontend-service.nv-config-manager.svc.cluster.local:7233
api_service = http://nv-config-manager-temporal-api:8000
api_url = https://workflow.config-manager.local
ui_url = https://config-manager.local
use_internal = true

[nautobot]
server = https://nautobot.config-manager.local

[redis]
host = redis.nv-config-manager.svc.cluster.local
port = 6379
```

## RBAC

Workflow RBAC is configured in installer config and rendered into Helm values. Defaults can grant broad access for local development; production deployments should set explicit admin, read, and execute roles.

```yaml
rbac:
  admin_roles:
    - network-admin
  default_read_roles:
    - network-operator
  default_execute_roles:
    - network-operator
  workflows:
    backup:
      execute_roles:
        - network-admin
```

## Development

```bash
uv run python -m nv_config_manager.temporal.worker.main
uv run uvicorn nv_config_manager.temporal.api.main:app --reload --port 8082
uv run pytest src/tests/temporal/
```

Deploy with Temporal enabled by setting `services.temporal: true` in installer config.

## Temporal UI

Temporal UI is exposed on `https://temporal.<base-hostname>` and the unified UI links workflow detail pages where available.

## Related Documentation

- [UI](ui.md)
- [Config Store](config-store.md)
- [Device Authentication](device-auth.md)
- [OpenAPI specs](../docs/api-specs)

