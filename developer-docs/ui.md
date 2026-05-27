# Unified UI

The NVIDIA Config Manager UI is a Next.js application for workflow operations, approval handling, and configuration browsing.

## Local Development

```bash
cd ui
npm install
cp .env.example .env.local 2>/dev/null || true
npm run dev
```

Access the dev server at `http://localhost:3000`.

Example `.env.local`:

```env
NEXT_PUBLIC_WORKFLOW_API_URL=https://workflow.config-manager.local
NEXT_PUBLIC_CONFIG_STORE_API_URL=https://config-store.config-manager.local
NAUTOBOT_URL=https://nautobot.config-manager.local
```

## Runtime Configuration

The production container reads runtime settings from Helm values and generated config files. The base hostname is provided by the installer through `cluster.hostname` and rendered into the chart as `global.baseHostname`.

```yaml
global:
  baseHostname: config-manager.local
ui:
  enabled: true
```

This exposes the UI at:

```text
https://config-manager.local
https://config-manager.local/workflows
https://config-manager.local/configs
```

## Main Views

| View | Purpose |
| ---- | ------- |
| `/workflows` | Browse, launch, approve, retry, and inspect workflows |
| `/configs` | Browse device configuration artifacts and versions |
| Auth callback routes | Complete OIDC login flows when SSO is enabled |

Dropdown parameters for workflow forms are fetched from Temporal parameter endpoints. Managed-device filters use the API `managed_only=true` query parameter.

## Testing

```bash
cd ui
npx playwright install
npm run test:e2e
npm run test:e2e:headed
npm run lint
npm run build
```

## Docker

```bash
make docker-build-ui
```

The Helm chart deploys the image as `nv-config-manager-ui`.

## Related Documentation

- [Temporal](temporal.md)
- [Config Store](config-store.md)
- [Authentication in README](../README.md#authentication)

