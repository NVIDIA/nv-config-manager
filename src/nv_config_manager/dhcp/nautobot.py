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
"""Nautobot GraphQL Client for DHCP service.

Async Nautobot client for DHCP configuration generation.
Extends the common aiohttp-based NautobotClient.
"""

from __future__ import annotations

import ipaddress
import pathlib
from typing import Any, cast

from nv_config_manager.common.client import NautobotClient as BaseNautobotClient
from nv_config_manager.common.client import NautobotException
from nv_config_manager.common.log import LogCategory, get_logger
from nv_config_manager.dhcp.metrics import DHCP_QUERY_ERRORS

logger = get_logger(__name__, category=LogCategory.DHCP_DATA)

QUERY_PATH = f"{pathlib.Path(__file__).parent.resolve()}/graphql"

# Fields that must be present for a device to be eligible for ZTP
NV_CONFIG_MANAGER_MANAGED_VLANS = [
    "vlan13",
    "vlan30",
    "vlan40",
    "vlan997",
    "vlan998",
    "vlan1002",
    "vlan1001",
    "vlan901",
]


class QueryException(NautobotException):
    """GraphQL Query Exception."""


def _get_gateway_ip(
    prefix_entry: dict[str, Any], prefix: ipaddress.IPv4Network | ipaddress.IPv6Network
) -> str:
    """Extract gateway IP from prefix entry or use first usable IP."""
    gateway_address = (
        prefix_entry["rel_prefix_to_gateway"].get("address")
        if prefix_entry["rel_prefix_to_gateway"]
        else None
    )
    if gateway_address:
        gateway_ip = str(ipaddress.ip_interface(gateway_address).ip)
        if ipaddress.ip_address(gateway_ip) not in prefix:
            DHCP_QUERY_ERRORS.labels(error_type="gateway_outside_subnet").inc()
            raise QueryException(f"Gateway {gateway_ip} is not within subnet {prefix}")
        return gateway_ip
    if prefix.prefixlen in (31, 127):
        return str(prefix.network_address)
    return str(prefix.network_address + 1)


def _build_interface_entry(iface: dict[str, Any]) -> dict[str, Any]:
    """Build common interface fields for option candidate or reservation."""
    return {
        "mac_address": iface.get("mac_address"),
        "serial": iface["device"].get("serial"),
        "platform": (iface["device"]["platform"]["name"] if iface["device"]["platform"] else None),
        "interface_name": iface["name"],
        "interface_role": iface["role"]["name"] if iface["role"] else None,
        "device_name": iface["device"]["name"],
        "device_id": iface["device"]["id"],
    }


def _passes_ztp_aggregate_filter(
    config_manager_device_status: dict[str, Any] | None,
    is_aggregate_managed: bool | None,
) -> bool:
    """True if device passes ZTP enabled and aggregate managed filters."""
    if config_manager_device_status and not config_manager_device_status.get("ztp_enabled", True):
        return False
    if (
        config_manager_device_status
        and config_manager_device_status.get("is_aggregate_managed", False) != is_aggregate_managed
    ):
        return False
    return True


def _pool_ip_matches_prefix(
    pool_ip: dict[str, Any],
    prefix_entry_id: str,
    family: int,
) -> bool:
    """True if pool IP belongs to this prefix and family."""
    return bool(pool_ip["ip_version"] == family and pool_ip["parent"]["id"] == prefix_entry_id)


def _try_build_option_candidate(
    pool_ip: dict[str, Any],
    is_aggregate_managed: bool | None,
) -> dict[str, Any] | None:
    """Build option candidate from pool IP if eligible, else None."""
    interfaces = pool_ip.get("interfaces")
    if not interfaces or len(interfaces) > 1:
        return None

    iface = interfaces[0]
    config_manager_device_status = iface["device"].get("configmanagerdevicestatus")
    if not _passes_ztp_aggregate_filter(config_manager_device_status, is_aggregate_managed):
        return None

    if not iface.get("mac_address") and not iface["device"].get("serial"):
        return None

    ip_addr = ipaddress.ip_interface(pool_ip["address"]).ip
    return {"address": ip_addr, **_build_interface_entry(iface)}


def _get_pool_ips_and_candidates(
    all_pool_ips: list[dict[str, Any]],
    prefix_entry: dict[str, Any],
    family: int,
    is_aggregate_managed: bool | None,
) -> tuple[list[Any], list[dict[str, Any]]]:
    """Build pool_ips and option_candidates for a prefix."""
    pool_ips = []
    option_candidates = []
    for pool_ip in all_pool_ips:
        if not _pool_ip_matches_prefix(pool_ip, prefix_entry["id"], family):
            continue
        ip_addr = ipaddress.ip_interface(pool_ip["address"]).ip
        pool_ips.append(ip_addr)
        candidate = _try_build_option_candidate(pool_ip, is_aggregate_managed)
        if candidate:
            option_candidates.append(candidate)
    return pool_ips, option_candidates


def _validate_reserved_ip_interfaces(reserved_ip: dict[str, Any]) -> dict[str, Any]:
    """Validate reserved IP has exactly one interface. Returns the interface."""
    interfaces = reserved_ip.get("interfaces")
    if not interfaces:
        DHCP_QUERY_ERRORS.labels(error_type="no_interfaces").inc()
        raise QueryException(f"Reserved IP {reserved_ip['address']} has no interfaces assigned")
    if len(interfaces) > 1:
        DHCP_QUERY_ERRORS.labels(error_type="multiple_interfaces").inc()
        raise QueryException(
            f"Reserved IP {reserved_ip['address']} has multiple interfaces assigned"
        )
    return cast(dict[str, Any], interfaces[0])


