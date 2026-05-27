# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0
"""Tests for conditional field visibility in TUI screens."""

from __future__ import annotations

import pytest
from textual.widgets import Input

from nv_config_manager_installer.schema import (
    NVConfigManagerInstallConfig,
    SecretsMethod,
    SiteConfig,
)
from nv_config_manager_installer.tui.app import NVConfigManagerInstallerApp


@pytest.mark.asyncio
async def test_vault_fields_hidden_when_kubernetes():
    """Vault fields should be hidden when secrets method is kubernetes."""
    config = NVConfigManagerInstallConfig()
    config.secrets.method = SecretsMethod.KUBERNETES
    app = NVConfigManagerInstallerApp(config=config)
    async with app.run_test():
        app.switch_section("secrets")
        vault_fields = app.query_one("#vault-fields")
        assert vault_fields.display is False


@pytest.mark.asyncio
async def test_vault_fields_shown_when_eso():
    """Vault fields should be visible when secrets method is ESO."""
    config = NVConfigManagerInstallConfig()
    config.secrets.method = SecretsMethod.ESO
    app = NVConfigManagerInstallerApp(config=config)
    async with app.run_test():
        app.switch_section("secrets")
        vault_fields = app.query_one("#vault-fields")
        assert vault_fields.display is True


@pytest.mark.asyncio
async def test_sso_fields_hidden_when_disabled():
    """SSO fields should be hidden when SSO is disabled."""
    config = NVConfigManagerInstallConfig()
    config.sso.enabled = False
    app = NVConfigManagerInstallerApp(config=config)
    async with app.run_test():
        app.switch_section("sso")
        sso_fields = app.query_one("#sso-fields")
        assert sso_fields.display is False


@pytest.mark.asyncio
async def test_sso_fields_shown_when_enabled():
    """SSO fields should be visible when SSO is enabled."""
    config = NVConfigManagerInstallConfig()
    config.sso.enabled = True
    app = NVConfigManagerInstallerApp(config=config)
    async with app.run_test():
        app.switch_section("sso")
        sso_fields = app.query_one("#sso-fields")
        assert sso_fields.display is True


@pytest.mark.asyncio
async def test_spiffe_fields_hidden_when_disabled():
    """SPIFFE fields should be hidden when SPIFFE is disabled."""
    config = NVConfigManagerInstallConfig()
    config.spiffe.enabled = False
    app = NVConfigManagerInstallerApp(config=config)
    async with app.run_test():
        app.switch_section("spiffe")
        spiffe_fields = app.query_one("#spiffe-fields")
        assert spiffe_fields.display is False


@pytest.mark.asyncio
async def test_cnpg_fields_hidden_when_backup_disabled():
    """CNPG backup fields should be hidden when backup is disabled."""
    config = NVConfigManagerInstallConfig()
    config.infrastructure.cnpg_s3_backup.enabled = False
    app = NVConfigManagerInstallerApp(config=config)
    async with app.run_test():
        app.switch_section("infrastructure")
        cnpg_fields = app.query_one("#cnpg-backup-fields")
        assert cnpg_fields.display is False


@pytest.mark.asyncio
async def test_deploy_section_exists():
    """Deploy section should exist in the nav."""
    config = NVConfigManagerInstallConfig()
    app = NVConfigManagerInstallerApp(config=config)
    async with app.run_test():
        assert "deploy" in app._nav_items
        assert "deploy" in app._screens


@pytest.mark.asyncio
async def test_site_vault_paths_shown_in_eso_mode():
    """Site vault path inputs should appear in App Secrets when ESO is active."""
    config = NVConfigManagerInstallConfig()
    config.secrets.method = SecretsMethod.ESO
    config.sites = [SiteConfig(name="dc01"), SiteConfig(name="dc02")]
    app = NVConfigManagerInstallerApp(config=config)
    async with app.run_test() as pilot:
        app.switch_section("secrets")
        await pilot.pause(0.1)
        secrets_screen = app._screens["secrets"]
        assert secrets_screen.query_one("#site-vault-0", Input) is not None
        assert secrets_screen.query_one("#site-vault-1", Input) is not None


@pytest.mark.asyncio
async def test_site_vault_paths_reflect_cluster_sites():
    """Navigating Cluster → App Secrets should populate vault path rows from config.sites."""
    config = NVConfigManagerInstallConfig()
    config.secrets.method = SecretsMethod.ESO
    config.sites = [SiteConfig(name="dc01", vault_path="prod/site/dc01/cfg")]
    app = NVConfigManagerInstallerApp(config=config)
    async with app.run_test() as pilot:
        app.switch_section("cluster")
        app.switch_section("secrets")
        await pilot.pause(0.1)
        secrets_screen = app._screens["secrets"]
        inp = secrets_screen.query_one("#site-vault-0", Input)
        assert inp.value == "prod/site/dc01/cfg"
