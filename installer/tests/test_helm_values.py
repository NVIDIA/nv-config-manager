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
"""Tests for nv_config_manager_installer.helm_values -- Helm values generation."""

from __future__ import annotations

import tempfile
from pathlib import Path

import yaml

from nv_config_manager_installer.helm_values import generate_helm_values
from nv_config_manager_installer.schema import (
    ClusterConfig,
    ContentConfig,
    ExternalServicesConfig,
    GitTokenEntry,
    ImageOverride,
    ImagePullSecret,
    ImagesConfig,
    ImageSource,
    InfrastructureConfig,
    JobPath,
    JobsConfig,
    JWTProvider,
    LBProvider,
    LoadBalancerConfig,
    MonitoringConfig,
    NVConfigManagerInstallConfig,
    RBACConfig,
    RedfishConfig,
    SecretsConfig,
    SecretsMethod,
    ServicesConfig,
    SiteConfig,
    SlackConfig,
    SSOConfig,
    SSOProvider,
    TemplatePath,
    TemplatePluginsConfig,
    VaultConfig,
    VaultPathConfig,
    VaultPathsConfig,
    WorkflowRBACOverride,
    ZTPStorageConfig,
    ZTPStorageType,
    get_known_workflows,
)


def _make_config(**kwargs):
    defaults = {
        "cluster": ClusterConfig(hostname="test.example.com", environment="prod"),
        "sites": [SiteConfig(name="dc01")],
    }
    defaults.update(kwargs)
    return NVConfigManagerInstallConfig(**defaults)


def _gen(
    config,
    *,
    local_images: bool = False,
    local_tags: dict[str, str] | None = None,
    complete: bool = False,
) -> dict[str, object]:
    """Generate values and return parsed YAML dict."""
    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        path = Path(f.name)
    try:
        generate_helm_values(
            config,
            {},
            path,
            local_images=local_images,
            local_tags=local_tags,
            complete=complete,
        )
        content = path.read_text()
        lines = content.split("\n")
        yaml_start = next(
            i for i, line in enumerate(lines) if not line.startswith("#") and line.strip()
        )
        return yaml.safe_load("\n".join(lines[yaml_start:]))
    finally:
        path.unlink(missing_ok=True)