def _build_reservation_entry(
    reserved_ip: dict[str, Any],
    iface: dict[str, Any],
    ip_addr: ipaddress.IPv4Address | ipaddress.IPv6Address,
) -> dict[str, Any]:
    """Build reservation dict from reserved_ip and interface."""
    entry = {
        "address": ip_addr,
        **_build_interface_entry(iface),
        "device_status": iface["device"]["status"]["name"],
    }
    return entry


def _get_reservations_for_prefix(
    all_reserved_ips: list[dict[str, Any]],
    prefix_entry: dict[str, Any],
    family: int,
    is_aggregate_managed: bool | None,
) -> list[dict[str, Any]]:
    """Build reservations list for a prefix."""
    reservations = []
    for reserved_ip in all_reserved_ips:
        if reserved_ip["ip_version"] != family:
            continue
        if reserved_ip["parent"]["id"] != prefix_entry["id"]:
            continue

        ip_addr = ipaddress.ip_interface(reserved_ip["address"]).ip
        iface = _validate_reserved_ip_interfaces(reserved_ip)

        config_manager_device_status = iface["device"].get("configmanagerdevicestatus")
        if not _passes_ztp_aggregate_filter(config_manager_device_status, is_aggregate_managed):
            if config_manager_device_status and not config_manager_device_status.get(
                "ztp_enabled", True
            ):
                logger.warning(
                    "Reserved IP %s is not ZTP enabled, skipping",
                    reserved_ip["address"],
                )
            else:
                logger.warning(
                    "Reserved IP %s is aggregate status mismatch, skipping",
                    reserved_ip["address"],
                )
            continue

        mac_address = iface.get("mac_address")
        serial = iface["device"].get("serial")
        if not mac_address and not serial:
            DHCP_QUERY_ERRORS.labels(error_type="missing_mac_serial").inc()
            raise QueryException(
                f"Interface {iface['name']} on IP {reserved_ip['address']} "
                "has no MAC address or serial number"
            )

        reservations.append(_build_reservation_entry(reserved_ip, iface, ip_addr))
    return reservations


class NautobotClient(BaseNautobotClient):
    """Async Nautobot GraphQL Client for DHCP service.

    Extends the common aiohttp-based NautobotClient with DHCP-specific
    methods for loading DHCP configuration data from Nautobot.
    """

    def __init__(
        self,
        nautobot_url: str,
        token: str,
        verify: bool | str = True,
    ) -> None:
        """Initialize Nautobot client.

        Args:
            nautobot_url: Base URL for Nautobot instance
            token: API token for authentication
            verify: SSL verification - True (default), False (disable), or str (path to CA cert)
        """
        super().__init__(
            nautobot_url=nautobot_url,
            token=token,
            verify=verify,
            timeout=60,  # DHCP queries can be slow
        )

    async def load_site_dhcp_options(self) -> Any:
        """Load site DHCP options."""
        with open(f"{QUERY_PATH}/site_dhcp_options.graphql", encoding="utf-8") as f:
            query = f.read()
        rsp = await self.graphql_query(query=query)
        config_contexts = rsp["data"].get("config_contexts", [])
        if config_contexts:
            return config_contexts[0].get("data", {})
        return {}

    async def load_dhcp_contexts(
        self, is_aggregate_managed: bool | None = None
    ) -> dict[str, dict[str, Any]]:
        """Load all devices eligible for ZTP, filtered by aggregate management."""
        with open(f"{QUERY_PATH}/dhcp_contexts.graphql", encoding="utf-8") as f:
            query = f.read()

        variables: dict[str, Any] = {}
        variables["is_aggregate_managed"] = is_aggregate_managed
        rsp = await self.graphql_query(query=query, variables=variables)
        return {
            entry["device"]["id"]: entry["device"]["config_context"]
            for entry in rsp["data"]["config_manager_devices"]
        }

    async def load_static_data(self) -> list[dict[str, Any]]:
        """Load static data from config contexts."""
        with open(f"{QUERY_PATH}/static_dhcp_data.graphql", encoding="utf-8") as f:
            query = f.read()
        rsp = await self.graphql_query(query=query)
        return [entry["data"] for entry in rsp["data"].get("config_contexts", [])]

    async def load_auto_dhcp_subnets(
        self, family: int = 4, is_aggregate_managed: bool | None = None
    ) -> list[dict[str, Any]]:
        """Load DHCP subnets using single combined query and join in code."""
        with open(f"{QUERY_PATH}/auto_dhcp_subnets.graphql", encoding="utf-8") as f:
            query = f.read()
        rsp = await self.graphql_query(query=query)

        prefixes = rsp["data"].get("prefixes", [])
        if not prefixes:
            return []

        all_pool_ips = rsp["data"].get("pool_ips", [])
        all_reserved_ips = rsp["data"].get("reserved_ips", [])

        subnets = []
        for prefix_entry in prefixes:
            if prefix_entry["ip_version"] != family:
                continue

            prefix = ipaddress.ip_network(prefix_entry["prefix"])
            gateway_ip = _get_gateway_ip(prefix_entry, prefix)
            pool_ips, option_candidates = _get_pool_ips_and_candidates(
                all_pool_ips, prefix_entry, family, is_aggregate_managed
            )
            reservations = _get_reservations_for_prefix(
                all_reserved_ips, prefix_entry, family, is_aggregate_managed
            )

            subnets.append(
                {
                    "prefix": prefix,
                    "gateway": ipaddress.ip_address(gateway_ip),
                    "id": prefix_entry["id"],
                    "pool_ips": pool_ips,
                    "option_candidates": option_candidates,
                    "reservations": reservations,
                }
            )
        return subnets
