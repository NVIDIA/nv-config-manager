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
import asyncio
import json
import os
import time
from unittest.mock import AsyncMock, call, patch

import jwt as pyjwt
import pytest
from aiohttp import ClientConnectionError, ClientResponseError, RequestInfo
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from multidict import CIMultiDict
from yarl import URL

from nv_config_manager.common.auth import AuthConfig, JwtProviderConfig
from nv_config_manager.dhcp.api import _fetch_lease_dashboard_sources, app
from nv_config_manager.dhcp.kea import KeaClient

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

LEASE_GET_RESPONSE = [
    {
        "arguments": {
            "cltt": int(time.time()) - 60,
            "hostname": "",
            "hw-address": "02:05:91:48:df:cf",
            "ip-address": "10.0.0.10",
            "state": 0,
            "subnet-id": 7,
            "valid-lft": 7200,
        },
        "result": 0,
        "text": "IPv4 lease found.",
    }
]


def lease_page(*leases: dict[str, object]) -> list[dict[str, object]]:
    """Wrap raw leases in a successful KEA page response."""
    return [
        {
            "arguments": {"count": len(leases), "leases": list(leases)},
            "result": 0,
        }
    ]


def active_lease(ip: str, hostname: str) -> dict[str, object]:
    """Return one active lease row for API pagination tests."""
    return {
        "cltt": int(time.time()) - 60,
        "hostname": hostname,
        "hw-address": f"02:00:00:00:00:{int(ip.rsplit('.', maxsplit=1)[1]):02x}",
        "ip-address": ip,
        "state": 0,
        "subnet-id": 7,
        "valid-lft": 3600,
    }


LEASE_DASHBOARD_CONFIG = [
    {
        "result": 0,
        "arguments": {
            "Dhcp4": {
                "reservations": [
                    {
                        "hostname": "reserved-switch",
                        "hw-address": "02:00:00:00:00:01",
                        "ip-address": "10.0.0.2",
                    }
                ],
                "subnet4": [
                    {
                        "id": 7,
                        "subnet": "10.0.0.0/24",
                        "pools": [{"pool": "10.0.0.10-10.0.0.19"}],
                    }
                ],
            }
        },
    }
]

LEASE_DASHBOARD_STATISTICS = [
    {
        "result": 0,
        "arguments": {
            "assigned-addresses": [[1, "2026-07-10 00:00:00"]],
            "subnet[7].pool[0].assigned-addresses": [[1, "2026-07-10 00:00:00"]],
            "subnet[7].pool[0].total-addresses": [[10, "2026-07-10 00:00:00"]],
        },
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


def test_get_lease():
    """Return one normalized lease without exposing KEA's command envelope."""
    client = TestClient(app)

    with (
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_lease",
            new_callable=AsyncMock,
            return_value=LEASE_GET_RESPONSE,
        ) as mock_get_lease,
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_config",
            new_callable=AsyncMock,
            return_value=LEASE_DASHBOARD_CONFIG,
        ) as mock_get_config,
        patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED),
    ):
        rsp = client.get("/lease?ip_address=10.0.0.10&ip_version=4")
        assert rsp.status_code == 403

        rsp = client.get(
            "/lease?ip_address=10.0.0.10",
            headers={"X-Auth-Request-Email": "test@example.com"},
        )

    assert rsp.status_code == 200
    assert rsp.json()["ip_address"] == "10.0.0.10"
    assert rsp.json()["subnet"] == "10.0.0.0/24"
    assert "result" not in rsp.json()
    assert "subnet_id" not in rsp.json()
    mock_get_lease.assert_awaited_once_with("10.0.0.10", version=4)
    mock_get_config.assert_awaited_once_with(4)


def test_lease_openapi_documents_not_found() -> None:
    """Advertise the domain-level missing lease response for both operations."""
    lease_operations = app.openapi()["paths"]["/lease"]

    for method in ("get", "delete"):
        assert lease_operations[method]["responses"]["404"] == {"description": "Lease not found"}


