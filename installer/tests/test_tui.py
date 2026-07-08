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
"""Textual pilot tests for the TUI app."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from textual.widgets import Input, Select

from nv_config_manager_installer.deployer import DeploymentMode
from nv_config_manager_installer.schema import (
    ClusterConfig,
    NVConfigManagerInstallConfig,
    SecretsConfig,
    SecretsMethod,
    SiteConfig,
    VaultAuth,
    VaultAuthMethod,
    VaultConfig,
    ZTPOSImage,
)
from nv_config_manager_installer.tui.app import NVConfigManagerInstallerApp
from nv_config_manager_installer.tui.screens.cluster import ClusterScreen
from nv_config_manager_installer.tui.widgets import LabeledSwitch


@pytest.mark.asyncio
async def test_app_starts_with_default_config():
    """The app should start and show the cluster screen."""
    app = NVConfigManagerInstallerApp(config=NVConfigManagerInstallConfig())
    async with app.run_test():
        assert app.active_section == "cluster"
        assert app.title == "NVCM Install Wizard"


@pytest.mark.asyncio
async def test_switch_section():
    """Clicking a nav item should switch the visible section."""
    app = NVConfigManagerInstallerApp(config=NVConfigManagerInstallConfig())
    async with app.run_test():
        app.switch_section("sso")
        assert app.active_section == "sso"
        assert app._screens["sso"].display is True
        assert app._screens["cluster"].display is False


@pytest.mark.asyncio
async def test_collect_config():
    """collect_config should read values from screens into the config model."""
    config = NVConfigManagerInstallConfig()
    app = NVConfigManagerInstallerApp(config=config)
    async with app.run_test():
        app.collect_config()
        assert app.config.cluster.environment == "local"


@pytest.mark.asyncio
async def test_sites_list_in_cluster_section():
    """Sites list widget should be present in the cluster section."""
    config = NVConfigManagerInstallConfig(sites=[SiteConfig(name="dc01")])
    app = NVConfigManagerInstallerApp(config=config)
    async with app.run_test():
        app.switch_section("cluster")
        cluster_screen = app._screens["cluster"]
        assert isinstance(cluster_screen, ClusterScreen)
        sites_list = cluster_screen.query_one("#sites-list")
        assert sites_list is not None


@pytest.mark.asyncio
async def test_sites_collected_from_cluster():
    """Sites written via ClusterScreen.write_to_config should land in the config."""
    config = NVConfigManagerInstallConfig(sites=[SiteConfig(name="dc01"), SiteConfig(name="dc02")])
    app = NVConfigManagerInstallerApp(config=config)
    async with app.run_test():
        app.collect_config()
        assert len(app.config.sites) == 2
        assert app.config.sites[0].name == "dc01"
        assert app.config.sites[1].name == "dc02"


@pytest.mark.asyncio
async def test_airgapped_collected_from_cluster():
    """Airgapped setting should round-trip through the cluster screen."""
    config = NVConfigManagerInstallConfig(cluster=ClusterConfig(airgapped=True))
    app = NVConfigManagerInstallerApp(config=config)
    async with app.run_test():
        app.collect_config()
        assert app.config.cluster.airgapped is True


@pytest.mark.asyncio
async def test_deploy_screen_offers_argocd_mode():
    app = NVConfigManagerInstallerApp(config=NVConfigManagerInstallConfig())
    async with app.run_test():
        app.switch_section("deploy")
        deploy_screen = app._screens["deploy"]
        mode_switch = deploy_screen.query_one("#opt-argocd-managed", LabeledSwitch)

        mode_switch.value = True
        await app.workers.wait_for_complete()

        assert mode_switch.value is True
        options = deploy_screen._collect_deploy_options()
        assert options.mode == DeploymentMode.ARGOCD
        assert options.values_output.name == "values-generated.yaml"
        assert options.openbao_token_file is None


@pytest.mark.asyncio
async def test_ztp_screen_preserves_unknown_platform_from_config():
    config = NVConfigManagerInstallConfig()
    config.infrastructure.ztp_storage.os_images = [
        ZTPOSImage(platform="sonic", version="e2e-v1", path="/tmp/sonic.bin")
    ]
    app = NVConfigManagerInstallerApp(config=config)

    async with app.run_test():
        app.switch_section("ztp")
        platform = app._screens["ztp"].query_one("#ztp-img-0-platform", Select)

        assert platform.value == "sonic"
        app.collect_config()
        assert app.config.infrastructure.ztp_storage.os_images[0].platform == "sonic"


@pytest.mark.asyncio
async def test_app_secrets_eso_defaults_site_path_and_collects_manual_value():
    config = NVConfigManagerInstallConfig(
        secrets=SecretsConfig(
            method=SecretsMethod.ESO,
            vault=VaultConfig(
                server="https://openbao.example.com",
                secrets_path="nv-config-manager",
                auth=VaultAuth(method=VaultAuthMethod.TOKEN, token_secret_name=""),
            ),
        ),
        sites=[SiteConfig(name="dc01")],
    )
    app = NVConfigManagerInstallerApp(config=config)

    async with app.run_test():
        app.switch_section("secrets")
        secrets_screen = app._screens["secrets"]

        assert secrets_screen.get_status(config) == "[*]"
        assert secrets_screen.query_one("#k8s-secrets-section").display is False
        secrets_screen.query_one("#vp-key-redis-password", Input).value = "redis_password"
        secrets_screen.query_one("#vp-value-redis-password", Input).value = "manual-password"
        app.collect_config()

        assert app.config.sites[0].vault_path == ""
        assert app.config.secrets.vault.paths.redis.keys["password"] == "redis_password"
        assert app.config.secrets.k8s.redis.values["password"] == "manual-password"


@pytest.mark.asyncio
@patch("nv_config_manager_installer.tui.screens.vault.OpenBaoClient")
@patch("nv_config_manager_installer.tui.screens.vault.K8sClient")
async def test_app_secrets_marks_existing_vault_values_without_copying_them(
    mock_k8s_cls,
    mock_vault_cls,
):
    mock_k8s_cls.return_value.read_secret_data.return_value = {"token": "vault-token"}
    mock_vault_cls.return_value.read_secret.return_value = ({"password": "vault-secret"}, 1)
    config = NVConfigManagerInstallConfig(
        secrets=SecretsConfig(
            method=SecretsMethod.ESO,
            vault=VaultConfig(
                server="https://vault.example.com",
                secrets_path="nv-config-manager",
                auth=VaultAuth(
                    method=VaultAuthMethod.TOKEN,
                    token_secret_name="vault-token",
                ),
            ),
        ),
    )
    app = NVConfigManagerInstallerApp(config=config)

    async def run_inline(function):
        return function()

    with patch("nv_config_manager_installer.tui.screens.vault.asyncio.to_thread", new=run_inline):
        async with app.run_test():
            app.switch_section("secrets")
            await app.workers.wait_for_complete()
            secrets_screen = app._screens["secrets"]
            value_input = secrets_screen.query_one("#vp-value-redis-password", Input)

            assert value_input.password is True
            assert value_input.value
            assert value_input.value != "vault-secret"
            assert "Present in Vault" in str(
                secrets_screen.query_one("#vp-status-redis-password").render()
            )
            app.collect_config()
            assert "password" not in app.config.secrets.k8s.redis.values
