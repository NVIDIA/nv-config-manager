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

import logging
import time

import pytest

from nv_config_manager.dhcp.kea import IpVersion, KeaException
from nv_config_manager.dhcp.lease_dashboard import (
    LeaseRecord,
    build_lease_dashboard,
    build_lease_list,
    build_pool_list,
    build_reservation_list,
    filter_lease_records,
    filter_pool_records,
    filter_reservation_records,
)


def dashboard_payloads() -> tuple[list[dict], list[dict], list[dict]]:
    """Return representative KEA responses for dashboard tests."""
    now = int(time.time())
    config = [
        {
            "result": 0,
            "arguments": {
                "Dhcp4": {
                    "reservations": [
                        {
                            "hostname": "switch-01",
                            "hw-address": "02:00:00:00:00:01",
                            "ip-address": "10.0.0.2",
                        }
                    ],
                    "subnet4": [
                        {
                            "id": 7,
                            "subnet": "10.0.0.0/24",
                            "pools": [
                                {"pool": "10.0.0.10-10.0.0.19"},
                                {"pool": "10.0.1.0/30"},
                            ],
                            "reservations": [
                                {
                                    "hostname": "switch-02",
                                    "client-id": "01:02:03:04",
                                    "ip-address": "10.0.0.3",
                                }
                            ],
                        }
                    ],
                }
            },
        }
    ]
    leases = [
        {
            "result": 0,
            "arguments": {
                "leases": [
                    {
                        "cltt": now - 60,
                        "hostname": "active-switch",
                        "hw-address": "02:00:00:00:00:10",
                        "ip-address": "10.0.0.10",
                        "state": 0,
                        "subnet-id": 7,
                        "valid-lft": 3600,
                    },
                    {
                        "cltt": now - 7200,
                        "hostname": "expired-switch",
                        "ip-address": "10.0.0.11",
                        "state": 0,
                        "subnet-id": 7,
                        "valid-lft": 3600,
                    },
                    {
                        "cltt": now - 60,
                        "hostname": "declined-switch",
                        "ip-address": "10.0.0.12",
                        "state": 1,
                        "subnet-id": 7,
                        "valid-lft": 3600,
                    },
                ]
            },
        }
    ]
    statistics = [
        {
            "result": 0,
            "arguments": {
                "assigned-addresses": [[3, "2026-07-10 00:00:00"]],
            },
        }
    ]
    return config, leases, statistics


def test_build_lease_dashboard() -> None:
    """Build a dashboard summary from configuration and statistics."""
    config, leases, statistics = dashboard_payloads()

    dashboard = build_lease_dashboard(config, statistics)

    assert dashboard.active_lease_count == 3
    assert dashboard.reservation_count == 2
    assert dashboard.pool_count == 2
    reservations = build_reservation_list(config, ip_version=IpVersion.V4)
    assert len(reservations) == 2
    assert reservations[0].identifier_type == "hw-address"
    assert reservations[0].subnet is None
    lease_records = build_lease_list(config, leases, ip_version=IpVersion.V4)
    assert len(lease_records) == 1
    pools = build_pool_list(config, ip_version=IpVersion.V4)
    assert [(pool.subnet, pool.pool) for pool in pools] == [
        ("10.0.0.0/24", "10.0.0.10-10.0.0.19"),
        ("10.0.0.0/24", "10.0.1.0/30"),
    ]


def test_build_lease_dashboard_counts_leases_from_unconfigured_subnets() -> None:
    """Keep active lease totals independent from configured pool inventory."""
    config, _, statistics = dashboard_payloads()
    stats = statistics[0]["arguments"]
    stats.pop("assigned-addresses")
    stats["subnet[7].assigned-addresses"] = [[3, "2026-07-10 00:00:00"]]
    stats["subnet[99].assigned-addresses"] = [[997, "2026-07-10 00:00:00"]]

    dashboard = build_lease_dashboard(config, statistics)

    assert dashboard.active_lease_count == 1000


