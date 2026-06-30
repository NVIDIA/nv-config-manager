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
"""Mock DHCP client for Kubernetes sandbox testing.

Sends DHCP DISCOVER/REQUEST packets to a Kea server and validates the response.
Uses standard UDP sockets (not raw L2) so packets route correctly through
Kubernetes ClusterIP services. Scapy is used only for BOOTP/DHCP encoding/decoding.
The giaddr field simulates a relay agent so Kea can match the correct subnet.
"""

from __future__ import annotations

import fcntl
import logging
import secrets
import socket
import struct
import time
from dataclasses import dataclass, field

import requests
from scapy.layers.dhcp import BOOTP, DHCP  # type: ignore[import-untyped]

from mock_device.config import DeviceConfig

logger = logging.getLogger(__name__)


@dataclass
class DhcpResult:
    """Result of a DHCP transaction."""

    success: bool
    message_type: str = ""
    offered_ip: str = ""
    server_id: str = ""
    options: dict[str, str] = field(default_factory=dict)
    raw_response: bytes = b""
    error: str = ""


def _get_pod_ip() -> str:
    """Get this pod's IP address by connecting to a known destination."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("10.96.0.1", 53))
        return str(s.getsockname()[0])
    except Exception:
        return "0.0.0.0"
    finally:
        s.close()


def _build_bootp_dhcp_payload(
    device: DeviceConfig,
    message_type: str = "discover",
    offered_ip: str = "",
    server_id: str = "",
    giaddr: str = "",
) -> tuple[bytes, int]:
    """Build raw BOOTP+DHCP bytes using Scapy for encoding.

    Returns (payload_bytes, transaction_id).
    """
    xid = secrets.randbits(32)

    bootp_kwargs: dict = {
        "chaddr": device.mac_bytes + b"\x00" * 10,
        "xid": xid,
        "flags": 0x0000,
    }
    relay = giaddr or device.relay_gateway
    if relay:
        bootp_kwargs["giaddr"] = relay

    options: list = []
    if message_type == "discover":
        options.append(("message-type", 1))
    elif message_type == "request":
        options.append(("message-type", 3))
        if offered_ip:
            options.append(("requested_addr", offered_ip))
        if server_id:
            options.append(("server_id", server_id))

    options.append(("hostname", device.name))

    client_id = device.client_id
    if client_id:
        options.append(("client_id", client_id))

    options.append(("param_req_list", [1, 3, 15, 67]))
    options.append("end")

    pkt = BOOTP(**bootp_kwargs) / DHCP(options=options)
    return bytes(pkt), xid


def _parse_bootp_dhcp_response(data: bytes, expected_xid: int) -> DhcpResult:
    """Parse raw BOOTP+DHCP response bytes."""
    try:
        pkt = BOOTP(data)

        if pkt.xid != expected_xid:
            return DhcpResult(
                success=False, error=f"XID mismatch: got {pkt.xid:#x}, expected {expected_xid:#x}"
            )

        offered_ip = pkt.yiaddr if pkt.yiaddr != "0.0.0.0" else ""

        if not pkt.haslayer(DHCP):
            return DhcpResult(success=False, error="Response has no DHCP options layer")

        dhcp_options: dict[str, str] = {}
        msg_type = ""
        for opt in pkt[DHCP].options:
            if isinstance(opt, tuple) and len(opt) >= 2:
                key, val = opt[0], opt[1]
                if key == "message-type":
                    type_map = {2: "offer", 5: "ack", 6: "nak"}
                    msg_type = type_map.get(val, f"unknown({val})")
                elif key == "server_id":
                    dhcp_options["server_id"] = str(val)
                elif key == "boot-file-name":
                    dhcp_options["boot_file"] = (
                        val if isinstance(val, str) else val.decode(errors="replace")
                    )
                elif isinstance(val, bytes):
                    dhcp_options[key] = val.decode(errors="replace")
                else:
                    dhcp_options[key] = str(val)

        return DhcpResult(
            success=msg_type in ("offer", "ack"),
            message_type=msg_type,
            offered_ip=offered_ip,
            server_id=dhcp_options.get("server_id", ""),
            options=dhcp_options,
            raw_response=data,
        )
    except Exception as exc:
        return DhcpResult(success=False, error=f"Failed to parse response: {exc}")


_SIOCGIFADDR = 0x8915


def _get_iface_ip(iface: str) -> str:
    """Return the IPv4 address of *iface*, falling back to the pod IP on error."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        result = fcntl.ioctl(s.fileno(), _SIOCGIFADDR, struct.pack("256s", iface.encode()[:15]))
        return socket.inet_ntoa(result[20:24])
    except OSError:
        return _get_pod_ip()
    finally:
        s.close()


