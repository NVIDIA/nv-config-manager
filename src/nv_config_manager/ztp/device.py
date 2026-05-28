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
"""Device Data is a dataclass that contains the Nautobot data for a device."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from nv_config_manager.common.client import (
    ConfigStoreClient,
    ConfigStoreFileNotFound,
)
from nv_config_manager.common.config import get_internal_auth_headers, load_config


@dataclass
class DeviceData:  # pylint: disable=too-many-instance-attributes
    """Nautobot Device Data."""

    id: str
    name: str
    addresses: list[str]
    platform_name: str
    version: str | None
    config_store_instance: str | None

    @property
    def platform(self) -> str:
        """Convert platform name to equivalent 1.x slug for compat."""
        return self.platform_name.lower().replace(" ", "-")

    def config_store_client(self) -> ConfigStoreClient:
        """Return the appropriate async config store client."""
        app_config = load_config()
        use_internal = app_config.getboolean(
            "config_store.client", "use_internal_endpoint", fallback=False
        )
        ui_url = app_config.get("config_store.client", "ui_url")

        if use_internal:
            # Internal HTTP cluster communication - no mTLS needed
            api_endpoint = app_config.get("config_store.client", "api_service")
            return ConfigStoreClient(
                api_endpoint,
                "intended",
                ui_url,
                verify=False,
                client_certificate=None,
                headers=get_internal_auth_headers,
            )
        else:
            # External mTLS communication
            if not self.config_store_instance:
                raise ValueError("Config store API endpoint not configured")
            api_endpoint = self.config_store_instance

            client_cert_path = None
            if app_config.get("mtls", "tls_client_cert_path") and app_config.get(
                "mtls", "tls_client_key_path"
            ):
                cert_path = app_config.get("mtls", "tls_client_cert_path")
                key_path = app_config.get("mtls", "tls_client_key_path")
                client_cert_path = (cert_path, key_path)

            # Parse verify parameter - can be bool or path to CA cert
            verify: bool | str = True
            if app_config.get("config_store.client", "verify"):
                try:
                    verify = app_config.getboolean("config_store.client", "verify")
                except ValueError:
                    # Path to custom CA certificate
                    verify = str(app_config.get("config_store.client", "verify"))

            return ConfigStoreClient(
                api_endpoint,
                "intended",
                ui_url,
                verify=verify,
                client_certificate=client_cert_path,
            )

    async def load_file(self, filename: str) -> str:
        """Return file content for the given device."""
        if self.config_store_instance is None:
            raise ConfigStoreFileNotFound(f"No config store file found for device {self.name}")

        client = self.config_store_client()
        async with client:
            config_file = await client.load_file(self.id, filename)
        return config_file.content

    @staticmethod
    def from_graphql(data: dict[str, Any]) -> DeviceData | None:
        """Create DeviceData from GraphQL query."""
        plugin_data = data["data"]["config_manager_device"]
        if plugin_data is None:
            return None
        device = plugin_data["device"]
        addresses = {
            address["host"]
            for interface in device["interfaces"]
            for address in interface["ip_addresses"]
        }

        version = None
        if device["config_context"] is not None:
            version = device["config_context"].get("intended-firmware", {}).get("version")

        instance = None
        if plugin_data["intended_config"]:
            instance = plugin_data["intended_config"]["config_store_instance"]
            instance = re.sub("ui", "api-mtls", instance)

        return DeviceData(
            id=device["id"],
            name=device["name"],
            addresses=sorted(addresses),
            platform_name=device["platform"]["name"],
            version=version,
            config_store_instance=instance,
        )