def test_lease_openapi_defaults_to_ipv4() -> None:
    """Advertise IPv4 as the optional default for every lease operation."""
    operations = (
        app.openapi()["paths"]["/lease"]["get"],
        app.openapi()["paths"]["/lease"]["delete"],
        app.openapi()["paths"]["/leases"]["get"],
        app.openapi()["paths"]["/lease-dashboard"]["get"],
    )

    for operation in operations:
        parameter = next(
            parameter for parameter in operation["parameters"] if parameter["name"] == "ip_version"
        )
        assert parameter["required"] is False
        assert parameter["schema"]["default"] == 4


def test_get_lease_not_found():
    """Translate KEA's empty result into a RESTful not-found response."""
    client = TestClient(app)

    with (
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_lease",
            new_callable=AsyncMock,
            return_value=[{"result": 3, "text": "Lease not found."}],
        ),
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_config",
            new_callable=AsyncMock,
            return_value=LEASE_DASHBOARD_CONFIG,
        ),
        patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED),
    ):
        rsp = client.get(
            "/lease?ip_address=10.0.0.99&ip_version=4",
            headers={"X-Auth-Request-Email": "test@example.com"},
        )

    assert rsp.status_code == 404
    assert rsp.json() == {"detail": "Lease 10.0.0.99 was not found"}


def test_list_leases():
    """Return a bounded normalized lease collection."""
    client = TestClient(app)
    lease_page = [{"result": 0, "arguments": {"leases": [LEASE_GET_RESPONSE[0]["arguments"]]}}]

    with (
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_lease_page",
            new_callable=AsyncMock,
            return_value=lease_page,
        ) as mock_get_lease_page,
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_config",
            new_callable=AsyncMock,
            return_value=LEASE_DASHBOARD_CONFIG,
        ),
        patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED),
    ):
        rsp = client.get(
            "/leases?limit=25",
            headers={"X-Auth-Request-Email": "test@example.com"},
        )

    assert rsp.status_code == 200
    payload = rsp.json()
    assert len(payload["leases"]) == 1
    assert payload["leases"][0]["subnet"] == "10.0.0.0/24"
    assert payload["next_cursor"] is None
    mock_get_lease_page.assert_awaited_once_with(
        25,
        version=4,
        from_address="start",
    )


def test_list_leases_follows_opaque_cursor():
    """Continue the normalized collection from KEA's last page address."""
    client = TestClient(app)
    first_page = lease_page(
        active_lease("10.0.0.10", "leaf-01"),
        active_lease("10.0.0.11", "leaf-02"),
    )
    second_page = lease_page(active_lease("10.0.0.12", "leaf-03"))

    with (
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_lease_page",
            new_callable=AsyncMock,
            side_effect=(first_page, second_page),
        ) as mock_get_lease_page,
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_config",
            new_callable=AsyncMock,
            return_value=LEASE_DASHBOARD_CONFIG,
        ),
        patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED),
    ):
        first_rsp = client.get(
            "/leases?limit=2",
            headers={"X-Auth-Request-Email": "test@example.com"},
        )
        cursor = first_rsp.json()["next_cursor"]
        second_rsp = client.get(
            "/leases",
            params={"cursor": cursor, "limit": 2},
            headers={"X-Auth-Request-Email": "test@example.com"},
        )

    assert first_rsp.status_code == 200
    assert [lease["hostname"] for lease in first_rsp.json()["leases"]] == [
        "leaf-01",
        "leaf-02",
    ]
    assert cursor is not None
    assert second_rsp.status_code == 200
    assert [lease["hostname"] for lease in second_rsp.json()["leases"]] == ["leaf-03"]
    assert second_rsp.json()["next_cursor"] is None
    assert mock_get_lease_page.await_args_list == [
        call(2, version=4, from_address="start"),
        call(2, version=4, from_address="10.0.0.11"),
    ]


