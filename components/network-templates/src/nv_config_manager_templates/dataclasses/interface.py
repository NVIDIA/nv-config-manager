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
"""Interface dataclass."""

from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ConnectedDevice:  # pylint: disable=too-many-instance-attributes
    """Representation of a Device connected on an interface."""

    name: str
    role: str
    asn: str | None
    tags: list[str] = field(compare=False)  # make this class hashable
    peer_ipv4: str
    peer_ipv6: str
    tenant: str | None = None

    @property
    def peer_group(self):
        """The BGP peer group for this device."""
        peer_group = self.role.upper()
        if peer_group == "AZURE-GATEWAY":
            return "GW"
        if peer_group.startswith("AZURE-"):
            return peer_group.replace("AZURE-", "")
        if peer_group == "NSV DEVICE":
            # Temp hack for things not properly modeled yet
            if "dpu" in self.name:
                return "DPU"
        if peer_group in (
            "GPU",
            "HIGHSPEEDSTORAGE-SERVER",
            "CONTROL-SERVER",
            "USERSTORAGE-SERVER",
        ):
            return "SERVER"
        return peer_group


@dataclass(frozen=True)
class ConnectedInterface:
    """Representation of a connected interface in nautobot."""

    name: str
    device: ConnectedDevice


@dataclass(frozen=True)
class Interface:  # pylint: disable=too-many-instance-attributes
    """Representation of a nautobot interface for ease of use in templates."""

    name: str
    primary_ipv4: str | None
    # These 4 IP fields are for future-proofing
    primary_ipv6: str | None
    secondary_ipv4: list[str] | None
    secondary_ipv6: list[str] | None
    link_local: str | None
    enabled: bool
    mtu: int
    tags: list[str]
    untagged_vlan: int | None
    tagged_vlans: list[int]
    vrf: str
    connected_interface: ConnectedInterface
    description: str
    role: str
    optic_type: str
    mgmt_only: bool
    member_interfaces: list[str]
    mac_address: str | None = None
    vip_ipv4: str | None = None

    @property
    def is_dot1q(self) -> bool:
        """Return True if this is a dot1q interface."""
        return bool(re.search(r"\d+\.\d+$", self.name))

    @property
    def optic_speed(self) -> str | None:
        """Return the optic speed."""
        match = re.search("A_(\\d+G?)BASE", self.optic_type)
        if match:
            if match.group(1).endswith("G"):
                return match.group(1)
            if match.group(1) == "1000":
                return "1G"
        return None

    @property
    def vlan_number(self) -> int | None:
        """Return the vlan number if this is an SVI."""
        match = re.search("vlan(\\d+)", self.name.lower())
        if match:
            return int(match.group(1))
        return None

    @property
    def parent(self) -> str | None:
        """Return the parent interface if applicable."""
        # Only applicable for Cumulus atm
        if self.is_dot1q:
            return self.name.split(".")[0]
        match = re.match(r"(swp\d+)s(\d)", self.name)
        if match:
            return match.group(1)
        return None

    def has_bgp_peer(self) -> bool:
        """Consolidated function to determine if a connected_interface is BGP eligible.

        Returns:
            bool: True if the interface is BGP eligible, False otherwise.
        """
        if not self.connected_interface:
            return False

        return not self.primary_ipv4 and not self.untagged_vlan

    @property
    def peer_tags(self) -> list[str] | None:
        """Return the peer tags if applicable."""
        if self.connected_interface:
            return self.connected_interface.device.tags
        return []

    @staticmethod
    def _build_addressing_v2(
        entry: dict[str, Any],
    ) -> tuple[str, str, list[str], list[str], str, str, str | None]:
        primary_ipv4 = None
        primary_ipv6 = None
        secondary_ipv4 = []
        secondary_ipv6 = []
        link_local = None
        vip_ipv4 = None
        vrf = entry["vrf"]["name"] if entry["vrf"] else "default"
        for ip_entry in entry["ip_addresses"]:
            if ip_entry["ip_version"] == 4:
                role_name = ip_entry["role"]["name"] if ip_entry.get("role") else None
                if role_name == "VIP":
                    vip_ipv4 = ip_entry["address"]
                elif not primary_ipv4:
                    primary_ipv4 = ip_entry["address"]
                else:
                    secondary_ipv4.append(ip_entry["address"])
            else:
                # Set primary, secondary, and link_local IPv6 Addresses
                if ipaddress.ip_interface(ip_entry["address"]).is_link_local:
                    link_local = ip_entry["address"]
                elif not primary_ipv6:
                    primary_ipv6 = ip_entry["address"]
                else:
                    secondary_ipv6.append(ip_entry["address"])

        # Convert NSV VRF to default for the purposes of configuration
        if vrf == "NSV":
            vrf = "default"

        # Strip site name from VRF name (e.g., "SITE_VRFNAME" becomes "VRFNAME")
        if "_" in vrf:
            vrf = vrf.split("_")[1]

        return (
            primary_ipv4,
            primary_ipv6,
            secondary_ipv4,
            secondary_ipv6,
            link_local,
            vrf,
            vip_ipv4,
        )

    @staticmethod
    def _normalize_vrf_name(vrf_name: str | None) -> str:
        if not vrf_name or vrf_name == "NSV":
            return "default"
        if "_" in vrf_name:
            return vrf_name.split("_", 1)[1]
        return vrf_name

    @staticmethod
    def _routing_instance_vrfs(instance: dict[str, Any]) -> set[str]:
        router_id_interfaces = (
            instance.get("router_id", {}).get("interfaces") if instance.get("router_id") else None
        )
        if not router_id_interfaces:
            return {"default"}

        return {
            Interface._normalize_vrf_name(
                router_id_interface["vrf"]["name"] if router_id_interface.get("vrf") else None
            )
            for router_id_interface in router_id_interfaces
        }

    @staticmethod
    def _bgp_asn_from_routing_instances(
        device: dict[str, Any], connected_interface_vrf: str
    ) -> str | None:
        routing_instances = device.get("bgp_routing_instances") or []
        for instance in routing_instances:
            if connected_interface_vrf in Interface._routing_instance_vrfs(instance):
                return str(instance["autonomous_system"]["asn"])

        if connected_interface_vrf == "default" and len(routing_instances) == 1:
            return str(routing_instances[0]["autonomous_system"]["asn"])

        return None

    @staticmethod
    def _build_connected_interface_v2(entry: dict[str, Any]) -> ConnectedInterface:
        # This is incomplete and just a sample as we also need frontport data
        # for breakout cables
        connected_interface = None
        if entry["connected_interface"]:
            # Build the ConnectedInterface object
            device = entry["connected_interface"]["device"]

            # Use the module-bays parent device as the object if the module exist.
            # If a module is inserted, the connected device will be `null`
            if not device and entry["connected_interface"].get("module"):
                device = entry["connected_interface"]["module"]["parent_module_bay"][
                    "parent_device"
                ]

            device_tags = [tag["name"] for tag in device["tags"]] if device else []
            connected_vrf_entry = entry["connected_interface"].get("vrf")
            connected_vrf = Interface._normalize_vrf_name(
                connected_vrf_entry["name"] if connected_vrf_entry else None
            )
            peer_asn = Interface._bgp_asn_from_routing_instances(device, connected_vrf)
            if peer_asn is None:
                peer_asn = (device.get("intent") or {}).get("bgp", {}).get("asn")
                if peer_asn is not None:
                    peer_asn = str(peer_asn)

            peer_ipv4 = None
            peer_ipv6 = None
            for ip_entry in entry["connected_interface"]["ip_addresses"]:
                if ip_entry["ip_version"] == 4:
                    peer_ipv4 = ip_entry["host"]
                else:
                    peer_ipv6 = ip_entry["host"]

            connected_device = ConnectedDevice(
                name=device["name"],
                role=device["role"]["name"],
                tags=device_tags,
                tenant=device["tenant"]["name"] if device["tenant"] else None,
                asn=peer_asn,
                peer_ipv4=peer_ipv4,
                peer_ipv6=peer_ipv6,
            )
            connected_interface = ConnectedInterface(
                name=entry["connected_interface"]["name"], device=connected_device
            )
        return connected_interface

    @staticmethod
    def _from_render_data(entry: dict[str, Any]) -> Interface:
        (
            primary_ipv4,
            primary_ipv6,
            secondary_ipv4,
            secondary_ipv6,
            link_local,
            vrf,
            vip_ipv4,
        ) = Interface._build_addressing_v2(entry)

        connected_interface = Interface._build_connected_interface_v2(entry)

        return Interface(
            name=entry["name"],
            primary_ipv4=primary_ipv4,
            primary_ipv6=primary_ipv6,
            secondary_ipv4=secondary_ipv4,
            secondary_ipv6=secondary_ipv6,
            link_local=link_local,
            enabled=entry["enabled"],
            mtu=entry["mtu"],
            tags=[tag["name"] for tag in entry["tags"]],
            untagged_vlan=entry["untagged_vlan"]["vid"] if entry["untagged_vlan"] else None,
            tagged_vlans=[vlan["vid"] for vlan in entry["tagged_vlans"]],
            vrf=vrf,
            connected_interface=connected_interface,
            description=entry["description"],
            role=entry["role"]["name"] if entry["role"] else None,
            optic_type=entry["type"],
            mgmt_only=entry["mgmt_only"],
            member_interfaces=[member["name"] for member in entry["member_interfaces"]],
            mac_address=entry.get("mac_address"),
            vip_ipv4=vip_ipv4,
        )

    @staticmethod
    def from_render_data(entry: dict[str, Any]) -> Interface:
        """Create an interface object from normalized render data."""
        return Interface._from_render_data(entry)
