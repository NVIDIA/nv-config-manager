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
"""Build the operator-facing DHCP lease dashboard response."""

from __future__ import annotations

import logging
from bisect import bisect_right
from dataclasses import dataclass
from datetime import UTC, datetime
from ipaddress import ip_address, ip_network
from typing import Any

from pydantic import BaseModel, IPvAnyAddress

from nv_config_manager.dhcp.kea import IpVersion, KeaException

LOG = logging.getLogger(__name__)


class LeaseRecord(BaseModel):
    """Active lease returned by the DHCP service."""

    ip_address: IPvAnyAddress
    hostname: str = ""
    hw_address: str | None = None
    client_id: str | None = None
    duid: str | None = None
    subnet: str | None = None
    state: int
    cltt: int
    valid_lft: int
    expires_at: datetime | None


class ReservationRecord(BaseModel):
    """Configured address reservation."""

    ip_address: IPvAnyAddress | None = None
    hostname: str = ""
    identifier_type: str | None = None
    identifier: str | None = None
    subnet: str | None = None


class PoolUsage(BaseModel):
    """Current allocation statistics for a configured address pool."""

    subnet: str
    pool: str
    assigned: int
    total: int
    utilization: float


class LeaseDashboardResponse(BaseModel):
    """Lease, reservation, and pool summary used by the dashboard."""

    active_lease_count: int
    reservation_count: int
    assigned_address_count: int
    pool_count: int
    pool_address_count: int


class LeasePageResponse(BaseModel):
    """Bounded page of normalized leases."""

    leases: list[LeaseRecord]
    next_cursor: str | None = None


class ReservationPageResponse(BaseModel):
    """Bounded page of normalized reservations."""

    reservations: list[ReservationRecord]
    total_count: int
    next_cursor: str | None = None


class PoolPageResponse(BaseModel):
    """Bounded page of configured pool usage."""

    pools: list[PoolUsage]
    total_count: int
    next_cursor: str | None = None


@dataclass(frozen=True)
class _PoolDefinition:
    """Preparsed pool metadata used for fast lease assignment."""

    subnet: str
    name: str
    statistics_prefix: str
    bounds: tuple[int, int, int] | None


def _response_arguments(
    payload: list[dict[str, Any]], command: str, *, allow_empty: bool = False
) -> dict[str, Any]:
    """Validate a logical KEA response and return its arguments."""
    if not payload or not isinstance(payload[0], dict):
        raise KeaException(f"KEA returned an invalid {command} response")

    response = payload[0]
    result = response.get("result")
    if allow_empty and result == 3:
        return {}
    if result != 0:
        message = response.get("text", "No message provided")
        raise KeaException(f"KEA {command} failed: {message}")

    arguments = response.get("arguments", {})
    if not isinstance(arguments, dict):
        raise KeaException(f"KEA returned invalid {command} arguments")
    return arguments


def _stat_value(statistics: dict[str, Any], name: str) -> int | None:
    """Return the latest integer value for a KEA statistic."""
    samples = statistics.get(name)
    if not isinstance(samples, list) or not samples:
        return None
    latest = samples[0]
    if not isinstance(latest, list) or not latest:
        return None
    value = latest[0]
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return int(value)


def _pool_bounds(pool: str) -> tuple[int, int, int] | None:
    """Return a pool's IP version and inclusive integer bounds."""
    try:
        if "-" in pool:
            start_text, end_text = (part.strip() for part in pool.split("-", maxsplit=1))
            start = ip_address(start_text)
            end = ip_address(end_text)
            if start.version != end.version:
                return None
            if int(start) > int(end):
                return None
            return start.version, int(start), int(end)

        network = ip_network(pool.strip(), strict=False)
        return network.version, int(network.network_address), int(network.broadcast_address)
    except ValueError:
        return None


def _pool_capacity(pool: str) -> int:
    """Return the address capacity represented by a range or network."""
    bounds = _pool_bounds(pool)
    return bounds[2] - bounds[1] + 1 if bounds is not None else 0


def _active_pool_assignments(
    pools: list[_PoolDefinition],
    leases: list[LeaseRecord],
) -> list[int]:
    """Count active leases by pool using one binary lookup per lease."""
    intervals_by_subnet: dict[tuple[str, int], list[tuple[int, int, int]]] = {}
    for pool_index, pool in enumerate(pools):
        if pool.bounds is None:
            continue
        version, start, end = pool.bounds
        intervals_by_subnet.setdefault((pool.subnet, version), []).append((start, end, pool_index))

    lookups: dict[
        tuple[str, int],
        tuple[list[int], list[tuple[int, int, int]]],
    ] = {}
    for key, intervals in intervals_by_subnet.items():
        sorted_intervals = sorted(intervals)
        lookups[key] = (
            [interval[0] for interval in sorted_intervals],
            sorted_intervals,
        )

    assigned = [0] * len(pools)
    for lease in leases:
        lookup = lookups.get((lease.subnet or "", lease.ip_address.version))
        if lookup is None:
            continue
        starts, intervals = lookup
        interval_index = bisect_right(starts, int(lease.ip_address)) - 1
        if interval_index < 0:
            continue
        _, end, pool_index = intervals[interval_index]
        if int(lease.ip_address) <= end:
            assigned[pool_index] += 1
    return assigned


