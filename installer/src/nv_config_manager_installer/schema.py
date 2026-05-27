# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Pydantic models for the nv-config-manager-install.yaml config schema.

This is the single source of truth for a NVIDIA Config Manager deployment configuration.
The TUI wizard populates these models; generate-values reads them to produce
Helm values and config-secrets.ini.
"""

from __future__ import annotations

import os
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, model_validator

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class DeploySize(StrEnum):
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class SecretsMethod(StrEnum):
    ESO = "eso"
    KUBERNETES = "kubernetes"


class VaultAuthMethod(StrEnum):
    JWT = "jwt"
    TOKEN = "token"


class PasswordSource(StrEnum):
    GENERATE = "generate"
    MANUAL = "manual"
    VAULT = "vault"


class SSOProvider(StrEnum):
    KEYCLOAK = "keycloak"
    AZURE = "azure"
    GENERIC = "generic"


class SPIFFEProvider(StrEnum):
    SPIRE = "spire"
    TELEPORT = "teleport"


class SPIFFEAuthMode(StrEnum):
    JWT = "jwt"
    MTLS = "mtls"


class GatewayType(StrEnum):
    ENVOY_GATEWAY = "envoyGateway"


class LBProvider(StrEnum):
    METALLB = "metallb"
    CILIUM = "cilium"
    NLB = "nlb"
    NONE = ""


class ZTPStorageType(StrEnum):
    S3 = "s3"
    FILE = "file"


class ImageSource(StrEnum):
    LOCAL = "local"
    REGISTRY = "registry"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------


class ClusterConfig(BaseModel):
    """Cluster-level deployment settings."""

    hostname: str = ""
    environment: str = "local"
    namespace: str = "nv-config-manager"
    release_name: str = "nv-config-manager"
    airgapped: bool = False
    mock_devices: bool = False
    size: DeploySize = DeploySize.SMALL


class VaultAuth(BaseModel):
    """Vault authentication configuration (token auth only).

    JWT auth fields (``mount_path``, ``role``) live on ``VaultConfig``
    because the Helm chart reads them at ``secrets.vault.mountPath`` and
    ``secrets.vault.role``, not under a nested auth key.
    """

    method: VaultAuthMethod = VaultAuthMethod.JWT
    token_secret_name: str = ""


class VaultPathConfig(BaseModel):
    """A single vault secret path with optional key-name overrides.

    When ``path`` is empty the installer auto-generates it from the
    environment name (``{env}/{group}``).  ``keys`` maps logical Helm key
    names to the actual Vault property names; the defaults match
    ``deploy/helm/sample-eso-config.yaml``.
    """

    enabled: bool = True
    path: str = ""
    keys: dict[str, str] = Field(default_factory=dict)


def _path(enabled: bool = True, **keys: str) -> VaultPathConfig:
    """Shorthand factory for default vault path configs."""
    return VaultPathConfig(enabled=enabled, keys=keys)


class VaultPathsConfig(BaseModel):
    """All vault secret path groups consumed by the Helm chart."""

    nautobot: VaultPathConfig = Field(
        default_factory=lambda: _path(token="token", natsPassword="nats_password")
    )
    redis: VaultPathConfig = Field(default_factory=lambda: _path(password="password"))
    postgres: VaultPathConfig = Field(
        default_factory=lambda: _path(
            temporalUser="temporal_user",
            temporalPassword="temporal_password",
            temporalVisibilityUser="temporal_visibility_user",
            temporalVisibilityPassword="temporal_visibility_password",
            configStoreUser="config_store_user",
            configStorePassword="config_store_password",
            dhcpUser="dhcp_user",
            dhcpPassword="dhcp_password",
            nautobotUser="nautobot_user",
            nautobotPassword="nautobot_password",
        )
    )
    network: VaultPathConfig = Field(
        default_factory=lambda: _path(user="user", password="password")
    )
    nautobot_app: VaultPathConfig = Field(
        default_factory=lambda: _path(
            adminPassword="admin_password",
            djangoSecretKey="django_secret_key",
            superuserApiToken="superuser_api_token",
        )
    )
    oidc: VaultPathConfig = Field(
        default_factory=lambda: _path(clientSecret="client_secret", cookieSecret="cookie_secret")
    )
    slack: VaultPathConfig = Field(default_factory=lambda: _path(enabled=False, token="token"))
    air: VaultPathConfig = Field(
        default_factory=lambda: _path(
            enabled=False, ssaClientId="ssa_client_id", ssaClientSecret="ssa_client_secret"
        )
    )
    jira: VaultPathConfig = Field(
        default_factory=lambda: _path(enabled=False, baseUrl="base_url", apiToken="api_token")
    )
    cnpg_backup: VaultPathConfig = Field(
        default_factory=lambda: _path(
            enabled=False, accessKeyId="ACCESS_KEY_ID", accessSecretKey="ACCESS_SECRET_KEY"
        )
    )


class VaultConfig(BaseModel):
    """Vault/OpenBao server configuration.

    ``mount_path`` and ``role`` are top-level because the chart reads them
    at ``secrets.vault.mountPath`` / ``secrets.vault.role``.
    """

    server: str = ""
    namespace: str = ""
    secrets_path: str = ""
    config_secrets_path: str = ""
    mount_path: str = ""
    role: str = ""
    auth: VaultAuth = Field(default_factory=VaultAuth)
    paths: VaultPathsConfig = Field(default_factory=VaultPathsConfig)


class K8sSecretGroup(BaseModel):
    """Manual value overrides for one secret group in kubernetes-secrets mode.

    Each key in ``values`` matches the corresponding vault property name so the
    same key names are meaningful in both ESO and kubernetes modes.
    An empty string value means the deployer should auto-generate a password.
    """

    enabled: bool = True
    values: dict[str, str] = Field(default_factory=dict)


class KubernetesSecretsConfig(BaseModel):
    """Optional manual overrides for kubernetes-mode secrets.

    Required groups default to enabled; optional integrations default to disabled.
    Any value left empty (or the group left at defaults) will be auto-generated
    by the deployer.
    """

    nautobot: K8sSecretGroup = Field(default_factory=K8sSecretGroup)
    redis: K8sSecretGroup = Field(default_factory=K8sSecretGroup)
    postgres: K8sSecretGroup = Field(default_factory=K8sSecretGroup)
    network: K8sSecretGroup = Field(default_factory=K8sSecretGroup)
    nautobot_app: K8sSecretGroup = Field(default_factory=K8sSecretGroup)
    slack: K8sSecretGroup = Field(default_factory=lambda: K8sSecretGroup(enabled=False))
    air: K8sSecretGroup = Field(default_factory=lambda: K8sSecretGroup(enabled=False))
    jira: K8sSecretGroup = Field(default_factory=lambda: K8sSecretGroup(enabled=False))
    cnpg_backup: K8sSecretGroup = Field(default_factory=lambda: K8sSecretGroup(enabled=False))


class SecretsConfig(BaseModel):
    """Secrets management configuration."""

    method: SecretsMethod = SecretsMethod.KUBERNETES
    vault: VaultConfig = Field(default_factory=VaultConfig)
    k8s: KubernetesSecretsConfig = Field(default_factory=KubernetesSecretsConfig)
    config_manager_service_username: str = "nv-config-manager"


class NetworkSecretEntry(BaseModel):
    """A network protocol secret (BGP, ISIS, TACACS, or any custom key).

    The name is a human-readable label. The secret_key is the INI field
    name (and Vault key when ESO is used). The description explains how
    the secret is used so operators understand its purpose.

    When source=manual, the ``value`` field must be populated with the actual
    secret before deployment.  Attempting to deploy with an empty value raises
    a ValueError.
    """

    name: str = ""
    description: str = ""
    source: PasswordSource = PasswordSource.GENERATE
    secret_key: str = ""
    rotation: str = "r1"
    required: bool = False
    value: str = ""


class SiteConfig(BaseModel):
    """A site (data center) that NVIDIA Config Manager manages."""

    name: str
    vault_path: str = ""


class JWTProvider(BaseModel):
    """An additional JWT provider for multi-issuer gateway validation.

    The primary provider is always derived from the main SSO config.
    Add entries here for extra issuers (e.g. SPIRE, Starfleet service accounts).
    Leave jwks_uri empty to auto-derive it from the issuer URL.
    """

    name: str = ""
    issuer: str = ""
    audiences: str = ""
    jwks_uri: str = ""


class SSOConfig(BaseModel):
    """SSO / OIDC configuration."""

    enabled: bool = False
    provider: SSOProvider = SSOProvider.KEYCLOAK
    issuer_url: str = ""
    client_id: str = ""
    client_secret: str = ""
    jwks_uri: str = ""
    internal_issuer: str = ""
    audiences: str = ""
    scopes: str = ""
    jwt_providers: list[JWTProvider] = Field(default_factory=list)


class SPIFFEConfig(BaseModel):
    """SPIFFE mTLS / JWT-SVID configuration."""

    enabled: bool = False
    provider: SPIFFEProvider = SPIFFEProvider.SPIRE
    auth_mode: SPIFFEAuthMode = SPIFFEAuthMode.JWT
    trust_domain: str = ""
    socket_mount_path: str = "/spiffe-workload-api"
    socket_file: str = "spire-agent.sock"
    socket_host_path: str = "/var/run/teleport"
    group_prefixes: list[str] = Field(default_factory=list)


class GitTokenEntry(BaseModel):
    """A git repository token for Nautobot git sync (e.g. Prismo).

    Creates a K8s secret ``git-token-<name>`` with the token value.
    Nautobot pods receive env vars ``GIT_TOKEN_<NAME>`` (and optionally
    ``GIT_USERNAME_<NAME>``).  For ESO, ``vault_path`` can point to
    the Vault path that holds the credential.
    """

    name: str
    token: str = ""
    username: str = ""
    vault_path: str = ""


class JobPath(BaseModel):
    """Path to a custom Nautobot job directory or tarball."""

    path: str


class TemplatePath(BaseModel):
    """Path to a template plugin directory or tarball."""

    path: str


class PostDeployJob(BaseModel):
    """A Nautobot job to run after deployment."""

    job: str
    input: str = ""


class TemplatePluginsConfig(BaseModel):
    """Scheduling and storage configuration for the template plugin PVC."""

    storage_class: str = ""
    access_mode: str = "ReadWriteOnce"
    node_selector: dict[str, str] = Field(default_factory=dict)


class JobsConfig(BaseModel):
    """Scheduling and storage configuration for the Nautobot jobs PVC."""

    storage_class: str = ""
    access_mode: str = "ReadWriteOnce"
    node_selector: dict[str, str] = Field(default_factory=dict)


class ContentConfig(BaseModel):
    """Custom jobs, template plugins, and post-deploy job execution."""

    jobs: list[JobPath] = Field(default_factory=list)
    jobs_config: JobsConfig = Field(default_factory=JobsConfig)
    template_plugins: list[TemplatePath] = Field(default_factory=list)
    template_plugins_config: TemplatePluginsConfig = Field(default_factory=TemplatePluginsConfig)
    include_bootstrap_jobs: bool = True
    run_after_deploy: list[PostDeployJob] = Field(default_factory=list)


class ServicesConfig(BaseModel):
    """Toggle individual NVIDIA Config Manager services on/off.

    When ``nautobot`` is True a local Nautobot + NATS + Redis stack is deployed.
    Set it to False and provide ``external_nautobot_url`` to use an existing
    Nautobot server (e.g. a shared staging/prod instance).
    """

    render: bool = True
    ztp: bool = True
    dhcp: bool = True
    temporal: bool = True
    config_store: bool = True
    nautobot: bool = True
    external_nautobot_url: str = ""


class RedfishVendorCreds(BaseModel):
    """Per-vendor Redfish/BMC credentials."""

    default_user: str = ""
    default_password: str = ""
    config_manager_password: str = ""


class RedfishConfig(BaseModel):
    """Redfish/BMC workflow configuration.

    Enable only if Redfish provisioning workflows are in use.
    Vendors default to ``lenovo`` and ``bluefield`` matching the Helm chart
    secret key layout (``lenovo-default-user``, etc.).
    """

    enabled: bool = False
    vendors: dict[str, RedfishVendorCreds] = Field(default_factory=dict)


class CNPGBackupConfig(BaseModel):
    """CNPG S3 backup configuration."""

    enabled: bool = False
    bucket: str = ""
    path: str = ""
    endpoint: str = ""


class MonitoringConfig(BaseModel):
    """Monitoring / observability configuration."""

    enabled: bool = False
    # Bundles Prometheus + Grafana Alloy as subcharts of nv-config-manager
    # (see deploy/helm/values-observability.yaml). LOCAL-DEV / KIND ONLY.
    # Grafana/Loki are AGPL-licensed and are not enabled by the default
    # installer-managed observability path.
    observability_enabled: bool = False


class NLBServiceConfig(BaseModel):
    """AWS NLB configuration for a single service (ZTP or DHCP).

    Each service gets its own NLB with independent security groups, subnets,
    static IPs, and DNS names.
    """

    type: str = "external"
    target_type: str = "ip"
    name: str = ""
    sg: str = ""
    subnets: str = ""
    ips: str = ""
    dns_name: str = ""


class NLBGatewayConfig(BaseModel):
    """AWS NLB configuration for the Envoy Gateway service.

    Controls the NLB that fronts the main Envoy Gateway for HTTP/HTTPS traffic.
    """

    type: str = "external"
    target_type: str = "ip"
    name: str = ""
    sg: str = ""
    subnets: str = ""
    ips: str = ""
    dns_name: str = ""


class LoadBalancerConfig(BaseModel):
    """Load balancer configuration for ZTP/DHCP device access."""

    provider: LBProvider = LBProvider.NONE

    # MetalLB / Cilium fields
    ztp_lb_ip: str = ""
    dhcp_lb_ip: str = ""
    ztp_dns_name: str = ""
    dhcp_dns_name: str = ""
    allowed_prefixes: list[str] = Field(default_factory=list)

    # AWS NLB fields (per-service and gateway)
    nlb_gateway: NLBGatewayConfig = Field(default_factory=NLBGatewayConfig)
    nlb_ztp: NLBServiceConfig = Field(default_factory=NLBServiceConfig)
    nlb_dhcp: NLBServiceConfig = Field(default_factory=NLBServiceConfig)


class ZTPOSImage(BaseModel):
    """A single OS image to upload to ZTP file storage."""

    platform: str = ""
    version: str = ""
    path: str = ""


class ZTPStorageConfig(BaseModel):
    """ZTP service storage configuration for OS images and firmware."""

    type: ZTPStorageType = ZTPStorageType.FILE
    pvc_name: str = "ztp-os-images"
    pvc_size: str = "10Gi"
    storage_class: str = ""
    access_mode: str = "ReadWriteOnce"
    node_selector: dict[str, str] = Field(default_factory=dict)
    s3_bucket: str = ""
    os_images: list[ZTPOSImage] = Field(default_factory=list)


class ExternalRedisConfig(BaseModel):
    """External Redis connection settings."""

    enabled: bool = False
    host: str = ""
    port: int = 6379
    ssl: bool = False
    password_auth: bool = True


class ExternalPostgresConfig(BaseModel):
    """External PostgreSQL host overrides (per-service).

    When enabled, any non-empty host replaces the default CNPG service name.
    Leave a host empty to keep the default in-cluster CNPG instance for that service.
    """

    enabled: bool = False
    port: int = 5432
    temporal_host: str = ""
    temporal_visibility_host: str = ""
    config_store_host: str = ""
    dhcp_host: str = ""
    nautobot_host: str = ""


class SlackConfig(BaseModel):
    """Slack integration configuration."""

    channel: str = ""


class ExternalServicesConfig(BaseModel):
    """Out-of-cluster dependency configuration."""

    redis: ExternalRedisConfig = Field(default_factory=ExternalRedisConfig)
    postgres: ExternalPostgresConfig = Field(default_factory=ExternalPostgresConfig)
    slack: SlackConfig = Field(default_factory=SlackConfig)


class InfrastructureConfig(BaseModel):
    """Infrastructure and gateway settings."""

    gateway: GatewayType = GatewayType.ENVOY_GATEWAY
    tls: bool = True
    cnpg_s3_backup: CNPGBackupConfig = Field(default_factory=CNPGBackupConfig)
    monitoring: MonitoringConfig = Field(default_factory=MonitoringConfig)
    load_balancer: LoadBalancerConfig = Field(default_factory=LoadBalancerConfig)
    ztp_storage: ZTPStorageConfig = Field(default_factory=ZTPStorageConfig)


class ImageOverride(BaseModel):
    """Per-image repository and/or tag override."""

    repository: str = ""
    tag: str = ""


class ImagePullSecret(BaseModel):
    """Docker registry pull secret configuration."""

    name: str = "regcred-nvcr"
    server: str = "nvcr.io"
    username: str = "$oauthtoken"
    password: str = ""


class ImagesConfig(BaseModel):
    """Container image source and registry configuration."""

    source: ImageSource = ImageSource.REGISTRY
    registry: str = "nvcr.io/nvidian/cfa"
    tag: str = ""
    pull_policy: str = "IfNotPresent"
    pull_secret: ImagePullSecret = Field(default_factory=ImagePullSecret)
    overrides: dict[str, ImageOverride] = Field(default_factory=dict)


NV_CONFIG_MANAGER_IMAGE_KEYS: list[tuple[str, str]] = [
    ("nvConfigManager", "nv-config-manager"),
    ("nvConfigManagerUi", "nv-config-manager-ui"),
    ("kea", "nv-config-manager-kea"),
    ("keaAdmin", "nv-config-manager-kea-admin"),
    ("nautobot", "nv-config-manager-nautobot"),
    ("natsReady", "nv-config-manager-nats-ready"),
]

# Image override keys accepted by the installer. The second field is the
# source repository used by airgap bundles before upload-to-registry.sh rewrites
# it under the target registry namespace.
IMAGE_OVERRIDE_KEYS: list[tuple[str, str]] = [
    ("nvConfigManager", "nvcr.io/nvidian/cfa/nv-config-manager"),
    ("nvConfigManagerUi", "nvcr.io/nvidian/cfa/nv-config-manager-ui"),
    ("kea", "nvcr.io/nvidian/cfa/nv-config-manager-kea"),
    ("keaAdmin", "nvcr.io/nvidian/cfa/nv-config-manager-kea-admin"),
    ("nautobot", "nvcr.io/nvidian/cfa/nv-config-manager-nautobot"),
    ("natsReady", "nvcr.io/nvidian/cfa/nv-config-manager-nats-ready"),
    ("httpEcho", "docker.io/hashicorp/http-echo"),
    ("kubectl", "docker.io/alpine/kubectl"),
    ("busybox", "docker.io/library/busybox"),
    ("redis", "docker.io/library/redis"),
    ("nats", "docker.io/library/nats"),
    ("natsBox", "docker.io/natsio/nats-box"),
    ("temporalServer", "docker.io/temporalio/server"),
    ("temporalAdminTools", "docker.io/temporalio/admin-tools"),
    ("temporalUi", "docker.io/temporalio/ui"),
    ("nautobotNginx", "docker.io/nginxinc/nginx-unprivileged"),
    ("spiffeHelper", "ghcr.io/spiffe/spiffe-helper"),
    ("oauth2Proxy", "quay.io/oauth2-proxy/oauth2-proxy"),
    ("templatePluginInstaller", "docker.io/library/python"),
    ("envoyGateway", "docker.io/envoyproxy/gateway"),
    ("envoyRatelimit", "docker.io/envoyproxy/ratelimit"),
    ("envoyProxy", "docker.io/envoyproxy/envoy"),
    ("certManagerController", "quay.io/jetstack/cert-manager-controller"),
    ("certManagerWebhook", "quay.io/jetstack/cert-manager-webhook"),
    ("certManagerCainjector", "quay.io/jetstack/cert-manager-cainjector"),
    ("certManagerStartupApiCheck", "quay.io/jetstack/cert-manager-startupapicheck"),
    ("certManagerAcmesolver", "quay.io/jetstack/cert-manager-acmesolver"),
    ("cnpgOperator", "ghcr.io/cloudnative-pg/cloudnative-pg"),
    ("postgresql", "ghcr.io/cloudnative-pg/postgresql"),
    ("pgbouncer", "ghcr.io/cloudnative-pg/pgbouncer"),
    ("prometheusServer", "quay.io/prometheus/prometheus"),
    ("prometheusConfigReloader", "quay.io/prometheus-operator/prometheus-config-reloader"),
    ("alloy", "docker.io/grafana/alloy"),
    ("alloyConfigReloader", "quay.io/prometheus-operator/prometheus-config-reloader"),
]


# ---------------------------------------------------------------------------
# Workflow RBAC
# ---------------------------------------------------------------------------

_RBAC_VALUES_REL = Path("deploy/helm/values-rbac-open.yaml")

_cached_workflows: list[str] | None = None


def get_known_workflows(project_root: Path | None = None) -> list[str]:
    """Read workflow names from ``deploy/helm/values-rbac-open.yaml``.

    The file is the enforced source of truth (a CI test ensures every
    registered workflow appears in it).  Parsing it at runtime avoids a
    hardcoded duplicate list that must be updated whenever a workflow is
    added.

    Results are cached after the first successful load.  If the file cannot
    be found, an empty list is returned so the installer still works in
    environments where the Helm chart directory is absent.
    """
    global _cached_workflows  # noqa: PLW0603
    if _cached_workflows is not None:
        return _cached_workflows

    rbac_file = _resolve_rbac_file(project_root)
    if rbac_file is None:
        return []

    with open(rbac_file) as f:
        data = yaml.safe_load(f) or {}

    workflows = [w["name"] for w in data.get("rbac", {}).get("workflows", []) if "name" in w]
    _cached_workflows = workflows
    return workflows


def _resolve_rbac_file(project_root: Path | None) -> Path | None:
    """Locate ``values-rbac-open.yaml`` relative to the project root."""
    if project_root:
        candidate = project_root / _RBAC_VALUES_REL
        if candidate.is_file():
            return candidate

    # Walk upward from CWD (same strategy as deployer.find_project_root)
    cur = Path.cwd().resolve()
    for _ in range(20):
        candidate = cur / _RBAC_VALUES_REL
        if candidate.is_file():
            return candidate
        parent = cur.parent
        if parent == cur:
            break
        cur = parent
    return None


class WorkflowRBACOverride(BaseModel):
    """Per-workflow RBAC role override.

    Workflows listed here use these roles instead of the defaults.
    """

    name: str
    read_roles: list[str] = Field(default_factory=list)
    execute_roles: list[str] = Field(default_factory=list)


class RBACConfig(BaseModel):
    """Temporal workflow RBAC configuration.

    Every workflow in ``get_known_workflows()`` gets ``default_read_roles`` and
    ``default_execute_roles`` unless explicitly overridden in
    ``workflow_overrides``.
    """

    admin_roles: list[str] = Field(default_factory=lambda: ["all"])
    default_read_roles: list[str] = Field(default_factory=lambda: ["all"])
    default_execute_roles: list[str] = Field(default_factory=lambda: ["all"])
    workflow_overrides: list[WorkflowRBACOverride] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Root model
# ---------------------------------------------------------------------------


class NVConfigManagerInstallConfig(BaseModel):
    """Root configuration model for nv-config-manager-install.yaml."""

    version: str = "1"
    cluster: ClusterConfig = Field(default_factory=ClusterConfig)
    secrets: SecretsConfig = Field(default_factory=SecretsConfig)
    network_secrets: list[NetworkSecretEntry] = Field(default_factory=list)
    git_tokens: list[GitTokenEntry] = Field(default_factory=list)
    sites: list[SiteConfig] = Field(default_factory=list)
    sso: SSOConfig = Field(default_factory=SSOConfig)
    spiffe: SPIFFEConfig = Field(default_factory=SPIFFEConfig)
    content: ContentConfig = Field(default_factory=ContentConfig)
    services: ServicesConfig = Field(default_factory=ServicesConfig)
    external_services: ExternalServicesConfig = Field(default_factory=ExternalServicesConfig)
    infrastructure: InfrastructureConfig = Field(default_factory=InfrastructureConfig)
    images: ImagesConfig = Field(default_factory=ImagesConfig)
    rbac: RBACConfig = Field(default_factory=RBACConfig)
    redfish: RedfishConfig = Field(default_factory=RedfishConfig)

    @model_validator(mode="after")
    def validate_external_nautobot(self) -> NVConfigManagerInstallConfig:
        """Custom jobs and bootstrap jobs require local Nautobot."""
        if not self.services.nautobot and (
            self.content.jobs or self.content.include_bootstrap_jobs
        ):
            msg = (
                "Custom jobs and bootstrap jobs require a local Nautobot deployment "
                "(services.nautobot must be true). Disable them or switch to local Nautobot."
            )
            raise ValueError(msg)
        return self

    # -- Serialization helpers -----------------------------------------------

    def to_yaml(self, path: Path | str) -> None:
        """Write config to a YAML file (owner-only permissions)."""
        path = Path(path)
        data = self._yaml_data()
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, path: Path | str) -> NVConfigManagerInstallConfig:
        """Load config from a YAML file."""
        with open(path) as f:
            data: dict[str, Any] = yaml.safe_load(f) or {}
        return cls.model_validate(data)

    def to_yaml_str(self) -> str:
        """Serialize config to a YAML string."""
        data = self._yaml_data()
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    def _yaml_data(self) -> dict[str, Any]:
        """Return serialized config with inactive TUI branches removed."""
        data = self.model_dump(mode="json")
        _prune_inactive_sections(data)
        return data


def _prune_inactive_sections(data: dict[str, Any]) -> None:
    """Remove values from conditional sections that are not currently active."""
    secrets = _as_dict(data.get("secrets"))
    _prune_secrets(secrets, data)
    _prune_git_tokens(data, secrets.get("method", SecretsMethod.KUBERNETES.value))
    _prune_sso(_as_dict(data.get("sso")))
    _prune_spiffe(_as_dict(data.get("spiffe")))
    _prune_services(_as_dict(data.get("services")))
    _prune_external_services(_as_dict(data.get("external_services")))
    _prune_infrastructure(_as_dict(data.get("infrastructure")))
    _prune_images(_as_dict(data.get("images")))
    _prune_redfish(_as_dict(data.get("redfish")))


def _as_dict(value: Any) -> dict[str, Any]:
    """Return *value* if it is a dict, otherwise an empty dict."""
    return value if isinstance(value, dict) else {}


def _replace_with_keys(section: dict[str, Any], keys: set[str]) -> None:
    """Drop every key from *section* except those explicitly listed."""
    for key in list(section):
        if key not in keys:
            section.pop(key, None)


def _prune_secrets(secrets: dict[str, Any], data: dict[str, Any]) -> None:
    method = secrets.get("method")
    if method == SecretsMethod.ESO.value:
        secrets.pop("k8s", None)
        _prune_vault(_as_dict(secrets.get("vault")))
        return

    secrets.pop("vault", None)
    for site in data.get("sites", []):
        if isinstance(site, dict):
            site.pop("vault_path", None)

    k8s = _as_dict(secrets.get("k8s"))
    for group in k8s.values():
        group_data = _as_dict(group)
        if group_data.get("enabled") is False:
            group_data.pop("values", None)


def _prune_vault(vault: dict[str, Any]) -> None:
    auth = _as_dict(vault.get("auth"))
    if auth.get("method") == VaultAuthMethod.TOKEN.value:
        vault.pop("mount_path", None)
        vault.pop("role", None)
    else:
        auth.pop("token_secret_name", None)

    paths = _as_dict(vault.get("paths"))
    for path_config in paths.values():
        path_data = _as_dict(path_config)
        if path_data.get("enabled") is False:
            _replace_with_keys(path_data, {"enabled"})


def _prune_git_tokens(data: dict[str, Any], secrets_method: Any) -> None:
    if secrets_method == SecretsMethod.ESO.value:
        return
    for token in data.get("git_tokens", []):
        if isinstance(token, dict):
            token.pop("vault_path", None)


def _prune_sso(sso: dict[str, Any]) -> None:
    if not sso.get("enabled"):
        _replace_with_keys(sso, {"enabled"})


def _prune_spiffe(spiffe: dict[str, Any]) -> None:
    if not spiffe.get("enabled"):
        _replace_with_keys(spiffe, {"enabled"})
        return
    if spiffe.get("provider") != SPIFFEProvider.TELEPORT.value:
        spiffe.pop("socket_host_path", None)


def _prune_services(services: dict[str, Any]) -> None:
    if services.get("nautobot", True):
        services.pop("external_nautobot_url", None)


def _prune_external_services(external_services: dict[str, Any]) -> None:
    redis = _as_dict(external_services.get("redis"))
    if not redis.get("enabled"):
        _replace_with_keys(redis, {"enabled"})

    postgres = _as_dict(external_services.get("postgres"))
    if not postgres.get("enabled"):
        _replace_with_keys(postgres, {"enabled"})


def _prune_infrastructure(infrastructure: dict[str, Any]) -> None:
    backup = _as_dict(infrastructure.get("cnpg_s3_backup"))
    if not backup.get("enabled"):
        _replace_with_keys(backup, {"enabled"})

    _prune_load_balancer(_as_dict(infrastructure.get("load_balancer")))
    _prune_ztp_storage(_as_dict(infrastructure.get("ztp_storage")))


def _prune_load_balancer(load_balancer: dict[str, Any]) -> None:
    provider = load_balancer.get("provider")
    static_keys = {
        "ztp_lb_ip",
        "dhcp_lb_ip",
        "ztp_dns_name",
        "dhcp_dns_name",
        "allowed_prefixes",
    }
    nlb_keys = {"nlb_gateway", "nlb_ztp", "nlb_dhcp"}

    if provider == LBProvider.NLB.value:
        for key in static_keys:
            load_balancer.pop(key, None)
    elif provider in {LBProvider.METALLB.value, LBProvider.CILIUM.value}:
        for key in nlb_keys:
            load_balancer.pop(key, None)
    else:
        for key in static_keys | nlb_keys:
            load_balancer.pop(key, None)


def _prune_ztp_storage(ztp_storage: dict[str, Any]) -> None:
    storage_type = ztp_storage.get("type")
    file_keys = {
        "pvc_name",
        "pvc_size",
        "storage_class",
        "access_mode",
        "node_selector",
        "os_images",
    }
    if storage_type == ZTPStorageType.S3.value:
        for key in file_keys:
            ztp_storage.pop(key, None)
    else:
        ztp_storage.pop("s3_bucket", None)


def _prune_images(images: dict[str, Any]) -> None:
    if images.get("source") != ImageSource.LOCAL.value:
        return
    _replace_with_keys(images, {"source"})


def _prune_redfish(redfish: dict[str, Any]) -> None:
    if not redfish.get("enabled"):
        _replace_with_keys(redfish, {"enabled"})
