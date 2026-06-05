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
"""CLI entrypoint for mock network devices."""

from __future__ import annotations

import json
import logging
import os
import sys
from pathlib import Path

import click

from mock_device.config import DeviceConfig
from mock_device.device_api.server import run_server
from mock_device.dhcp_client import run_dhcp_transaction, validate_dhcp_config
from mock_device.fixture_generator import generate_for_device
from mock_device.wire_nautobot import wire_all_devices
from mock_device.ztp_client import validate_ztp_flow

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("mock-device")


@click.group()
def cli() -> None:
    """Mock network device toolkit for NVIDIA Config Manager sandbox testing."""


@cli.command()
@click.option("--name", envvar="MOCK_DEVICE_NAME", default="mock-device-1", help="Device hostname")
@click.option(
    "--platform",
    envvar="MOCK_DEVICE_PLATFORM",
    default="cumulus",
    type=click.Choice(["cumulus", "arista", "nvos", "mellanox"]),
    help="Device platform",
)
@click.option("--mac", envvar="MOCK_DEVICE_MAC", default=None, help="MAC address")
@click.option("--serial", envvar="MOCK_DEVICE_SERIAL", default="", help="Serial number")
@click.option("--os-version", envvar="MOCK_DEVICE_OS_VERSION", default="", help="OS version for fixtures")
@click.option("--port", envvar="MOCK_DEVICE_API_PORT", default=0, type=int, help="API port")
def serve(name: str, platform: str, mac: str | None, serial: str, os_version: str, port: int) -> None:
    """Run the mock device API server (EAPI or NVUE)."""
    kwargs: dict = {"name": name, "platform": platform, "serial": serial, "os_version": os_version}
    if mac:
        kwargs["mac_address"] = mac
    if port:
        kwargs["api_port"] = port
    device = DeviceConfig(**kwargs)

    logger.info(
        "Starting mock %s device: name=%s mac=%s serial=%s os_version=%s",
        device.platform,
        device.name,
        device.mac_address,
        device.serial or "(none)",
        device.os_version or "(none)",
    )
    run_server(device)


@cli.command()
@click.option("--name", envvar="MOCK_DEVICE_NAME", default="mock-device-1", help="Device hostname")
@click.option("--platform", envvar="MOCK_DEVICE_PLATFORM", default="cumulus")
@click.option("--mac", envvar="MOCK_DEVICE_MAC", default=None, help="MAC address")
@click.option("--serial", envvar="MOCK_DEVICE_SERIAL", default="", help="Serial number")
@click.option(
    "--dhcp-server",
    envvar="MOCK_DHCP_SERVER",
    required=True,
    help="Kea DHCP server IP or hostname",
)
@click.option(
    "--relay-gateway",
    envvar="MOCK_DHCP_RELAY_GATEWAY",
    default="",
    help="Gateway IP for DHCP relay (giaddr)",
)
@click.option(
    "--client-id-template",
    envvar="MOCK_DHCP_CLIENT_ID_TEMPLATE",
    default="",
    help="Jinja2 template for client-id",
)
@click.option("--iface", default="eth0", help="Network interface")
@click.option("--timeout", default=10, type=int, help="Response timeout in seconds")
@click.option("--broadcast", is_flag=True, help="Use L2 broadcast instead of unicast")
@click.option("--expected-ip", default="", help="Expected IP (warn on mismatch)")
def dhcp(
    name: str,
    platform: str,
    mac: str | None,
    serial: str,
    dhcp_server: str,
    relay_gateway: str,
    client_id_template: str,
    iface: str,
    timeout: int,
    broadcast: bool,
    expected_ip: str,
) -> None:
    """Send DHCP DISCOVER/REQUEST and display the result."""
    kwargs: dict = {
        "name": name,
        "platform": platform,
        "serial": serial,
        "dhcp_server": dhcp_server,
        "relay_gateway": relay_gateway,
        "client_id_template": client_id_template,
        "management_ip": expected_ip,
    }
    if mac:
        kwargs["mac_address"] = mac
    device = DeviceConfig(**kwargs)

    result = run_dhcp_transaction(device, iface=iface, timeout=timeout, use_broadcast=broadcast)

    output = {
        "device": device.name,
        "mac": device.mac_address,
        "serial": device.serial or None,
        "success": result.success,
        "message_type": result.message_type,
        "offered_ip": result.offered_ip,
        "server_id": result.server_id,
        "options": result.options,
        "error": result.error or None,
    }
    click.echo(json.dumps(output, indent=2))
    sys.stdout.flush()

    os._exit(0 if result.success else 1)


@cli.command()
@click.option("--name", envvar="MOCK_DEVICE_NAME", default="mock-device-1", help="Device hostname")
@click.option("--platform", envvar="MOCK_DEVICE_PLATFORM", default="cumulus")
@click.option("--mac", envvar="MOCK_DEVICE_MAC", default=None, help="MAC address")
@click.option("--serial", envvar="MOCK_DEVICE_SERIAL", default="", help="Serial number")
@click.option(
    "--client-id-template",
    envvar="MOCK_DHCP_CLIENT_ID_TEMPLATE",
    default="",
    help="Jinja2 template for client-id",
)
@click.option(
    "--dhcp-api-url",
    envvar="MOCK_DHCP_API_URL",
    required=True,
    help="DHCP API base URL (e.g. https://dhcp.nv-config-manager.local)",
)
def validate(
    name: str,
    platform: str,
    mac: str | None,
    serial: str,
    client_id_template: str,
    dhcp_api_url: str,
) -> None:
    """Validate DHCP config via the Kea API (no packets sent).

    Checks that the device has a matching reservation in the Kea config.
    """
    kwargs: dict = {
        "name": name,
        "platform": platform,
        "serial": serial,
        "client_id_template": client_id_template,
    }
    if mac:
        kwargs["mac_address"] = mac
    device = DeviceConfig(**kwargs)

    result = validate_dhcp_config(device, dhcp_api_url)

    output = {
        "device": device.name,
        "mac": device.mac_address,
        "serial": device.serial or None,
        "client_id_hex": device.client_id.hex() if device.client_id else None,
        "success": result.success,
        "message_type": result.message_type,
        "offered_ip": result.offered_ip,
        "match_info": result.options,
        "error": result.error or None,
    }
    click.echo(json.dumps(output, indent=2))
    sys.stdout.flush()

    os._exit(0 if result.success else 1)


