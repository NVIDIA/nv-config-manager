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
"""Tests for nv_config_manager_installer.accounts -- config-secrets.ini, ESO paths, bootstrap scanner."""

from __future__ import annotations

from pathlib import Path

import yaml

from nv_config_manager_installer.accounts import (
    build_config_secrets_ini,
    build_eso_config_secrets,
    get_vault_sourced_keys,
    scan_bootstrap_secrets,
)
from nv_config_manager_installer.schema import (
    NetworkSecretEntry,
    NVConfigManagerInstallConfig,
    PasswordSource,
    SecretsConfig,
    SecretsMethod,
    SiteConfig,
)


def _make_config(**kwargs):
    defaults = {
        "network_secrets": [
            NetworkSecretEntry(name="BGP Password", secret_key="bgp_password"),
            NetworkSecretEntry(name="Root Password", secret_key="root_password"),
            NetworkSecretEntry(name="API User Key", secret_key="api_user_key"),
            NetworkSecretEntry(name="TACACS Key", secret_key="tacacs_key"),
        ],
        "sites": [SiteConfig(name="dc01")],
    }
    defaults.update(kwargs)
    return NVConfigManagerInstallConfig(**defaults)


class TestConfigSecretsIni:
    def test_build_ini(self):
        config = _make_config()
        secrets_state = {
            "root_password_r1": "genpass123",
            "bgp_password_r1": "bgppass456",
            "api_user_key_r1": "apipass789",
            "tacacs_key_r1": "tacacspass000",
            "hash_salt": "abc12345",
        }

        ini = build_config_secrets_ini(config, secrets_state)

        assert "[site.dc01]" in ini
        assert "root_password_r1 = genpass123" in ini
        assert "bgp_password_r1 = bgppass456" in ini
        assert "api_user_key_r1 = apipass789" in ini
        assert "hash_salt = abc12345" in ini

    def test_multiple_sites(self):
        config = _make_config(sites=[SiteConfig(name="dc01"), SiteConfig(name="dc02")])
        secrets_state = {"root_password_r1": "pass", "hash_salt": "salt"}

        ini = build_config_secrets_ini(config, secrets_state)

        assert "[site.dc01]" in ini
        assert "[site.dc02]" in ini

    def test_non_rotated_secret_key(self):
        config = _make_config(
            network_secrets=[
                NetworkSecretEntry(name="UFM API User", secret_key="ufm_api_user", rotation=""),
                NetworkSecretEntry(name="UFM API Token", secret_key="ufm_api_token"),
            ],
        )
        secrets_state = {
            "ufm_api_user": "admin",
            "ufm_api_token_r1": "token",
        }

        ini = build_config_secrets_ini(config, secrets_state)

        assert "ufm_api_user = admin" in ini
        assert "ufm_api_token_r1 = token" in ini
        assert "ufm_api_user_" not in ini

    def test_preserves_existing_generated_site_values(self):
        config = _make_config()
        existing = """
[site.dc01]
root_password_r1 = existing-root
hash_salt = existing-salt
"""
        secrets_state = {
            "root_password_r1": "new-root",
            "bgp_password_r1": "new-bgp",
            "hash_salt": "new-salt",
        }

        ini = build_config_secrets_ini(config, secrets_state, existing_content=existing)

        assert "root_password_r1 = existing-root" in ini
        assert "hash_salt = existing-salt" in ini
        assert "bgp_password_r1 = new-bgp" in ini

    def test_manual_values_replace_existing_site_values(self):
        config = _make_config(
            network_secrets=[
                NetworkSecretEntry(
                    name="Root Password",
                    secret_key="root_password",
                    source=PasswordSource.MANUAL,
                    value="manual-root",
                )
            ]
        )
        existing = """
[site.dc01]
root_password_r1 = existing-root
"""
        secrets_state = {"root_password_r1": "manual-root", "hash_salt": "salt"}

        ini = build_config_secrets_ini(config, secrets_state, existing_content=existing)

        assert "root_password_r1 = manual-root" in ini
        assert "existing-root" not in ini


