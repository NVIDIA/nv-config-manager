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

from typing import Any

import pytest
from click.testing import CliRunner

from nv_config_manager.common.oidc import AuthDiscovery
from nv_config_manager.mcp import cli as mcp_cli


class FakeOIDCAuth:
    auth_discovered: list[tuple[str, bool]] = []
    discovered: list[tuple[str, bool]] = []
    created: list[tuple[str, str, bool]] = []
    token_requests: list[bool] = []
    auth_discovery_result: AuthDiscovery | None = AuthDiscovery(
        auth_required=True,
        issuer_url="https://issuer.example.com",
        client_id="cli-client-id",
        scopes=("openid", "profile", "email"),
    )
    discovery_result: tuple[str, str] | None = ("https://issuer.example.com", "client-id")

    def __init__(
        self,
        issuer_url: str,
        client_id: str,
        scopes: list[str] | None = None,
        verify: bool = True,
    ) -> None:
        self.issuer_url = issuer_url
        self.client_id = client_id
        self.scopes = scopes
        self.verify = verify
        self.created.append((issuer_url, client_id, verify))

    @classmethod
    def discover_auth_config(
        cls,
        discovery_url: str,
        verify: bool = True,
    ) -> AuthDiscovery | None:
        cls.auth_discovered.append((discovery_url, verify))
        return cls.auth_discovery_result

    @classmethod
    def discover_oidc_config(cls, gateway_url: str, verify: bool = True) -> tuple[str, str] | None:
        cls.discovered.append((gateway_url, verify))
        return cls.discovery_result

    def get_access_token(self, force_refresh: bool = False) -> str:
        self.token_requests.append(force_refresh)
        return "access-token"


class FakeResponse:
    status_code = 200

    def raise_for_status(self) -> None:
        return None