class TestGenerateHelmValues:
    def test_basic_values(self):
        values = _gen(_make_config())

        assert values["global"]["baseDomain"] == "test.example.com"
        assert values["global"]["environment"] == "prod"
        assert values["secrets"]["method"] == "kubernetes"

        ext = values["externalServices"]
        assert ext["nautobot"]["local"] is True
        assert ext["nats"]["local"] is True
        assert ext["redis"]["local"] is True
        assert ext["redis"]["localHost"] == "redis-master"
        assert ext["postgres"]["temporal"]["host"] == "cluster-temporal-rw"
        assert ext["postgres"]["configStore"]["host"] == "cluster-config-store-rw"
        assert values["mcp"]["enabled"] is True

    def test_local_environment_uses_recreate_deployment_strategy(self):
        values = _gen(
            _make_config(cluster=ClusterConfig(hostname="local.test", environment="local"))
        )

        assert values["global"]["deploymentStrategy"] == {"type": "Recreate"}

    def test_key_names_match_chart(self):
        values = _gen(_make_config())

        assert "networkZtp" in values
        assert "networkDhcp" in values
        assert "oidc" in values
        assert "ztp" not in values
        assert "dhcp" not in values
        assert "sso" not in values

    def test_service_internal_endpoints(self):
        values = _gen(_make_config())

        assert values["renderService"]["client"]["useInternalEndpoint"] is True
        assert values["networkZtp"]["client"]["useInternalEndpoint"] is True
        assert values["temporal"]["client"]["useInternalEndpoint"] is True
        assert values["configStore"]["client"]["useInternalEndpoint"] is True

    def test_template_plugin_values_use_populated_pvc_and_updater_scheduling(self):
        config = _make_config(
            content=ContentConfig(
                template_plugins=[TemplatePath(path="/tmp/templates")],
                template_plugins_config=TemplatePluginsConfig(
                    node_selector={"nv-config-manager.nvidia.com/node-type": "worker"}
                ),
            )
        )

        values = _gen(config)

        assert values["renderService"]["templatePlugins"] == {
            "enabled": True,
            "pvcName": "render-service-template-plugins",
            "mountPath": "/opt/template-plugins",
            "images": [],
        }
        assert "template" not in values["renderService"]["consumers"]
        assert values["renderService"]["templateUpdater"]["nodeSelector"] == {
            "nv-config-manager.nvidia.com/node-type": "worker"
        }

    def test_ui_enabled(self):
        values = _gen(_make_config())
        assert values["ui"]["enabled"] is True

    def test_mock_auth_when_sso_disabled(self):
        values = _gen(_make_config())

        assert values["oidc"]["enabled"] is False
        assert values["localDev"]["mockAuth"]["enabled"] is True
        assert values["localDev"]["mockAuth"]["email"] == "dev@localhost"

    def test_no_mock_auth_when_sso_enabled(self):
        config = _make_config(
            sso=SSOConfig(
                enabled=True,
                provider=SSOProvider.KEYCLOAK,
                issuer_url="https://kc.test/realms/nv-config-manager",
                client_id="test-client",
            ),
        )
        values = _gen(config)

        assert values["oidc"]["enabled"] is True
        assert values["oidc"]["issuerUrl"] == "https://kc.test/realms/nv-config-manager"
        assert "localDev" not in values

    def test_gateway_jwt_follows_sso(self):
        values = _gen(_make_config())
        assert values["gateway"]["auth"]["jwt"]["enabled"] is False
        assert values["gateway"]["rateLimit"]["enabled"] is False

        config = _make_config(
            sso=SSOConfig(
                enabled=True,
                provider=SSOProvider.KEYCLOAK,
                issuer_url="https://kc.test/realms/nv-config-manager",
                client_id="test-client",
            ),
        )
        values = _gen(config)
        jwt = values["gateway"]["auth"]["jwt"]
        assert jwt["enabled"] is True
        assert "providers" in jwt
        assert jwt["providers"][0]["issuer"] == "https://kc.test/realms/nv-config-manager"
        assert jwt["providers"][0]["name"] == SSOProvider.KEYCLOAK.value

    def test_nautobot_full_section(self):
        values = _gen(_make_config())

        nb = values["nautobot"]
        assert nb["enabled"] is True
        assert nb["admin"]["username"] == "admin"
        assert nb["server"]["db"]["host"] == "cluster-nautobot-rw"
        assert nb["celery"]["enabled"] is True
        assert nb["nginx"]["enabled"] is True
        assert nb["initJob"]["enabled"] is True
        assert nb["persistence"]["staticFiles"]["enabled"] is True

    def test_nautobot_nats_section(self):
        values = _gen(_make_config())
        assert values["nautobotNats"]["enabled"] is True
        assert values["nautobotNats"]["jetstream"]["enabled"] is True
        assert values["nautobotNats"]["natsReady"]["useNatsCli"] is True

    def test_nautobot_disabled(self):
        config = _make_config(
            services=ServicesConfig(nautobot=False),
            content=ContentConfig(jobs=[], include_bootstrap_jobs=False),
        )
        values = _gen(config)

        assert values["nautobot"]["enabled"] is False
        assert "admin" not in values["nautobot"]
        assert values["nautobotNats"]["enabled"] is False
        assert "nats" not in values["externalServices"]

    def test_cnpg_per_database_clusters(self):
        values = _gen(_make_config())

        cnpg = values["cnpg"]
        assert cnpg["enabled"] is True
        assert cnpg["temporal"]["enabled"] is True
        assert cnpg["temporal"]["enablePDB"] is False
        assert cnpg["temporalVisibility"]["enabled"] is True
        assert cnpg["configStore"]["enabled"] is True
        assert cnpg["dhcp"]["enabled"] is True
        assert cnpg["nautobot"]["enabled"] is True

    def test_cnpg_follows_service_toggles(self):
        config = _make_config(
            services=ServicesConfig(temporal=False, config_store=False, dhcp=False),
        )
        values = _gen(config)

        assert values["cnpg"]["temporal"]["enabled"] is False
        assert values["cnpg"]["temporalVisibility"]["enabled"] is False
        assert values["cnpg"]["configStore"]["enabled"] is False
        assert values["cnpg"]["dhcp"]["enabled"] is False
        assert values["cnpg"]["nautobot"]["enabled"] is True

    def test_network_policy(self):
        values = _gen(_make_config())
        assert values["networkPolicy"]["enabled"] is True
        assert "gatewayNamespace" not in values["networkPolicy"]

    def test_config_secrets_kubernetes(self):
        values = _gen(_make_config())
        cs = values["secrets"]["vault"]["configSecrets"]
        assert cs["enabled"] is True
        assert cs["sites"] == [{"name": "dc01"}]

    def test_config_secrets_eso_under_vault(self):
        config = _make_config(
            secrets=SecretsConfig(
                method=SecretsMethod.ESO,
                vault=VaultConfig(server="https://vault.test", secrets_path="nv-config-manager"),
            ),
        )
        values = _gen(config)
        vault_cs = values["secrets"]["vault"]["configSecrets"]
        assert vault_cs["enabled"] is True
        assert vault_cs["sites"][0]["name"] == "dc01"
        assert "configSecrets" not in values

    def test_eso_all_path_groups_emitted(self):
        config = _make_config(
            secrets=SecretsConfig(
                method=SecretsMethod.ESO,
                vault=VaultConfig(server="https://vault.test", secrets_path="nv-config-manager"),
            ),
        )
        values = _gen(config)
        paths = values["secrets"]["vault"]["paths"]
        for group in (
            "nautobot",
            "redis",
            "postgres",
            "network",
            "nautobotApp",
            "oidc",
        ):
            assert group in paths, f"{group} missing"
            assert "path" in paths[group]
            assert "keys" in paths[group]

    def test_eso_custom_path(self):
        config = _make_config(
            secrets=SecretsConfig(
                method=SecretsMethod.ESO,
                vault=VaultConfig(
                    server="https://vault.test",
                    secrets_path="nv-config-manager",
                    paths=VaultPathsConfig(
                        nautobot=VaultPathConfig(path="custom/nb"),
                    ),
                ),
            ),
        )
        values = _gen(config)
        nb = values["secrets"]["vault"]["paths"]["nautobot"]
        assert nb["path"] == "custom/nb"
        assert nb["keys"]["token"] == "token"

    def test_local_images(self):
        values = _gen(_make_config(), local_images=True)

        images = values["global"]["images"]
        assert images["nvConfigManager"]["repository"] == "nv-config-manager"
        assert images["nvConfigManager"]["tag"] == "local"
        assert images["nvConfigManager"]["pullPolicy"] == "IfNotPresent"
        assert images["nautobot"]["repository"] == "nv-config-manager-nautobot"
        assert images["natsReady"]["repository"] == "nv-config-manager-nats-ready"

    def test_registry_images_present_by_default(self):
        values = _gen(_make_config())
        assert "images" in values["global"]
        assert (
            values["global"]["images"]["nvConfigManager"]["repository"]
            == "nvcr.io/nvidian/cfa/nv-config-manager"
        )

    def test_sso_enabled(self):
        config = _make_config(
            sso=SSOConfig(
                enabled=True,
                provider=SSOProvider.KEYCLOAK,
                issuer_url="https://kc.test/realms/nv-config-manager",
                client_id="test-client",
            ),
        )
        values = _gen(config)

        assert values["oidc"]["enabled"] is True
        assert values["oidc"]["issuerUrl"] == "https://kc.test/realms/nv-config-manager"
        assert values["oidc"]["cliClientId"] == "test-client"
        assert values["oidc"]["authUtility"]["enabled"] is True
        assert (
            values["oidc"]["jwksUri"]
            == "https://kc.test/realms/nv-config-manager/protocol/openid-connect/certs"
        )
        assert (
            values["oidc"]["endSessionEndpoint"]
            == "https://kc.test/realms/nv-config-manager/protocol/openid-connect/logout"
        )
        assert "auth" in values["gateway"]
        assert "authorizationEndpoint" not in values["oidc"]
        assert "tokenEndpoint" not in values["oidc"]
        # Keycloak default audiences include "account"
        assert "account" in values["oidc"]["audiences"]
        assert "test-client" in values["oidc"]["audiences"]

    def test_sso_cli_client_id_can_be_configured(self):
        config = _make_config(
            sso=SSOConfig(
                enabled=True,
                provider=SSOProvider.KEYCLOAK,
                issuer_url="https://kc.test/realms/nv-config-manager",
                client_id="test-client",
                cli_client_id="test-cli-client",
            ),
        )
        values = _gen(config)

        assert values["oidc"]["clientId"] == "test-client"
        assert values["oidc"]["cliClientId"] == "test-cli-client"

    def test_sso_azure_endpoints(self):
        tenant = "43083d15-7273-40c1-b7db-39efd9ccc17a"
        config = _make_config(
            sso=SSOConfig(
                enabled=True,
                provider=SSOProvider.AZURE,
                issuer_url=f"https://login.microsoftonline.com/{tenant}/v2.0",
                client_id="test-client",
                client_secret="secret",
            ),
        )
        values = _gen(config)

        base = f"https://login.microsoftonline.com/{tenant}"
        assert values["oidc"]["authorizationEndpoint"] == f"{base}/oauth2/v2.0/authorize"
        assert values["oidc"]["tokenEndpoint"] == f"{base}/oauth2/v2.0/token"
        assert values["oidc"]["endSessionEndpoint"] == f"{base}/oauth2/v2.0/logout"
        assert values["oidc"]["jwksUri"] == f"{base}/discovery/v2.0/keys"
        # Azure-specific scopes and audiences (needed for v2 access tokens)
        assert "api://test-client/access" in values["oidc"]["scopes"]
        assert "api://test-client" in values["oidc"]["audiences"]
        assert "test-client" in values["oidc"]["audiences"]
        # JWT section: primary provider should have Azure audiences
        jwt = values["gateway"]["auth"]["jwt"]
        primary = jwt["providers"][0]
        assert "api://test-client" in primary["audiences"]
        assert "test-client" in primary["audiences"]

    def test_sso_azure_no_trailing_slash(self):
        config = _make_config(
            sso=SSOConfig(
                enabled=True,
                provider=SSOProvider.AZURE,
                issuer_url="https://login.microsoftonline.com/my-tenant/v2.0/",
                client_id="c",
                client_secret="s",
            ),
        )
        values = _gen(config)
        assert values["oidc"]["authorizationEndpoint"].endswith("/oauth2/v2.0/authorize")
        assert "/v2.0//" not in values["oidc"]["authorizationEndpoint"]

    def test_sso_jwks_override_takes_precedence(self):
        config = _make_config(
            sso=SSOConfig(
                enabled=True,
                provider=SSOProvider.AZURE,
                issuer_url="https://login.microsoftonline.com/t/v2.0",
                client_id="c",
                client_secret="s",
                jwks_uri="https://custom.jwks/keys",
                end_session_endpoint="https://logout.example.com/end",
            ),
        )
        values = _gen(config)
        assert values["oidc"]["jwksUri"] == "https://custom.jwks/keys"
        assert values["oidc"]["endSessionEndpoint"] == "https://logout.example.com/end"

    def test_sso_scopes_and_internal_issuer(self):
        config = _make_config(
            sso=SSOConfig(
                enabled=True,
                provider=SSOProvider.KEYCLOAK,
                issuer_url="https://kc.test/realms/nv-config-manager",
                client_id="c",
                client_secret="s",
                scopes="openid,email,profile",
                internal_issuer="http://keycloak.svc:8080/realms/nv-config-manager",
            ),
        )
        values = _gen(config)
        assert values["oidc"]["scopes"] == ["openid", "email", "profile"]
        assert (
            values["oidc"]["internalIssuerUrl"]
            == "http://keycloak.svc:8080/realms/nv-config-manager"
        )

    def test_jwt_multi_provider(self):
        config = _make_config(
            sso=SSOConfig(
                enabled=True,
                provider=SSOProvider.KEYCLOAK,
                issuer_url="https://kc.test/realms/nv-config-manager",
                client_id="c",
                jwt_providers=[
                    JWTProvider(
                        name="spire",
                        issuer="https://spire.example.com",
                        audiences="spiffe://example.com",
                        jwks_uri="https://spire.example.com/jwks",
                    ),
                    JWTProvider(
                        name="starfleet",
                        issuer="https://starfleet.example.com",
                    ),
                ],
            ),
        )
        values = _gen(config)
        jwt = values["gateway"]["auth"]["jwt"]
        assert jwt["enabled"] is True
        providers = jwt["providers"]
        assert len(providers) == 3
        # Primary provider synthesized from SSO config
        assert providers[0]["name"] == "keycloak"
        assert providers[0]["issuer"] == "https://kc.test/realms/nv-config-manager"
        # Additional providers
        assert providers[1]["name"] == "spire"
        assert providers[1]["issuer"] == "https://spire.example.com"
        assert providers[1]["audiences"] == ["spiffe://example.com"]
        assert providers[1]["jwksUri"] == "https://spire.example.com/jwks"
        assert providers[2]["name"] == "starfleet"
        assert providers[2]["issuer"] == "https://starfleet.example.com"
        assert "audiences" not in providers[2]
        assert "jwksUri" not in providers[2]

    def test_slack_channel_in_external_services(self):
        config = _make_config(
            external_services=ExternalServicesConfig(
                slack=SlackConfig(channel="#nv-config-manager-alerts")
            ),
        )
        values = _gen(config)
        assert values["externalServices"]["slack"]["channel"] == "#nv-config-manager-alerts"

    def test_no_slack_key_when_channel_empty(self):
        values = _gen(_make_config())
        assert "slack" not in values["externalServices"]

    def test_services_disabled(self):
        config = _make_config(services=ServicesConfig(render=False, dhcp=False))
        values = _gen(config)

        assert values["renderService"]["enabled"] is False
        assert values["networkDhcp"]["enabled"] is False
        assert values["networkZtp"]["enabled"] is True
        assert values["mcp"]["enabled"] is False

    def test_nodeport_when_no_lb(self):
        config = _make_config(
            infrastructure=InfrastructureConfig(
                load_balancer=LoadBalancerConfig(provider=LBProvider.NONE),
            ),
        )
        values = _gen(config)
        assert values["gateway"]["nodePort"]["enabled"] is True

    def test_custom_jobs_in_values(self):
        config = _make_config(
            content=ContentConfig(
                jobs=[JobPath(path="/opt/jobs/custom")],
                include_bootstrap_jobs=True,
            ),
        )
        values = _gen(config)

        assert values["nautobot"]["customJobs"]["enabled"] is True
        assert values["nautobot"]["customJobs"]["createPvc"] is False
        assert values["nautobot"]["customJobs"]["pvcName"] == "nautobot-custom-jobs"

    def test_custom_jobs_node_selector_in_values(self):
        config = _make_config(
            content=ContentConfig(
                jobs=[JobPath(path="/opt/jobs/custom")],
                jobs_config=JobsConfig(
                    storage_class="local-path",
                    access_mode="ReadWriteOnce",
                    node_selector={"kubernetes.io/hostname": "worker-1"},
                ),
            ),
        )
        values = _gen(config)

        assert values["nautobot"]["customJobs"]["storageClass"] == "local-path"
        assert values["nautobot"]["customJobs"]["accessMode"] == "ReadWriteOnce"
        assert values["nautobot"]["customJobs"]["nodeSelector"] == {
            "kubernetes.io/hostname": "worker-1"
        }

    def test_combined_values_include_size_profile_without_base_values(self):
        config = _make_config(
            content=ContentConfig(
                template_plugins_config={
                    "node_selector": {"kubernetes.io/hostname": "worker-1"},
                },
            ),
        )
        values = _gen(config, complete=True)

        assert "busybox" not in values["global"]["images"]
        assert values["nautobot"]["server"]["resources"]["requests"]["memory"] == "2Gi"
        assert values["temporal"]["services"]["frontend"]["replicas"] == 1
        assert values["renderService"]["api"]["nodeSelector"] == {
            "kubernetes.io/hostname": "worker-1"
        }

    def test_external_nautobot(self):
        config = _make_config(
            services=ServicesConfig(
                nautobot=False,
                external_nautobot_url="https://nb.prod.example.com",
            ),
            content=ContentConfig(jobs=[], include_bootstrap_jobs=False),
        )
        values = _gen(config)

        ext = values["externalServices"]
        assert ext["nautobot"]["local"] is False
        assert ext["nautobot"]["server"] == "https://nb.prod.example.com"
        assert "nats" not in ext
        assert ext["redis"]["local"] is True
        assert ext["postgres"]["temporal"]["host"] == "cluster-temporal-rw"
        assert values["mcp"]["enabled"] is True


