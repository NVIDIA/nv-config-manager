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
"""Mock Cumulus/NV-OS NVUE REST API.

Responds to the same REST endpoints that CumulusConnection/NVOSConnection use in
src/nv_config_manager/temporal/client/device.py.
"""

from __future__ import annotations

import time
import uuid
from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from mock_device.config import DeviceConfig
from mock_device.device_api.fixtures import FixtureLoader

router = APIRouter(prefix="/nvue_v1")

_device: DeviceConfig | None = None
_loader: FixtureLoader | None = None
_revisions: dict[str, dict[str, Any]] = {}
_applied_config: dict[str, Any] = {}


def configure(device: DeviceConfig) -> None:
    """Set the device config for NVUE responses."""
    global _device, _loader, _applied_config
    _device = device
    _applied_config = _default_config()
    _loader = FixtureLoader(
        platform="nvue",
        os_version=device.os_version,
        device_name=device.name,
    )


def _hostname() -> str:
    return _device.name if _device else "mock-cumulus"


_LLDP_NEIGHBORS: dict[str, dict[str, dict[str, Any]]] = {
    "leaf1-cp1-smn1-dc01": {
        "swp51": {"spine2-cp1-smn1-dc01": {"port": {"name": "swp1"}, "age": "120"}},
        "swp52": {"spine1-cp1-smn1-dc01": {"port": {"name": "swp1"}, "age": "120"}},
        "swp12": {"bbr1-cp1-tan1-dc01": {"port": {"name": "Management1/1"}, "age": "60"}},
    },
    "leaf2-cp1-smn1-dc01": {
        "swp51": {"spine2-cp1-smn1-dc01": {"port": {"name": "swp2"}, "age": "120"}},
        "swp52": {"spine1-cp1-smn1-dc01": {"port": {"name": "swp2"}, "age": "120"}},
        "swp12": {"bbr2-cp1-tan1-dc01": {"port": {"name": "Management1/1"}, "age": "60"}},
    },
    "spine1-cp1-smn1-dc01": {
        "swp1": {"leaf1-cp1-smn1-dc01": {"port": {"name": "swp52"}, "age": "120"}},
        "swp2": {"leaf2-cp1-smn1-dc01": {"port": {"name": "swp52"}, "age": "120"}},
    },
    "spine2-cp1-smn1-dc01": {
        "swp1": {"leaf1-cp1-smn1-dc01": {"port": {"name": "swp51"}, "age": "120"}},
        "swp2": {"leaf2-cp1-smn1-dc01": {"port": {"name": "swp51"}, "age": "120"}},
    },
}


def _default_config() -> dict[str, Any]:
    """Generate a default NVUE config tree."""
    hostname = _hostname()

    interfaces: dict[str, Any] = {
        "eth0": {
            "type": "eth",
            "link": {"state": {"up": {}}, "oper-status": "up"},
            "ip": {"address": {}},
            "lldp": {"neighbor": {}},
        },
        "lo": {
            "type": "loopback",
            "link": {"state": {"up": {}}, "oper-status": "up"},
            "ip": {"address": {}},
            "lldp": {"neighbor": {}},
        },
    }

    lldp = _LLDP_NEIGHBORS.get(hostname, {})
    swp_names = sorted(lldp.keys()) if lldp else ["swp1"]
    for swp in swp_names:
        interfaces[swp] = {
            "type": "swp",
            "link": {"state": {"up": {}}, "oper-status": "up"},
            "ip": {"address": {}},
            "lldp": {"neighbor": lldp.get(swp, {})},
        }

    if not lldp and "swp1" not in interfaces:
        interfaces["swp1"] = {
            "type": "swp",
            "link": {"state": {"up": {}}, "oper-status": "up"},
            "ip": {"address": {}},
            "lldp": {"neighbor": {}},
        }

    return {
        "system": {"hostname": hostname},
        "router": {"bgp": {"autonomous-system": 65000, "router-id": "10.0.0.1"}},
        "interface": interfaces,
        "bridge": {"domain": {}},
    }


