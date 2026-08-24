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
"""Tests for NautobotClient timeout configuration."""

from configparser import ConfigParser
from unittest.mock import patch

import pytest

from nv_config_manager.common.client.nautobot import NautobotClient
from nv_config_manager.dhcp.nautobot import NautobotClient as DhcpNautobotClient
from nv_config_manager.temporal.client.nautobot import NautobotClient as TemporalNautobotClient


def _nautobot_config(**kwargs: str) -> ConfigParser:
    config = ConfigParser()
    config.add_section("nautobot")
    config.set("nautobot", "server", "https://nautobot.example.com")
    config.set("nautobot", "token", "token")
    for key, value in kwargs.items():
        config.set("nautobot", key, value)
    return config


def test_base_from_config_defaults_timeout_to_30_when_unset() -> None:
    client = NautobotClient.from_config(_nautobot_config())
    assert client._timeout == 30


def test_base_from_config_reads_timeout_from_ini() -> None:
    client = NautobotClient.from_config(_nautobot_config(timeout="120"))
    assert client._timeout == 120


def test_base_from_config_blank_timeout_uses_default() -> None:
    client = NautobotClient.from_config(_nautobot_config(timeout="  "))
    assert client._timeout == 30


def test_dhcp_from_config_defaults_timeout_to_60_when_unset() -> None:
    client = DhcpNautobotClient.from_config(_nautobot_config())
    assert client._timeout == 60


def test_dhcp_from_config_reads_timeout_from_ini() -> None:
    client = DhcpNautobotClient.from_config(_nautobot_config(timeout="180"))
    assert client._timeout == 180


@pytest.mark.asyncio
async def test_temporal_graphql_omitted_timeout_uses_configured_value() -> None:
    """Temporal GraphQL must not hardcode 10s when callers omit timeout."""
    config = _nautobot_config(timeout="120")
    with patch("nv_config_manager.temporal.client.nautobot.load_config", return_value=config):
        client = TemporalNautobotClient()

    seen: dict[str, object] = {}

    async def fake_base_graphql_query(
        self: NautobotClient,
        query: str,
        variables: dict[str, object] | None = None,
        timeout: int | None = None,
    ) -> dict[str, object]:
        seen["timeout"] = timeout
        seen["self_timeout"] = self._timeout
        return {"data": {}}

    with patch.object(NautobotClient, "graphql_query", fake_base_graphql_query):
        await client.graphql_query("query { x }")

    assert seen["timeout"] is None
    assert seen["self_timeout"] == 120
