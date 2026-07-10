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
import json
import os
import time
from unittest.mock import AsyncMock, patch

import jwt as pyjwt
from aiohttp import ClientResponseError, RequestInfo
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from multidict import CIMultiDict
from yarl import URL

from nv_config_manager.common.auth import AuthConfig, JwtProviderConfig
from nv_config_manager.dhcp.api import app

_HEADERS_TRUSTED = AuthConfig(accept_request_headers=True)
_AUTH_DISABLED = AuthConfig(required=False)


def make_client_response_error(message: str) -> ClientResponseError:
    """Create a ClientResponseError for testing."""
    request_info = RequestInfo(
        url=URL("http://test"),
        method="POST",
        headers=CIMultiDict(),
        real_url=URL("http://test"),
    )
    return ClientResponseError(
        request_info=request_info,
        history=(),
        message=message,
    )


# Get the directory containing this test file
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))

MIN_READY_CONFIG = [
    {
        "arguments": {
            "Dhcp4": {
                "lease-database": {
                    "host": "dhcp-db.example.local",
                    "name": "kea_dhcp",
                    "type": "postgresql",
                }
            }
        },
        "result": 0,
    }
]

MIN_UNSYNCED_CONFIG = [
    {
        "arguments": {
            "Dhcp4": {
                "lease-database": {
                    "type": "memfile",
                }
            }
        },
        "result": 0,
    }
]

LEASE_GET_REQUEST = {
    "command": "lease4-get",
    "service": ["dhcp4"],
    "arguments": {"ip-address": "7.245.196.5"},
}

LEASE_GET_RESPONSE = [
    {
        "arguments": {
            "hostname": "",
            "hw-address": "02:05:91:48:df:cf",
            "ip-address": "7.245.196.5",
            "state": 0,
            "subnet-id": 104,
            "valid-lft": 7200,
        },
        "result": 0,
        "text": "IPv4 lease found.",
    }
]


