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
make openapi
```

Check that committed specs are current:

```bash
make openapi-check
```

Regenerate the specifications and all committed Go clients together:

```bash
make api-generate
```

API path and method changes should be intentional and reviewed separately from documentation text changes.
