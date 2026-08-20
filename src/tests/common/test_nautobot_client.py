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

from nv_config_manager.common.client.nautobot import NautobotClient
from nv_config_manager.dhcp.nautobot import NautobotClient as DhcpNautobotClient


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
