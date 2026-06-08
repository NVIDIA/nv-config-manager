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

from starlette.testclient import TestClient

from nv_config_manager.mcp.main import create_app
from nv_config_manager.mcp.settings import MCPSettings


def test_healthcheck() -> None:
    settings = _settings()

    client = TestClient(create_app(settings))
    response = client.get("/healthcheck")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_mcp_endpoint_accepts_gateway_host_without_auth() -> None:
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


def _settings() -> MCPSettings:
    return MCPSettings(
        workflow_api_url="http://workflow:9000",
        config_store_api_url="http://config-store:9000",
        dhcp_api_url="http://dhcp:9000",
        nautobot_url="http://nautobot",
        nautobot_token="token",
        nautobot_verify=True,
        nautobot_auth_mode="jwt",
        nautobot_token_fallback_enabled=False,
        max_response_bytes=1000,
    )