def test_list_leases_searches_across_backend_pages():
    """Search thousands of leases rather than only the first KEA page."""
    client = TestClient(app)
    pages = [
        lease_page(
            *(
                active_lease(
                    f"10.{page_index}.0.{lease_index}",
                    "target-switch"
                    if page_index == 9 and lease_index == 100
                    else f"leaf-{page_index:02d}-{lease_index:03d}",
                )
                for lease_index in range(1, 101)
            )
        )
        for page_index in range(10)
    ]
    pages.append(lease_page())

    with (
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_lease_page",
            new_callable=AsyncMock,
            side_effect=pages,
        ) as mock_get_lease_page,
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_config",
            new_callable=AsyncMock,
            return_value=LEASE_DASHBOARD_CONFIG,
        ),
        patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED),
    ):
        rsp = client.get(
            "/leases?limit=100&search=target",
            headers={"X-Auth-Request-Email": "test@example.com"},
        )

    assert rsp.status_code == 200
    assert [lease["hostname"] for lease in rsp.json()["leases"]] == ["target-switch"]
    assert rsp.json()["next_cursor"] is None
    assert mock_get_lease_page.await_count == 11
    assert mock_get_lease_page.await_args_list[0] == call(
        100,
        version=4,
        from_address="start",
    )
    assert mock_get_lease_page.await_args_list[-1] == call(
        100,
        version=4,
        from_address="10.9.0.100",
    )


def test_list_leases_rejects_invalid_cursor():
    """Reject malformed cursors before contacting the DHCP server."""
    client = TestClient(app)

    with (
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_lease_page",
            new_callable=AsyncMock,
        ) as mock_get_lease_page,
        patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED),
    ):
        rsp = client.get(
            "/leases?cursor=not-a-cursor",
            headers={"X-Auth-Request-Email": "test@example.com"},
        )

    assert rsp.status_code == 422
    assert rsp.json() == {"detail": "Invalid lease cursor"}
    mock_get_lease_page.assert_not_awaited()


def test_delete_lease():
    """Delete a lease through the domain API without returning KEA's body."""
    client = TestClient(app)

    with patch(
        "nv_config_manager.dhcp.api.KeaClient.delete_lease",
        new_callable=AsyncMock,
        return_value=[{"result": 0, "text": "Lease deleted."}],
    ) as mock_delete_lease:
        with patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED):
            rsp = client.delete(
                "/lease?ip_address=10.0.0.10",
                headers={"X-Auth-Request-Email": "test@example.com"},
            )

    assert rsp.status_code == 204
    assert not rsp.content
    mock_delete_lease.assert_awaited_once_with("10.0.0.10", version=4)


def test_delete_lease_enforces_allowed_groups():
    """Reject lease deletion when the caller is outside DHCP's allowed groups."""
    client = TestClient(app)
    auth_config = AuthConfig(
        accept_request_headers=True,
        allowed_groups=("dhcp-admins",),
    )

    with patch(
        "nv_config_manager.dhcp.api.KeaClient.delete_lease",
        new_callable=AsyncMock,
    ) as mock_delete_lease:
        with patch("nv_config_manager.common.auth._auth_config", auth_config):
            rsp = client.delete(
                "/lease?ip_address=10.0.0.10&ip_version=4",
                headers={
                    "X-Auth-Request-Email": "test@example.com",
                    "X-Auth-Request-Groups": "dhcp-viewers",
                },
            )

    assert rsp.status_code == 403
    mock_delete_lease.assert_not_awaited()


def test_delete_lease_not_found():
    """Return 404 when the selected DHCP service has no matching lease."""
    client = TestClient(app)

    with patch(
        "nv_config_manager.dhcp.api.KeaClient.delete_lease",
        new_callable=AsyncMock,
        return_value=[{"result": 3, "text": "Lease not found."}],
    ):
        with patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED):
            rsp = client.delete(
                "/lease?ip_address=10.0.0.99&ip_version=4",
                headers={"X-Auth-Request-Email": "test@example.com"},
            )

    assert rsp.status_code == 404


