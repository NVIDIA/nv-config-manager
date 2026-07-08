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
"""Validation helpers for mock topology device source data."""

from pathlib import Path
from typing import Any


def require_cumulus_primary_ip4_interface(device: dict[str, Any], source: Path) -> None:
    """Require an explicit, valid primary IPv4 interface for Cumulus devices."""
    platform_name = (device.get("platform") or {}).get("name", "")
    if "Cumulus" not in platform_name:
        return

    device_name = device.get("name") or source.name
    primary_interface_name = device.get("primary_ip4_interface")
    if not primary_interface_name:
        raise ValueError(
            f"Mock Cumulus device {device_name} in {source} must define primary_ip4_interface"
        )

    primary_interface = next(
        (
            interface
            for interface in device.get("interfaces", [])
            if interface.get("name") == primary_interface_name
        ),
        None,
    )
    if primary_interface is None:
        raise ValueError(
            f"Mock Cumulus device {device_name} in {source} declares "
            f"primary_ip4_interface={primary_interface_name!r}, but that interface "
            "does not exist"
        )

    has_ipv4_address = any(
        address.get("ip_version") == 4 and address.get("address")
        for address in primary_interface.get("ip_addresses", [])
    )
    if not has_ipv4_address:
        raise ValueError(
            f"Mock Cumulus device {device_name} in {source} declares "
            f"primary_ip4_interface={primary_interface_name!r}, but that interface "
            "does not have an IPv4 address"
        )