def _expires_at(cltt: int, valid_lft: int) -> datetime | None:
    """Convert a KEA lease lifetime into an absolute expiry time."""
    if valid_lft >= 0xFFFFFFFF:
        return None
    try:
        return datetime.fromtimestamp(cltt + valid_lft, tz=UTC)
    except (OSError, OverflowError, ValueError):
        return None


def _subnet_prefixes(dhcp_config: dict[str, Any], ip_version: IpVersion) -> dict[int, str]:
    """Map KEA's internal subnet identifiers to operator-facing prefixes."""
    prefixes: dict[int, str] = {}
    for subnet in dhcp_config.get(f"subnet{ip_version}", []):
        if not isinstance(subnet, dict) or "id" not in subnet:
            continue
        try:
            prefixes[int(subnet["id"])] = str(subnet.get("subnet", ""))
        except (TypeError, ValueError):
            continue
    return prefixes


def _lease_records(raw_leases: Any, subnet_prefixes: dict[int, str]) -> list[LeaseRecord]:
    """Normalize and sort active, unexpired leases."""
    if not isinstance(raw_leases, list):
        return []

    now = int(datetime.now(tz=UTC).timestamp())
    leases: list[LeaseRecord] = []
    for raw_lease in raw_leases:
        if not isinstance(raw_lease, dict):
            continue
        try:
            cltt = int(raw_lease.get("cltt", 0))
            valid_lft = int(raw_lease.get("valid-lft", 0))
            state = int(raw_lease.get("state", 0))
            if state != 0 or cltt + valid_lft <= now:
                continue
            subnet_id = int(raw_lease["subnet-id"])
            leases.append(
                LeaseRecord(
                    ip_address=raw_lease["ip-address"],
                    hostname=str(raw_lease.get("hostname", "")),
                    hw_address=raw_lease.get("hw-address"),
                    client_id=raw_lease.get("client-id"),
                    duid=raw_lease.get("duid"),
                    subnet=subnet_prefixes.get(subnet_id),
                    state=state,
                    cltt=cltt,
                    valid_lft=valid_lft,
                    expires_at=_expires_at(cltt, valid_lft),
                )
            )
        except (KeyError, TypeError, ValueError) as exc:
            LOG.debug("Skipping malformed KEA lease row %r: %s", raw_lease, exc)
            continue
    return sorted(leases, key=lambda lease: int(lease.ip_address))


def filter_lease_records(leases: list[LeaseRecord], search: str | None) -> list[LeaseRecord]:
    """Filter normalized leases using the dashboard's user-facing search fields."""
    query, mac_query = _normalized_search(search)
    if not query:
        return leases

    def matches(lease: LeaseRecord) -> bool:
        return _matches_search(
            (
                lease.ip_address,
                lease.hostname,
                lease.hw_address,
                lease.client_id,
                lease.duid,
                lease.subnet,
            ),
            query,
            mac_query,
        )

    return [lease for lease in leases if matches(lease)]


def _normalized_search(search: str | None) -> tuple[str, str | None]:
    """Return a normalized query and complete separator-free MAC when present."""
    query = (search or "").strip().lower()
    compact_query = query.translate(str.maketrans("", "", ":.-"))
    mac_query = (
        compact_query
        if len(compact_query) == 12
        and all(character in "0123456789abcdef" for character in compact_query)
        else None
    )
    return query, mac_query


def _matches_search(
    values: tuple[Any, ...],
    query: str,
    mac_query: str | None,
) -> bool:
    """Return whether any value contains the query or the same complete MAC."""
    for value in values:
        normalized = str(value or "").lower()
        if query in normalized:
            return True
        compact_value = normalized.translate(str.maketrans("", "", ":.-"))
        if mac_query is not None and compact_value == mac_query:
            return True
    return False


