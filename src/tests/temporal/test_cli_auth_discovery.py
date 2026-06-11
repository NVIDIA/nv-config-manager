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

import pytest

from nv_config_manager.common.oidc import AuthDiscovery
from nv_config_manager.temporal import cli as temporal_cli


class FakeOIDCAuth:
    auth_discovered: list[tuple[str, bool]] = []
    redirect_discovered: list[tuple[str, bool]] = []
    created: list[dict[str, object]] = []
    auth_discovery_result: AuthDiscovery | None = AuthDiscovery(
        auth_required=True,
        issuer_url="https://issuer.example.com",
        client_id="workflow-cli-client",
        scopes=("openid", "profile", "email"),
        services={"workflow": "https://workflow-api.example.com/v1/workflow/"},
    )
    redirect_discovery_result: tuple[str, str] | None = (
        "https://issuer.example.com",
        "gateway-client",
    )

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
        self.created.append(
            {
                "issuer_url": issuer_url,
                "client_id": client_id,
                "scopes": scopes,
                "verify": verify,
            }
        )

    @classmethod
    def discover_auth_config(
        cls,
        discovery_url: str,
        verify: bool = True,
    ) -> AuthDiscovery | None:
        cls.auth_discovered.append((discovery_url, verify))
        return cls.auth_discovery_result

    @classmethod
    def discover_oidc_config(
        cls,
        gateway_url: str,
        verify: bool = True,
    ) -> tuple[str, str] | None:
        cls.redirect_discovered.append((gateway_url, verify))
        return cls.redirect_discovery_result


@pytest.fixture(autouse=True)
def reset_fake_oidc(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeOIDCAuth.auth_discovered = []
    FakeOIDCAuth.redirect_discovered = []
    FakeOIDCAuth.created = []
    FakeOIDCAuth.auth_discovery_result = AuthDiscovery(
        auth_required=True,
        issuer_url="https://issuer.example.com",
        client_id="workflow-cli-client",
        scopes=("openid", "profile", "email"),
        services={"workflow": "https://workflow-api.example.com/v1/workflow/"},
    )
    FakeOIDCAuth.redirect_discovery_result = ("https://issuer.example.com", "gateway-client")
    monkeypatch.setattr(temporal_cli, "OIDCAuth", FakeOIDCAuth)


def test_build_auth_uses_base_auth_discovery() -> None:
    auth, workflow_url = temporal_cli._build_auth(
        base_hostname="config-manager.example.com",
        issuer=None,
        client_id=None,
        insecure=True,
    )

    assert auth is not None
    assert workflow_url == "https://workflow-api.example.com/v1/workflow"
    assert FakeOIDCAuth.auth_discovered == [
        ("https://config-manager.example.com/auth/discovery", False)
    ]
    assert FakeOIDCAuth.redirect_discovered == []
    assert FakeOIDCAuth.created == [
        {
            "issuer_url": "https://issuer.example.com",
            "client_id": "workflow-cli-client",
            "scopes": ["openid", "profile", "email"],
            "verify": False,
        }
    ]


def test_build_auth_returns_regular_workflow_url_when_auth_is_disabled() -> None:
    FakeOIDCAuth.auth_discovery_result = AuthDiscovery(
        auth_required=False,
        services={"workflow": "https://workflow.config-manager.example.com/v1/workflow/"},
    )

    auth, workflow_url = temporal_cli._build_auth(
        base_hostname="config-manager.example.com",
        issuer=None,
        client_id=None,
        insecure=False,
    )

    assert auth is None
    assert workflow_url == "https://workflow.config-manager.example.com/v1/workflow"
    assert FakeOIDCAuth.created == []


def test_build_auth_falls_back_to_redirect_discovery() -> None:
    FakeOIDCAuth.auth_discovery_result = None

    auth, workflow_url = temporal_cli._build_auth(
        base_hostname="config-manager.example.com",
        issuer=None,
        client_id=None,
        insecure=False,
    )

    assert auth is not None
    assert workflow_url == "https://svc-workflow.config-manager.example.com/v1/workflow"
    assert FakeOIDCAuth.redirect_discovered == [
        ("https://workflow.config-manager.example.com/v1/workflow", True)
    ]
    assert FakeOIDCAuth.created == [
        {
            "issuer_url": "https://issuer.example.com",
            "client_id": "gateway-client",
            "scopes": None,
            "verify": True,
        }
    ]
