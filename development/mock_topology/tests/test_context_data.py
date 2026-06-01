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

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

MOCK_TOPOLOGY_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = MOCK_TOPOLOGY_ROOT.parents[1]
MOCK_TOPOLOGY_CONTEXT = MOCK_TOPOLOGY_ROOT / "context"
MOCK_TOPOLOGY_DESIGNS = MOCK_TOPOLOGY_ROOT / "jobs" / "designs"


def _load_device(path: Path) -> dict[str, Any]:
    with path.open() as f:
        return json.load(f).get("data", {}).get("device") or {}


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open() as f:
        return yaml.safe_load(f) or {}


def _interface_by_name(device: dict[str, Any], name: str) -> dict[str, Any]:
    return next(
        (interface for interface in device.get("interfaces", []) if interface.get("name") == name),
        {},
    )


def _devices_by_name(context_path: Path) -> dict[str, dict[str, Any]]:
    devices = {}
    for path in sorted((context_path / "devices").glob("*.json")):
        device = _load_device(path)
        if device.get("name"):
            devices[device["name"]] = device
    return devices


def test_cumulus_mock_devices_define_explicit_ztp_identifiers() -> None:
    missing_eth0_mac = []
    missing_serial = []

    for path in sorted(MOCK_TOPOLOGY_CONTEXT.glob("*/devices/*.json")):
        device = _load_device(path)

        platform_name = (device.get("platform") or {}).get("name", "")
        if "Cumulus" not in platform_name:
            continue

        if not device.get("serial"):
            missing_serial.append(f"{path.name}:{device.get('name')}")

        eth0 = _interface_by_name(device, "eth0")
        if not eth0.get("mac_address"):
            missing_eth0_mac.append(f"{path.name}:{device.get('name')}")

    assert missing_serial == []
    assert missing_eth0_mac == []


def test_air_trial_cumulus_serials_match_eth0_mac_addresses() -> None:
    mismatches = []

    for path in sorted((MOCK_TOPOLOGY_CONTEXT / "air_trial" / "devices").glob("*.json")):
        device = _load_device(path)

        platform_name = (device.get("platform") or {}).get("name", "")
        if "Cumulus" not in platform_name:
            continue

        eth0 = _interface_by_name(device, "eth0")
        if device.get("serial") != eth0.get("mac_address"):
            mismatches.append(f"{path.name}:{device.get('name')}")

    assert mismatches == []


def test_air_trial_keeps_only_oob_chain_as_dhcp_pool() -> None:
    oob_mleaf = _load_device(MOCK_TOPOLOGY_CONTEXT / "air_trial" / "devices" / "oob-mleaf-01.json")
    oob_uplink = _interface_by_name(oob_mleaf, "swp1")

    tan_leaf_pools = []
    for path in sorted((MOCK_TOPOLOGY_CONTEXT / "air_trial" / "devices").glob("tan-*.json")):
        device = _load_device(path)
        eth0 = _interface_by_name(device, "eth0")
        if eth0.get("dhcp_pool"):
            tan_leaf_pools.append(f"{path.name}:eth0")

    assert oob_uplink["dhcp_pool"] is True
    assert oob_uplink["ip_addresses"][0]["mask_length"] == 31
    assert tan_leaf_pools == []


def test_air_trial_tan_leaf_management_interfaces_use_vlan_subnet() -> None:
    wrong_masks = []

    for path in sorted((MOCK_TOPOLOGY_CONTEXT / "air_trial" / "devices").glob("tan-*.json")):
        device = _load_device(path)
        eth0 = _interface_by_name(device, "eth0")
        addresses = eth0.get("ip_addresses", [])
        if not addresses or addresses[0].get("mask_length") != 24:
            wrong_masks.append(f"{path.name}:eth0")

    assert wrong_masks == []


def test_cumulus_mock_devices_define_intended_firmware() -> None:
    missing_firmware = []

    for path in sorted(MOCK_TOPOLOGY_CONTEXT.glob("*/devices/*.json")):
        device = _load_device(path)

        platform_name = (device.get("platform") or {}).get("name", "")
        if "Cumulus" not in platform_name:
            continue

        firmware = device.get("config_context", {}).get("intended-firmware", {}).get("version")
        if not firmware:
            missing_firmware.append(f"{path.name}:{device.get('name')}")

    assert missing_firmware == []


