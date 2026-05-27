# NVIDIA Config Manager Architecture

NVIDIA Config Manager is deployed as a Helm release that combines APIs, workers, Nautobot, data stores, eventing, and device-facing services.

## Control Plane

```text
Users and automation
  -> Envoy Gateway
     -> UI
     -> Workflow API
     -> Config Store API
     -> Render API
     -> Nautobot

Nautobot
  -> NATS JetStream
     -> Render event consumers
     -> Workflow event consumers

Temporal workers
  -> Nautobot
  -> Render
  -> Config Store
  -> Managed devices

ZTP and DHCP
  -> Nautobot inventory
  -> Config Store artifacts
  -> Device-facing HTTP, SFTP, and DHCP flows
```

## Service Responsibilities

| Component | Responsibility |
| --------- | -------------- |
| Envoy Gateway | TLS termination, host routing, OIDC/JWT enforcement, and service exposure |
| UI | Workflow launch and review, configuration browsing, and operator-facing navigation |
| Nautobot | Source of truth, Git-backed jobs, custom app data, and event publishing |
| NATS JetStream | Durable event streams for inventory changes, device state, and workflow results |
| Render | Template rendering, intended configuration writes, and render queue processing |
| Config Store | Versioned rendered, intended, and backup configuration files |
| Temporal | Workflow API, workers, approvals, retries, and long-running network operations |
| ZTP | Boot scripts, OS images, startup configuration delivery, and provisioning callbacks |
| DHCP | Kea configuration generation and DHCP service management |
| PostgreSQL | Service databases managed by CloudNativePG unless external Postgres is configured |
| Redis | Caching and distributed locking |

## Configuration Flow

The installer owns deployment configuration. `nv-config-manager-install.yaml` is converted into Helm values, generated Kubernetes secrets, and the `nv-config-manager-ini` secret consumed by runtime services.

Common generated artifacts:

- Helm override values for enabled services, hostnames, images, operators, load balancers, SSO, SPIFFE, and monitoring.
- Application secrets for Kubernetes-native mode, or External Secrets Operator mappings for Vault/OpenBao mode.
- Per-site `config-secrets.ini` entries for device credentials and workflow secrets.
- PVC content for custom Nautobot jobs, template plugins, and file-backed ZTP OS images.

## Eventing

Nautobot publishes durable events into NATS JetStream. Stream names and subjects are Helm-configurable so existing environments can keep their current stream topology while new deployments can choose their own names. Consumers should read stream and subject values from configuration rather than hardcoding them.

## Authentication

Browser traffic normally uses OIDC through Envoy Gateway. CLI and automation traffic can use `svc-*` hostnames with bearer tokens. Service-to-service traffic can use internal cluster service names, SPIFFE JWT-SVIDs, or mTLS depending on installer configuration.

## OpenAPI Surface

OpenAPI specs are generated from the FastAPI applications and stored under `docs/api-specs`. The rename does not intentionally change API paths or HTTP methods. Run `make openapi-check` before merging API changes.