def test_lease_address_must_match_ip_version():
    """Reject addresses that do not match the selected DHCP service."""
    client = TestClient(app)

    with patch(
        "nv_config_manager.dhcp.api.KeaClient.get_lease",
        new_callable=AsyncMock,
    ) as mock_get_lease:
        with patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED):
            rsp = client.get(
                "/lease?ip_address=2001:db8::1&ip_version=4",
                headers={"X-Auth-Request-Email": "test@example.com"},
            )

    assert rsp.status_code == 422
    mock_get_lease.assert_not_awaited()


def test_get_lease_http_error():
    """Verify KEA HTTP errors are surfaced by the DHCP API."""
    client = TestClient(app)

    with (
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_lease",
            new_callable=AsyncMock,
            side_effect=make_client_response_error("HTTP ERROR"),
        ),
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_config",
            new_callable=AsyncMock,
            return_value=LEASE_DASHBOARD_CONFIG,
        ),
        patch(
            "nv_config_manager.dhcp.api.KeaClient.close",
            new_callable=AsyncMock,
        ) as mock_close,
    ):
        with patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED):
            rsp = client.get(
                "/lease?ip_address=10.0.0.10&ip_version=4",
                headers={"X-Auth-Request-Email": "test@example.com"},
            )

    assert rsp.status_code == 500
    assert rsp.json() == {"detail": "HTTP ERROR"}
    mock_close.assert_awaited_once()


def test_get_lease_timeout():
    """Verify KEA timeouts are surfaced by the DHCP API."""
    client = TestClient(app)

    with (
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_lease",
            new_callable=AsyncMock,
            side_effect=TimeoutError("KEA Request timed out"),
        ),
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_config",
            new_callable=AsyncMock,
            return_value=LEASE_DASHBOARD_CONFIG,
        ),
    ):
        with patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED):
            rsp = client.get(
                "/lease?ip_address=10.0.0.10&ip_version=4",
                headers={"X-Auth-Request-Email": "test@example.com"},
            )

    assert rsp.status_code == 500
    assert rsp.json() == {"detail": "KEA Request timed out"}


def test_delete_lease_connection_error():
    """Verify other KEA transport errors are surfaced by the DHCP API."""
    client = TestClient(app)

    with patch(
        "nv_config_manager.dhcp.api.KeaClient.delete_lease",
        new_callable=AsyncMock,
        side_effect=ClientConnectionError("KEA connection failed"),
    ):
        with patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED):
            rsp = client.delete(
                "/lease?ip_address=10.0.0.10&ip_version=4",
                headers={"X-Auth-Request-Email": "test@example.com"},
            )

    assert rsp.status_code == 500
    assert rsp.json() == {"detail": "KEA connection failed"}