def _resolve_server(server: str) -> str:
    """Resolve hostname to IP address."""
    try:
        return str(socket.getaddrinfo(server, 67, socket.AF_INET)[0][4][0])
    except socket.gaierror as exc:
        raise RuntimeError(f"Cannot resolve DHCP server '{server}': {exc}") from exc


def send_dhcp_discover(
    device: DeviceConfig,
    timeout: int = 10,
    iface: str = "eth0",
    use_broadcast: bool = False,
) -> DhcpResult:
    """Send a DHCP DISCOVER via UDP and wait for an OFFER.

    When *use_broadcast* is False (default), acts as a relay agent: sets giaddr
    to the *iface* IP so Kea unicasts the response back on port 67, avoiding
    broadcast issues in Kubernetes overlay networks.

    When *use_broadcast* is True, sends to 255.255.255.255 without giaddr so
    Kea broadcasts the response (useful outside overlay networks).
    """
    if use_broadcast:
        server_ip = "255.255.255.255"
        giaddr = ""
        bind_ip = "0.0.0.0"
    else:
        server_ip = _resolve_server(device.dhcp_server) if device.dhcp_server else "255.255.255.255"
        iface_ip = _get_iface_ip(iface)
        giaddr = device.relay_gateway or iface_ip
        bind_ip = iface_ip

    payload, xid = _build_bootp_dhcp_payload(device, "discover", giaddr=giaddr)

    logger.info(
        "Sending DHCP DISCOVER: device=%s mac=%s serial=%s server=%s giaddr=%s xid=%#x",
        device.name,
        device.mac_address,
        device.serial or "(none)",
        server_ip,
        giaddr or "(broadcast)",
        xid,
    )

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout)

    try:
        sock.bind((bind_ip, 67))
        sock.sendto(payload, (server_ip, 67))
        logger.info(
            "DHCP DISCOVER sent (%d bytes) to %s:67 (relay giaddr=%s)",
            len(payload),
            server_ip,
            giaddr,
        )

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            remaining = max(0.1, deadline - time.monotonic())
            sock.settimeout(remaining)
            try:
                data, addr = sock.recvfrom(4096)
                logger.info("Received %d bytes from %s", len(data), addr)
                result = _parse_bootp_dhcp_response(data, xid)
                if result.message_type in ("offer", "ack", "nak"):
                    return result
            except TimeoutError:
                break

        return DhcpResult(
            success=False, error=f"No DHCP response within {timeout}s from {server_ip}"
        )
    except OSError as exc:
        return DhcpResult(success=False, error=f"Socket error (DISCOVER): {exc}")
    finally:
        sock.close()


def send_dhcp_request(
    device: DeviceConfig,
    offered_ip: str,
    server_id: str,
    timeout: int = 10,
    iface: str = "eth0",
    use_broadcast: bool = False,
) -> DhcpResult:
    """Send a DHCP REQUEST for the offered IP and wait for ACK/NAK."""
    if use_broadcast:
        server_ip = "255.255.255.255"
        giaddr = ""
        bind_ip = "0.0.0.0"
    else:
        server_ip = _resolve_server(device.dhcp_server) if device.dhcp_server else "255.255.255.255"
        iface_ip = _get_iface_ip(iface)
        giaddr = device.relay_gateway or iface_ip
        bind_ip = iface_ip

    payload, xid = _build_bootp_dhcp_payload(
        device, "request", offered_ip, server_id, giaddr=giaddr
    )

    logger.info(
        "Sending DHCP REQUEST: device=%s requested_ip=%s server=%s giaddr=%s",
        device.name,
        offered_ip,
        server_id,
        giaddr,
    )

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(timeout)

    try:
        sock.bind((bind_ip, 67))
        sock.sendto(payload, (server_ip, 67))

        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            remaining = max(0.1, deadline - time.monotonic())
            sock.settimeout(remaining)
            try:
                data, _ = sock.recvfrom(4096)
                result = _parse_bootp_dhcp_response(data, xid)
                if result.message_type in ("ack", "nak"):
                    return result
            except TimeoutError:
                break

        return DhcpResult(success=False, error=f"No DHCP ACK/NAK within {timeout}s")
    except OSError as exc:
        return DhcpResult(success=False, error=f"Socket error (REQUEST): {exc}")
    finally:
        sock.close()


