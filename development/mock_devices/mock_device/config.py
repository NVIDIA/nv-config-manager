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
"""Mock device configuration models."""

from __future__ import annotations

import os
import random

from pydantic import BaseModel, Field


def _generate_mac() -> str:
    """Generate a random locally-administered unicast MAC address."""
    octets = [random.randint(0x00, 0xFF) for _ in range(6)]
    octets[0] = (octets[0] | 0x02) & 0xFE  # locally administered, unicast
    return ":".join(f"{b:02x}" for b in octets)


class DeviceConfig(BaseModel):
    """Configuration for a single mock network device."""

    name: str = Field(description="Device hostname")
    platform: str = Field(description="Platform: cumulus, arista, nvos, mellanox")
    mac_address: str = Field(default_factory=_generate_mac, description="MAC for DHCP hw-address")
    serial: str = Field(default="", description="Serial number for client-id based DHCP")
    device_id: str = Field(default="", description="Nautobot device UUID")
    role: str = Field(default="", description="Device role (e.g. SMN-Leaf, TAN-Spine)")
    management_ip: str = Field(default="", description="Expected management IP from DHCP")

    # DHCP parameters
    dhcp_server: str = Field(default="", description="Kea server address (IP or service name)")
    relay_gateway: str = Field(
        default="", description="Gateway IP to set as giaddr for relayed DHCP"
    )
    client_id_template: str = Field(
        default="", description="Jinja2 template for client-id (e.g. '00:{{ serial | hex }}')"
    )

    # Mock API parameters
    api_port: int = Field(default=0, description="Port for mock device API (0 = auto)")
    os_version: str = Field(default="", description="OS version for fixture selection (e.g. 5.11.0, 4.29.5M)")
    running_config: str = Field(default="", description="Canned running configuration")

    @property
    def client_id(self) -> bytes | None:
        """Compute the DHCP client-id from serial and template."""
        if not self.serial:
            return None

        template = self.client_id_template
        if not template:
            if self.platform in ("cumulus", "nvos"):
                template = "00:{{ serial | hex }}"
            else:
                return None

        hex_serial = ":".join(f"{ord(c):02x}" for c in self.serial)
        rendered = template.replace("{{ serial | hex }}", hex_serial)
        rendered = rendered.replace("{{ serial }}", self.serial)

        # Handle the NVOS compound template
        if "NVOS##N5110_LD##" in template:
            compound = "NVOS##N5110_LD##" + self.serial
            hex_compound = ":".join(f"{ord(c):02x}" for c in compound)
            rendered = hex_compound

        return bytes.fromhex(rendered.replace(":", ""))

    @property
    def mac_bytes(self) -> bytes:
        return bytes.fromhex(self.mac_address.replace(":", ""))

    @staticmethod
    def from_env() -> DeviceConfig:
        """Load device configuration from environment variables."""
        return DeviceConfig(
            name=os.environ.get("MOCK_DEVICE_NAME", "mock-device-1"),
            platform=os.environ.get("MOCK_DEVICE_PLATFORM", "cumulus"),
            mac_address=os.environ.get("MOCK_DEVICE_MAC", _generate_mac()),
            serial=os.environ.get("MOCK_DEVICE_SERIAL", ""),
            device_id=os.environ.get("MOCK_DEVICE_ID", ""),
            role=os.environ.get("MOCK_DEVICE_ROLE", ""),
            management_ip=os.environ.get("MOCK_DEVICE_MGMT_IP", ""),
            dhcp_server=os.environ.get("MOCK_DHCP_SERVER", ""),
            relay_gateway=os.environ.get("MOCK_DHCP_RELAY_GATEWAY", ""),
            client_id_template=os.environ.get("MOCK_DHCP_CLIENT_ID_TEMPLATE", ""),
            api_port=int(os.environ.get("MOCK_DEVICE_API_PORT", "0")),
            os_version=os.environ.get("MOCK_DEVICE_OS_VERSION", ""),
            running_config=os.environ.get("MOCK_DEVICE_RUNNING_CONFIG", ""),
        )
