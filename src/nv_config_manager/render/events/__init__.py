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
"""NB NATS Event Handlers."""

# Import here for dynamic dispatching
from nv_config_manager.render.events.dcim import (
    cable,
    cablepath,
    device,
    deviceredundancygroup,
    frontport,
    interface,
    rearport,
)
from nv_config_manager.render.events.extras import configcontext
from nv_config_manager.render.events.ipam import ipaddress, prefix, vrf
from nv_config_manager.render.events.nautobot_bgp_models import (
    autonomoussystem,
    bgproutinginstance,
    peerendpoint,
    peergroup,
    peering,
)
from nv_config_manager.render.events.nv_config_manager import (
    configmanagerdevicestatus,
)

__all__ = (
    "autonomoussystem",
    "peering",
    "peergroup",
    "peerendpoint",
    "bgproutinginstance",
    "cable",
    "cablepath",
    "configcontext",
    "device",
    "deviceredundancygroup",
    "frontport",
    "interface",
    "ipaddress",
    "configmanagerdevicestatus",
    "prefix",
    "rearport",
    "vrf",
)