class TestImagesInHelmValues:
    def test_registry_prefix_applied(self):
        config = _make_config(
            images=ImagesConfig(
                source=ImageSource.REGISTRY,
                registry="registry.corp.com/team",
                tag="v2.0",
            )
        )
        values = _gen(config)
        images = values["global"]["images"]
        assert images["nvConfigManager"]["repository"] == "registry.corp.com/team/nv-config-manager"
        assert images["nvConfigManager"]["tag"] == "v2.0"
        assert (
            images["nautobot"]["repository"] == "registry.corp.com/team/nv-config-manager-nautobot"
        )
        assert images["nautobot"]["tag"] == "v2.0"

    def test_per_image_override_repository(self):
        config = _make_config(
            images=ImagesConfig(
                source=ImageSource.REGISTRY,
                registry="nvcr.io/nvidian/cfa",
                tag="v1.0",
                overrides={
                    "nautobot": ImageOverride(repository="my-reg/custom-nautobot"),
                },
            )
        )
        values = _gen(config)
        images = values["global"]["images"]
        assert images["nautobot"]["repository"] == "my-reg/custom-nautobot"
        assert images["nautobot"]["tag"] == "v1.0"
        assert images["nvConfigManager"]["repository"] == "nvcr.io/nvidian/cfa/nv-config-manager"

    def test_per_image_override_tag(self):
        config = _make_config(
            images=ImagesConfig(
                source=ImageSource.REGISTRY,
                registry="nvcr.io/nvidian/cfa",
                tag="v1.0",
                overrides={
                    "nvConfigManager": ImageOverride(tag="dev-branch"),
                },
            )
        )
        values = _gen(config)
        images = values["global"]["images"]
        assert images["nvConfigManager"]["tag"] == "dev-branch"
        assert images["nautobot"]["tag"] == "v1.0"

    def test_pull_secret_name_from_config(self):
        config = _make_config(
            images=ImagesConfig(
                pull_secret=ImagePullSecret(
                    name="my-custom-secret",
                    password="some-key",
                ),
            )
        )
        values = _gen(config)
        assert values["global"]["imagePullSecrets"] == ["my-custom-secret"]

    def test_pull_policy_from_config(self):
        config = _make_config(
            images=ImagesConfig(pull_policy="Always"),
        )
        values = _gen(config)
        assert values["global"]["imagePullPolicy"] == "Always"

    def test_local_source_uses_short_names(self):
        config = _make_config(
            images=ImagesConfig(source=ImageSource.LOCAL),
        )
        values = _gen(config)
        images = values["global"]["images"]
        assert images["nvConfigManager"]["repository"] == "nv-config-manager"
        assert images["nvConfigManager"]["tag"] == "local"
        assert images["nautobot"]["repository"] == "nv-config-manager-nautobot"
        assert values["global"]["imagePullSecrets"] == []

    def test_no_global_tag_omits_tag_key(self):
        config = _make_config(
            images=ImagesConfig(
                source=ImageSource.REGISTRY,
                registry="nvcr.io/nvidian/cfa",
                tag="",
            )
        )
        values = _gen(config)
        images = values["global"]["images"]
        assert "tag" not in images["nvConfigManager"]

    def test_local_content_addressed_tags(self):
        tags = {
            "nv-config-manager": "a1b2c3d4e5f6",
            "nv-config-manager-nautobot": "deadbeef0123",
            "nv-config-manager-ui": "111222333444",
        }
        config = _make_config(images=ImagesConfig(source=ImageSource.LOCAL))
        values = _gen(config, local_tags=tags)
        images = values["global"]["images"]

        assert images["nvConfigManager"]["tag"] == "a1b2c3d4e5f6"
        assert images["nautobot"]["tag"] == "deadbeef0123"
        assert images["nvConfigManagerUi"]["tag"] == "111222333444"
        # Images not in local_tags fall back to "local"
        assert images["kea"]["tag"] == "local"
        assert images["keaAdmin"]["tag"] == "local"

    def test_local_no_tags_falls_back(self):
        config = _make_config(images=ImagesConfig(source=ImageSource.LOCAL))
        values = _gen(config, local_tags=None)
        images = values["global"]["images"]
        assert images["nvConfigManager"]["tag"] == "local"
        assert images["nautobot"]["tag"] == "local"

    def test_airgapped_registry_maps_uploaded_source_paths(self):
        config = _make_config(
            cluster=ClusterConfig(
                hostname="test.example.com",
                environment="prod",
                airgapped=True,
            ),
            content=ContentConfig(template_plugins=[TemplatePath(path="/tmp/templates")]),
            infrastructure=InfrastructureConfig(
                monitoring=MonitoringConfig(observability_enabled=True),
            ),
            images=ImagesConfig(
                source=ImageSource.REGISTRY,
                registry="registry.example.com/nv-config-manager",
                tag="1.2.2-rc.23",
            ),
        )

        values = _gen(config)
        images = values["global"]["images"]

        assert (
            images["nvConfigManager"]["repository"]
            == "registry.example.com/nv-config-manager/nvidian/cfa/nv-config-manager"
        )
        assert images["nvConfigManager"]["tag"] == "1.2.2-rc.23"
        assert (
            images["redis"]["repository"] == "registry.example.com/nv-config-manager/library/redis"
        )
        assert (
            images["temporalServer"]["repository"]
            == "registry.example.com/nv-config-manager/temporalio/server"
        )
        assert (
            values["nautobot"]["nginx"]["image"]["repository"]
            == "nv-config-manager/nginxinc/nginx-unprivileged"
        )
        assert values["nautobot"]["nginx"]["image"]["registry"] == "registry.example.com"
        assert (
            values["spiffe"]["helper"]["image"]["repository"]
            == "registry.example.com/nv-config-manager/spiffe/spiffe-helper"
        )
        assert (
            values["oidc"]["oauth2Proxy"]["image"]["repository"]
            == "registry.example.com/nv-config-manager/oauth2-proxy/oauth2-proxy"
        )
        assert (
            values["renderService"]["templatePlugins"]["installerImage"]
            == "registry.example.com/nv-config-manager/library/python:3.13-alpine"
        )
        assert (
            values["gateway"]["envoyProxy"]["image"]
            == "registry.example.com/nv-config-manager/envoyproxy/envoy:distroless-v1.36.5"
        )
        assert (
            values["cnpg"]["imageName"]
            == "registry.example.com/nv-config-manager/cloudnative-pg/postgresql:18.0-system-trixie"
        )
        assert (
            values["prometheus"]["server"]["image"]["repository"]
            == "registry.example.com/nv-config-manager/prometheus/prometheus"
        )
        assert values["prometheus"]["enabled"] is True
        assert values["alloy"]["enabled"] is True
        assert values["alloy"]["image"]["registry"] == "registry.example.com"
        assert values["alloy"]["image"]["repository"] == "nv-config-manager/grafana/alloy"
        assert values["alloy"]["configReloader"]["image"]["registry"] == "registry.example.com"
        assert (
            values["alloy"]["configReloader"]["image"]["repository"]
            == "nv-config-manager/prometheus-operator/prometheus-config-reloader"
        )
        assert values["alloy"]["configReloader"]["image"]["tag"] == "v0.90.1"
        assert values.get("grafana", {}).get("enabled") is not True
        assert values.get("loki", {}).get("enabled") is not True