def run_dhcp_transaction(
    device: DeviceConfig,
    iface: str = "eth0",
    timeout: int = 10,
    use_broadcast: bool = False,
) -> DhcpResult:
    """Run a full DHCP DORA transaction (Discover -> Offer -> Request -> Ack)."""
    logger.info("Starting DHCP transaction for %s", device.name)

    discover_result = send_dhcp_discover(device, timeout, iface=iface, use_broadcast=use_broadcast)
    if not discover_result.success:
        logger.error("DHCP DISCOVER failed for %s: %s", device.name, discover_result.error)
        return discover_result

    logger.info(
        "Got DHCP OFFER for %s: ip=%s server=%s",
        device.name,
        discover_result.offered_ip,
        discover_result.server_id,
    )

    request_result = send_dhcp_request(
        device,
        discover_result.offered_ip,
        discover_result.server_id,
        timeout,
        iface=iface,
        use_broadcast=use_broadcast,
    )
    if not request_result.success:
        logger.error("DHCP REQUEST failed for %s: %s", device.name, request_result.error)
        return request_result

    logger.info(
        "DHCP ACK for %s: ip=%s options=%s",
        device.name,
        request_result.offered_ip,
        request_result.options,
    )

    if device.management_ip and request_result.offered_ip != device.management_ip:
        logger.warning(
            "IP mismatch for %s: expected=%s got=%s",
            device.name,
            device.management_ip,
            request_result.offered_ip,
        )

    return request_result


def validate_dhcp_config(
    device: DeviceConfig,
    dhcp_api_url: str,
) -> DhcpResult:
    """Validate DHCP configuration via the Kea API without sending packets.

    Queries the DHCP API and checks that a reservation exists for this device.
    """
    logger.info("Validating DHCP config for %s via API at %s", device.name, dhcp_api_url)

    try:
        response = requests.get(f"{dhcp_api_url}/config", params={"ip_version": 4}, timeout=30)
        response.raise_for_status()
    except requests.RequestException as exc:
        return DhcpResult(success=False, error=f"Failed to query DHCP API: {exc}")

    try:
        config = response.json()
    except ValueError as exc:
        return DhcpResult(
            success=False,
            error=(
                f"Failed to parse DHCP API response as JSON: {exc} "
                f"(status={response.status_code}, body={response.text[:200]!r})"
            ),
        )

    dhcp4 = None
    if isinstance(config, list) and len(config) > 0:
        first = config[0]
        if "arguments" in first and "Dhcp4" in first["arguments"]:
            dhcp4 = first["arguments"]["Dhcp4"]
    elif isinstance(config, dict) and "Dhcp4" in config:
        dhcp4 = config["Dhcp4"]

    if not dhcp4:
        return DhcpResult(success=False, error="No Dhcp4 configuration found")

    all_reservations = list(dhcp4.get("reservations", []))
    for subnet in dhcp4.get("subnet4", []):
        all_reservations.extend(subnet.get("reservations", []))

    mac_lower = device.mac_address.lower()
    client_id_hex = device.client_id.hex() if device.client_id else ""
    client_id_colon = ":".join(f"{b:02x}" for b in device.client_id) if device.client_id else ""

    for reservation in all_reservations:
        hw = reservation.get("hw-address", "").lower()
        cid = reservation.get("client-id", "").lower()

        if hw and hw == mac_lower:
            return DhcpResult(
                success=True,
                message_type="reservation-match",
                offered_ip=reservation.get("ip-address", ""),
                options={"match_type": "hw-address", "hostname": reservation.get("hostname", "")},
            )

        if cid and client_id_hex:
            cid_normalized = cid.replace(":", "").lower()
            if cid_normalized == client_id_hex.lower() or cid.lower() == client_id_colon:
                return DhcpResult(
                    success=True,
                    message_type="reservation-match",
                    offered_ip=reservation.get("ip-address", ""),
                    options={
                        "match_type": "client-id",
                        "hostname": reservation.get("hostname", ""),
                    },
                )

    subnet_count = len(dhcp4.get("subnet4", []))
    pool_count = sum(len(s.get("pools", [])) for s in dhcp4.get("subnet4", []))

    return DhcpResult(
        success=False,
        error=(
            f"No matching reservation found for device {device.name} "
            f"(mac={mac_lower}, client_id={client_id_colon or '(none)'}). "
            f"Config has {len(all_reservations)} reservations, "
            f"{subnet_count} subnets, {pool_count} pools."
        ),
    )
