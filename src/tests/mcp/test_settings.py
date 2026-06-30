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
from __future__ import annotations

from configparser import ConfigParser

import pytest

from nv_config_manager.mcp.settings import MCPOAuthSettings, MCPSettings


def _config(nautobot_server: str, auth_mode: str = "auto") -> ConfigParser:
    config = ConfigParser()
    config["mcp"] = {
        "use_internal_endpoints": "true",
        "nautobot_auth_mode": auth_mode,
        "nautobot_read_only_token": "read-only-token",
    }
    config["temporal"] = {
        "api_service": "http://workflow:9000",
        "api_url": "https://workflow.example.test",
        "ui_url": "https://config-manager.example.test",
    }
    config["config_store.client"] = {
        "api_service": "http://config-store:9000",
        "api_url": "https://config-store.example.test",
    }
    config["dhcp"] = {
        "api_service": "http://dhcp:9000",
        "api_url": "https://dhcp.example.test",
    }
    config["nautobot"] = {
        "server": nautobot_server,
        "token": "rw-token",
        "verify": "true",
    }
    return config


def test_nautobot_auth_auto_uses_jwt_for_local_nautobot() -> None:
    settings = MCPSettings.from_config(_config("http://nv-config-manager-nautobot"))

    assert settings.nautobot_auth_mode == "jwt"
    assert settings.workflow_ui_url == "https://config-manager.example.test"


def test_nautobot_auth_auto_uses_token_for_external_nautobot() -> None:
    settings = MCPSettings.from_config(_config("https://nautobot.example.test"))

    assert settings.nautobot_auth_mode == "token"
    assert settings.nautobot_read_only_token == "read-only-token"


def test_nautobot_read_only_token_does_not_fallback_to_rw_token() -> None:
    config = _config("https://nautobot.example.test")
    del config["mcp"]["nautobot_read_only_token"]

    settings = MCPSettings.from_config(config)

    assert settings.nautobot_auth_mode == "token"
    assert settings.nautobot_read_only_token == ""


def test_nautobot_auth_explicit_override() -> None:
    settings = MCPSettings.from_config(_config("https://nautobot.example.test", auth_mode="jwt"))

    assert settings.nautobot_auth_mode == "jwt"


def test_workflow_ui_url_falls_back_to_base_hostname() -> None:
    config = _config("http://nv-config-manager-nautobot")
    del config["temporal"]["ui_url"]

    settings = MCPSettings.from_config(config)

    assert settings.workflow_ui_url == "https://example.test"


def test_mcp_oauth_settings_disabled_without_section() -> None:
    settings = MCPOAuthSettings.from_config(ConfigParser())

    assert settings.enabled is False


def test_mcp_oauth_settings_direct_construction_defaults_resource_identifier() -> None:
    settings = MCPOAuthSettings(
        enabled=True,
        resource_url="https://svc-mcp.example.test/mcp",
    )

    assert settings.resource_identifier == "https://svc-mcp.example.test/mcp"


def test_mcp_oauth_settings_parse_metadata_config() -> None:
    settings = MCPOAuthSettings.from_config(_oauth_config())

    assert settings.enabled is True
    assert settings.resource_url == "https://svc-mcp.example.test/mcp"
    assert settings.resource_identifier == "https://svc-mcp.example.test/mcp"
    assert settings.issuer_url == "https://idp.example.test/realms/nvcm"
    assert settings.client_id == "nvcm-cli"
    assert settings.scopes == ("openid", "email", "profile")
    assert (
        settings.resource_metadata_url
        == "https://svc-mcp.example.test/.well-known/oauth-protected-resource/mcp"
    )
    assert settings.authorization_server_url == "https://svc-mcp.example.test"
    assert settings.well_known_paths == {
        "/.well-known/oauth-protected-resource",
        "/.well-known/oauth-protected-resource/mcp",
        "/.well-known/oauth-authorization-server",
    }


def test_mcp_oauth_settings_accepts_distinct_resource_identifier() -> None:
    config = _oauth_config()
    config["mcp.oauth"]["resource_identifier"] = "api://client-id/"

    settings = MCPOAuthSettings.from_config(config)

    assert settings.resource_url == "https://svc-mcp.example.test/mcp"
    assert settings.resource_identifier == "api://client-id"
    assert (
        settings.resource_metadata_url
        == "https://svc-mcp.example.test/.well-known/oauth-protected-resource/mcp"
    )


def test_mcp_oauth_well_known_paths_follow_resource_url_path() -> None:
    config = _oauth_config()
    config["mcp.oauth"]["resource_url"] = "https://svc-mcp.example.test/custom/mcp/"

    settings = MCPOAuthSettings.from_config(config)

    assert (
        settings.resource_metadata_url
        == "https://svc-mcp.example.test/.well-known/oauth-protected-resource/custom/mcp"
    )
    assert settings.well_known_paths == {
        "/.well-known/oauth-protected-resource",
        "/.well-known/oauth-protected-resource/custom/mcp",
        "/.well-known/oauth-authorization-server",
    }


def test_mcp_oauth_settings_requires_valid_urls_when_enabled() -> None:
    config = _oauth_config()
    config["mcp.oauth"]["resource_url"] = "svc-mcp.example.test/mcp"

    with pytest.raises(ValueError, match="resource_url"):
        MCPOAuthSettings.from_config(config)


def _oauth_config() -> ConfigParser:
    config = ConfigParser()
    config["mcp.oauth"] = {
        "enabled": "true",
        "resource_url": "https://svc-mcp.example.test/mcp/",
        "issuer_url": "https://idp.example.test/realms/nvcm/",
        "client_id": "nvcm-cli",
        "scopes": "openid,email profile",
        "authorization_endpoint": "https://idp.example.test/realms/nvcm/auth",
        "token_endpoint": "https://idp.example.test/realms/nvcm/token",
        "jwks_uri": "https://idp.example.test/realms/nvcm/certs/",
    }
    return config