class TestGitTokensInHelmValues:
    def test_no_git_tokens_by_default(self):
        config = _make_config()
        values = _gen(config)
        git_tokens = values.get("secrets", {}).get("vault", {}).get("paths", {}).get("gitTokens")
        assert git_tokens is None

    def test_git_token_generates_entry(self):
        config = _make_config(
            git_tokens=[GitTokenEntry(name="prismo", token="tok123")],
        )
        values = _gen(config)
        git_tokens = values["secrets"]["vault"]["paths"]["gitTokens"]
        assert len(git_tokens) == 1
        assert git_tokens[0]["name"] == "prismo"
        assert git_tokens[0]["secretName"] == "git-token-prismo"
        assert git_tokens[0]["hasUsername"] is False

    def test_git_token_with_username(self):
        config = _make_config(
            git_tokens=[GitTokenEntry(name="prismo", token="tok", username="bot")],
        )
        values = _gen(config)
        git_tokens = values["secrets"]["vault"]["paths"]["gitTokens"]
        assert git_tokens[0]["hasUsername"] is True

    def test_git_token_with_vault_path(self):
        config = _make_config(
            git_tokens=[
                GitTokenEntry(name="prismo", token="tok", vault_path="nv-config-manager/prod/git")
            ],
        )
        values = _gen(config)
        gt = values["secrets"]["vault"]["paths"]["gitTokens"][0]
        assert gt["path"] == "nv-config-manager/prod/git"

    def test_multiple_git_tokens(self):
        config = _make_config(
            git_tokens=[
                GitTokenEntry(name="prismo", token="tok1"),
                GitTokenEntry(name="gitlab", token="tok2", username="ci-bot"),
            ],
        )
        values = _gen(config)
        git_tokens = values["secrets"]["vault"]["paths"]["gitTokens"]
        assert len(git_tokens) == 2
        assert git_tokens[0]["secretName"] == "git-token-prismo"
        assert git_tokens[1]["secretName"] == "git-token-gitlab"
        assert git_tokens[1]["hasUsername"] is True

    def test_empty_name_skipped(self):
        config = _make_config(
            git_tokens=[GitTokenEntry(name="", token="tok")],
        )
        values = _gen(config)
        git_tokens = values.get("secrets", {}).get("vault", {}).get("paths", {}).get("gitTokens")
        assert git_tokens is None