@router.get("/")
async def get_root(
    rev: str = Query(default="applied"),
    filled: str = Query(default="true"),
    diff: str | None = Query(default=None),
) -> JSONResponse:
    """GET /nvue_v1/ — return running config or diff."""
    if diff:
        # Return an empty diff (no changes)
        return JSONResponse(content={})
    return JSONResponse(content=_applied_config)


@router.delete("/")
async def delete_root(rev: str = Query(default="")) -> JSONResponse:
    """DELETE /nvue_v1/ — clear config for a revision."""
    return JSONResponse(content={})


@router.patch("/")
async def patch_root(request: Request, rev: str = Query(default="")) -> JSONResponse:
    """PATCH /nvue_v1/ — apply config to a revision."""
    body = await request.json()
    if rev in _revisions:
        _revisions[rev]["config"] = body
    return JSONResponse(content={})


@router.get("/interface")
async def get_interfaces(include: list[str] | None = Query(default=None)) -> JSONResponse:
    """GET /nvue_v1/interface — return all interfaces."""
    if _loader and not include:
        fixture = _loader.load("interface")
        if fixture and isinstance(fixture, dict):
            return JSONResponse(content=fixture)
    interfaces = _applied_config.get("interface", {})
    if include:
        filtered = {}
        for name, data in interfaces.items():
            entry: dict[str, Any] = {}
            for inc in include:
                # Parse include paths like "/*/link/state"
                parts = inc.strip("/").split("/")
                if parts[0] == "*":
                    parts = parts[1:]
                cur = data
                for part in parts:
                    if isinstance(cur, dict) and part in cur:
                        cur = cur[part]
                    else:
                        cur = None
                        break
                if cur is not None:
                    dest = entry
                    for part in parts[:-1]:
                        dest = dest.setdefault(part, {})
                    dest[parts[-1]] = cur
            if "/*/lldp/neighbor" in str(include):
                entry.setdefault("lldp", {}).setdefault("neighbor", {})
            filtered[name] = entry
        return JSONResponse(content=filtered)
    return JSONResponse(content=interfaces)


@router.get("/interface/{iface_name}/lldp")
async def get_interface_lldp(iface_name: str) -> JSONResponse:
    """GET /nvue_v1/interface/{name}/lldp — LLDP neighbor data."""
    intf = _applied_config.get("interface", {}).get(iface_name, {})
    neighbor = intf.get("lldp", {}).get("neighbor", {})
    return JSONResponse(content={"neighbor": neighbor})


@router.get("/interface/{iface_name}/ip/neighbor")
async def get_interface_neighbor(iface_name: str) -> JSONResponse:
    """GET /nvue_v1/interface/{name}/ip/neighbor — ARP data."""
    intf = _applied_config.get("interface", {}).get(iface_name)
    if intf and intf.get("type") in ("swp", "eth"):
        return JSONResponse(
            content={
                "ipv4": {
                    "10.0.0.2": {"lladdr": "00:1c:73:00:00:02", "state": "reachable"},
                }
            }
        )
    return JSONResponse(status_code=404, content={})


@router.get("/system")
async def get_system() -> JSONResponse:
    """GET /nvue_v1/system — system info."""
    if _loader:
        fixture = _loader.load("system")
        if fixture and isinstance(fixture, dict):
            fixture["hostname"] = _hostname()
            return JSONResponse(content=fixture)
    return JSONResponse(
        content={
            "hostname": _hostname(),
            "uptime": 86400,
            "product-release": "5.11.0",
            "version": {"product-release": "5.11.0"},
        }
    )


@router.get("/platform")
async def get_platform() -> JSONResponse:
    """GET /nvue_v1/platform — platform info."""
    if _loader:
        fixture = _loader.load("platform")
        if fixture and isinstance(fixture, dict):
            return JSONResponse(content=fixture)
    return JSONResponse(content={"model": "MSN2201-CB2RC", "vendor": "NVIDIA"})


