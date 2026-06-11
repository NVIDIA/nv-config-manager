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

from pathlib import Path
from typing import Any

import pytest
import requests

from nv_config_manager.common.oidc import AuthDiscovery, OIDCAuth


class MetadataResponse:
    status_code = 200
    headers: dict[str, str] = {}

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, Any]:
        return self.payload


class RedirectResponse:
    status_code = 302

    def __init__(self, location: str) -> None:
        self.headers = {"Location": location}


class StatusResponse:
    headers: dict[str, str] = {}

    def __init__(self, status_code: int, payload: dict[str, Any] | None = None) -> None:
        self.status_code = status_code
        self.payload = payload or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            response = requests.Response()
            response.status_code = self.status_code
            raise requests.exceptions.HTTPError(response=response)

    def json(self) -> dict[str, Any]:
        return self.payload


def test_provider_metadata_wins_for_endpoint_resolution(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []

    def fake_get(url: str, timeout: int, verify: bool | str) -> MetadataResponse:
        calls.append({"url": url, "timeout": timeout, "verify": verify})
        return MetadataResponse(
            {
                "authorization_endpoint": "https://idp.example.com/oauth2/auth",
                "token_endpoint": "https://idp.example.com/oauth2/token",
            }
        )

    monkeypatch.setattr(requests, "get", fake_get)

    auth = OIDCAuth(
        issuer_url="https://idp.example.com/issuer",
        client_id="client-id",
        token_file=tmp_path / "token.json",
        verify="/ca.pem",
    )

    assert auth._get_auth_endpoint() == "https://idp.example.com/oauth2/auth"
    assert auth._get_token_endpoint() == "https://idp.example.com/oauth2/token"
    assert calls == [
        {
            "url": "https://idp.example.com/issuer/.well-known/openid-configuration",
            "timeout": 10,
            "verify": "/ca.pem",
        }
    ]


def test_auth_discovery_parses_public_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(
        url: str,
        allow_redirects: bool,
        timeout: int,
        verify: bool | str,
    ) -> StatusResponse:
        assert url == "https://config-manager.local/auth/discovery"
        assert allow_redirects is False
        assert timeout == 10
        assert verify is False
        return StatusResponse(
            200,
            {
                "version": 1,
                "authRequired": True,
                "issuerUrl": "https://idp.example.com/realms/nvcm/",
                "clientId": "nv-config-manager-cli",
                "scopes": ["openid", "profile", "email"],
                "services": {
                    "mcp": "https://svc-mcp.config-manager.local/mcp/",
                    "workflow": "https://svc-workflow.config-manager.local/v1/workflow/",
                    "bad": "",
                },
            },
        )

    monkeypatch.setattr(requests, "get", fake_get)

    assert OIDCAuth.discover_auth_config(
        "https://config-manager.local/auth/discovery",
        verify=False,
    ) == AuthDiscovery(
        auth_required=True,
        issuer_url="https://idp.example.com/realms/nvcm",
        client_id="nv-config-manager-cli",
        scopes=("openid", "profile", "email"),
        services={
            "mcp": "https://svc-mcp.config-manager.local/mcp",
            "workflow": "https://svc-workflow.config-manager.local/v1/workflow",
        },
    )


def test_auth_discovery_returns_none_when_endpoint_is_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get(
        url: str,
        allow_redirects: bool,
        timeout: int,
        verify: bool | str,
    ) -> StatusResponse:
        return StatusResponse(404)

    monkeypatch.setattr(requests, "get", fake_get)

    assert OIDCAuth.discover_auth_config("https://config-manager.local/auth/discovery") is None


def test_auth_discovery_requires_oidc_metadata_when_auth_is_required(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get(
        url: str,
        allow_redirects: bool,
        timeout: int,
        verify: bool | str,
    ) -> StatusResponse:
        return StatusResponse(200, {"authRequired": True, "issuerUrl": "https://issuer"})

    monkeypatch.setattr(requests, "get", fake_get)

    with pytest.raises(RuntimeError, match="clientId"):
        OIDCAuth.discover_auth_config("https://config-manager.local/auth/discovery")


def test_redirect_discovery_matches_keycloak_style_metadata_without_hostname(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redirect_url = (
        "https://identity.example.test/realms/nv-config-manager/protocol/openid-connect/auth"
        "?client_id=nv-config-manager&response_type=code"
    )
    metadata_url = (
        "https://identity.example.test/realms/nv-config-manager/.well-known/openid-configuration"
    )

    def fake_get(
        url: str,
        allow_redirects: bool | None = None,
        timeout: int = 10,
        verify: bool | str = True,
    ) -> object:
        if url == "https://mcp.config-manager.local/mcp":
            return RedirectResponse(redirect_url)
        if url == metadata_url:
            return MetadataResponse(
                {
                    "issuer": "https://identity.example.test/realms/nv-config-manager",
                    "authorization_endpoint": (
                        "https://identity.example.test/realms/nv-config-manager"
                        "/protocol/openid-connect/auth"
                    ),
                    "token_endpoint": (
                        "https://identity.example.test/realms/nv-config-manager"
                        "/protocol/openid-connect/token"
                    ),
                }
            )
        raise requests.exceptions.ConnectionError(f"unexpected URL: {url}")

    monkeypatch.setattr(requests, "get", fake_get)

    assert OIDCAuth.discover_oidc_config(
        "https://mcp.config-manager.local/mcp",
        verify=False,
    ) == (
        "https://identity.example.test/realms/nv-config-manager",
        "nv-config-manager",
    )


def test_redirect_discovery_matches_azure_style_metadata_without_hostname(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    redirect_url = (
        "https://identity.example.test/tenant-id/oauth2/v2.0/authorize"
        "?client_id=client-id&response_type=code"
    )
    metadata_url = "https://identity.example.test/tenant-id/v2.0/.well-known/openid-configuration"

    def fake_get(
        url: str,
        allow_redirects: bool | None = None,
        timeout: int = 10,
        verify: bool | str = True,
    ) -> object:
        if url == "https://mcp.config-manager.local/mcp":
            return RedirectResponse(redirect_url)
        if url == metadata_url:
            return MetadataResponse(
                {
                    "issuer": "https://identity.example.test/tenant-id/v2.0",
                    "authorization_endpoint": (
                        "https://identity.example.test/tenant-id/oauth2/v2.0/authorize"
                    ),
                    "token_endpoint": ("https://identity.example.test/tenant-id/oauth2/v2.0/token"),
                }
            )
        raise requests.exceptions.ConnectionError(f"unexpected URL: {url}")

    monkeypatch.setattr(requests, "get", fake_get)

    assert OIDCAuth.discover_oidc_config(
        "https://mcp.config-manager.local/mcp",
        verify=False,
    ) == ("https://identity.example.test/tenant-id/v2.0", "client-id")


def test_keycloak_fallback_uses_keycloak_oidc_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail_metadata(url: str, timeout: int, verify: bool | str) -> MetadataResponse:
        raise requests.exceptions.ConnectionError("metadata unavailable")

    monkeypatch.setattr(requests, "get", fail_metadata)

    auth = OIDCAuth(
        issuer_url="https://keycloak.example.com/realms/nv-config-manager",
        client_id="nv-config-manager",
        token_file=tmp_path / "token.json",
    )

    assert (
        auth._get_auth_endpoint()
        == "https://keycloak.example.com/realms/nv-config-manager/protocol/openid-connect/auth"
    )
    assert (
        auth._get_token_endpoint()
        == "https://keycloak.example.com/realms/nv-config-manager/protocol/openid-connect/token"
    )
    assert auth.scopes == ["openid", "profile", "email"]


def test_azure_fallback_keeps_azure_paths_and_scope(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail_metadata(url: str, timeout: int, verify: bool | str) -> MetadataResponse:
        raise requests.exceptions.ConnectionError("metadata unavailable")

    monkeypatch.setattr(requests, "get", fail_metadata)

    auth = OIDCAuth(
        issuer_url="https://login.microsoftonline.com/tenant-id/v2.0",
        client_id="client-id",
        token_file=tmp_path / "token.json",
    )

    assert auth._get_auth_endpoint() == (
        "https://login.microsoftonline.com/tenant-id/oauth2/v2.0/authorize"
    )
    assert auth._get_token_endpoint() == (
        "https://login.microsoftonline.com/tenant-id/oauth2/v2.0/token"
    )
    assert auth.scopes == ["api://client-id/.default", "openid", "profile"]


def test_generic_oidc_fallback_uses_issuer_relative_paths(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def fail_metadata(url: str, timeout: int, verify: bool | str) -> MetadataResponse:
        raise requests.exceptions.ConnectionError("metadata unavailable")

    monkeypatch.setattr(requests, "get", fail_metadata)

    auth = OIDCAuth(
        issuer_url="https://idp.example.com/oauth2/default",
        client_id="client-id",
        token_file=tmp_path / "token.json",
    )

    assert auth._get_auth_endpoint() == "https://idp.example.com/oauth2/default/authorize"
    assert auth._get_token_endpoint() == "https://idp.example.com/oauth2/default/token"
    assert auth.scopes == ["openid", "profile", "email"]
