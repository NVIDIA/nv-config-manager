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
"""Tests for AIR topology generation from mock_topology context."""

from __future__ import annotations

from typing import Any

from nv_config_manager_installer.air_sim.context_topology import (
    build_site_design_from_mock_context,
)


def _devices_by_name(site_design: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {device["name"]: device for device in site_design["devices"]}


def test_air_trial_builds_devices_and_explicit_eth0_macs() -> None:
    site_design = build_site_design_from_mock_context("air_trial", "demo")

    devices = _devices_by_name(site_design)
    assert "oob-mgmt-server" in devices
    assert len(devices) >= 6

    cumulus_names = {
        device["name"]
        for device in site_design["devices"]
        if "Cumulus" in device.get("platform", "")
    }
    assert cumulus_names

    eth0_macs = {
        interface["device"]: interface.get("mac_address")
        for interface in site_design["interfaces"]
        if interface["device"] in cumulus_names and interface["name"] == "eth0"
    }
    assert set(eth0_macs) == cumulus_names
    assert all(isinstance(mac, str) and mac for mac in eth0_macs.values())


def test_air_superpod_builds_non_empty_topology_source() -> None:
    site_design = build_site_design_from_mock_context("air_superpod", "demo")

    assert site_design["devices"]
    assert site_design["interfaces"]
    assert site_design["ip_addresses"]
    assert site_design["cabling_assignments"]["connections"]
    assert "oob-mgmt-server" in _devices_by_name(site_design)
    assert "bgp" not in _devices_by_name(site_design)["oob-mgmt-server"][
        "local_config_context_data"
    ]