@cli.command("ztp-validate")
@click.option("--name", envvar="MOCK_DEVICE_NAME", default="mock-device-1", help="Device hostname")
@click.option("--platform", envvar="MOCK_DEVICE_PLATFORM", default="cumulus")
@click.option("--mac", envvar="MOCK_DEVICE_MAC", default=None, help="MAC address")
@click.option("--serial", envvar="MOCK_DEVICE_SERIAL", default="", help="Serial number")
@click.option(
    "--client-id-template",
    envvar="MOCK_DHCP_CLIENT_ID_TEMPLATE",
    default="",
    help="Jinja2 template for client-id",
)
@click.option(
    "--dhcp-api-url",
    envvar="MOCK_DHCP_API_URL",
    required=True,
    help="DHCP API base URL",
)
@click.option(
    "--ztp-api-url",
    envvar="MOCK_ZTP_API_URL",
    required=True,
    help="ZTP API base URL (internal, port 9000)",
)
@click.option("--skip-serial", is_flag=True, help="Skip serial validation step")
def ztp_validate(
    name: str,
    platform: str,
    mac: str | None,
    serial: str,
    client_id_template: str,
    dhcp_api_url: str,
    ztp_api_url: str,
    skip_serial: bool,
) -> None:
    """Validate end-to-end ZTP provisioning chain.

    Checks DHCP reservation for ZTP options, fetches boot script from the ZTP
    service, validates the serial number, and retrieves config from Config Store.
    """
    kwargs: dict = {
        "name": name,
        "platform": platform,
        "serial": serial,
        "client_id_template": client_id_template,
    }
    if mac:
        kwargs["mac_address"] = mac
    device = DeviceConfig(**kwargs)

    result = validate_ztp_flow(device, dhcp_api_url, ztp_api_url, skip_serial=skip_serial)

    output = {
        "device": result.device_name,
        "success": result.success,
        "device_uuid": result.device_uuid or None,
        "offered_ip": result.offered_ip or None,
        "boot_file_url": result.boot_file_url or None,
        "provision_url": result.provision_url or None,
        "steps": [
            {
                "step": s.step,
                "success": s.success,
                "message": s.message,
                "details": s.details or None,
            }
            for s in result.steps
        ],
    }
    click.echo(json.dumps(output, indent=2))
    sys.stdout.flush()

    os._exit(0 if result.success else 1)


@cli.command()
@click.option(
    "--nautobot-url",
    envvar="NAUTOBOT_URL",
    default="http://nv-config-manager-nautobot.nv-config-manager.svc:80",
    help="Nautobot API base URL",
)
@click.option(
    "--nautobot-token",
    envvar="NAUTOBOT_TOKEN",
    required=True,
    help="Nautobot API token",
)
def wire(nautobot_url: str, nautobot_token: str) -> None:
    """Wire mock device service IPs into Nautobot.

    Resolves each mock device's Kubernetes Service ClusterIP and updates
    Nautobot so the device's primary_ip4 points to the mock service.
    This allows Temporal workflows to reach mock devices.
    """
    logger.info("Wiring mock devices into Nautobot at %s", nautobot_url)
    results = wire_all_devices(nautobot_url, nautobot_token)

    all_ok = True
    for r in results:
        status = "OK" if r.success else "FAIL"
        icon = "+" if r.success else "-"
        click.echo(f"  [{icon}] {r.device_name}: {status} — {r.message}")
        if not r.success:
            all_ok = False

    if all_ok:
        click.echo("\nAll mock devices wired successfully.")
    else:
        click.echo("\nSome devices failed to wire. Check logs above.")
        sys.exit(1)


@cli.command("generate-fixtures")
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--output-dir",
    type=click.Path(),
    default=None,
    help="Fixture output directory (default: development/mock_devices/fixtures/)",
)
@click.option(
    "--device-overrides",
    is_flag=True,
    help="Also write per-device override fixtures (e.g. LLDP neighbors)",
)
def generate_fixtures(path: str, output_dir: str | None, device_overrides: bool) -> None:
    """Generate fixture files from topology device JSON.

    PATH can be a single device JSON file or a directory of them.
    Reads each device's platform and intended-firmware version from the JSON,
    then writes version-specific fixture files to the fixtures directory.
    """
    target = Path(path)
    out = Path(output_dir) if output_dir else None
    files: list[Path] = []

    if target.is_file():
        files = [target]
    elif target.is_dir():
        files = sorted(target.glob("*.json"))
    else:
        click.echo(f"Error: {path} is not a file or directory", err=True)
        sys.exit(1)

    if not files:
        click.echo(f"No JSON files found in {path}", err=True)
        sys.exit(1)

    total_written: list[Path] = []
    for f in files:
        click.echo(f"Processing {f.name}...")
        written = generate_for_device(f, output_dir=out, device_overrides=device_overrides)
        total_written.extend(written)
        for w in written:
            click.echo(f"  -> {w}")

    click.echo(f"\nGenerated {len(total_written)} fixture files from {len(files)} device(s).")


if __name__ == "__main__":
    cli()
