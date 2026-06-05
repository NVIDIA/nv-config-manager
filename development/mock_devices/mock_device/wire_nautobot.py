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
"""Wire mock device service IPs into Nautobot so Temporal workflows can reach them.

Resolves each mock device's Kubernetes Service to a ClusterIP, then creates
the necessary Nautobot objects (namespace, prefix, IP address, interface) and
sets the device's primary_ip4 to the mock service address.
"""

from __future__ import annotations

import logging
import socket
from dataclasses import dataclass

import requests

logger = logging.getLogger(__name__)


class _ApiClient:
    """Thin wrapper around requests.Session that supports base_url (like httpx.Client)."""

    def __init__(self, base_url: str, headers: dict, timeout: int = 30):
        self._session = requests.Session()
        self._session.headers.update(headers)
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def request(self, method: str, path: str, **kwargs) -> requests.Response:
        kwargs.setdefault("timeout", self._timeout)
        return self._session.request(method, self._base_url + path, **kwargs)

    def close(self) -> None:
        self._session.close()

SANDBOX_NAMESPACE = "Sandbox"
SANDBOX_PREFIX = "10.96.0.0/12"
MOCK_MGMT_INTF = "mock-mgmt"

DEFAULT_DEVICE_MAP: list[dict[str, str | int]] = [
    {"device_name": "a04-u44-p01-tor-01", "service_name": "mock-sp-tor-01", "port": 8765},
    {"device_name": "a08-u28-p01-oobspine-01", "service_name": "mock-sp-oobspine-01", "port": 8765},
    {"device_name": "a08-u32-p01-cleaf-01", "service_name": "mock-sp-cleaf-01", "port": 8765},
    {"device_name": "a08-u44-p01-mleaf-01", "service_name": "mock-sp-mleaf-01", "port": 8765},
    {"device_name": "a09-u28-p01-bleaf-01", "service_name": "mock-sp-bleaf-01", "port": 8765},
    {"device_name": "a09-u32-p01-sleaf-01", "service_name": "mock-sp-sleaf-01", "port": 8765},
    {"device_name": "a09-u36-p01-spine-01", "service_name": "mock-sp-spine-01", "port": 8765},
    {"device_name": "a09-u44-p01-pleaf-01", "service_name": "mock-sp-pleaf-01", "port": 8765},
]


@dataclass
class WireResult:
    device_name: str
    service_ip: str
    success: bool
    message: str


def _resolve_service(service_name: str, port: int) -> str:
    """Resolve a Kubernetes service DNS name to its ClusterIP."""
    try:
        results = socket.getaddrinfo(service_name, port, socket.AF_INET, socket.SOCK_STREAM)
        if results:
            return results[0][4][0]
    except socket.gaierror:
        pass
    raise RuntimeError(f"Cannot resolve service {service_name}:{port}")


def _api(client: _ApiClient, method: str, path: str, **kwargs) -> requests.Response:
    resp = client.request(method, path, **kwargs)
    if resp.status_code >= 400:
        logger.error("Nautobot API %s %s -> %d: %s", method, path, resp.status_code, resp.text[:500])
    return resp


def _find_or_create(client: _ApiClient, endpoint: str, lookup: dict, create_data: dict) -> dict:
    """Find an existing object or create it. Returns the object dict."""
    resp = _api(client, "GET", endpoint, params=lookup)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if results:
        return results[0]
    resp = _api(client, "POST", endpoint, json=create_data)
    resp.raise_for_status()
    return resp.json()


def _get_or_create_namespace(client: _ApiClient) -> dict:
    return _find_or_create(
        client,
        "/api/ipam/namespaces/",
        {"name": SANDBOX_NAMESPACE},
        {"name": SANDBOX_NAMESPACE},
    )


def _get_status_id(client: _ApiClient, name: str = "Active") -> str:
    resp = _api(client, "GET", "/api/extras/statuses/", params={"name": name})
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if not results:
        raise RuntimeError(f"Status '{name}' not found in Nautobot")
    return results[0]["id"]


def _get_or_create_prefix(client: _ApiClient, namespace_id: str, status_id: str) -> dict:
    resp = _api(client, "GET", "/api/ipam/prefixes/", params={
        "prefix": SANDBOX_PREFIX,
        "namespace": namespace_id,
    })
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if results:
        return results[0]
    resp = _api(client, "POST", "/api/ipam/prefixes/", json={
        "prefix": SANDBOX_PREFIX,
        "namespace": namespace_id,
        "status": status_id,
        "type": "network",
    })
    resp.raise_for_status()
    return resp.json()