class TestZTPStorage:
    def test_default_file_storage(self):
        """Default ZTP storage is file-based (airgap-friendly)."""
        values = _gen(_make_config())
        storage = values["networkZtp"]["storage"]
        assert storage["type"] == "file"
        assert "file" in storage

    def test_file_storage(self):
        """File-based ZTP storage generates PVC fields."""
        config = _make_config(
            infrastructure=InfrastructureConfig(
                ztp_storage=ZTPStorageConfig(
                    type=ZTPStorageType.FILE,
                    pvc_name="my-ztp-images",
                    pvc_size="50Gi",
                    storage_class="fast-ssd",
                )
            )
        )
        values = _gen(config)
        storage = values["networkZtp"]["storage"]
        assert storage["type"] == "file"
        assert storage["file"]["pvcName"] == "my-ztp-images"
        assert storage["file"]["mountPath"] == "/mnt/images"
        assert storage["file"]["storageClass"] == "fast-ssd"
        assert storage["file"]["size"] == "50Gi"

    def test_file_storage_no_storage_class(self):
        """File storage without storage class omits the field."""
        config = _make_config(
            infrastructure=InfrastructureConfig(
                ztp_storage=ZTPStorageConfig(
                    type=ZTPStorageType.FILE,
                    pvc_name="ztp-os-images",
                    pvc_size="10Gi",
                )
            )
        )
        values = _gen(config)
        storage = values["networkZtp"]["storage"]
        assert storage["type"] == "file"
        assert "storageClass" not in storage["file"]

    def test_s3_storage_explicit(self):
        """Explicit S3 config does not include file section."""
        config = _make_config(
            infrastructure=InfrastructureConfig(
                ztp_storage=ZTPStorageConfig(type=ZTPStorageType.S3)
            )
        )
        values = _gen(config)
        storage = values["networkZtp"]["storage"]
        assert storage["type"] == "s3"
        assert "file" not in storage


