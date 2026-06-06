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
"""ZTP validation client for Kubernetes sandbox testing.

Validates the end-to-end ZTP provisioning chain by:
1. Checking DHCP reservations for boot-file-name / cumulus-provision-url options
2. Fetching the boot script from the ZTP service
3. Validating the device serial number against Nautobot (via ZTP)
4. Fetching config files from the ZTP service (which reads from Config Store)

"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, cast

import requests

from mock_device.config import DeviceConfig

logger = logging.getLogger(__name__)

MOCK_AUTH_HEADERS = {
    "X-Auth-Request-Email": "dev@localhost",
    "X-Auth-Request-User": "dev@localhost",
    "X-Auth-Request-Groups": "nv-config-manager",
}


@dataclass
class ZtpStepResult:
    """Result of a single ZTP validation step."""

    step: str
    success: bool
    message: str
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class ZtpValidationResult:
    """Aggregate result of the full ZTP validation chain."""

    device_name: str
    success: bool
    steps: list[ZtpStepResult] = field(default_factory=list)
    boot_file_url: str = ""
    provision_url: str = ""
    device_uuid: str = ""
    offered_ip: str = ""


def _extract_dhcp4(config: Any) -> dict | None:
    """Extract the Dhcp4 config block from a Kea API response."""
    if isinstance(config, list) and len(config) > 0:
        first = config[0]
        if "arguments" in first and "Dhcp4" in first["arguments"]:
            return cast(dict[Any, Any], first["arguments"]["Dhcp4"])
    elif isinstance(config, dict) and "Dhcp4" in config:
        return cast(dict[Any, Any], config["Dhcp4"])
    return None


def _find_reservation(dhcp4: dict, device: DeviceConfig) -> tuple[dict | None, str]:
    """Find a DHCP reservation matching the device. Returns (reservation, match_type)."""
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
            return reservation, "hw-address"

        if cid and client_id_hex:
            cid_normalized = cid.replace(":", "").lower()
            if cid_normalized == client_id_hex.lower() or cid.lower() == client_id_colon:
                return reservation, "client-id"

    return None, ""


def _extract_option(reservation: dict, option_name: str) -> str:
    """Extract a named option from a reservation's option-data list."""
    for opt in reservation.get("option-data", []):
        if opt.get("name") == option_name:
            return cast(str, opt.get("data", ""))
    return ""


def _parse_device_uuid_from_url(url: str) -> str:
    """Extract the device UUID from a ZTP URL like http://host/v1/device/<uuid>/onie."""
    match = re.search(r"/v1/device/([0-9a-f-]+)/", url)
    return match.group(1) if match else ""


def validate_ztp_flow(
    device: DeviceConfig,
    dhcp_api_url: str,
    ztp_api_url: str,
    skip_serial: bool = False,
) -> ZtpValidationResult:
    """Validate the full ZTP provisioning chain for a mock device.

    Steps:
    1. Query DHCP API for reservation with boot-file-name
    2. Fetch boot script from ZTP service
    3. Validate serial number via ZTP service
    4. Fetch a config file via ZTP service
    """
    result = ZtpValidationResult(device_name=device.name, success=False)

    # Step 1: Check DHCP reservation and ZTP options
    step1 = _step_dhcp_reservation(device, dhcp_api_url, result)
    result.steps.append(step1)
    if not step1.success:
        return result

    # Step 2: Fetch boot script from ZTP
    step2 = _step_fetch_boot_script(result, ztp_api_url)
    result.steps.append(step2)
    if not step2.success:
        return result

    # Step 3: Validate serial number
    if not skip_serial and device.serial:
        step3 = _step_validate_serial(device, result, ztp_api_url)
        result.steps.append(step3)
        if not step3.success:
            return result

    # Step 4: Fetch config from ZTP (boot-script configlet)
    step4 = _step_fetch_config(result, ztp_api_url)
    result.steps.append(step4)
    if not step4.success:
        return result

    result.success = True
    return result


def _step_dhcp_reservation(
    device: DeviceConfig, dhcp_api_url: str, result: ZtpValidationResult
) -> ZtpStepResult:
    """Step 1: Find DHCP reservation and extract ZTP options."""
    try:
        resp = requests.get(f"{dhcp_api_url}/config", params={"ip_version": 4}, timeout=30)
        resp.raise_for_status()
    except requests.RequestException as exc:
        return ZtpStepResult(
            step="dhcp-reservation",
            success=False,
            message=f"Failed to query DHCP API: {exc}",
        )

    dhcp4 = _extract_dhcp4(resp.json())
    if not dhcp4:
        return ZtpStepResult(
            step="dhcp-reservation",
            success=False,
            message="No Dhcp4 configuration found in DHCP API response",
        )

    reservation, match_type = _find_reservation(dhcp4, device)
    if not reservation:
        return ZtpStepResult(
            step="dhcp-reservation",
            success=False,
            message=f"No DHCP reservation found for {device.name}",
        )

    result.offered_ip = reservation.get("ip-address", "")
    boot_file = _extract_option(reservation, "boot-file-name")
    provision_url = _extract_option(reservation, "cumulus-provision-url")

    if not boot_file and not provision_url:
        return ZtpStepResult(
            step="dhcp-reservation",
            success=False,
            message=(
                f"Reservation found (match={match_type}, ip={result.offered_ip}) "
                "but no boot-file-name or cumulus-provision-url option"
            ),
            details={"match_type": match_type, "ip": result.offered_ip},
        )

    result.boot_file_url = boot_file
    result.provision_url = provision_url
    result.device_uuid = _parse_device_uuid_from_url(boot_file or provision_url)

    return ZtpStepResult(
        step="dhcp-reservation",
        success=True,
        message=f"Reservation found: ip={result.offered_ip}, uuid={result.device_uuid}",
        details={
            "match_type": match_type,
            "ip": result.offered_ip,
            "boot_file_name": boot_file,
            "cumulus_provision_url": provision_url,
            "device_uuid": result.device_uuid,
        },
    )


