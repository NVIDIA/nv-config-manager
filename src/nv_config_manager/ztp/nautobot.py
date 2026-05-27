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
"""Nautobot Client for ZTP service.

Extends the base NautobotClient with ZTP-specific methods for
device bootstrapping and provisioning.
"""

from __future__ import annotations

from nv_config_manager.common.client import NautobotClient as BaseNautobotClient
from nv_config_manager.common.config import load_config
from nv_config_manager.common.log import LogCategory, get_logger
from nv_config_manager.ztp.device import DeviceData

logger = get_logger(__name__, category=LogCategory.NAUTOBOT)

DEVICE_QUERY = """
query ($id: ID!) {
  config_manager_device(id: $id) {
    intended_config {
      config_store_instance
      path
    }
    device {
      id
      name
      platform {
        name
      }
      config_context
      interfaces: interfaces(has_ip_addresses: true) {
        ip_addresses {
          host
        }
      }
    }
  }
}
"""


class NotFoundError(Exception):
    """No device data found in GraphQL."""


class NautobotClient(BaseNautobotClient):
    """Async Nautobot Client for ZTP service.

    Extends the base NautobotClient with methods specific to ZTP,
    including device data retrieval and provisioning status updates.
    """

    def __init__(
        self,
        nautobot_url: str | None = None,
        token: str | None = None,
    ) -> None:
        """Initialize ZTP NB Client."""
        # Lazy import to avoid circular dependency with nv_config_manager.common.config
        from nv_config_manager.common.config import parse_verify_param

        config = load_config()
        super().__init__(
            nautobot_url=nautobot_url or config["nautobot"]["server"],
            token=token or config["nautobot"]["token"],
            verify=parse_verify_param(config["nautobot"]),
        )

    async def get_device_data(self, device_id: str) -> DeviceData:
        """Load device data from GraphQL."""
        data = await self.graphql_query(DEVICE_QUERY, variables={"id": device_id})
        device_data = DeviceData.from_graphql(data)
        if not device_data:
            raise NotFoundError(f"No data found in NB for {device_id}.")
        return device_data

    async def get_device_serial(self, device_id: str) -> str:
        """Return the serial number for the device from Nautobot."""
        query = """
query ($id: ID!) {
    device(id: $id) {
        serial
    }
}
"""
        data = await self.graphql_query(query, variables={"id": device_id})
        if "errors" in data:
            raise NotFoundError(f"No serial found in NB for {device_id}.")
        serial: str = data["data"]["device"]["serial"]
        return serial

    async def set_status_provisioned(self, device_id: str) -> None:
        """Update the device status to Provisioned."""
        await self.patch(f"dcim/devices/{device_id}/", {"status": "Provisioned"})
