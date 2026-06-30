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
"""Generate mock device fixture files from topology device JSON snapshots."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

FIXTURES_ROOT = Path(__file__).resolve().parent.parent / "fixtures"

# Platform name mapping from Nautobot to fixture directory names
_PLATFORM_MAP: dict[str, str] = {
    "cumulus linux": "nvue",
    "cumulus": "nvue",
    "nvos": "nvue",
    "nv_os": "nvue",
    "arista eos": "eapi",
    "arista": "eapi",
}


def _platform_key(platform_name: str) -> str:
    """Normalise a Nautobot platform name to the fixture directory key (e.g. 'nvue', 'eapi')."""
    return _PLATFORM_MAP.get(platform_name.lower(), platform_name.lower())


def generate_for_device(
    device_json_path: Path,
    output_dir: Path | None = None,
    device_overrides: bool = False,
) -> list[Path]:
    """Read a topology device JSON and emit fixture files.

    Returns the list of files written.
    """
    data = json.loads(device_json_path.read_text(encoding="utf-8"))
    device = data.get("data", {}).get("device", {})
    if not device:
        logger.warning("No device data in %s", device_json_path)
        return []

    hostname = device["name"]
    platform_raw = (device.get("platform") or {}).get("name", "")
    platform = _platform_key(platform_raw)
    serial = device.get("serial", "MOCK0001")
    config_ctx = device.get("config_context") or {}
    os_version = config_ctx.get("intended-firmware", {}).get("version", "")
    model = (device.get("device_type") or {}).get("model", "Unknown")
    interfaces = device.get("interfaces", [])

    if not os_version:
        logger.warning("Device %s has no intended-firmware version, skipping", hostname)
        return []

    root = output_dir or FIXTURES_ROOT
    written: list[Path] = []

    if platform == "nvue":
        written.extend(
            _generate_nvue(root, hostname, serial, os_version, model, interfaces, device_overrides)
        )
    elif platform == "eapi":
        written.extend(
            _generate_eapi(root, hostname, serial, os_version, model, interfaces, device_overrides)
        )
    else:
        logger.warning("Unknown platform %r for %s", platform_raw, hostname)

    return written


def _generate_nvue(
    root: Path,
    hostname: str,
    serial: str,
    version: str,
    model: str,
    interfaces: list[dict[str, Any]],
    device_overrides: bool,
) -> list[Path]:
    """Write NVUE fixture files for one device version or per-device override set."""
    written: list[Path] = []

    if not device_overrides:
        # Shared version-level fixtures — schema/format only, no device-specific values.
        # Using generic placeholders so multiple devices sharing a version don't clobber
        # each other's hostname, serial, or interface data here.
        version_dir = root / "nvue" / version
        version_dir.mkdir(parents=True, exist_ok=True)

        written.append(
            _write_json(version_dir / "system.json", _nvue_system("mock-device", version))
        )
        written.append(_write_json(version_dir / "interface.json", {}))
        written.append(
            _write_json(version_dir / "platform.json", {"model": "Mock-Device", "vendor": "NVIDIA"})
        )
        written.append(
            _write_json(
                version_dir / "platform_inventory.json",
                {"model": "Mock-Device", "serial": "MOCK-SERIAL-0001"},
            )
        )

    if device_overrides:
        device_dir = root / "devices" / hostname
        device_dir.mkdir(parents=True, exist_ok=True)
        written.append(_write_json(device_dir / "system.json", _nvue_system(hostname, version)))
        dev_intf = _nvue_interfaces(version, interfaces, include_lldp=True)
        written.append(_write_json(device_dir / "interface.json", dev_intf))
        written.append(
            _write_json(device_dir / "platform.json", {"model": model, "vendor": "NVIDIA"})
        )
        written.append(
            _write_json(device_dir / "platform_inventory.json", {"model": model, "serial": serial})
        )

    return written


def _nvue_system(hostname: str, version: str) -> dict[str, Any]:
    """Build the NVUE system fixture, adapting the schema to the OS version."""
    major_minor = _parse_major_minor(version)
    if major_minor and major_minor >= (5, 14):
        return {
            "hostname": hostname,
            "uptime": 86400,
            "version": {
                "product-release": version,
                "build-date": "2025-01-15",
                "kernel": "6.1.0-cl-1-amd64",
            },
        }
    return {
        "hostname": hostname,
        "uptime": 86400,
        "product-release": version,
        "version": {},
    }


def _nvue_interfaces(
    version: str,
    interfaces: list[dict[str, Any]],
    include_lldp: bool = False,
) -> dict[str, Any]:
    """Build the NVUE interface fixture dict, version-aware for link state field differences."""
    major_minor = _parse_major_minor(version)
    use_oper_status = major_minor is not None and major_minor >= (5, 14)
    result: dict[str, Any] = {}

    for iface in interfaces:
        name = iface.get("name", "")
        if not name:
            continue
        enabled = iface.get("enabled", True)

        if use_oper_status:
            link: dict[str, Any] = {"oper-status": "up" if enabled else "down"}
        else:
            link = {"state": {"up": {}} if enabled else {"down": {}}}

        entry: dict[str, Any] = {
            "type": _nvue_iface_type(name),
            "link": link,
            "ip": {"address": {}},
            "lldp": {"neighbor": {}},
        }

        if include_lldp and iface.get("connected_interface"):
            peer = iface["connected_interface"]
            peer_device = peer.get("device", {}).get("name", "")
            peer_port = peer.get("name", "")
            if peer_device and peer_port:
                entry["lldp"]["neighbor"] = {
                    peer_device: {"port": {"name": peer_port}, "age": "120"}
                }

        ips = iface.get("ip_addresses", [])
        if ips:
            entry["ip"]["address"] = {ip["address"]: {} for ip in ips if "address" in ip}

        result[name] = entry

    return result


def _nvue_iface_type(name: str) -> str:
    """Map an interface name to its NVUE type string (swp, eth, loopback, svi, bond)."""
    lower = name.lower()
    if lower.startswith("swp"):
        return "swp"
    if lower.startswith("eth"):
        return "eth"
    if lower in ("lo",) or lower.startswith("lo"):
        return "loopback"
    if lower.startswith("vlan"):
        return "svi"
    if lower.startswith("bond"):
        return "bond"
    return "swp"


def _generate_eapi(
    root: Path,
    hostname: str,
    serial: str,
    version: str,
    model: str,
    interfaces: list[dict[str, Any]],
    device_overrides: bool,
) -> list[Path]:
    """Write eAPI fixture files for one Arista device version or per-device override set."""
    written: list[Path] = []

    # show_lldp_neighbors_detail — built from topology regardless of mode
    neighbors: dict[str, Any] = {}
    for iface in interfaces:
        peer = iface.get("connected_interface")
        if not peer:
            continue
        peer_device = peer.get("device", {}).get("name", "")
        peer_port = peer.get("name", "")
        if peer_device and peer_port:
            neighbors[iface["name"]] = {
                "lldpNeighborInfo": [
                    {
                        "systemName": peer_device,
                        "neighborInterfaceInfo": {"interfaceId": f'"{peer_port}"'},
                        "chassisId": "00:00:00:00:00:00",
                    }
                ],
            }

    if not device_overrides:
        # Shared version-level fixtures — schema/format only, no device-specific values.
        version_dir = root / "eapi" / version
        version_dir.mkdir(parents=True, exist_ok=True)

        show_version = {
            "modelName": "Mock-Device",
            "internalVersion": f"{version}-mock",
            "systemMacAddress": "00:1c:73:00:00:01",
            "serialNumber": "MOCK-SERIAL-0001",
            "memTotal": 65777320,
            "bootupTimestamp": 1700000000.0,
            "memFree": 52000000,
            "version": version,
            "configMacAddress": "00:00:00:00:00:00",
            "isIntlVersion": False,
            "internalBuildId": "mock-build-id",
            "hardwareRevision": "02.01",
            "hwMacAddress": "00:1c:73:00:00:01",
            "architecture": "x86_64",
            "uptime": 86400,
        }
        written.append(_write_json(version_dir / "show_version.json", show_version))
        written.append(
            _write_json(
                version_dir / "show_hostname.json",
                {"hostname": "mock-device", "fqdn": "mock-device.local"},
            )
        )
        written.append(
            _write_json(
                version_dir / "show_interfaces_status.json",
                {"interfaceStatuses": {}},
            )
        )
        written.append(
            _write_json(
                version_dir / "show_lldp_neighbors_detail.json",
                {"lldpNeighbors": {}},
            )
        )
        written.append(
            _write_json(
                version_dir / "show_mac_address_table.json",
                {"unicastTable": {"tableEntries": []}},
            )
        )
        written.append(
            _write_json(
                version_dir / "show_mpls_interface.json",
                {"interfaces": {}},
            )
        )

    if device_overrides:
        device_dir = root / "devices" / hostname
        device_dir.mkdir(parents=True, exist_ok=True)

        show_version_device = {
            "modelName": model,
            "internalVersion": f"{version}-mock",
            "systemMacAddress": "00:1c:73:00:00:01",
            "serialNumber": serial,
            "memTotal": 65777320,
            "bootupTimestamp": 1700000000.0,
            "memFree": 52000000,
            "version": version,
            "configMacAddress": "00:00:00:00:00:00",
            "isIntlVersion": False,
            "internalBuildId": "mock-build-id",
            "hardwareRevision": "02.01",
            "hwMacAddress": "00:1c:73:00:00:01",
            "architecture": "x86_64",
            "uptime": 86400,
        }
        written.append(_write_json(device_dir / "show_version.json", show_version_device))
        written.append(
            _write_json(
                device_dir / "show_hostname.json",
                {"hostname": hostname, "fqdn": f"{hostname}.local"},
            )
        )

        statuses: dict[str, Any] = {}
        for iface in interfaces:
            name = iface.get("name", "")
            if not name:
                continue
            enabled = iface.get("enabled", True)
            statuses[name] = {
                "linkStatus": "connected" if enabled else "disabled",
                "lineProtocolStatus": "up" if enabled else "down",
            }
        written.append(
            _write_json(
                device_dir / "show_interfaces_status.json",
                {"interfaceStatuses": statuses},
            )
        )

        if neighbors:
            written.append(
                _write_json(
                    device_dir / "show_lldp_neighbors_detail.json",
                    {"lldpNeighbors": neighbors},
                )
            )

    return written


def _parse_major_minor(version: str) -> tuple[int, int] | None:
    """Extract (major, minor) from a version string like '5.14.0' or '4.29.5M'."""
    parts = version.split(".")
    if len(parts) < 2:
        return None
    try:
        return (int(parts[0]), int(parts[1]))
    except ValueError:
        return None


def _write_json(path: Path, data: Any) -> Path:
    """Serialise *data* as indented JSON and write to *path*, creating parent dirs as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    logger.info("Wrote %s", path)
    return path
