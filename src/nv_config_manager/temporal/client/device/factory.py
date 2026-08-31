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
"""Factory for platform-specific network connections."""

from __future__ import annotations

from nv_config_manager.common.config import load_config
from nv_config_manager.temporal.client.device.base import NetworkConnection
from nv_config_manager.temporal.common.mixins.device import NetworkDeviceData, Platform


def from_device_data(device_data: NetworkDeviceData) -> NetworkConnection:
    """Return a NetworkConnection for a given device."""
    # Avoid circular import with device/__init__.py. Resolve classes from the
    # public package so unittest patches of device.CumulusConnection still apply.
    from nv_config_manager.temporal.client import device as device_clients

    config = load_config()
    connection: NetworkConnection | None = None
    if config["device"].getboolean("mock", fallback=False):
        connection = device_clients.MockNetworkConnection(device_data.host, site=device_data.site)
    elif device_data.platform == Platform.ARISTA_EOS:
        connection = device_clients.AristaConnection(device_data.host, site=device_data.site)
    elif device_data.platform == Platform.CUMULUS_LINUX:
        connection = device_clients.CumulusConnection(device_data.host, site=device_data.site)
    elif device_data.platform == Platform.NV_OS:
        connection = device_clients.NVOSConnection(device_data.host, site=device_data.site)
    elif device_data.platform == Platform.MLNX_OS:
        connection = device_clients.MellanoxConnection(device_data.host, site=device_data.site)
    elif device_data.platform == Platform.JUNIPER_JUNOS:
        connection = device_clients.JuniperConnection(device_data.host, site=device_data.site)
    else:
        raise NotImplementedError(f"No handler implemented for platform {device_data.platform}")
    return connection
