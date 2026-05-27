# Nautobot Integration

Nautobot is the source of truth for inventory, topology, locations, roles, platforms, IP assignments, config contexts, and NVIDIA Config Manager application data.

## Deployment

Set `services.nautobot: true` to deploy the bundled Nautobot stack. Set it to `false` and configure `external_services.nautobot` when using an existing Nautobot instance.

```yaml
services:
  nautobot: true
external_services:
  nautobot:
    enabled: false
    url: https://nautobot.config-manager.local
```

The installer can stage bootstrap jobs and custom jobs into the Nautobot jobs PVC:

```yaml
content:
  include_bootstrap_jobs: true
  jobs:
    - path: development/mock_topology
  run_after_deploy:
    - job: mock_topology.jobs.mock_topology_design.MockTopologyDesign
      input: '{"blueprint": "superpod", "deployment_name": "test"}'
```

## Access

```bash
kubectl get secret nautobot-admin -n nv-config-manager -o jsonpath='{.data.password}' | base64 -d && echo
kubectl get secret nautobot-admin -n nv-config-manager -o jsonpath='{.data.api_token}' | base64 -d && echo
```

Local profile URL:

```text
https://nautobot.config-manager.local
```

## GraphQL and REST

Runtime services query Nautobot through GraphQL and REST using the Nautobot API token from installer-managed secrets. Exact plugin field names are currently dictated by the vendored Nautobot plugin and should remain isolated to client/query code until the plugin rename lands.

## NATS Events

The bundled Nautobot deployment can publish events to NATS JetStream through `nautobot-broker-nats`. Stream names and subjects are configured in Helm values and rendered into the app config; existing deployments can retain their current subjects.

## Jobs

Use installer `content.jobs` for job directories or tarballs. Use `content.run_after_deploy` for post-deploy job execution. Re-running the installer updates the jobs PVC and restarts Nautobot only when staged job content changes.

## Development

```bash
make docker-build-nb
make topology
kubectl logs -n nv-config-manager deployment/nautobot -f
```

## Related Documentation

- [Architecture](architecture.md)
- [Render](render.md)
- [Temporal](temporal.md)

