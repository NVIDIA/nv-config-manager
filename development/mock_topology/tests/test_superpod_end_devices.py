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

"""Data-level tests for the SuperPod mock topology GPU end devices.

These tests run without booting Nautobot or design-builder. They validate the
JSON device files and the Jinja templates that render the design YAML so any
breakage in the topology contract surfaces in unit tests rather than at
deploy time.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml
from jinja2 import Environment, FileSystemLoader

MOCK_TOPOLOGY_ROOT = Path(__file__).resolve().parents[1]
SUPERPOD_DEVICES_DIR = MOCK_TOPOLOGY_ROOT / "context" / "superpod" / "devices"
DESIGNS_DIR = MOCK_TOPOLOGY_ROOT / "jobs" / "designs"

GPU_DEVICE_NAMES = (
    "a09-u01-p01-gpu-01",
    "a09-u02-p01-gpu-02",
    "a09-u03-p01-gpu-03",
    "a09-u04-p01-gpu-04",
)
HCA_INTERFACE_NAMES = ("mlx5_0", "mlx5_1")
SLEAF_NAME = "a09-u32-p01-sleaf-01"
# cf_ib_guid is stored bare-hex (no 0x), matching what UFM discovery writes and
# what resolve_guids_to_interfaces queries against. See test_ib_nautobot.py.
IB_GUID_PATTERN = re.compile(r"^[0-9a-f]{16}$")

GLOBAL_DEFAULTS = {
    "tenant": "SuperPod",
    "namespace": "Global",
    "status": "Active",
    "cable_status": "Connected",
    "prefix_status": "Active",
    "device_status": "Active",
    "ip_address_status": "Active",
}


def _load_device(name: str) -> dict:
    path = SUPERPOD_DEVICES_DIR / f"{name}.json"
    with path.open() as fh:
        return json.load(fh)["data"]["device"]


def _load_superpod_devices() -> list[dict]:
    return [
        json.loads(p.read_text())["data"]["device"]
        for p in sorted(SUPERPOD_DEVICES_DIR.glob("[ab]0*.json"))
    ]


@pytest.fixture(scope="module")
def gpu_devices() -> list[dict]:
    return [_load_device(name) for name in GPU_DEVICE_NAMES]


@pytest.fixture(scope="module")
def all_devices() -> list[dict]:
    return _load_superpod_devices()


@pytest.fixture(scope="module")
def jinja_env() -> Environment:
    return Environment(loader=FileSystemLoader(str(DESIGNS_DIR)))


class TestGPUDevicePresence:
    """Each GPU host JSON parses and self-identifies correctly."""

    def test_all_four_gpu_files_exist(self) -> None:
        for name in GPU_DEVICE_NAMES:
            assert (SUPERPOD_DEVICES_DIR / f"{name}.json").is_file(), (
                f"missing GPU device file for {name}"
            )

    def test_filename_matches_device_name(self, gpu_devices: list[dict]) -> None:
        for name, dev in zip(GPU_DEVICE_NAMES, gpu_devices, strict=True):
            assert dev["name"] == name

    def test_filename_starts_with_a0_so_superpod_glob_picks_it_up(self) -> None:
        for name in GPU_DEVICE_NAMES:
            assert name.startswith("a0"), (
                "SuperpodContext.device_file_glob is '[ab]0*.json' - "
                f"filename {name!r} must begin with a0 or b0"
            )

    def test_role_is_gpu(self, gpu_devices: list[dict]) -> None:
        for dev in gpu_devices:
            assert dev["role"]["name"] == "GPU"


class TestHCAInterfaces:
    """Each GPU host carries two HCA interfaces with valid ib_guid custom fields."""

    def test_two_hca_interfaces_per_host(self, gpu_devices: list[dict]) -> None:
        for dev in gpu_devices:
            iface_names = [i["name"] for i in dev["interfaces"]]
            for hca in HCA_INTERFACE_NAMES:
                assert hca in iface_names, f"{dev['name']} missing HCA {hca!r}"

    def test_hca_interfaces_have_ib_guid_custom_field(self, gpu_devices: list[dict]) -> None:
        for dev in gpu_devices:
            for iface in dev["interfaces"]:
                if iface["name"] not in HCA_INTERFACE_NAMES:
                    continue
                cf = iface.get("custom_fields") or {}
                guid = cf.get("ib_guid", "")
                assert IB_GUID_PATTERN.match(guid), (
                    f"{dev['name']}/{iface['name']} ib_guid {guid!r} must match ^[0-9a-f]{{16}}$"
                )

    def test_ib_guids_are_globally_unique(self, gpu_devices: list[dict]) -> None:
        seen: dict[str, str] = {}
        for dev in gpu_devices:
            for iface in dev["interfaces"]:
                guid = (iface.get("custom_fields") or {}).get("ib_guid")
                if not guid:
                    continue
                key = guid.lower()
                assert key not in seen, (
                    f"duplicate ib_guid {guid} on {seen[key]} and {dev['name']}/{iface['name']}"
                )
                seen[key] = f"{dev['name']}/{iface['name']}"

    def test_eth0_has_no_ib_guid(self, gpu_devices: list[dict]) -> None:
        for dev in gpu_devices:
            for iface in dev["interfaces"]:
                if iface["name"] != "eth0":
                    continue
                cf = iface.get("custom_fields") or {}
                assert "ib_guid" not in cf

    def test_hca_interface_type_renders_to_infiniband_ndr(self, gpu_devices: list[dict]) -> None:
        # interfaces.yaml.j2 lowercases the type, strips "a_", and replaces "_" with "-"
        for dev in gpu_devices:
            for iface in dev["interfaces"]:
                if iface["name"] not in HCA_INTERFACE_NAMES:
                    continue
                rendered = iface["type"].lower().replace("a_", "").replace("_", "-")
                assert rendered == "infiniband-ndr"


class TestCabling:
    """Every HCA cable points at a device + interface that actually exists."""

    def test_each_hca_cable_targets_sleaf(self, gpu_devices: list[dict]) -> None:
        for dev in gpu_devices:
            for iface in dev["interfaces"]:
                if iface["name"] not in HCA_INTERFACE_NAMES:
                    continue
                connected = iface.get("connected_interface")
                assert connected is not None, (
                    f"{dev['name']}/{iface['name']} must declare a connected_interface"
                )
                assert connected["device"]["name"] == SLEAF_NAME

    def test_each_remote_interface_exists_on_sleaf(self, gpu_devices: list[dict]) -> None:
        sleaf = _load_device(SLEAF_NAME)
        sleaf_iface_names = {i["name"] for i in sleaf["interfaces"]}
        for dev in gpu_devices:
            for iface in dev["interfaces"]:
                if iface["name"] not in HCA_INTERFACE_NAMES:
                    continue
                remote = iface["connected_interface"]["name"]
                assert remote in sleaf_iface_names, (
                    f"{dev['name']}/{iface['name']} cables to "
                    f"{SLEAF_NAME}/{remote} which does not exist"
                )

    def test_no_duplicate_sleaf_target_ports(self, gpu_devices: list[dict]) -> None:
        seen: dict[str, str] = {}
        for dev in gpu_devices:
            for iface in dev["interfaces"]:
                if iface["name"] not in HCA_INTERFACE_NAMES:
                    continue
                remote = iface["connected_interface"]["name"]
                assert remote not in seen, (
                    f"{remote} is targeted by both {seen[remote]} and {dev['name']}/{iface['name']}"
                )
                seen[remote] = f"{dev['name']}/{iface['name']}"


class TestTemplateRender:
    """interfaces.yaml.j2 emits ib_guid; cables.yaml.j2 emits 8 GPU<->leaf cables."""

    def test_interfaces_template_renders_ib_guid_block(
        self, jinja_env: Environment, all_devices: list[dict]
    ) -> None:
        rendered = jinja_env.get_template("interfaces.yaml.j2").render(
            json={"devices": all_devices},
            global_defaults=GLOBAL_DEFAULTS,
        )
        doc = yaml.safe_load(rendered)
        interfaces = doc["interfaces"]
        hca_entries = [
            i
            for i in interfaces
            if i.get("!create_or_update:name") in HCA_INTERFACE_NAMES
            and any(f"intf-{name}-" in i.get("!ref", "") for name in GPU_DEVICE_NAMES)
        ]
        assert len(hca_entries) == len(GPU_DEVICE_NAMES) * len(HCA_INTERFACE_NAMES)
        for entry in hca_entries:
            cf = entry.get("custom_fields") or {}
            assert IB_GUID_PATTERN.match(cf.get("ib_guid", "") or "")

    def test_interfaces_template_omits_ib_guid_for_non_hca(
        self, jinja_env: Environment, all_devices: list[dict]
    ) -> None:
        rendered = jinja_env.get_template("interfaces.yaml.j2").render(
            json={"devices": all_devices},
            global_defaults=GLOBAL_DEFAULTS,
        )
        doc = yaml.safe_load(rendered)
        for entry in doc["interfaces"]:
            if entry.get("!create_or_update:name") == "eth0":
                assert "custom_fields" not in entry, "eth0 should not carry an ib_guid custom field"

    def test_cables_template_emits_eight_gpu_cables(
        self, jinja_env: Environment, all_devices: list[dict]
    ) -> None:
        rendered = jinja_env.get_template("cables.yaml.j2").render(
            json={"devices": all_devices},
            global_defaults=GLOBAL_DEFAULTS,
        )
        doc = yaml.safe_load(rendered)
        gpu_cables = [
            entry
            for entry in doc.get("interfaces", [])
            if any(f"device-{name}" in entry.get("!update:device", "") for name in GPU_DEVICE_NAMES)
        ]
        assert len(gpu_cables) == len(GPU_DEVICE_NAMES) * len(HCA_INTERFACE_NAMES)
        for entry in gpu_cables:
            target = entry["!connect_cable"]["to"]
            assert SLEAF_NAME in target
