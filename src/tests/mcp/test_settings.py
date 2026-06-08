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

from configparser import ConfigParser

from nv_config_manager.mcp.settings import MCPSettings


def _config(nautobot_server: str, auth_mode: str = "auto") -> ConfigParser:
    config = ConfigParser()
    config["mcp"] = {
        "use_internal_endpoints": "true",
        "nautobot_auth_mode": auth_mode,
    }
    config["temporal"] = {
        "api_service": "http://workflow:9000",
        "api_url": "https://workflow.example.test",
    }
    config["config_store.client"] = {
        "api_service": "http://config-store:9000",
        "api_url": "https://config-store.example.test",
    }
    config["dhcp"] = {
        "api_service": "http://dhcp:9000",
        "api_url": "https://dhcp.example.test",
    }
    config["nautobot"] = {
        "server": nautobot_server,
        "token": "read-only-token",
        "verify": "true",
    }
    return config


def test_nautobot_auth_auto_uses_jwt_for_local_nautobot() -> None:
    settings = MCPSettings.from_config(_config("http://nv-config-manager-nautobot"))

    assert settings.nautobot_auth_mode == "jwt"


def test_nautobot_auth_auto_uses_token_for_external_nautobot() -> None:
    settings = MCPSettings.from_config(_config("https://nautobot.example.test"))

    assert settings.nautobot_auth_mode == "token"


def test_nautobot_auth_explicit_override() -> None:
    settings = MCPSettings.from_config(_config("https://nautobot.example.test", auth_mode="jwt"))

    assert settings.nautobot_auth_mode == "jwt"