def make_jwt_token(claims: dict) -> tuple[str, rsa.RSAPublicKey]:
    """Create a signed JWT and return it with the public key for JWKS mocking."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    token = pyjwt.encode(
        claims,
        key,
        algorithm="RS256",
        headers={"kid": "dhcp-test"},
    )
    return token, key.public_key()


def make_auth_config_with_jwt_provider() -> AuthConfig:
    """Return auth config with a non-OIDC JWT provider."""
    return AuthConfig(
        jwt_providers=(
            JwtProviderConfig(
                name="ssa",
                issuer="https://ssa.example.com",
                audiences=["s:nv-config-manager"],
                jwks_uri="https://ssa.example.com/jwks",
                claim_email="sub",
                claim_user="sub",
                claim_groups="scopes",
            ),
        )
    )


def test_healthcheck_success():
    """Verify healthcheck success case."""
    client = TestClient(app)

    with patch(
        "nv_config_manager.dhcp.api.KeaClient.status", new_callable=AsyncMock
    ) as mock_status:
        mock_status.return_value = [
            {"arguments": {"pid": 9, "reload": 63173, "uptime": 63173}, "result": 0}
        ]
        with patch(
            "nv_config_manager.dhcp.api.KeaClient.get_config", new_callable=AsyncMock
        ) as mock_get_config:
            mock_get_config.return_value = MIN_READY_CONFIG
            with patch(
                "nv_config_manager.dhcp.api.RedisClient.load_kea_config", new_callable=AsyncMock
            ) as mock_load_kea:
                mock_load_kea.return_value = {"some": "data"}
                rsp = client.get("/healthcheck")
                assert rsp.status_code == 200
                assert rsp.json() == "OK"


def test_healthcheck_unsynced():
    """Verify healthcheck with unsynced config."""
    client = TestClient(app)

    with patch(
        "nv_config_manager.dhcp.api.KeaClient.status", new_callable=AsyncMock
    ) as mock_status:
        mock_status.return_value = [
            {"arguments": {"pid": 9, "reload": 63173, "uptime": 63173}, "result": 0}
        ]
        with patch(
            "nv_config_manager.dhcp.api.KeaClient.get_config", new_callable=AsyncMock
        ) as mock_get_config:
            mock_get_config.return_value = MIN_UNSYNCED_CONFIG
            with patch(
                "nv_config_manager.dhcp.api.RedisClient.load_kea_config", new_callable=AsyncMock
            ) as mock_load_kea:
                mock_load_kea.return_value = {"some": "data"}
                rsp = client.get("/healthcheck")
                assert rsp.status_code == 500
                assert rsp.json() == {"detail": "Lease database not present in Dhcp4 config"}


def test_healthcheck_status_error():
    """Verify healthcheck with status error."""
    client = TestClient(app)

    with patch(
        "nv_config_manager.dhcp.api.KeaClient.status", new_callable=AsyncMock
    ) as mock_status:
        mock_status.return_value = [
            {"arguments": {"pid": 9, "reload": 63173, "uptime": 63173}, "result": 1}
        ]
        with patch(
            "nv_config_manager.dhcp.api.RedisClient.load_kea_config", new_callable=AsyncMock
        ) as mock_load_kea:
            mock_load_kea.return_value = {"some": "data"}
            rsp = client.get("/healthcheck")
            assert rsp.status_code == 500
            assert rsp.json() == {
                "detail": [{"arguments": {"pid": 9, "reload": 63173, "uptime": 63173}, "result": 1}]
            }


def test_healthcheck_http_error():
    """Verify healthcheck with HTTP error."""
    client = TestClient(app)

    with patch(
        "nv_config_manager.dhcp.api.KeaClient.status", new_callable=AsyncMock
    ) as mock_status:
        mock_status.side_effect = make_client_response_error("HTTP ERROR")
        with patch(
            "nv_config_manager.dhcp.api.RedisClient.load_kea_config", new_callable=AsyncMock
        ) as mock_load_kea:
            mock_load_kea.return_value = {"some": "data"}
            rsp = client.get("/healthcheck")
            assert rsp.status_code == 500
            assert rsp.json() == {"detail": "HTTP ERROR"}


def test_metrics():
    """Verify /metrics returns Prometheus metrics without auth."""
    client = TestClient(app)

    with patch(
        "nv_config_manager.dhcp.api.RedisClient.load_refresh_timestamp",
        new_callable=AsyncMock,
        side_effect=lambda v: 1700000000.0 if v == 4 else None,
    ):
        rsp = client.get("/metrics")
        assert rsp.status_code == 200
        assert "text/plain" in rsp.headers["content-type"]
        body = rsp.text
        assert "nv_config_manager_dhcp_cache_last_refresh_timestamp_seconds" in body
        assert 'ip_version="4"' in body
        assert 'ip_version="6"' not in body

    with patch(
        "nv_config_manager.dhcp.api.RedisClient.load_refresh_timestamp",
        new_callable=AsyncMock,
        return_value=None,
    ):
        rsp = client.get("/metrics")
        assert rsp.status_code == 200
        assert "nv_config_manager_dhcp_cache_last_refresh_timestamp_seconds" in rsp.text


def test_whoami_requires_auth():
    """Verify /whoami is protected on the DHCP API."""
    client = TestClient(app)

    with patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED):
        rsp = client.get("/whoami")
        assert rsp.status_code == 403

        rsp = client.get("/whoami", headers={"X-Auth-Request-Email": "admin@example.com"})
        assert rsp.status_code == 200
        assert rsp.json() == {"user": "admin", "roles": ["all"]}


def test_flush_cache():
    """Verify DELETE /admin/cache."""
    client = TestClient(app)

    with patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED):
        rsp = client.delete("/admin/cache")
        assert rsp.status_code == 403

        with patch(
            "nv_config_manager.dhcp.api.RedisClient.flush_kea_config",
            new_callable=AsyncMock,
            return_value=True,
        ):
            rsp = client.delete(
                "/admin/cache",
                headers={"X-Auth-Request-Email": "admin@example.com"},
            )
            assert rsp.status_code == 200
            assert rsp.json() == {"detail": "DHCPv4 cached configuration flushed"}

        with patch(
            "nv_config_manager.dhcp.api.RedisClient.flush_kea_config",
            new_callable=AsyncMock,
            return_value=True,
        ):
            rsp = client.delete(
                "/admin/cache?ip_version=6",
                headers={"X-Auth-Request-Email": "admin@example.com"},
            )
            assert rsp.status_code == 200
            assert rsp.json() == {"detail": "DHCPv6 cached configuration flushed"}

        with patch(
            "nv_config_manager.dhcp.api.RedisClient.flush_kea_config",
            new_callable=AsyncMock,
            return_value=False,
        ):
            rsp = client.delete(
                "/admin/cache",
                headers={"X-Auth-Request-Email": "admin@example.com"},
            )
            assert rsp.status_code == 404
            assert rsp.json() == {"detail": "No cached configuration found for DHCPv4"}


def test_get_config_success():
    """Verify /config GET success."""
    client = TestClient(app)
    with open(os.path.join(_THIS_DIR, "resources/config_get.json")) as f:
        mock_response = json.load(f)

    with patch(
        "nv_config_manager.dhcp.api.KeaClient.get_config", new_callable=AsyncMock
    ) as mock_get_config:
        mock_get_config.return_value = mock_response
        with patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED):
            # Did not come in through nginx sso
            rsp = client.get("/config")
            assert rsp.status_code == 403
            assert rsp.json() == {"detail": "This endpoint requires SSO authentication."}

            # Came in through nginx sso
            rsp = client.get("/config", headers={"X-Auth-Request-Email": "test@example.com"})
            assert rsp.status_code == 200
            assert rsp.json() == MIN_READY_CONFIG


def test_get_config_accepts_non_oidc_jwt_provider():
    """Verify DHCP accepts a valid Bearer JWT from any configured JWT provider."""
    client = TestClient(app)
    with open(os.path.join(_THIS_DIR, "resources/config_get.json")) as f:
        mock_response = json.load(f)

    token, public_key = make_jwt_token(
        {
            "iss": "https://ssa.example.com",
            "aud": "s:nv-config-manager",
            "sub": "service-account",
            "scopes": ["nv-config-manager"],
            "exp": int(time.time()) + 300,
            "iat": int(time.time()),
        }
    )
    mock_jwk = type("JWK", (), {"key": public_key})()

    with patch(
        "nv_config_manager.dhcp.api.KeaClient.get_config", new_callable=AsyncMock
    ) as mock_get_config:
        mock_get_config.return_value = mock_response
        with patch(
            "nv_config_manager.common.auth._auth_config", make_auth_config_with_jwt_provider()
        ):
            with patch("nv_config_manager.common.auth._get_jwks_client") as mock_get_client:
                mock_client = type(
                    "JWKSClient",
                    (),
                    {"get_signing_key_from_jwt": lambda self, jwt: mock_jwk},
                )()
                mock_get_client.return_value = mock_client

                rsp = client.get("/config", headers={"Authorization": f"Bearer {token}"})

    assert rsp.status_code == 200
    assert rsp.json() == MIN_READY_CONFIG


def test_get_config_auth_disabled():
    """Verify /config GET succeeds without auth headers when auth is disabled."""
    client = TestClient(app)
    with open(os.path.join(_THIS_DIR, "resources/config_get.json")) as f:
        mock_response = json.load(f)

    with patch(
        "nv_config_manager.dhcp.api.KeaClient.get_config", new_callable=AsyncMock
    ) as mock_get_config:
        mock_get_config.return_value = mock_response
        with patch("nv_config_manager.common.auth._auth_config", _AUTH_DISABLED):
            rsp = client.get("/config")
            assert rsp.status_code == 200
            assert rsp.json() == MIN_READY_CONFIG


def test_get_config_error():
    """Verify /config GET with error."""
    client = TestClient(app)

    with patch(
        "nv_config_manager.dhcp.api.KeaClient.get_config", new_callable=AsyncMock
    ) as mock_get_config:
        mock_get_config.side_effect = make_client_response_error("HTTP ERROR")
        with patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED):
            rsp = client.get("/config", headers={"X-Auth-Request-Email": "test@example.com"})
            assert rsp.status_code == 500
            assert rsp.json() == {"detail": "HTTP ERROR"}


def test_proxy_lease_get():
    """Verify POST /lease proxies a lease4-get command."""
    client = TestClient(app)

    with patch(
        "nv_config_manager.dhcp.api.KeaClient.lease_command",
        new_callable=AsyncMock,
        return_value=LEASE_GET_RESPONSE,
    ) as mock_lease_command:
        with patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED):
            rsp = client.post("/lease", json=LEASE_GET_REQUEST)
            assert rsp.status_code == 403

            rsp = client.post(
                "/lease",
                json=LEASE_GET_REQUEST,
                headers={"X-Auth-Request-Email": "test@example.com"},
            )

    assert rsp.status_code == 200
    assert rsp.json() == LEASE_GET_RESPONSE
    mock_lease_command.assert_awaited_once_with("lease4-get", "7.245.196.5")


def test_proxy_lease_delete():
    """Verify POST /lease proxies a lease4-del command."""
    client = TestClient(app)
    request = {
        "command": "lease4-del",
        "service": ["dhcp4"],
        "arguments": {"ip-address": "7.245.196.5"},
    }
    response = [{"result": 0, "text": "IPv4 lease deleted."}]

    with patch(
        "nv_config_manager.dhcp.api.KeaClient.lease_command",
        new_callable=AsyncMock,
        return_value=response,
    ) as mock_lease_command:
        with patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED):
            rsp = client.post(
                "/lease",
                json=request,
                headers={"X-Auth-Request-Email": "test@example.com"},
            )

    assert rsp.status_code == 200
    assert rsp.json() == response
    mock_lease_command.assert_awaited_once_with("lease4-del", "7.245.196.5")


def test_proxy_lease_rejects_unsupported_requests():
    """Verify the lease proxy cannot be used for arbitrary KEA commands."""
    client = TestClient(app)
    invalid_requests = [
        {**LEASE_GET_REQUEST, "command": "config-get"},
        {**LEASE_GET_REQUEST, "service": ["dhcp6"]},
        {**LEASE_GET_REQUEST, "service": []},
        {**LEASE_GET_REQUEST, "service": ["dhcp4", "dhcp4"]},
        {
            **LEASE_GET_REQUEST,
            "arguments": {"ip-address": "2001:db8::1"},
        },
        {
            **LEASE_GET_REQUEST,
            "arguments": {"ip-address": "7.245.196.5", "subnet-id": 104},
        },
    ]

    with patch(
        "nv_config_manager.dhcp.api.KeaClient.lease_command", new_callable=AsyncMock
    ) as mock_lease_command:
        with patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED):
            for request in invalid_requests:
                rsp = client.post(
                    "/lease",
                    json=request,
                    headers={"X-Auth-Request-Email": "test@example.com"},
                )
                assert rsp.status_code == 422

    mock_lease_command.assert_not_awaited()


def test_proxy_lease_http_error():
    """Verify KEA HTTP errors are surfaced by the DHCP API."""
    client = TestClient(app)

    with patch(
        "nv_config_manager.dhcp.api.KeaClient.lease_command",
        new_callable=AsyncMock,
        side_effect=make_client_response_error("HTTP ERROR"),
    ):
        with patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED):
            rsp = client.post(
                "/lease",
                json=LEASE_GET_REQUEST,
                headers={"X-Auth-Request-Email": "test@example.com"},
            )

    assert rsp.status_code == 500
    assert rsp.json() == {"detail": "HTTP ERROR"}


def test_proxy_lease_timeout():
    """Verify KEA timeouts are surfaced by the DHCP API."""
    client = TestClient(app)

    with patch(
        "nv_config_manager.dhcp.api.KeaClient.lease_command",
        new_callable=AsyncMock,
        side_effect=TimeoutError("KEA Request timed out"),
    ):
        with patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED):
            rsp = client.post(
                "/lease",
                json=LEASE_GET_REQUEST,
                headers={"X-Auth-Request-Email": "test@example.com"},
            )

    assert rsp.status_code == 500
    assert rsp.json() == {"detail": "KEA Request timed out"}