class TestESOConfigSecrets:
    def test_eso_disabled_for_kubernetes_method(self):
        config = _make_config()
        result = build_eso_config_secrets(config)
        assert result["enabled"] is False

    def test_eso_enabled_with_vault_paths(self):
        config = _make_config(
            secrets=SecretsConfig(method=SecretsMethod.ESO),
            sites=[SiteConfig(name="dc01", vault_path="prod/site/dc01/config_secrets")],
        )
        result = build_eso_config_secrets(config)

        assert result["enabled"] is True
        assert len(result["sites"]) == 1
        assert result["sites"][0]["name"] == "dc01"
        assert result["sites"][0]["path"] == "prod/site/dc01/config_secrets"

    def test_eso_auto_derives_path_from_env(self):
        config = NVConfigManagerInstallConfig(
            secrets=SecretsConfig(method=SecretsMethod.ESO),
            sites=[SiteConfig(name="dc01")],
        )
        config.cluster.environment = "staging"
        result = build_eso_config_secrets(config)

        assert result["sites"][0]["path"] == "staging/site/dc01/config_secrets"


class TestHelpers:
    def test_get_vault_sourced_keys(self):
        config = _make_config(
            network_secrets=[
                NetworkSecretEntry(
                    name="Vault Secret",
                    secret_key="vault_key",
                    source=PasswordSource.VAULT,
                ),
                NetworkSecretEntry(
                    name="Generated Secret",
                    secret_key="gen_key",
                    source=PasswordSource.GENERATE,
                ),
            ],
        )
        keys = get_vault_sourced_keys(config)
        assert ("vault_key", "r1") in keys
        assert ("gen_key", "r1") not in keys


class TestBootstrapScanner:
    def test_scan_discovers_password_keys(self, tmp_path: Path):
        config_contexts = [
            {
                "name": "Cumulus Password Mappings",
                "data": {
                    "password_mappings": {
                        "cumulus": {"password": "root_password", "rotation": "r1"},
                        "nv-config-manager": {"password": "api_user_key", "rotation": "r1"},
                    }
                },
            },
        ]
        ctx_dir = tmp_path / "components" / "nautobot" / "nv_config_manager_jobs" / "data"
        ctx_dir.mkdir(parents=True)
        (ctx_dir / "config_contexts.yaml").write_text(
            yaml.dump(config_contexts, default_flow_style=False)
        )

        results = scan_bootstrap_secrets(tmp_path)

        keys = {r[1] for r in results}
        assert "root_password" in keys
        assert "api_user_key" in keys

    def test_scan_deduplicates(self, tmp_path: Path):
        config_contexts = [
            {
                "name": "Platform A",
                "data": {
                    "password_mappings": {
                        "admin": {"password": "root_password", "rotation": "r1"},
                    }
                },
            },
            {
                "name": "Platform B",
                "data": {
                    "password_mappings": {
                        "root": {"password": "root_password", "rotation": "r1"},
                    }
                },
            },
        ]
        ctx_dir = tmp_path / "components" / "nautobot" / "nv_config_manager_jobs" / "data"
        ctx_dir.mkdir(parents=True)
        (ctx_dir / "config_contexts.yaml").write_text(
            yaml.dump(config_contexts, default_flow_style=False)
        )

        results = scan_bootstrap_secrets(tmp_path)
        keys = [r[1] for r in results]
        assert keys.count("root_password") == 1

    def test_scan_returns_empty_for_missing_file(self, tmp_path: Path):
        results = scan_bootstrap_secrets(tmp_path)
        assert results == []

    def test_scan_handles_non_password_contexts(self, tmp_path: Path):
        config_contexts = [
            {
                "name": "Firmware Context",
                "data": {"intended-firmware": {"version": "5.14.0"}},
            },
        ]
        ctx_dir = tmp_path / "components" / "nautobot" / "nv_config_manager_jobs" / "data"
        ctx_dir.mkdir(parents=True)
        (ctx_dir / "config_contexts.yaml").write_text(
            yaml.dump(config_contexts, default_flow_style=False)
        )

        results = scan_bootstrap_secrets(tmp_path)
        assert results == []

    def test_scan_returns_rotation(self, tmp_path: Path):
        config_contexts = [
            {
                "name": "Test",
                "data": {
                    "password_mappings": {
                        "user": {"password": "my_key", "rotation": "r2"},
                    }
                },
            },
        ]
        ctx_dir = tmp_path / "components" / "nautobot" / "nv_config_manager_jobs" / "data"
        ctx_dir.mkdir(parents=True)
        (ctx_dir / "config_contexts.yaml").write_text(
            yaml.dump(config_contexts, default_flow_style=False)
        )

        results = scan_bootstrap_secrets(tmp_path)
        assert len(results) == 1
        assert results[0] == ("My Key", "my_key", "r2")
