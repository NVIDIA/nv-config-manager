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

from urllib.parse import parse_qs, urlparse

import pytest
from fastapi import HTTPException
from starlette.testclient import TestClient

from nv_config_manager.mcp.main import create_app
from nv_config_manager.mcp.settings import MCPOAuthSettings, MCPSettings


def test_healthcheck() -> None:
    settings = _settings()

    client = TestClient(create_app(settings))
    response = client.get("/healthcheck")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_mcp_endpoint_accepts_gateway_host_without_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("nv_config_manager.common.auth.auth_required", lambda: False)

    with TestClient(
        create_app(_settings()),
        base_url="http://mcp.config-manager.local",
    ) as client:
        response = client.post(
            "/mcp",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "0.0.0"},
                },
            },
        )

    assert response.status_code == 200


def test_mcp_endpoint_requires_auth_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    async def reject_identity(request: object) -> object:
        raise HTTPException(status_code=403, detail="This endpoint requires SSO authentication.")

    monkeypatch.setattr(
        "nv_config_manager.mcp.auth.require_authenticated_identity",
        reject_identity,
    )

    with TestClient(
        create_app(_settings()),
        base_url="http://svc-mcp.config-manager.local",
    ) as client:
        response = client.post(
            "/mcp",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "0.0.0"},
                },
            },
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "This endpoint requires SSO authentication."}


def test_oauth_metadata_endpoints_bypass_service_auth(monkeypatch: pytest.MonkeyPatch) -> None:
    async def reject_identity(request: object) -> object:
        raise HTTPException(status_code=403, detail="This endpoint requires SSO authentication.")

    monkeypatch.setattr(
        "nv_config_manager.mcp.auth.require_authenticated_identity",
        reject_identity,
    )

    with TestClient(
        create_app(_settings(), _oauth_settings()),
        base_url="https://svc-mcp.config-manager.local",
    ) as client:
        protected_resource_response = client.get("/.well-known/oauth-protected-resource/mcp")
        root_protected_resource_response = client.get("/.well-known/oauth-protected-resource")
        auth_server_response = client.get("/.well-known/oauth-authorization-server")

    assert protected_resource_response.status_code == 200
    assert root_protected_resource_response.status_code == 200
    assert protected_resource_response.json() == {
        "resource": "https://svc-mcp.config-manager.local/mcp",
        "authorization_servers": ["https://idp.example.test/realms/nvcm"],
        "bearer_methods_supported": ["header"],
        "resource_name": "NVIDIA Config Manager MCP",
        "scopes_supported": ["openid", "email", "profile"],
        "jwks_uri": "https://idp.example.test/realms/nvcm/certs",
    }
    assert root_protected_resource_response.json() == protected_resource_response.json()
    assert auth_server_response.status_code == 200
    assert auth_server_response.json() == {
        "issuer": "https://idp.example.test/realms/nvcm",
        "authorization_endpoint": "https://idp.example.test/realms/nvcm/auth",
        "token_endpoint": "https://idp.example.test/realms/nvcm/token",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["none"],
        "code_challenge_methods_supported": ["S256"],
        "client_id_metadata_document_supported": False,
        "scopes_supported": ["openid", "email", "profile"],
        "jwks_uri": "https://idp.example.test/realms/nvcm/certs",
    }