@pytest.fixture(autouse=True)
def reset_fake_oidc(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeOIDCAuth.auth_discovered = []
    FakeOIDCAuth.discovered = []
    FakeOIDCAuth.created = []
    FakeOIDCAuth.token_requests = []
    FakeOIDCAuth.auth_discovery_result = AuthDiscovery(
        auth_required=True,
        issuer_url="https://issuer.example.com",
        client_id="cli-client-id",
        scopes=("openid", "profile", "email"),
    )
    FakeOIDCAuth.discovery_result = ("https://issuer.example.com", "client-id")
    monkeypatch.setattr(mcp_cli, "OIDCAuth", FakeOIDCAuth)


def test_endpoint_defaults_to_service_mcp_hostname() -> None:
    runner = CliRunner()

    result = runner.invoke(mcp_cli.main, ["endpoint", "-H", "config-manager.example.com"])

    assert result.exit_code == 0
    assert result.output == "https://svc-mcp.config-manager.example.com/mcp\n"


def test_endpoint_prefers_discovered_mcp_service_url() -> None:
    FakeOIDCAuth.auth_discovery_result = AuthDiscovery(
        auth_required=True,
        issuer_url="https://issuer.example.com",
        client_id="cli-client-id",
        services={"mcp": "https://custom-svc.example.com/mcp/"},
    )
    runner = CliRunner()

    result = runner.invoke(mcp_cli.main, ["endpoint", "-H", "config-manager.example.com"])

    assert result.exit_code == 0
    assert result.output == "https://custom-svc.example.com/mcp\n"


def test_discovery_defaults_to_oidc_mcp_hostname() -> None:
    runner = CliRunner()

    result = runner.invoke(mcp_cli.main, ["token", "-H", "config-manager.example.com"])

    assert result.exit_code == 0
    assert result.output == "access-token\n"
    assert FakeOIDCAuth.auth_discovered == [
        ("https://config-manager.example.com/auth/discovery", True)
    ]
    assert FakeOIDCAuth.discovered == []
    assert FakeOIDCAuth.created == [("https://issuer.example.com", "cli-client-id", True)]


def test_mcp_url_can_drive_endpoint_and_discovery() -> None:
    runner = CliRunner()

    result = runner.invoke(
        mcp_cli.main,
        ["token", "--mcp-url", "https://svc-mcp.custom.example.com/mcp/"],
    )

    assert result.exit_code == 0
    assert FakeOIDCAuth.auth_discovered == [("https://custom.example.com/auth/discovery", True)]
    assert FakeOIDCAuth.discovered == []
    assert result.output == "access-token\n"


def test_legacy_redirect_discovery_is_used_when_auth_discovery_is_unavailable() -> None:
    FakeOIDCAuth.auth_discovery_result = None
    runner = CliRunner()

    result = runner.invoke(mcp_cli.main, ["token", "-H", "config-manager.example.com"])

    assert result.exit_code == 0
    assert FakeOIDCAuth.auth_discovered == [
        ("https://config-manager.example.com/auth/discovery", True)
    ]
    assert FakeOIDCAuth.discovered == [("https://mcp.config-manager.example.com/mcp", True)]
    assert FakeOIDCAuth.created == [("https://issuer.example.com", "client-id", True)]


def test_explicit_issuer_and_client_id_skip_discovery() -> None:
    runner = CliRunner()

    result = runner.invoke(
        mcp_cli.main,
        [
            "token",
            "-H",
            "config-manager.example.com",
            "--issuer",
            "https://issuer.local",
            "--client-id",
            "client-local",
        ],
    )

    assert result.exit_code == 0
    assert FakeOIDCAuth.auth_discovered == []
    assert FakeOIDCAuth.discovered == []
    assert FakeOIDCAuth.created == [("https://issuer.local", "client-local", True)]


def test_client_id_can_override_discovered_gateway_client_id() -> None:
    runner = CliRunner()

    result = runner.invoke(
        mcp_cli.main,
        ["token", "-H", "config-manager.example.com", "--client-id", "nv-config-manager-cli"],
    )

    assert result.exit_code == 0
    assert FakeOIDCAuth.auth_discovered == [
        ("https://config-manager.example.com/auth/discovery", True)
    ]
    assert FakeOIDCAuth.discovered == []
    assert FakeOIDCAuth.created == [("https://issuer.example.com", "nv-config-manager-cli", True)]


def test_sso_mode_token_discovers_oidc_for_service_mcp_url() -> None:
    runner = CliRunner()

    result = runner.invoke(
        mcp_cli.main,
        [
            "token",
            "--auth-mode",
            "sso",
            "--mcp-url",
            "https://svc-mcp.custom.example.com/mcp",
        ],
    )

    assert result.exit_code == 0
    assert FakeOIDCAuth.auth_discovered == [("https://custom.example.com/auth/discovery", True)]
    assert FakeOIDCAuth.discovered == []
    assert FakeOIDCAuth.created == [("https://issuer.example.com", "cli-client-id", True)]


def test_auto_endpoint_uses_mcp_hostname_when_sso_is_not_enabled() -> None:
    FakeOIDCAuth.auth_discovery_result = AuthDiscovery(auth_required=False)
    runner = CliRunner()

    result = runner.invoke(mcp_cli.main, ["endpoint", "-H", "config-manager.example.com"])

    assert result.exit_code == 0
    assert result.output == "https://mcp.config-manager.example.com/mcp\n"


def test_login_noops_when_sso_is_not_enabled() -> None:
    FakeOIDCAuth.auth_discovery_result = AuthDiscovery(auth_required=False)
    runner = CliRunner()

    result = runner.invoke(mcp_cli.main, ["login", "-H", "config-manager.example.com"])

    assert result.exit_code == 0
    assert "no login is required" in result.output
    assert FakeOIDCAuth.created == []


def test_token_prints_no_secret_when_sso_is_not_enabled() -> None:
    FakeOIDCAuth.auth_discovery_result = AuthDiscovery(auth_required=False)
    runner = CliRunner()

    result = runner.invoke(mcp_cli.main, ["token", "-H", "config-manager.example.com"])

    assert result.exit_code == 0
    assert (
        result.output == "SSO is not enabled for this MCP endpoint; no bearer token is required.\n"
    )
    assert FakeOIDCAuth.created == []


def test_token_force_refresh_passes_through() -> None:
    runner = CliRunner()

    result = runner.invoke(
        mcp_cli.main,
        ["token", "-H", "config-manager.example.com", "--force-auth-refresh"],
    )

    assert result.exit_code == 0
    assert FakeOIDCAuth.token_requests == [True]


def test_insecure_flag_applies_to_oidc_auth() -> None:
    runner = CliRunner()

    result = runner.invoke(mcp_cli.main, ["token", "-H", "config-manager.example.com", "-k"])

    assert result.exit_code == 0
    assert FakeOIDCAuth.auth_discovered == [
        ("https://config-manager.example.com/auth/discovery", False)
    ]
    assert FakeOIDCAuth.discovered == []
    assert FakeOIDCAuth.created == [("https://issuer.example.com", "cli-client-id", False)]


def test_config_output_is_generic() -> None:
    runner = CliRunner()

    result = runner.invoke(
        mcp_cli.main,
        ["config", "-H", "config-manager.example.com", "--token-env-var", "TOKEN_ENV"],
    )

    assert result.exit_code == 0
    assert "MCP transport: Streamable HTTP" in result.output
    assert "MCP endpoint: https://svc-mcp.config-manager.example.com/mcp" in result.output
    assert "Authorization: Bearer ${TOKEN_ENV}" in result.output
    assert (
        "nvcm-mcp-cli token --auth-mode sso "
        "--mcp-url https://svc-mcp.config-manager.example.com/mcp"
    ) in result.output
    assert "agent" not in result.output.lower()
    assert "model" not in result.output.lower()


def test_config_output_omits_auth_when_sso_is_not_enabled() -> None:
    FakeOIDCAuth.auth_discovery_result = AuthDiscovery(auth_required=False)
    runner = CliRunner()

    result = runner.invoke(mcp_cli.main, ["config", "-H", "config-manager.example.com"])

    assert result.exit_code == 0
    assert "MCP endpoint: https://mcp.config-manager.example.com/mcp" in result.output
    assert "Authentication: none" in result.output
    assert "No Authorization header is required." in result.output
    assert "Bearer" not in result.output


def test_check_validates_token_and_healthcheck(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, Any]] = []

    def fake_get(
        url: str,
        headers: dict[str, str],
        timeout: int,
        allow_redirects: bool,
        verify: bool,
    ) -> FakeResponse:
        calls.append(
            {
                "url": url,
                "headers": headers,
                "timeout": timeout,
                "allow_redirects": allow_redirects,
                "verify": verify,
            }
        )
        return FakeResponse()

    monkeypatch.setattr(mcp_cli.requests, "get", fake_get)
    runner = CliRunner()

    result = runner.invoke(mcp_cli.main, ["check", "-H", "config-manager.example.com"])

    assert result.exit_code == 0
    assert calls == [
        {
            "url": "https://svc-mcp.config-manager.example.com/healthcheck",
            "headers": {"Authorization": "Bearer access-token"},
            "timeout": 10,
            "allow_redirects": False,
            "verify": True,
        }
    ]
    assert "Healthcheck passed" in result.output