class TestWorkflowRBAC:
    def test_default_rbac_all_workflows(self):
        """Default RBAC gives every workflow admin/read/execute = ['all']."""
        values = _gen(_make_config())
        known = get_known_workflows()

        rbac = values["rbac"]
        assert rbac["admin_roles"] == ["all"]
        assert len(rbac["workflows"]) == len(known)
        for wf in rbac["workflows"]:
            assert wf["read_roles"] == ["all"]
            assert wf["execute_roles"] == ["all"]

    def test_custom_default_roles(self):
        """Changing default roles propagates to all non-overridden workflows."""
        config = _make_config(
            rbac=RBACConfig(
                admin_roles=["nv-config-manager-admin"],
                default_read_roles=["viewer", "admin"],
                default_execute_roles=["admin"],
            ),
        )
        values = _gen(config)

        rbac = values["rbac"]
        assert rbac["admin_roles"] == ["nv-config-manager-admin"]
        for wf in rbac["workflows"]:
            assert wf["read_roles"] == ["viewer", "admin"]
            assert wf["execute_roles"] == ["admin"]

    def test_per_workflow_override(self):
        """Per-workflow overrides replace the defaults for that workflow only."""
        config = _make_config(
            rbac=RBACConfig(
                workflow_overrides=[
                    WorkflowRBACOverride(
                        name="DeployWorkflow",
                        read_roles=["ngc-gni"],
                        execute_roles=["ngc-gni", "nv-config-manager-admin"],
                    ),
                ],
            ),
        )
        values = _gen(config)

        rbac = values["rbac"]
        deploy_wf = next(w for w in rbac["workflows"] if w["name"] == "DeployWorkflow")
        assert deploy_wf["read_roles"] == ["ngc-gni"]
        assert deploy_wf["execute_roles"] == ["ngc-gni", "nv-config-manager-admin"]

        hello_wf = next(w for w in rbac["workflows"] if w["name"] == "HelloWorld")
        assert hello_wf["read_roles"] == ["all"]
        assert hello_wf["execute_roles"] == ["all"]

    def test_multiple_overrides(self):
        """Multiple overrides each apply independently."""
        config = _make_config(
            rbac=RBACConfig(
                default_read_roles=["viewer"],
                default_execute_roles=["ops"],
                workflow_overrides=[
                    WorkflowRBACOverride(
                        name="HelloWorld",
                        read_roles=["all"],
                        execute_roles=["all"],
                    ),
                    WorkflowRBACOverride(
                        name="DiagnosticsWorkflow",
                        read_roles=["sre"],
                        execute_roles=["sre"],
                    ),
                ],
            ),
        )
        values = _gen(config)

        rbac = values["rbac"]
        hello = next(w for w in rbac["workflows"] if w["name"] == "HelloWorld")
        assert hello["read_roles"] == ["all"]
        assert hello["execute_roles"] == ["all"]

        diag = next(w for w in rbac["workflows"] if w["name"] == "DiagnosticsWorkflow")
        assert diag["read_roles"] == ["sre"]
        assert diag["execute_roles"] == ["sre"]

        backup = next(w for w in rbac["workflows"] if w["name"] == "BackupWorkflow")
        assert backup["read_roles"] == ["viewer"]
        assert backup["execute_roles"] == ["ops"]

    def test_workflow_order_matches_known_workflows(self):
        """Generated workflow entries preserve the values-rbac-open.yaml order."""
        values = _gen(_make_config())
        names = [w["name"] for w in values["rbac"]["workflows"]]
        assert names == get_known_workflows()


class TestRedfishInHelmValues:
    def test_redfish_disabled_by_default(self):
        values = _gen(_make_config())
        assert values["temporal"]["redfish"]["enabled"] is False

    def test_redfish_enabled(self):
        config = _make_config(redfish=RedfishConfig(enabled=True))
        values = _gen(config)
        assert values["temporal"]["redfish"]["enabled"] is True

    def test_temporal_still_has_client(self):
        values = _gen(_make_config())
        assert values["temporal"]["client"]["useInternalEndpoint"] is True