def test_oauth_compatibility_proxy_uses_local_issuer_and_strips_resource(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token_request: dict[str, object] = {}
    mcp_cli_callback = "http://127.0.0.1:8765/callback/mcp-cli-callback-id"

    class StubResponse:
        status = 200
        headers = {
            "Content-Type": "application/json",
            "Cache-Control": "no-store",
        }

        async def __aenter__(self) -> StubResponse:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        async def read(self) -> bytes:
            return b'{"access_token":"redacted","token_type":"Bearer"}'

    class StubClientSession:
        def __init__(self, *, timeout: object) -> None:
            assert getattr(timeout, "total") == 30

        async def __aenter__(self) -> StubClientSession:
            return self

        async def __aexit__(self, *args: object) -> None:
            return None

        def post(
            self,
            url: str,
            *,
            data: str,
            headers: dict[str, str],
        ) -> StubResponse:
            token_request.update(url=url, content=data, headers=headers)
            return StubResponse()

    monkeypatch.setattr(
        "nv_config_manager.mcp.oauth_proxy.aiohttp.ClientSession", StubClientSession
    )
    oauth_settings = _oauth_settings(forward_resource_parameter=False)

    with TestClient(
        create_app(_settings(), oauth_settings),
        base_url="https://svc-mcp.config-manager.local",
    ) as client:
        protected_response = client.get("/.well-known/oauth-protected-resource/mcp")
        auth_server_response = client.get("/.well-known/oauth-authorization-server")
        authorize_response = client.get(
            "/oauth/authorize",
            params={
                "client_id": "nvcm-cli",
                "scope": "openid api://nvcm-api/access",
                "state": "state-value",
                "redirect_uri": mcp_cli_callback,
                "resource": "https://svc-mcp.config-manager.local/mcp",
            },
            follow_redirects=False,
        )
        upstream_state = parse_qs(urlparse(authorize_response.headers["location"]).query)["state"][
            0
        ]
        callback_response = client.get(
            "/oauth/callback",
            params={
                "code": "code-value",
                "state": upstream_state,
                "session_state": "session-value",
            },
            follow_redirects=False,
        )
        token_response = client.post(
            "/oauth/token",
            data={
                "grant_type": "authorization_code",
                "client_id": "nvcm-cli",
                "code": "code-value",
                "redirect_uri": mcp_cli_callback,
                "resource": "https://svc-mcp.config-manager.local/mcp",
            },
        )
        invalid_client_response = client.post(
            "/oauth/token",
            data={"grant_type": "authorization_code", "client_id": "other-client"},
        )

    assert protected_response.json()["resource"] == ("https://svc-mcp.config-manager.local/mcp")
    assert protected_response.json()["authorization_servers"] == [
        "https://svc-mcp.config-manager.local"
    ]
    assert auth_server_response.json()["issuer"] == "https://svc-mcp.config-manager.local"
    assert auth_server_response.json()["authorization_endpoint"] == (
        "https://svc-mcp.config-manager.local/oauth/authorize"
    )
    assert auth_server_response.json()["token_endpoint"] == (
        "https://svc-mcp.config-manager.local/oauth/token"
    )

    redirect_query = parse_qs(urlparse(authorize_response.headers["location"]).query)
    assert authorize_response.status_code == 302
    assert "resource" not in redirect_query
    assert redirect_query["scope"] == ["openid api://nvcm-api/access"]
    assert redirect_query["redirect_uri"] == ["https://svc-mcp.config-manager.local/oauth/callback"]
    assert redirect_query["state"] != ["state-value"]

    callback_location = urlparse(callback_response.headers["location"])
    assert callback_response.status_code == 302
    assert f"{callback_location.scheme}://{callback_location.netloc}{callback_location.path}" == (
        mcp_cli_callback
    )
    assert parse_qs(callback_location.query) == {
        "code": ["code-value"],
        "session_state": ["session-value"],
        "state": ["state-value"],
    }

    assert token_response.status_code == 200
    assert token_response.json()["access_token"] == "redacted"
    assert token_request["url"] == "https://idp.example.test/realms/nvcm/token"
    token_params = parse_qs(str(token_request["content"]))
    assert "resource" not in token_params
    assert token_params["code"] == ["code-value"]
    assert token_params["redirect_uri"] == ["https://svc-mcp.config-manager.local/oauth/callback"]
    assert invalid_client_response.status_code == 400
    assert invalid_client_response.json() == {"error": "invalid_client"}


@pytest.mark.parametrize(
    "redirect_uri",
    [
        "https://127.0.0.1:8765/callback/id",
        "http://localhost:8765/callback/id",
        "http://127.0.0.1:8765/not-a-callback/id",
        "http://127.0.0.1:8765/callback/id?next=https://example.test",
    ],
)
def test_oauth_compatibility_proxy_rejects_non_dcr_mcp_cli_redirects(
    redirect_uri: str,
) -> None:
    with TestClient(
        create_app(_settings(), _oauth_settings(forward_resource_parameter=False)),
        base_url="https://svc-mcp.config-manager.local",
    ) as client:
        response = client.get(
            "/oauth/authorize",
            params={
                "client_id": "nvcm-cli",
                "state": "state-value",
                "redirect_uri": redirect_uri,
            },
        )

    assert response.status_code == 400
    assert response.json() == {"error": "invalid_request"}


def test_configured_oauth_metadata_path_bypasses_service_auth(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def reject_identity(request: object) -> object:
        raise HTTPException(status_code=403, detail="This endpoint requires SSO authentication.")

    monkeypatch.setattr(
        "nv_config_manager.mcp.auth.require_authenticated_identity",
        reject_identity,
    )
    oauth_settings = _oauth_settings(resource_url="https://svc-mcp.config-manager.local/custom/mcp")

    with TestClient(
        create_app(_settings(), oauth_settings),
        base_url="https://svc-mcp.config-manager.local",
    ) as client:
        response = client.get("/.well-known/oauth-protected-resource/custom/mcp")

    assert response.status_code == 200
    assert response.json()["resource"] == "https://svc-mcp.config-manager.local/custom/mcp"


def test_oauth_metadata_endpoints_not_registered_when_disabled() -> None:
    client = TestClient(create_app(_settings(), MCPOAuthSettings(enabled=False)))

    response = client.get("/.well-known/oauth-protected-resource/mcp")

    assert response.status_code == 404


def test_mcp_auth_failure_includes_resource_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def reject_identity(request: object) -> object:
        raise HTTPException(status_code=401, detail="Authentication required")

    monkeypatch.setattr(
        "nv_config_manager.mcp.auth.require_authenticated_identity",
        reject_identity,
    )

    with TestClient(
        create_app(_settings(), _oauth_settings()),
        base_url="https://svc-mcp.config-manager.local",
    ) as client:
        response = client.post(
            "/mcp",
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "test-client", "version": "0.0.0"},
                },
            },
        )

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == (
        'Bearer error="invalid_token", '
        'error_description="Authentication required", '
        'resource_metadata="https://svc-mcp.config-manager.local'
        '/.well-known/oauth-protected-resource/mcp"'
    )


def _settings() -> MCPSettings:
    return MCPSettings(
        workflow_api_url="http://workflow:9000",
        workflow_ui_url="https://config-manager.example.test",
        config_store_api_url="http://config-store:9000",
        dhcp_api_url="http://dhcp:9000",
        nautobot_url="http://nautobot",
        nautobot_read_only_token="token",
        nautobot_verify=True,
        nautobot_auth_mode="jwt",
        nautobot_token_fallback_enabled=False,
        max_response_bytes=1000,
    )


def _oauth_settings(
    resource_url: str = "https://svc-mcp.config-manager.local/mcp",
    forward_resource_parameter: bool = True,
) -> MCPOAuthSettings:
    return MCPOAuthSettings(
        enabled=True,
        resource_url=resource_url,
        issuer_url="https://idp.example.test/realms/nvcm",
        client_id="nvcm-cli",
        scopes=("openid", "email", "profile"),
        authorization_endpoint="https://idp.example.test/realms/nvcm/auth",
        token_endpoint="https://idp.example.test/realms/nvcm/token",
        jwks_uri="https://idp.example.test/realms/nvcm/certs",
        forward_resource_parameter=forward_resource_parameter,
    )