def test_build_lease_list_logs_malformed_lease(caplog: pytest.LogCaptureFixture) -> None:
    """Log malformed KEA rows at debug level while keeping the response safe."""
    config, leases, _ = dashboard_payloads()
    malformed_row = {
        "cltt": int(time.time()) - 60,
        "ip-address": "not-an-address",
        "state": 0,
        "subnet-id": 7,
        "valid-lft": 3600,
    }
    leases[0]["arguments"]["leases"].append(malformed_row)

    with caplog.at_level(logging.DEBUG, logger="nv_config_manager.dhcp.lease_dashboard"):
        records = build_lease_list(config, leases, ip_version=IpVersion.V4)

    assert len(records) == 1
    assert "Skipping malformed KEA lease row" in caplog.text
    assert "not-an-address" in caplog.text


@pytest.mark.parametrize("search", ["020000000010", "0200.0000.0010"])
def test_filter_lease_records_normalizes_mac_addresses(search: str) -> None:
    """Match complete MAC addresses independently of common separators."""
    lease = LeaseRecord(
        ip_address="10.0.0.10",
        hostname="leaf-01",
        hw_address="02:00:00:00:00:10",
        state=0,
        cltt=int(time.time()) - 60,
        valid_lft=3600,
        expires_at=None,
    )

    assert filter_lease_records([lease], search) == [lease]


@pytest.mark.parametrize("search", ["020000000001", "0200.0000.0001"])
def test_filter_reservation_records_normalizes_mac_addresses(search: str) -> None:
    """Match reservation identifiers independently of common MAC separators."""
    config, _, _ = dashboard_payloads()
    reservations = build_reservation_list(config, ip_version=IpVersion.V4)

    assert filter_reservation_records(reservations, search) == [reservations[0]]


def test_filter_pool_records_matches_subnet_and_range() -> None:
    """Match configured pools by their subnet or range."""
    config, _, _ = dashboard_payloads()
    pools = build_pool_list(config, ip_version=IpVersion.V4)

    assert filter_pool_records(pools, "10.0.1.0/30") == [pools[1]]


def test_build_ipv6_lease_dashboard() -> None:
    """Normalize DHCPv6 leases, reservations, prefixes, and configured pools."""
    now = int(time.time())
    config = [
        {
            "result": 0,
            "arguments": {
                "Dhcp6": {
                    "subnet6": [
                        {
                            "id": 9,
                            "subnet": "2001:db8:1::/64",
                            "pools": [{"pool": "2001:db8:1::10-2001:db8:1::1f"}],
                            "reservations": [
                                {
                                    "duid": "00:01:00:01:aa:bb:cc:dd",
                                    "hostname": "switch-v6",
                                    "ip-addresses": ["2001:db8:1::2"],
                                }
                            ],
                        }
                    ]
                }
            },
        }
    ]
    leases = [
        {
            "result": 0,
            "arguments": {
                "leases": [
                    {
                        "cltt": now - 60,
                        "duid": "00:01:00:01:11:22:33:44",
                        "hostname": "active-v6",
                        "ip-address": "2001:db8:1::10",
                        "state": 0,
                        "subnet-id": 9,
                        "valid-lft": 3600,
                    }
                ]
            },
        }
    ]
    statistics = [
        {
            "result": 0,
            "arguments": {
                "assigned-nas": [[1, "2026-07-10 00:00:00"]],
            },
        }
    ]

    dashboard = build_lease_dashboard(config, statistics, ip_version=IpVersion.V6)
    lease_records = build_lease_list(config, leases, ip_version=IpVersion.V6)
    reservations = build_reservation_list(config, ip_version=IpVersion.V6)
    pools = build_pool_list(config, ip_version=IpVersion.V6)

    assert str(lease_records[0].ip_address) == "2001:db8:1::10"
    assert lease_records[0].duid == "00:01:00:01:11:22:33:44"
    assert lease_records[0].subnet == "2001:db8:1::/64"
    assert dashboard.reservation_count == 1
    assert str(reservations[0].ip_address) == "2001:db8:1::2"
    assert reservations[0].identifier_type == "duid"
    assert pools[0].pool == "2001:db8:1::10-2001:db8:1::1f"


def test_build_lease_dashboard_rejects_kea_error() -> None:
    """Surface logical KEA command failures to the API route."""
    _, _, statistics = dashboard_payloads()

    with pytest.raises(KeaException, match="config-get failed: configuration unavailable"):
        build_lease_dashboard(
            [{"result": 1, "text": "configuration unavailable"}],
            statistics,
        )
