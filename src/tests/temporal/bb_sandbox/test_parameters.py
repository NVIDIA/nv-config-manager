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
"""Parameter API coverage for the Backbone sandbox workflow forms."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nv_config_manager.temporal.api.main import app
from nv_config_manager.temporal.bb_sandbox import parameters


def test_backbone_parameter_routes_are_registered() -> None:
    """Both forms have every dynamic parameter route available from v1."""
    paths = {route.path for route in parameters.router.routes}
    assert {
        "/parameter/bb-sandbox/devices",
        "/parameter/bb-sandbox/circuits",
        "/parameter/bb-sandbox/devices/{device_id}/interfaces",
        "/parameter/bb-sandbox/next-lag",
        "/parameter/bb-sandbox/next-prefix",
    }.issubset(paths)
    assert any(getattr(route, "original_router", None) is parameters.router for route in app.routes)


@pytest.mark.asyncio
async def test_next_prefix_parameter_delegates_to_nautobot_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The route returns the explicit prefix and parent used to auto-fill the form."""

    class Client:
        async def __aenter__(self) -> "Client":
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def get_next_available_prefix(
            self, role_name: str, prefix_length: int
        ) -> tuple[str, str]:
            assert (role_name, prefix_length) == ("BB-P2P", 127)
            return "2001:db8::2/127", "2001:db8::/120"

    monkeypatch.setattr(parameters, "NautobotClient", Client)
    result = await parameters.get_next_backbone_prefix(127, "BB-P2P")

    assert result.prefix == "2001:db8::2/127"
    assert result.parent_prefix == "2001:db8::/120"


def test_next_prefix_parameter_accepts_url_query_integer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Normal URL-encoded query values are parsed before allowed-length validation."""

    class Client:
        async def __aenter__(self) -> "Client":
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def get_next_available_prefix(
            self, role_name: str, prefix_length: int
        ) -> tuple[str, str]:
            assert (role_name, prefix_length) == ("BB-P2P", 31)
            return "198.18.0.0/31", "198.18.0.0/24"

    monkeypatch.setattr(parameters, "NautobotClient", Client)
    test_app = FastAPI()
    test_app.include_router(parameters.router, prefix="/v1")
    response = TestClient(test_app).get(
        "/v1/parameter/bb-sandbox/next-prefix", params={"prefix_length": "31"}
    )

    assert response.status_code == 200
    assert response.json()["prefix"] == "198.18.0.0/31"