def test_get_lease_dashboard():
    """Verify GET /lease-dashboard combines bounded KEA operator data."""
    client = TestClient(app)
    lease_page = [
        {
            "result": 0,
            "arguments": {
                "leases": [
                    {
                        "cltt": int(time.time()) - 60,
                        "hostname": "active-switch",
                        "hw-address": "02:00:00:00:00:10",
                        "ip-address": "10.0.0.10",
                        "state": 0,
                        "subnet-id": 7,
                        "valid-lft": 3600,
                    }
                ]
            },
        }
    ]

    with (
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_config",
            new_callable=AsyncMock,
            return_value=LEASE_DASHBOARD_CONFIG,
        ) as mock_get_config,
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_lease_page",
            new_callable=AsyncMock,
            return_value=lease_page,
        ) as mock_get_lease_page,
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_statistics",
            new_callable=AsyncMock,
            return_value=LEASE_DASHBOARD_STATISTICS,
        ) as mock_get_statistics,
        patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED),
    ):
        rsp = client.get("/lease-dashboard?limit=25&ip_version=4")
        assert rsp.status_code == 403

        rsp = client.get(
            "/lease-dashboard?limit=25",
            headers={"X-Auth-Request-Email": "test@example.com"},
        )

    assert rsp.status_code == 200
    payload = rsp.json()
    assert payload["active_lease_count"] == 1
    assert payload["reservation_count"] == 1
    assert payload["assigned_address_count"] == 1
    assert payload["pool_address_count"] == 10
    assert payload["leases"][0]["ip_address"] == "10.0.0.10"
    assert payload["leases"][0]["subnet"] == "10.0.0.0/24"
    assert "subnet_id" not in payload["leases"][0]
    assert payload["reservations"][0]["hostname"] == "reserved-switch"
    assert payload["reservations"][0]["subnet"] is None
    assert payload["pools"][0]["utilization"] == 10.0
    assert "subnet_id" not in payload["pools"][0]
    mock_get_config.assert_awaited_once_with(4)
    mock_get_lease_page.assert_awaited_once_with(25, version=4)
    mock_get_statistics.assert_awaited_once_with(4)


def test_get_lease_dashboard_validates_limit():
    """Keep the splash-page lease response bounded."""
    client = TestClient(app)

    with patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED):
        rsp = client.get(
            "/lease-dashboard?limit=501",
            headers={"X-Auth-Request-Email": "test@example.com"},
        )

    assert rsp.status_code == 422


def test_get_lease_dashboard_kea_error():
    """Surface logical KEA failures as DHCP API errors."""
    client = TestClient(app)

    with (
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_config",
            new_callable=AsyncMock,
            return_value=[{"result": 1, "text": "configuration unavailable"}],
        ),
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_lease_page",
            new_callable=AsyncMock,
            return_value=[{"result": 3, "text": "no leases"}],
        ),
        patch(
            "nv_config_manager.dhcp.api.KeaClient.get_statistics",
            new_callable=AsyncMock,
            return_value=LEASE_DASHBOARD_STATISTICS,
        ),
        patch("nv_config_manager.common.auth._auth_config", _HEADERS_TRUSTED),
    ):
        rsp = client.get(
            "/lease-dashboard",
            headers={"X-Auth-Request-Email": "test@example.com"},
        )

    assert rsp.status_code == 500
    assert rsp.json() == {"detail": "KEA config-get failed: configuration unavailable"}


async def test_dashboard_source_failure_cancels_and_drains_siblings() -> None:
    """Cancel and await sibling KEA requests before propagating a failure."""
    lease_started = asyncio.Event()
    statistics_started = asyncio.Event()
    cancelled: set[str] = set()

    async def fail_config(version: int) -> list[dict]:
        """Fail after both sibling requests have started."""
        assert version == 4
        await lease_started.wait()
        await statistics_started.wait()
        raise ClientConnectionError("KEA connection failed")

    async def block_lease(limit: int, *, version: int) -> list[dict]:
        """Record cancellation of the in-flight lease request."""
        assert limit == 25
        assert version == 4
        lease_started.set()
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            cancelled.add("leases")
            raise

    async def block_statistics(version: int) -> list[dict]:
        """Record cancellation of the in-flight statistics request."""
        assert version == 4
        statistics_started.set()
        try:
            await asyncio.Future()
        except asyncio.CancelledError:
            cancelled.add("statistics")
            raise

    client = KeaClient(host="kea.example.com", port=8000)
    with (
        patch.object(client, "get_config", new=AsyncMock(side_effect=fail_config)),
        patch.object(client, "get_lease_page", new=AsyncMock(side_effect=block_lease)),
        patch.object(client, "get_statistics", new=AsyncMock(side_effect=block_statistics)),
        pytest.raises(ClientConnectionError, match="KEA connection failed"),
    ):
        await _fetch_lease_dashboard_sources(client, limit=25, ip_version=4)

    assert cancelled == {"leases", "statistics"}