def lease_page_details(
    lease_payload: list[dict[str, Any]],
    *,
    ip_version: IpVersion,
) -> tuple[int, str | None]:
    """Return a KEA page's row count and address cursor."""
    arguments = _response_arguments(
        lease_payload,
        f"lease{ip_version}-get-page",
        allow_empty=True,
    )
    raw_leases = arguments.get("leases", [])
    if not isinstance(raw_leases, list):
        raise KeaException(f"KEA returned invalid lease{ip_version}-get-page leases")
    if not raw_leases:
        return 0, None

    last_lease = raw_leases[-1]
    if not isinstance(last_lease, dict):
        raise KeaException(f"KEA returned an invalid lease{ip_version}-get-page cursor")
    try:
        last_address = ip_address(last_lease["ip-address"])
    except (KeyError, TypeError, ValueError) as exc:
        raise KeaException(f"KEA returned an invalid lease{ip_version}-get-page cursor") from exc
    if last_address.version != ip_version:
        raise KeaException(f"KEA returned a mismatched lease{ip_version}-get-page cursor")
    return len(raw_leases), str(last_address)


def _reservation_ip(reservation: dict[str, Any]) -> IPvAnyAddress | None:
    """Return the first configured address from either DHCP reservation format."""
    raw_ip = reservation.get("ip-address")
    if raw_ip is None:
        raw_ips = reservation.get("ip-addresses")
        raw_ip = raw_ips[0] if isinstance(raw_ips, list) and raw_ips else None
    try:
        return ip_address(raw_ip) if raw_ip else None
    except ValueError:
        return None


def _reservation_records(
    dhcp_config: dict[str, Any],
    ip_version: IpVersion,
) -> list[ReservationRecord]:
    """Flatten global and subnet reservations into dashboard records."""
    raw_reservations: list[tuple[dict[str, Any], str | None]] = []
    for reservation in dhcp_config.get("reservations", []):
        if isinstance(reservation, dict):
            raw_reservations.append((reservation, None))

    for subnet in dhcp_config.get(f"subnet{ip_version}", []):
        if not isinstance(subnet, dict):
            continue
        subnet_prefix = str(subnet.get("subnet", "")) or None
        for reservation in subnet.get("reservations", []):
            if isinstance(reservation, dict):
                raw_reservations.append((reservation, subnet_prefix))

    records: list[ReservationRecord] = []
    for reservation, subnet_prefix in raw_reservations:
        identifier_type = next(
            (
                key
                for key in ("hw-address", "client-id", "duid", "circuit-id", "flex-id")
                if reservation.get(key)
            ),
            None,
        )
        records.append(
            ReservationRecord(
                ip_address=_reservation_ip(reservation),
                hostname=str(reservation.get("hostname", "")),
                identifier_type=identifier_type,
                identifier=str(reservation[identifier_type]) if identifier_type else None,
                subnet=subnet_prefix,
            )
        )

    return sorted(
        records,
        key=lambda reservation: (
            reservation.ip_address is None,
            int(reservation.ip_address) if reservation.ip_address else 0,
        ),
    )


def filter_reservation_records(
    reservations: list[ReservationRecord],
    search: str | None,
) -> list[ReservationRecord]:
    """Filter reservations using their user-facing identifier fields."""
    query, mac_query = _normalized_search(search)
    if not query:
        return reservations

    return [
        reservation
        for reservation in reservations
        if _matches_search(
            (
                reservation.ip_address,
                reservation.hostname,
                reservation.identifier_type,
                reservation.identifier,
                reservation.subnet,
            ),
            query,
            mac_query,
        )
    ]


def _pool_usage(
    dhcp_config: dict[str, Any],
    statistics: dict[str, Any],
    ip_version: IpVersion,
    active_leases: list[LeaseRecord] | None = None,
) -> list[PoolUsage]:
    """Combine configured pools with their current KEA statistics."""
    pool_definitions: list[_PoolDefinition] = []
    assigned_stat = "assigned-addresses" if ip_version == 4 else "assigned-nas"
    total_stat = "total-addresses" if ip_version == 4 else "total-nas"
    for subnet in dhcp_config.get(f"subnet{ip_version}", []):
        if not isinstance(subnet, dict) or "id" not in subnet:
            continue
        subnet_id = int(subnet["id"])
        subnet_name = str(subnet.get("subnet", ""))
        for pool_index, pool_config in enumerate(subnet.get("pools", [])):
            if not isinstance(pool_config, dict) or not pool_config.get("pool"):
                continue
            pool_name = str(pool_config["pool"])
            pool_definitions.append(
                _PoolDefinition(
                    subnet=subnet_name,
                    name=pool_name,
                    statistics_prefix=f"subnet[{subnet_id}].pool[{pool_index}]",
                    bounds=_pool_bounds(pool_name),
                )
            )

    active_assignments = (
        _active_pool_assignments(pool_definitions, active_leases)
        if active_leases is not None
        else None
    )
    pools: list[PoolUsage] = []
    for pool_index, pool in enumerate(pool_definitions):
        assigned = (
            active_assignments[pool_index]
            if active_assignments is not None
            else _stat_value(statistics, f"{pool.statistics_prefix}.{assigned_stat}") or 0
        )
        total = _stat_value(statistics, f"{pool.statistics_prefix}.{total_stat}")
        if total is None:
            total = _pool_capacity(pool.name)
        utilization = round(min(assigned / total * 100, 100.0) if total else 0.0, 1)
        pools.append(
            PoolUsage(
                subnet=pool.subnet,
                pool=pool.name,
                assigned=assigned,
                total=total,
                utilization=utilization,
            )
        )
    return pools


