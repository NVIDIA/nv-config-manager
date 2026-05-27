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
"""Console Server Port dataclass."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ConnectedDevice:  # pylint: disable=too-many-instance-attributes
    """Representation of a Device connected on a console port."""

    name: str
    manufacturer: str


@dataclass(frozen=True)
class ConnectedConsolePort:
    """Representation of a connected console port in nautobot."""

    name: str
    device: ConnectedDevice


@dataclass(frozen=True)
class ConsoleServerPort:  # pylint: disable=too-many-instance-attributes
    """Representation of a nautobot console server port for ease of use in templates."""

    name: str
    connected_console_port: ConnectedConsolePort | None
    connected: bool

    @staticmethod
    def from_nautobot_graphql(entry: dict[str, Any]) -> ConsoleServerPort:
        """Create ConsoleServerPort object from nautobot data."""
        connected_console_port = None

        if entry["connected_console_port"]:
            device_entry = entry["connected_console_port"]["device"]
            device = ConnectedDevice(
                name=device_entry["name"],
                manufacturer=device_entry["device_type"]["manufacturer"]["name"],
            )
            connected_console_port = ConnectedConsolePort(
                name=entry["connected_console_port"]["name"], device=device
            )
        return ConsoleServerPort(
            name=entry["name"],
            connected_console_port=connected_console_port,
            connected=connected_console_port is not None,
        )