def test_mock_topology_uses_bgp_model_seed_data() -> None:
    context_bgp_devices = []

    for path in sorted(MOCK_TOPOLOGY_CONTEXT.glob("*/devices/*.json")):
        payload = json.loads(path.read_text())
        relative_path = str(path.relative_to(PROJECT_ROOT))
        stack: list[object] = [payload]

        while stack:
            value = stack.pop()
            if isinstance(value, dict):
                config_context = value.get("config_context")
                if isinstance(config_context, dict) and config_context.get("bgp"):
                    context_bgp_devices.append(relative_path)
                stack.extend(value.values())
            elif isinstance(value, list):
                stack.extend(value)

    air_trial_routing_instances = _load_yaml(
        MOCK_TOPOLOGY_CONTEXT / "air_trial" / "bgp_routing_instances.yaml"
    )["bgp_routing_instances"]
    air_superpod_routing_instances = _load_yaml(
        MOCK_TOPOLOGY_CONTEXT / "air_superpod" / "bgp_routing_instances.yaml"
    )["bgp_routing_instances"]

    assert context_bgp_devices == []
    assert {"device": "oob-mgmt-server", "asn": 65000} in air_trial_routing_instances
    assert {"device": "oob-mleaf-01", "asn": 65101} in air_trial_routing_instances
    assert {"device": "oob-mgmt-server", "asn": 4266000000} in air_superpod_routing_instances
    assert {"device": "su01-oob-mleaf01", "asn": 65101} in air_superpod_routing_instances


def test_bgp_peering_seed_data_references_loaded_interfaces() -> None:
    missing = []

    for path in sorted(MOCK_TOPOLOGY_CONTEXT.glob("*/bgp_routing_instances.yaml")):
        context_data = _load_yaml(path)
        peerings = context_data.get("bgp_peerings", [])
        if not peerings:
            continue

        devices = _devices_by_name(path.parent)
        routing_instance_devices = {
            entry["device"] for entry in context_data.get("bgp_routing_instances", [])
        }

        for peering in peerings:
            for device_key, interface_key in (
                ("device", "source_interface"),
                ("peer_device", "peer_source_interface"),
            ):
                device_name = peering.get(device_key)
                interface_name = peering.get(interface_key)
                device = devices.get(device_name)
                if not device:
                    missing.append(f"{path.parent.name}:{device_name}")
                    continue
                if device_name not in routing_instance_devices:
                    missing.append(f"{path.parent.name}:{device_name}:bgp_routing_instance")
                if not _interface_by_name(device, interface_name):
                    missing.append(f"{path.parent.name}:{device_name}:{interface_name}")

    assert missing == []


def test_mock_topology_templates_quote_string_identifiers() -> None:
    interfaces_template = (MOCK_TOPOLOGY_DESIGNS / "interfaces.yaml.j2").read_text()
    devices_template = (MOCK_TOPOLOGY_DESIGNS / "devices.yaml.j2").read_text()

    assert 'mac_address: "{{ intf.mac_address }}"' in interfaces_template
    assert 'serial: "{{ device.serial }}"' in devices_template
    assert "local_config_context_data" in devices_template


def test_ip_address_templates_use_topology_namespace() -> None:
    ip_addresses_template = (MOCK_TOPOLOGY_DESIGNS / "ip_addresses.yaml.j2").read_text()

    assert (
        '"!create_or_update:parent__namespace__name": {{ global_defaults.namespace }}'
        in ip_addresses_template
    )


def test_role_design_does_not_replace_content_type_memberships() -> None:
    roles_template = (MOCK_TOPOLOGY_DESIGNS / "roles.yaml.j2").read_text()

    assert "content_types:" not in roles_template


def test_managed_devices_template_allows_devices_without_platform() -> None:
    managed_devices_template = (MOCK_TOPOLOGY_DESIGNS / "managed_devices.yaml.j2").read_text()

    assert "device.platform is defined" in managed_devices_template