@router.get("/platform/environment/fan")
async def get_platform_fan() -> JSONResponse:
    if _loader:
        fixture = _loader.load("platform_environment_fan")
        if fixture and isinstance(fixture, dict):
            return JSONResponse(content=fixture)
    return JSONResponse(content={"fan1": {"speed": 5000, "state": "ok"}})


@router.get("/platform/environment/led")
async def get_platform_led() -> JSONResponse:
    return JSONResponse(content={"status": {"color": "green", "state": "ok"}})


@router.get("/platform/environment/psu")
async def get_platform_psu() -> JSONResponse:
    return JSONResponse(content={"psu1": {"state": "ok", "output_watts": 150}})


@router.get("/platform/environment/voltage")
async def get_platform_voltage() -> JSONResponse:
    return JSONResponse(content={"12V": {"voltage": 12.1, "state": "ok"}})


@router.get("/platform/inventory")
async def get_platform_inventory() -> JSONResponse:
    if _loader:
        fixture = _loader.load("platform_inventory")
        if fixture and isinstance(fixture, dict):
            fixture["serial"] = _device.serial if _device else "MOCK0001"
            return JSONResponse(content=fixture)
    return JSONResponse(
        content={
            "model": "MSN2201-CB2RC",
            "serial": _device.serial if _device else "MOCK0001",
        }
    )


@router.get("/platform/firmware")
async def get_platform_firmware() -> JSONResponse:
    if _loader:
        fixture = _loader.load("platform_firmware")
        if fixture and isinstance(fixture, dict):
            return JSONResponse(content=fixture)
    return JSONResponse(content={"ONIE": {"version": "2024.02"}, "ASIC": {"version": "1.0"}})


@router.get("/bridge/domain")
async def get_bridge_domains() -> JSONResponse:
    """GET /nvue_v1/bridge/domain — list bridge domains."""
    return JSONResponse(content=["br_default"])


@router.get("/bridge/domain/{domain}/mac-table")
async def get_mac_table(domain: str) -> JSONResponse:
    """GET /nvue_v1/bridge/domain/{domain}/mac-table — MAC table."""
    if _loader:
        fixture = _loader.load("bridge_domain_mac_table")
        if fixture and isinstance(fixture, dict):
            return JSONResponse(content=fixture)
    return JSONResponse(
        content={
            "1": {
                "mac": "00:1c:73:00:00:01",
                "interface": "swp1",
                "vlan": 100,
                "last-update": str(int(time.time()) - 60),
            }
        }
    )


@router.post("/revision")
async def create_revision() -> JSONResponse:
    """POST /nvue_v1/revision — create a new config revision."""
    rev_id = str(uuid.uuid4())[:8]
    _revisions[rev_id] = {"state": "pending", "config": {}}
    return JSONResponse(content={rev_id: {"state": "pending"}})


@router.get("/revision/{rev_id}")
async def get_revision(rev_id: str) -> JSONResponse:
    """GET /nvue_v1/revision/{id} — revision state."""
    if rev_id == "applied":
        return JSONResponse(content={"state": "applied_and_saved"})
    rev = _revisions.get(rev_id, {"state": "applied_and_saved"})
    return JSONResponse(content=rev)


@router.patch("/revision/{rev_id}")
async def patch_revision(rev_id: str, request: Request) -> JSONResponse:
    """PATCH /nvue_v1/revision/{id} — apply or confirm revision."""
    body = await request.json()
    state = body.get("state", "")
    if state == "apply":
        if rev_id in _revisions:
            _revisions[rev_id]["state"] = "applied_and_saved"
    elif state == "save":
        pass
    return JSONResponse(content={})


@router.get("/system/ztp")
async def get_ztp_status() -> JSONResponse:
    return JSONResponse(content={"status": "disabled"})


@router.post("/system")
async def post_system(request: Request) -> JSONResponse:
    """POST /nvue_v1/system — handle reboot and factory-default."""
    return JSONResponse(content={})


@router.post("/system/factory-default")
async def factory_default(request: Request) -> JSONResponse:
    """POST /nvue_v1/system/factory-default — factory reset (ZTP trigger)."""
    return JSONResponse(content={})
