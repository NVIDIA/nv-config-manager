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
"""Validation tests for development mock topology source data."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
MOCK_TOPOLOGY_CONTEXT = PROJECT_ROOT / "development" / "mock_topology" / "context"
MOCK_TOPOLOGY_DESIGNS = PROJECT_ROOT / "development" / "mock_topology" / "jobs" / "designs"


def test_cumulus_mock_devices_define_explicit_ztp_identifiers() -> None:
    missing_eth0_mac = []
    missing_serial = []

    for path in sorted(MOCK_TOPOLOGY_CONTEXT.glob("*/devices/*.json")):
        with path.open() as f:
            device = json.load(f).get("data", {}).get("device") or {}

        platform_name = (device.get("platform") or {}).get("name", "")
        if "Cumulus" not in platform_name:
            continue

        if not device.get("serial"):
            missing_serial.append(f"{path.name}:{device.get('name')}")

        eth0 = next(
            (interface for interface in device.get("interfaces", []) if interface.get("name") == "eth0"),
            None,
        )
        if not eth0 or not eth0.get("mac_address"):
            missing_eth0_mac.append(f"{path.name}:{device.get('name')}")

    assert missing_serial == []
    assert missing_eth0_mac == []


def test_air_trial_cumulus_serials_match_eth0_mac_addresses() -> None:
    mismatches = []

    for path in sorted((MOCK_TOPOLOGY_CONTEXT / "air_trial" / "devices").glob("*.json")):
        with path.open() as f:
            device = json.load(f).get("data", {}).get("device") or {}

        platform_name = (device.get("platform") or {}).get("name", "")
        if "Cumulus" not in platform_name:
            continue

        eth0 = next(
            (interface for interface in device.get("interfaces", []) if interface.get("name") == "eth0"),
            {},
        )
        if device.get("serial") != eth0.get("mac_address"):
            mismatches.append(f"{path.name}:{device.get('name')}")

    assert mismatches == []


def test_cumulus_mock_devices_define_intended_firmware() -> None:
    missing_firmware = []

    for path in sorted(MOCK_TOPOLOGY_CONTEXT.glob("*/devices/*.json")):
        with path.open() as f:
            device = json.load(f).get("data", {}).get("device") or {}

        platform_name = (device.get("platform") or {}).get("name", "")
        if "Cumulus" not in platform_name:
            continue

        firmware = (
            device.get("config_context", {}).get("intended-firmware", {}).get("version")
        )
        if not firmware:
            missing_firmware.append(f"{path.name}:{device.get('name')}")

    assert missing_firmware == []


def test_mock_topology_templates_quote_string_identifiers() -> None:
    interfaces_template = (MOCK_TOPOLOGY_DESIGNS / "interfaces.yaml.j2").read_text()
    devices_template = (MOCK_TOPOLOGY_DESIGNS / "devices.yaml.j2").read_text()

    assert 'mac_address: "{{ intf.mac_address }}"' in interfaces_template
    assert 'serial: "{{ device.serial }}"' in devices_template
    assert "local_config_context_data" in devices_template


def test_ip_address_templates_use_topology_namespace() -> None:
    ip_addresses_template = (MOCK_TOPOLOGY_DESIGNS / "ip_addresses.yaml.j2").read_text()

    assert '"!create_or_update:parent__namespace__name": {{ global_defaults.namespace }}' in ip_addresses_template


def test_role_design_does_not_replace_content_type_memberships() -> None:
    roles_template = (MOCK_TOPOLOGY_DESIGNS / "roles.yaml.j2").read_text()

    assert "content_types:" not in roles_template


def test_managed_devices_template_allows_devices_without_platform() -> None:
    managed_devices_template = (MOCK_TOPOLOGY_DESIGNS / "managed_devices.yaml.j2").read_text()

    assert "device.platform is defined" in managed_devices_template
