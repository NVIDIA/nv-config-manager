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

from datetime import UTC, datetime
from ipaddress import IPv4Address, ip_address, ip_network
from typing import Any

from pydantic import BaseModel

from nv_config_manager.dhcp.kea import KeaException


class LeaseRecord(BaseModel):
    """Active IPv4 lease returned by KEA."""

    ip_address: IPv4Address
    hostname: str = ""
    hw_address: str | None = None
    client_id: str | None = None
    subnet_id: int
    state: int
    cltt: int
    valid_lft: int
    expires_at: datetime | None


class ReservationRecord(BaseModel):
    """Configured IPv4 reservation."""

    ip_address: IPv4Address | None = None
    hostname: str = ""
    identifier_type: str | None = None
    identifier: str | None = None
    subnet_id: int | None = None


class PoolUsage(BaseModel):
    """Current allocation statistics for a configured IPv4 pool."""

    subnet_id: int
    subnet: str
    pool: str
    assigned: int
    total: int
    utilization: float


class LeaseDashboardResponse(BaseModel):
    """Lease, reservation, and pool data used by the splash-page dashboard."""

    active_lease_count: int
    reservation_count: int
    assigned_address_count: int
    pool_address_count: int
    leases_truncated: bool
    reservations_truncated: bool
    leases: list[LeaseRecord]
    reservations: list[ReservationRecord]
    pools: list[PoolUsage]


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


def _pool_capacity(pool: str) -> int:
    """Return the IPv4 capacity represented by a range or network."""
    try:
        if "-" in pool:
            start_text, end_text = (part.strip() for part in pool.split("-", maxsplit=1))
            start = ip_address(start_text)
            end = ip_address(end_text)
            if not isinstance(start, IPv4Address) or not isinstance(end, IPv4Address):
                return 0
            return max(int(end) - int(start) + 1, 0)

        network = ip_network(pool.strip(), strict=False)
        return network.num_addresses if network.version == 4 else 0
    except ValueError:
        return 0


def _expires_at(cltt: int, valid_lft: int) -> datetime | None:
    """Convert a KEA lease lifetime into an absolute expiry time."""
    if valid_lft >= 0xFFFFFFFF:
        return None
    try:
        return datetime.fromtimestamp(cltt + valid_lft, tz=UTC)
    except (OSError, OverflowError, ValueError):
        return None


def _lease_records(raw_leases: Any) -> list[LeaseRecord]:
    """Normalize and sort active, unexpired IPv4 leases."""
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
            leases.append(
                LeaseRecord(
                    ip_address=raw_lease["ip-address"],
                    hostname=str(raw_lease.get("hostname", "")),
                    hw_address=raw_lease.get("hw-address"),
                    client_id=raw_lease.get("client-id"),
                    subnet_id=int(raw_lease["subnet-id"]),
                    state=state,
                    cltt=cltt,
                    valid_lft=valid_lft,
                    expires_at=_expires_at(cltt, valid_lft),
                )
            )
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(leases, key=lambda lease: int(lease.ip_address))


def _reservation_records(dhcp4: dict[str, Any]) -> list[ReservationRecord]:
    """Flatten global and subnet reservations into dashboard records."""
    raw_reservations: list[tuple[dict[str, Any], int | None]] = []
    for reservation in dhcp4.get("reservations", []):
        if isinstance(reservation, dict):
            raw_reservations.append((reservation, None))

    for subnet in dhcp4.get("subnet4", []):
        if not isinstance(subnet, dict):
            continue
        subnet_id = subnet.get("id")
        for reservation in subnet.get("reservations", []):
            if isinstance(reservation, dict):
                raw_reservations.append((reservation, subnet_id))

    records: list[ReservationRecord] = []
    for reservation, subnet_id in raw_reservations:
        identifier_type = next(
            (
                key
                for key in ("hw-address", "client-id", "circuit-id", "flex-id")
                if reservation.get(key)
            ),
            None,
        )
        raw_ip = reservation.get("ip-address")
        try:
            reservation_ip = IPv4Address(raw_ip) if raw_ip else None
        except ValueError:
            reservation_ip = None
        records.append(
            ReservationRecord(
                ip_address=reservation_ip,
                hostname=str(reservation.get("hostname", "")),
                identifier_type=identifier_type,
                identifier=str(reservation[identifier_type]) if identifier_type else None,
                subnet_id=int(subnet_id) if subnet_id is not None else None,
            )
        )

    return sorted(
        records,
        key=lambda reservation: (
            reservation.ip_address is None,
            int(reservation.ip_address) if reservation.ip_address else 0,
        ),
    )


def _pool_usage(dhcp4: dict[str, Any], statistics: dict[str, Any]) -> list[PoolUsage]:
    """Combine configured pools with their current KEA statistics."""
    pools: list[PoolUsage] = []
    for subnet in dhcp4.get("subnet4", []):
        if not isinstance(subnet, dict) or "id" not in subnet:
            continue
        subnet_id = int(subnet["id"])
        subnet_name = str(subnet.get("subnet", ""))
        for pool_index, pool_config in enumerate(subnet.get("pools", [])):
            if not isinstance(pool_config, dict) or not pool_config.get("pool"):
                continue
            pool_name = str(pool_config["pool"])
            prefix = f"subnet[{subnet_id}].pool[{pool_index}]"
            assigned = _stat_value(statistics, f"{prefix}.assigned-addresses") or 0
            total = _stat_value(statistics, f"{prefix}.total-addresses")
            if total is None:
                total = _pool_capacity(pool_name)
            utilization = round((assigned / total * 100) if total else 0.0, 1)
            pools.append(
                PoolUsage(
                    subnet_id=subnet_id,
                    subnet=subnet_name,
                    pool=pool_name,
                    assigned=assigned,
                    total=total,
                    utilization=utilization,
                )
            )
    return pools


def build_lease_dashboard(
    config_payload: list[dict[str, Any]],
    lease_payload: list[dict[str, Any]],
    statistics_payload: list[dict[str, Any]],
    *,
    limit: int,
) -> LeaseDashboardResponse:
    """Convert KEA command responses into the bounded dashboard response."""
    config = _response_arguments(config_payload, "config-get")
    dhcp4 = config.get("Dhcp4")
    if not isinstance(dhcp4, dict):
        raise KeaException("KEA config-get response is missing Dhcp4")

    lease_arguments = _response_arguments(lease_payload, "lease4-get-page", allow_empty=True)
    statistics = _response_arguments(statistics_payload, "statistic-get-all")

    leases = _lease_records(lease_arguments.get("leases", []))
    reservations = _reservation_records(dhcp4)
    pools = _pool_usage(dhcp4, statistics)
    assigned_count = _stat_value(statistics, "assigned-addresses")
    if assigned_count is None:
        assigned_count = sum(pool.assigned for pool in pools)
    active_lease_count = max(assigned_count, len(leases))
    pool_address_count = sum(pool.total for pool in pools)

    return LeaseDashboardResponse(
        active_lease_count=active_lease_count,
        reservation_count=len(reservations),
        assigned_address_count=assigned_count,
        pool_address_count=pool_address_count,
        leases_truncated=active_lease_count > len(leases),
        reservations_truncated=len(reservations) > limit,
        leases=leases[:limit],
        reservations=reservations[:limit],
        pools=pools,
    )