def _step_fetch_boot_script(result: ZtpValidationResult, ztp_api_url: str) -> ZtpStepResult:
    """Step 2: Fetch the boot script from the ZTP service."""
    if not result.device_uuid:
        return ZtpStepResult(
            step="fetch-boot-script",
            success=False,
            message="No device UUID extracted from DHCP options",
        )

    url = f"{ztp_api_url}/v1/device/{result.device_uuid}/boot-script"
    try:
        resp = requests.get(url, headers=MOCK_AUTH_HEADERS, timeout=30)
    except requests.RequestException as exc:
        return ZtpStepResult(
            step="fetch-boot-script",
            success=False,
            message=f"Failed to reach ZTP service: {exc}",
        )

    if resp.status_code == 404:
        return ZtpStepResult(
            step="fetch-boot-script",
            success=False,
            message=(
                f"Boot script not found (404) for device {result.device_uuid}. "
                "Ensure the device has a rendered boot-script in Config Store."
            ),
        )

    if resp.status_code >= 400:
        return ZtpStepResult(
            step="fetch-boot-script",
            success=False,
            message=f"ZTP returned {resp.status_code}: {resp.text[:200]}",
        )

    content = resp.text
    return ZtpStepResult(
        step="fetch-boot-script",
        success=True,
        message=f"Boot script retrieved ({len(content)} bytes)",
        details={"size_bytes": len(content), "preview": content[:200]},
    )


def _step_validate_serial(
    device: DeviceConfig, result: ZtpValidationResult, ztp_api_url: str
) -> ZtpStepResult:
    """Step 3: Validate the device serial via the ZTP API."""
    url = f"{ztp_api_url}/v1/device/{result.device_uuid}/validate_serial"
    try:
        resp = requests.post(
            url,
            json={"serial": device.serial},
            headers=MOCK_AUTH_HEADERS,
            timeout=30,
        )
    except requests.RequestException as exc:
        return ZtpStepResult(
            step="validate-serial",
            success=False,
            message=f"Failed to reach ZTP service: {exc}",
        )

    if resp.status_code == 400:
        return ZtpStepResult(
            step="validate-serial",
            success=False,
            message=f"Serial mismatch: {resp.text[:200]}",
            details={"serial_sent": device.serial},
        )

    if resp.status_code >= 400:
        return ZtpStepResult(
            step="validate-serial",
            success=False,
            message=f"ZTP returned {resp.status_code}: {resp.text[:200]}",
        )

    return ZtpStepResult(
        step="validate-serial",
        success=True,
        message=f"Serial '{device.serial}' matches Nautobot record",
        details={"serial": device.serial},
    )


def _step_fetch_config(result: ZtpValidationResult, ztp_api_url: str) -> ZtpStepResult:
    """Step 4: Fetch a config file from the ZTP service (reads from Config Store)."""
    if not result.device_uuid:
        return ZtpStepResult(
            step="fetch-config",
            success=False,
            message="No device UUID available",
        )

    url = f"{ztp_api_url}/v1/device/{result.device_uuid}/config/startup.yaml"
    try:
        resp = requests.get(url, headers=MOCK_AUTH_HEADERS, timeout=30)
    except requests.RequestException as exc:
        return ZtpStepResult(
            step="fetch-config",
            success=False,
            message=f"Failed to reach ZTP service: {exc}",
        )

    if resp.status_code == 404:
        return ZtpStepResult(
            step="fetch-config",
            success=False,
            message=(
                f"Config not found (404) for device {result.device_uuid}. "
                "Rendering is triggered automatically via NATS events after topology loads. "
                "Check the render consumer logs: kubectl logs -n nv-config-manager deploy/nv-config-manager-render-consumer-device"
            ),
        )

    if resp.status_code >= 400:
        return ZtpStepResult(
            step="fetch-config",
            success=False,
            message=f"ZTP returned {resp.status_code}: {resp.text[:200]}",
        )

    content = resp.text
    return ZtpStepResult(
        step="fetch-config",
        success=True,
        message=f"Config retrieved ({len(content)} bytes)",
        details={"size_bytes": len(content), "preview": content[:200]},
    )