def filter_pool_records(pools: list[PoolUsage], search: str | None) -> list[PoolUsage]:
    """Filter pools using their user-facing subnet and range fields."""
    query, mac_query = _normalized_search(search)
    if not query:
        return pools

    return [pool for pool in pools if _matches_search((pool.subnet, pool.pool), query, mac_query)]


def _dhcp_config(
    config_payload: list[dict[str, Any]],
    ip_version: IpVersion,
) -> dict[str, Any]:
    """Return the selected DHCP configuration from a KEA response."""
    config = _response_arguments(config_payload, "config-get")
    key = f"Dhcp{ip_version}"
    dhcp_config = config.get(key)
    if not isinstance(dhcp_config, dict):
        raise KeaException(f"KEA config-get response is missing {key}")
    return dhcp_config


def build_lease_list(
    config_payload: list[dict[str, Any]],
    lease_payload: list[dict[str, Any]],
    *,
    ip_version: IpVersion,
) -> list[LeaseRecord]:
    """Build normalized active leases from KEA configuration and lease responses."""
    dhcp_config = _dhcp_config(config_payload, ip_version)
    lease_arguments = _response_arguments(
        lease_payload,
        f"lease{ip_version}-get-page",
        allow_empty=True,
    )
    return _lease_records(
        lease_arguments.get("leases", []),
        _subnet_prefixes(dhcp_config, ip_version),
    )


def build_reservation_list(
    config_payload: list[dict[str, Any]],
    *,
    ip_version: IpVersion,
) -> list[ReservationRecord]:
    """Build normalized reservations from KEA configuration."""
    return _reservation_records(_dhcp_config(config_payload, ip_version), ip_version)


def build_pool_list(
    config_payload: list[dict[str, Any]],
    statistics_payload: list[dict[str, Any]],
    active_leases: list[LeaseRecord] | None,
    *,
    ip_version: IpVersion,
) -> list[PoolUsage]:
    """Build pool usage from active leases or KEA statistics when the scan is bounded."""
    dhcp_config = _dhcp_config(config_payload, ip_version)
    statistics = _response_arguments(statistics_payload, "statistic-get-all")
    return _pool_usage(dhcp_config, statistics, ip_version, active_leases)


def build_lease(
    config_payload: list[dict[str, Any]],
    lease_payload: list[dict[str, Any]],
    *,
    ip_version: IpVersion,
) -> LeaseRecord | None:
    """Build one normalized active lease, returning none when it is not found."""
    dhcp_config = _dhcp_config(config_payload, ip_version)
    lease_arguments = _response_arguments(
        lease_payload,
        f"lease{ip_version}-get",
        allow_empty=True,
    )
    raw_leases = lease_arguments.get("leases", []) if ip_version == IpVersion.V6 else []
    if ip_version == IpVersion.V4 and lease_arguments:
        raw_leases = [lease_arguments]
    records = _lease_records(raw_leases, _subnet_prefixes(dhcp_config, ip_version))
    return records[0] if records else None


def lease_deleted(delete_payload: list[dict[str, Any]], *, ip_version: IpVersion) -> bool:
    """Validate a KEA delete response and report whether a lease was found."""
    if delete_payload and delete_payload[0].get("result") == 3:
        return False
    _response_arguments(delete_payload, f"lease{ip_version}-del")
    return True


def build_lease_dashboard(
    config_payload: list[dict[str, Any]],
    statistics_payload: list[dict[str, Any]],
    *,
    ip_version: IpVersion = IpVersion.V4,
) -> LeaseDashboardResponse:
    """Convert KEA configuration and statistics into the dashboard summary."""
    dhcp_config = _dhcp_config(config_payload, ip_version)
    statistics = _response_arguments(statistics_payload, "statistic-get-all")

    reservations = _reservation_records(dhcp_config, ip_version)
    pools = _pool_usage(dhcp_config, statistics, ip_version)
    assigned_stat = "assigned-addresses" if ip_version == 4 else "assigned-nas"
    assigned_count = _stat_value(statistics, assigned_stat)
    if assigned_count is None:
        assigned_count = sum(pool.assigned for pool in pools)
    pool_address_count = sum(pool.total for pool in pools)

    return LeaseDashboardResponse(
        active_lease_count=assigned_count,
        reservation_count=len(reservations),
        assigned_address_count=assigned_count,
        pool_count=len(pools),
        pool_address_count=pool_address_count,
    )
