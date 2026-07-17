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

from unittest.mock import Mock

import pytest

from nv_config_manager_installer.deployer import DeployOptions
from nv_config_manager_installer.schema import (
    ClusterConfig,
    ImageSource,
    NVConfigManagerInstallConfig,
    SiteConfig,
)
from nv_config_manager_installer.tui.app import NVConfigManagerInstallerApp
from nv_config_manager_installer.tui.screens.cluster import ClusterScreen
from nv_config_manager_installer.tui.screens.deploy import DeployScreen


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


@pytest.mark.parametrize(
    "options",
    [DeployOptions(build_images=True), DeployOptions(load_kind=True)],
)
@pytest.mark.asyncio
async def test_deployment_start_selects_local_image_source(
    monkeypatch: pytest.MonkeyPatch, options: DeployOptions
):
    """Deployment must use local images when building or loading them."""
    config = NVConfigManagerInstallConfig()
    app = NVConfigManagerInstallerApp(config=config)
    deployer = Mock()
    deployer.return_value.steps = []
    monkeypatch.setattr("nv_config_manager_installer.tui.screens.deploy.Deployer", deployer)
    monkeypatch.setattr(DeployScreen, "_collect_deploy_options", lambda self: options)
    monkeypatch.setattr(DeployScreen, "_run_deploy", lambda self: None)

    async with app.run_test():
        screen = app._screens["deploy"]
        assert isinstance(screen, DeployScreen)
        screen._start_deploy()

    deployed_config, deployed_options, _ = deployer.call_args.args

    assert deployed_config.images.source == ImageSource.LOCAL
    assert deployed_options is options
