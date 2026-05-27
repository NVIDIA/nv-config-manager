# OpenAPI Specifications

This directory contains generated OpenAPI JSON for the FastAPI services in NVIDIA Config Manager.

| File | Service |
| ---- | ------- |
| `ztp.openapi.json` | ZTP API |
| `dhcp.openapi.json` | DHCP API |
| `temporal.openapi.json` | Temporal workflow API |
| `render.openapi.json` | Render API |
| `config-store.openapi.json` | Config Store API |

Regenerate specs from the repository root:

```bash
uv run python scripts/generate_openapi.py
```

Check that committed specs are current:

```bash
uv run python scripts/generate_openapi.py --check
```

API path and method changes should be intentional and reviewed separately from documentation text changes.
