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
"""Mock Arista EAPI (JSON-RPC over HTTPS).

Responds to the same JSON-RPC commands that AristaConnection uses in
src/nv_config_manager/temporal/client/device.py.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from mock_device.config import DeviceConfig
from mock_device.device_api.fixtures import FixtureLoader

router = APIRouter()

_device: DeviceConfig | None = None
_loader: FixtureLoader | None = None
_sessions: dict[str, dict[str, Any]] = {}
_pending_config: str = ""


def configure(device: DeviceConfig) -> None:
    """Set the device config for EAPI responses."""
    global _device, _loader
    _device = device
    _loader = FixtureLoader(
        platform="eapi",
        os_version=device.os_version,
        device_name=device.name,
    )


def _hostname() -> str:
    return _device.name if _device else "mock-arista"


def _running_config() -> str:
    if _device and _device.running_config:
        return _device.running_config
    return (
        f"! Command: show running-config\n"
        f"! device: {_hostname()} (mock)\n"
        f"!\n"
        f"hostname {_hostname()}\n"
        f"!\n"
        f"interface Management1\n"
        f"   ip address dhcp\n"
        f"!\n"
        f"ip routing\n"
        f"!\n"
        f"end\n"
    )


_COMMAND_HANDLERS: dict[str, Any] = {}


def _handle_show_running_config(**kwargs: Any) -> dict[str, Any]:
    return {"output": _running_config()}


def _handle_show_hostname(**kwargs: Any) -> dict[str, Any]:
    if _loader:
        fixture = _loader.load("show_hostname")
        if fixture and isinstance(fixture, dict):
            fixture["hostname"] = _hostname()
            fixture["fqdn"] = f"{_hostname()}.local"
            return fixture
    return {"hostname": _hostname(), "fqdn": f"{_hostname()}.local"}


def _handle_show_mac_address_table(**kwargs: Any) -> dict[str, Any]:
    if _loader:
        fixture = _loader.load("show_mac_address_table")
        if fixture and isinstance(fixture, dict):
            return fixture
    return {
        "unicastTable": {
            "tableEntries": [
                {
                    "macAddress": "00:1c:73:00:00:01",
                    "interface": "Ethernet1",
                    "vlanId": 100,
                    "lastMove": time.time() - 3600,
                    "entryType": "dynamic",
                },
            ]
        }
    }


def _handle_show_ip_arp(**kwargs: Any) -> dict[str, Any]:
    if _loader:
        fixture = _loader.load("show_ip_arp")
        if fixture and isinstance(fixture, dict):
            return fixture
    return {
        "ipV4Neighbors": [
            {
                "address": "10.0.0.1",
                "hwAddress": "00:1c:73:00:00:01",
                "interface": "Ethernet1",
            },
        ]
    }


_BBR_LLDP: dict[str, dict[str, Any]] = {
    "bbr1-cp1-tan1-dc01": {
        "Management1/1": {
            "lldpNeighborInfo": [
                {
                    "systemName": "leaf1-cp1-smn1-dc01",
                    "neighborInterfaceInfo": {"interfaceId": '"swp12"'},
                    "chassisId": "00:1c:73:00:00:10",
                }
            ],
        },
    },
    "bbr2-cp1-tan1-dc01": {
        "Management1/1": {
            "lldpNeighborInfo": [
                {
                    "systemName": "leaf2-cp1-smn1-dc01",
                    "neighborInterfaceInfo": {"interfaceId": '"swp12"'},
                    "chassisId": "00:1c:73:00:00:11",
                }
            ],
        },
    },
}

_BBR_DEVICES = frozenset(_BBR_LLDP)


def _handle_show_version(**kwargs: Any) -> dict[str, Any]:
    fixture: dict[str, Any] = {}
    if _loader:
        loaded = _loader.load("show_version")
        if loaded and isinstance(loaded, dict):
            fixture = dict(loaded)
    if not fixture:
        fixture = {
            "modelName": "DCS-7804R3-BND",
            "version": "4.29.5M",
            "serialNumber": "MOCK0001",
            "systemMacAddress": "00:1c:73:00:00:01",
            "uptime": 86400,
        }
    fixture["serialNumber"] = _device.serial if _device else fixture.get("serialNumber", "MOCK0001")
    return fixture


def _handle_show_lldp_neighbors_detail(**kwargs: Any) -> dict[str, Any]:
    if _loader:
        fixture = _loader.load("show_lldp_neighbors_detail")
        if fixture and isinstance(fixture, dict):
            return fixture
    neighbors: dict[str, Any] = {}
    if _device and _device.name in _BBR_LLDP:
        neighbors = _BBR_LLDP[_device.name]
    return {"lldpNeighbors": neighbors}


def _handle_show_interfaces_status(**kwargs: Any) -> dict[str, Any]:
    if _loader:
        fixture = _loader.load("show_interfaces_status")
        if fixture and isinstance(fixture, dict):
            return fixture
    statuses: dict[str, Any] = {
        "Ethernet1": {"linkStatus": "connected", "lineProtocolStatus": "up"},
        "Management1": {"linkStatus": "connected", "lineProtocolStatus": "up"},
    }
    if _device and _device.name in _BBR_DEVICES:
        statuses["Management1/1"] = {"linkStatus": "connected", "lineProtocolStatus": "up"}
        statuses["Loopback0"] = {"linkStatus": "connected", "lineProtocolStatus": "up"}
    return {"interfaceStatuses": statuses}


def _handle_show_uptime(**kwargs: Any) -> dict[str, Any]:
    return {"upTime": 86400}


def _handle_show_configuration_sessions(**kwargs: Any) -> dict[str, Any]:
    return {"sessions": {sid: {"state": "pending"} for sid in _sessions}}


def _handle_configure_session(session_id: str, **kwargs: Any) -> dict[str, Any]:
    _sessions[session_id] = {"state": "pending", "config": ""}
    return {}


def _handle_show_session_config_diffs(session_id: str, **kwargs: Any) -> dict[str, Any]:
    return {"output": f"--- session:/{session_id}-session-config\n+++ system:/running-config\n"}


def _fixture_key_for_command(cmd_lower: str) -> str | None:
    """Map a CLI command to a fixture key for generic lookups."""
    mapping = {
        "show mpls interface": "show_mpls_interface",
    }
    for prefix, key in mapping.items():
        if cmd_lower == prefix or cmd_lower.startswith(prefix + " "):
            return key
    return None


def _dispatch_command(cmd: str) -> dict[str, Any] | str:
    """Route a CLI command to the appropriate handler."""
    cmd_lower = cmd.strip().lower()

    # Try generic fixture lookup first for commands not handled specially
    if _loader:
        fkey = _fixture_key_for_command(cmd_lower)
        if fkey:
            fixture = _loader.load(fkey)
            if fixture is not None:
                return fixture if isinstance(fixture, dict) else {"output": fixture}

    if cmd_lower.startswith("show running-config"):
        return _handle_show_running_config()
    if cmd_lower == "show version":
        return _handle_show_version()
    if cmd_lower == "show hostname":
        return _handle_show_hostname()
    if cmd_lower == "show mac address-table":
        return _handle_show_mac_address_table()
    if cmd_lower == "show ip arp":
        return _handle_show_ip_arp()
    if "show lldp neighbors" in cmd_lower:
        return _handle_show_lldp_neighbors_detail()
    if cmd_lower == "show interfaces status":
        return _handle_show_interfaces_status()
    if cmd_lower == "show uptime":
        return _handle_show_uptime()
    if cmd_lower == "show configuration sessions":
        return _handle_show_configuration_sessions()
    if cmd_lower.startswith("configure session"):
        parts = cmd.split()
        session_id = parts[2] if len(parts) > 2 else str(uuid.uuid4())
        if "abort" in cmd_lower:
            _sessions.pop(session_id, None)
            return {}
        if "commit" in cmd_lower:
            _sessions.pop(session_id, None)
            return {}
        return _handle_configure_session(session_id)
    if "show session-config named" in cmd_lower and "diffs" in cmd_lower:
        parts = cmd.split()
        idx = next((i for i, p in enumerate(parts) if p == "named"), -1)
        session_id = parts[idx + 1] if idx >= 0 and idx + 1 < len(parts) else "unknown"
        return _handle_show_session_config_diffs(session_id)
    if cmd_lower in ("rollback clean-config", "end", "copy running-config startup-config"):
        return {}

    # Unknown commands return empty result
    return {}


@router.post("/command-api")
async def command_api(request: Request) -> JSONResponse:
    """Arista EAPI JSON-RPC endpoint."""
    body = await request.json()

    params = body.get("params", {})
    req_id = body.get("id", "1")
    commands = params.get("cmds", [])
    encoding = params.get("format", "json")

    results = []
    for cmd in commands:
        cmd_str = cmd if isinstance(cmd, str) else cmd.get("cmd", "")
        result = _dispatch_command(cmd_str)
        if encoding == "text" and isinstance(result, dict) and "output" not in result:
            result = {"output": str(result)}
        results.append({"result": result})

    return JSONResponse(
        content={
            "jsonrpc": "2.0",
            "id": req_id,
            "result": [r["result"] for r in results],
        }
    )