def _get_device(client: _ApiClient, name: str) -> dict | None:
    resp = _api(client, "GET", "/api/dcim/devices/", params={"name": name})
    resp.raise_for_status()
    results = resp.json().get("results", [])
    return results[0] if results else None


def _get_or_create_interface(client: _ApiClient, device_id: str, status_id: str) -> dict:
    resp = _api(client, "GET", "/api/dcim/interfaces/", params={
        "device": device_id,
        "name": MOCK_MGMT_INTF,
    })
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if results:
        return results[0]
    resp = _api(client, "POST", "/api/dcim/interfaces/", json={
        "device": device_id,
        "name": MOCK_MGMT_INTF,
        "type": "virtual",
        "mgmt_only": True,
        "status": status_id,
        "description": "Mock device service IP for sandbox testing",
    })
    resp.raise_for_status()
    return resp.json()


def _get_or_create_ip(
    client: _ApiClient,
    address: str,
    namespace_id: str,
    status_id: str,
) -> dict:
    """Create or find an IP address. Returns the IP address object."""
    cidr = f"{address}/32"
    resp = _api(client, "GET", "/api/ipam/ip-addresses/", params={
        "address": cidr,
        "namespace": namespace_id,
    })
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if results:
        return results[0]

    resp = _api(client, "POST", "/api/ipam/ip-addresses/", json={
        "address": cidr,
        "namespace": namespace_id,
        "status": status_id,
    })
    resp.raise_for_status()
    return resp.json()


def _assign_ip_to_interface(client: _ApiClient, interface_id: str, ip_id: str) -> None:
    """Assign an IP address to an interface via the IPAddressToInterface through table."""
    resp = _api(client, "GET", "/api/ipam/ip-address-to-interface/", params={
        "ip_address": ip_id,
        "interface": interface_id,
    })
    resp.raise_for_status()
    if resp.json().get("count", 0) > 0:
        return

    _api(client, "POST", "/api/ipam/ip-address-to-interface/", json={
        "ip_address": ip_id,
        "interface": interface_id,
    }).raise_for_status()


def _set_primary_ip4(client: _ApiClient, device_id: str, ip_id: str) -> None:
    _api(client, "PATCH", f"/api/dcim/devices/{device_id}/", json={
        "primary_ip4": {"id": ip_id},
    }).raise_for_status()


def wire_device(
    client: _ApiClient,
    device_name: str,
    service_ip: str,
    namespace_id: str,
    status_id: str,
) -> WireResult:
    """Wire a single mock device's primary IP to its service ClusterIP."""
    device = _get_device(client, device_name)
    if not device:
        return WireResult(device_name, service_ip, False, f"Device '{device_name}' not found in Nautobot")

    device_id = device["id"]

    intf = _get_or_create_interface(client, device_id, status_id)
    ip_obj = _get_or_create_ip(client, service_ip, namespace_id, status_id)
    _assign_ip_to_interface(client, intf["id"], ip_obj["id"])
    _set_primary_ip4(client, device_id, ip_obj["id"])

    return WireResult(device_name, service_ip, True, f"primary_ip4 -> {service_ip}")


def wire_all_devices(
    nautobot_url: str,
    nautobot_token: str,
    device_map: list[dict[str, str | int]] | None = None,
) -> list[WireResult]:
    """Wire all mock devices to their Kubernetes service IPs in Nautobot."""
    if device_map is None:
        device_map = DEFAULT_DEVICE_MAP

    client = _ApiClient(
        base_url=nautobot_url,
        headers={"Authorization": f"Token {nautobot_token}", "Content-Type": "application/json"},
        timeout=30,
    )

    results: list[WireResult] = []

    try:
        ns = _get_or_create_namespace(client)
        namespace_id = ns["id"]
        logger.info("Using namespace '%s' (id=%s)", SANDBOX_NAMESPACE, namespace_id)

        status_id = _get_status_id(client, "Active")

        _get_or_create_prefix(client, namespace_id, status_id)
        logger.info("Ensured prefix %s exists in namespace '%s'", SANDBOX_PREFIX, SANDBOX_NAMESPACE)

        for entry in device_map:
            device_name = str(entry["device_name"])
            service_name = str(entry["service_name"])
            port = int(entry["port"])

            try:
                service_ip = _resolve_service(service_name, port)
                logger.info("Resolved %s -> %s", service_name, service_ip)
            except RuntimeError as e:
                results.append(WireResult(device_name, "", False, str(e)))
                continue

            result = wire_device(client, device_name, service_ip, namespace_id, status_id)
            results.append(result)
            if result.success:
                logger.info("Wired %s -> %s", device_name, service_ip)
            else:
                logger.error("Failed to wire %s: %s", device_name, result.message)

    finally:
        client.close()

    return results
