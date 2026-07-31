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
"""Network Device clients."""

from __future__ import annotations

import contextvars
import datetime
import ipaddress
import json
import logging
import re
import ssl
import sys
import threading
import time
from collections.abc import Callable
from copy import deepcopy
from io import BytesIO, StringIO
from typing import Any, cast
from uuid import uuid4

import netaddr
import paramiko
import pyeapi
import pyeapi.eapilib
import requests
import urllib3
from jnpr.junos import Device
from jnpr.junos.exception import (
    CommitError,
    ConfigLoadError,
    ConnectAuthError,
    ConnectError,
    LockError,
    ProbeError,
    RpcError,
    UnlockError,
)
from jnpr.junos.utils.config import Config
from netmiko import ConnectHandler  # type: ignore[import-untyped]
from netmiko.base_connection import BaseConnection  # type: ignore[import-untyped]
from netmiko.exceptions import NetmikoAuthenticationException  # type: ignore[import-untyped]
from pydantic import BaseModel
from pyeapi.client import Node
from requests.adapters import HTTPAdapter, Retry
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from temporalio.exceptions import ApplicationError

from nv_config_manager.common.config import load_config
from nv_config_manager.common.log import LogCategory, get_logger
from nv_config_manager.temporal.common.mixins.device import NetworkDeviceData, Platform
from nv_config_manager.temporal.common.secrets import (
    get_credential,
    get_rotation_passwords,
    resolve_config_section,
)

logger = get_logger(__name__, category=LogCategory.TEMPORAL_ACTIVITY)
logging.getLogger("paramiko").setLevel(logging.WARNING)

# Suppress SSL warnings for network devices which typically use self-signed certificates
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Commit-confirm rollback: 5 minutes. Arista uses HH:MM:SS; Cumulus uses seconds.
COMMIT_CONFIRM_ROLLBACK_SECONDS = 5 * 60


def is_mac_address(mac: str | None) -> bool:
    """Check if a string is a valid MAC address."""
    if mac is None:
        return False
    try:
        netaddr.EUI(mac)
        return True
    except netaddr.core.AddrFormatError:
        return False


def format_mac(mac: str) -> str:
    """Format a MAC address to colon-separated lowercase (e.g. 00:00:00:00:a3:42)."""
    return mac.replace("-", ":").lower()


class NetworkDeviceException(ApplicationError):
    """Exception when interacting with a network device."""


class DiffChangedException(NetworkDeviceException):
    """To be thrown if the approved diff is no longer valid."""


class InvalidConfigException(NetworkDeviceException):
    """To be thrown if the config cannot be applied."""


class ConfigApplyFailureException(NetworkDeviceException):
    """To be thrown when config apply fails with ignore_fail state."""

    @staticmethod
    def format_nvue_apply_error(transition_data: dict[str, Any]) -> str:
        """Format NVUE API transition error into human-readable string."""
        if not transition_data or "issue" not in transition_data or not transition_data["issue"]:
            msg = f"Configuration apply failed: {json.dumps(transition_data)}"
            return msg

        formatted_errors = []
        for issue_data in transition_data["issue"].values():
            code = issue_data.get("code", "unknown")
            message = issue_data.get("message", "No message provided")
            severity = issue_data.get("severity", "unknown")
            formatted_errors.append(f"[{severity.upper()}] {code}: {message}")

        error_summary = "\n".join(formatted_errors)
        progress = transition_data.get("progress", "Configuration apply failed")
        return f"{progress}\n\n{error_summary}"


class ConfigSyntaxException(ApplicationError):
    """To be thrown for syntactically invalid config."""

    def __init__(self, message: str) -> None:
        """Initialize with a stable Temporal failure type for retry policies."""
        super().__init__(message, type="ConfigSyntaxException")

    @staticmethod
    def format_nvue_error(error_json: dict[str, Any]) -> str:
        """Formats an NVUE API error response into a human-readable string."""
        if (
            not error_json
            or "validation" not in error_json
            or "selected_errors" not in error_json["validation"]
        ):
            return f"Unknown NVUE API error: {json.dumps(error_json)}"

        errors = error_json["validation"]["selected_errors"]
        if not errors:
            return f"Unknown NVUE API error details: {json.dumps(error_json)}"

        formatted_errors = []
        for error in errors:
            error_message = error.get("error", "Unknown error")
            location = error.get("instanceLocation", "Unknown location")
            formatted_errors.append(f"Error at '{location}': {error_message}")

        return "\n".join(formatted_errors)


class DiffValidationError(NetworkDeviceException):
    """Exception for diff validation failures with detailed information."""

    def __init__(
        self,
        message: str,
        invalid_diff: str,
        valid_lines: list[str] | None = None,
        device_name: str | None = None,
        username: str | None = None,
    ) -> None:
        super().__init__(message, non_retryable=True)
        self.invalid_diff = invalid_diff
        self.device_name = device_name
        self.username = username


class DeviceMacEntry(BaseModel):
    """Represents a MAC address table entry."""

    mac: str
    interface: str
    age: int
    vlan: int | None = None

    @staticmethod
    def from_nvue(data: dict[str, Any]) -> DeviceMacEntry:
        """Produce a MAC entry from NVUE API JSON."""
        return DeviceMacEntry(
            mac=str(netaddr.EUI(data["mac"])),
            interface=data["interface"],
            vlan=data.get("vlan"),
            age=int(data["last-update"]) if data.get("last-update") else sys.maxsize,
        )

    @staticmethod
    def from_eapi(data: dict[str, Any]) -> DeviceMacEntry:
        """Produce a MAC entry from PYEAPI JSON."""
        return DeviceMacEntry(
            mac=str(netaddr.EUI(data["macAddress"])),
            vlan=data["vlanId"],
            interface=data["interface"],
            age=int(
                datetime.datetime.now().timestamp() - data["lastMove"]
                if data.get("lastMove")
                else sys.maxsize
            ),
        )


class DeviceArpTable(BaseModel):
    """Device ARP Table."""

    ip_to_mac: dict[str, list[str]] = {}
    mac_to_ip: dict[str, list[str]] = {}
    interface_to_mac: dict[str, list[str]] = {}

    def _add_ip_mac_mapping(self, ip_std: str, mac_std: str) -> None:
        """Add IP to MAC and MAC to IP mappings."""
        if ip_std not in self.ip_to_mac:
            self.ip_to_mac[ip_std] = []
        if mac_std not in self.mac_to_ip:
            self.mac_to_ip[mac_std] = []
        self.ip_to_mac[ip_std].append(mac_std)
        self.mac_to_ip[mac_std].append(ip_std)

    def _add_interface_mac_mapping(self, interface: str, mac_std: str) -> None:
        """Add interface to MAC mapping."""
        if interface not in self.interface_to_mac:
            self.interface_to_mac[interface] = []
        if mac_std not in self.interface_to_mac[interface]:
            self.interface_to_mac[interface].append(mac_std)

    def _process_eapi_neighbor(self, neighbor: dict[str, Any]) -> None:
        """Process a single EAPI neighbor entry."""
        if not (
            neighbor.get("address") and neighbor.get("hwAddress") and neighbor.get("interface")
        ):
            logger.warning("ARP entry missing data, skipping: %s", neighbor)
            return

        ip_std = str(ipaddress.ip_address(neighbor["address"]))
        mac_std = str(netaddr.EUI(neighbor["hwAddress"]))

        self._add_ip_mac_mapping(ip_std, mac_std)

        for interface in neighbor["interface"].split(","):
            interface = interface.strip()
            self._add_interface_mac_mapping(interface, mac_std)

    @staticmethod
    def from_eapi(data: dict[str, list[dict[str, Any]]]) -> DeviceArpTable:
        """ARP table from EAPI."""
        result = DeviceArpTable()

        for neighbor in data.get("ipV4Neighbors", []):
            result._process_eapi_neighbor(neighbor)

        return result

    @staticmethod
    def from_nvue(data: dict[str, dict[str, Any]]) -> DeviceArpTable:
        """ARP table from NVUE API."""
        result = DeviceArpTable()
        for interface, item in data.items():
            result.interface_to_mac[interface] = []
            for ipaddr, ip_data in item.get("ipv4", {}).items():
                if ip_data.get("lladdr"):
                    ip_std = str(ipaddress.ip_address(ipaddr))
                    mac_std = str(netaddr.EUI(ip_data["lladdr"]))
                    if not result.ip_to_mac.get(ip_std):
                        result.ip_to_mac[ip_std] = []
                    if not result.mac_to_ip.get(mac_std):
                        result.mac_to_ip[mac_std] = []
                    result.ip_to_mac[ip_std].append(mac_std)
                    result.mac_to_ip[mac_std].append(ip_std)
                    if mac_std not in result.interface_to_mac[interface]:
                        result.interface_to_mac[interface].append(mac_std)
                else:
                    logger.warning("ARP entry missing data, skipping: %s %s", ipaddr, ip_data)

        return result


class InterfaceNeighborData(BaseModel):
    """Interface data needed for cable validation."""

    name: str | None = None
    macs: list[str] = []
    device_name: str | None = None
    device_serial: str | None = None
    device_role: str | None = None
    device_rack: str | None = None
    device_position: int | None = None
    link_up: bool | None = None
    ts_info: str | None = None

    @staticmethod
    def from_graphql(data: dict[str, Any]) -> InterfaceNeighborData:
        """Produce InterfaceNeighborData from nautobot graphql."""
        if not data["connected_interface"]:
            return InterfaceNeighborData()

        device = (
            data["connected_interface"]["device"]
            if data["connected_interface"].get("device")
            else data["connected_interface"]["module"]["device"]
        )
        role = device["role"]
        if role:
            role = role["name"].lower().replace(" ", "-")

        if device.get("rack"):
            rack = device["rack"]["name"]
        else:
            rack = None

        return InterfaceNeighborData(
            name=(data["connected_interface"]["name"]),
            macs=(
                [str(netaddr.EUI(data["connected_interface"]["mac_address"]))]
                if data["connected_interface"]["mac_address"]
                else []
            ),
            device_name=(device["name"]),
            device_serial=(device["serial"]),
            device_role=role,
            device_rack=rack,
            device_position=device.get("position"),
        )

    @staticmethod
    def from_eapi(data: dict[str, Any]) -> InterfaceNeighborData:
        """Produce InterfaceNeighborData from Arista EAPI JSON."""
        name = re.sub(
            r"[\"\']",
            "",
            data["lldpNeighborInfo"][0]["neighborInterfaceInfo"]["interfaceId"],
        )
        return InterfaceNeighborData(
            device_name=data["lldpNeighborInfo"][0]["systemName"],
            name=str(netaddr.EUI(name)) if is_mac_address(name) else name,
        )

    @staticmethod
    def from_nvue(data: dict[str, Any]) -> InterfaceNeighborData:
        """Produce InterfaceNeighborData from cumulus NVUE API JSON."""
        # dict with one key being the neighbor device name
        device = [*data][0]
        return InterfaceNeighborData(
            device_name=device,
            name=(
                str(netaddr.EUI(data[device]["port"]["name"]))
                if is_mac_address(data[device]["port"]["name"])
                else data[device]["port"]["name"]
            ),
        )


class DeviceNeighborData(BaseModel, validate_assignment=True):
    """Neighbor data for a device."""

    # key is the interface name
    neighbors: dict[str, InterfaceNeighborData] = {}
    link_states: dict[str, bool] = {}
    ts_info: dict[str, str] = {}
    ignore: list[str] = []
    link_state_only: list[str] = []


class DeviceMacTable(BaseModel):
    """Represents a MAC address table for a device."""

    by_mac: dict[str, DeviceMacEntry] = {}
    by_interface: dict[str, list[str]] = {}


class NetworkConnection:
    """Generic Network Connection Class."""

    def __init__(
        self,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        site: str | None = None,
    ) -> None:
        """Initialize a network connection.

        Args:
            host: Device hostname or IP address
            port: Connection port
            username: Username for authentication (optional, defaults from config)
            password: Password for authentication (optional, defaults from config)
            site: Site name for site-specific password lookup (optional)
        """
        config = load_config()
        self._host = host
        self._port = port
        self._username = username or config["device"]["username"]

        # Build list of passwords to try for authentication
        self._passwords_to_try: list[str] = []
        self._working_password: str | None = None

        # If explicit password provided, use only that
        if password:
            self._passwords_to_try = [password]
            logger.debug("Using explicit password for %s@%s", self._username, self._host)
            return

        # Determine which config and section to use for passwords
        # This checks the secrets config first, then falls back to main config
        password_config, password_section = resolve_config_section(config, "device", site)
        passwords = get_rotation_passwords(password_config, password_section)

        if passwords:
            logger.debug(
                "Loaded %d rotation password(s) for %s@%s",
                len(passwords),
                self._username,
                self._host,
            )
            self._passwords_to_try = passwords
        else:
            # Fallback to "password" key using get_credential (handles site fallback)
            fallback = get_credential(config, "device", "password", site)
            logger.debug(
                "Using fallback password (no rotation keys found) for %s@%s",
                self._username,
                self._host,
            )
            self._passwords_to_try = [fallback] if fallback else []

    def _get_passwords_to_try(self) -> list[str]:
        """Get list of passwords to try, with cached working password first."""
        if self._working_password and self._working_password in self._passwords_to_try:
            # Put working password first, then the rest (deduplicated)
            return [self._working_password] + [
                p for p in self._passwords_to_try if p != self._working_password
            ]
        return list(self._passwords_to_try)

    def _try_passwords_with_callback(
        self,
        connect_callback: Callable[[str], Any],
        error_types: tuple[type[Exception], ...],
    ) -> Any:
        """Try authentication with password rotations using a callback.

        Args:
            connect_callback: Function that takes a password and returns a connection
            error_types: Tuple of exception types to catch and retry

        Returns:
            The result from the successful connect_callback

        Raises:
            NetworkDeviceException: If all password attempts fail
        """
        passwords = self._get_passwords_to_try()
        last_error = None

        for idx, password in enumerate(passwords, 1):
            try:
                logger.debug(
                    "Attempting authentication to %s with %s (attempt %d/%d)",
                    self._host,
                    self._username,
                    idx,
                    len(passwords),
                )
                result = connect_callback(password)
                # Connection successful - cache this password
                self._working_password = password
                logger.debug(
                    "Successfully authenticated to %s with %s (attempt %d)",
                    self._host,
                    self._username,
                    idx,
                )
                return result
            except error_types as exc:
                last_error = exc
                logger.warning(
                    "Authentication failed for %s@%s (attempt %d/%d): %s",
                    self._username,
                    self._host,
                    idx,
                    len(passwords),
                    exc,
                )
                continue

        raise NetworkDeviceException(
            f"All passwords failed for {self._username}@{self._host} after {len(passwords)} attempt(s)"
        ) from last_error

    def get_running_configuration(self) -> str:
        """Load the running configuration for a given device."""
        raise NotImplementedError()

    def get_hostname(self) -> str:
        """Get the system hostname."""
        raise NotImplementedError()

    def get_mac_table(self) -> DeviceMacTable:
        """Get the device MAC table."""
        raise NotImplementedError()

    def get_arp_table(self) -> DeviceArpTable:
        """Get the device ARP table."""
        raise NotImplementedError()

    def get_lldp_data(self, interface_name: str) -> InterfaceNeighborData | None:
        """Get the raw LLDP data for a given interface."""
        raise NotImplementedError()

    def get_interface_connections(self) -> DeviceNeighborData:
        """Get all interface connections for the device."""
        raise NotImplementedError()

    def perform_candidate_diff(self, new_configuration: str, partial: bool = False) -> str:
        """Load the candidate configuration and return the diff."""
        raise NotImplementedError()

    def commit_candidate_config(
        self,
        new_configuration: str,
        approved_diff: str,
        partial: bool = False,
        *,
        commit_confirm: bool = True,
    ) -> None:
        """Load the candidate configuration and commit."""
        raise NotImplementedError()

    def get_rollback_diff(self, rollback_id: int = 1) -> str:
        """Return the diff between the active config and a numbered rollback."""
        raise NotImplementedError()

    def rollback_configuration(self, rollback_id: int = 1, *, commit_confirm: bool = True) -> None:
        """Roll back to a numbered rollback revision and commit."""
        raise NotImplementedError()

    def save_rescue_configuration(self) -> None:
        """Save the current active config as the rescue checkpoint."""
        raise NotImplementedError()

    def get_rescue_configuration(self) -> str | None:
        """Return the saved rescue configuration, or None if none is set."""
        raise NotImplementedError()

    def delete_rescue_configuration(self) -> None:
        """Delete the saved rescue configuration."""
        raise NotImplementedError()

    def rollback_to_rescue(self, *, commit_confirm: bool = True) -> None:
        """Roll back to the saved rescue configuration and commit."""
        raise NotImplementedError()

    def execute_ztp(self) -> None:
        """Execute ZTP on the device."""
        raise NotImplementedError()

    def get_running_image(self) -> str:
        """Get the running image on the device."""
        raise NotImplementedError()

    def get_ztp_status(self) -> str:
        """Get the ZTP status of the device."""
        raise NotImplementedError()

    def get_uptime(self) -> int:
        """Get the device uptime in seconds."""
        raise NotImplementedError()

    def get_platform(self) -> Any:
        """Get the platform information."""
        raise NotImplementedError()

    def get_platform_environment_fan(self) -> Any:
        """Get platform fan information."""
        raise NotImplementedError()

    def get_platform_environment_led(self) -> Any:
        """Get platform LED information."""
        raise NotImplementedError()

    def get_platform_environment_psu(self) -> Any:
        """Get platform PSU information."""
        raise NotImplementedError()

    def get_platform_environment_voltage(self) -> Any:
        """Get platform voltage information."""
        raise NotImplementedError()

    def get_platform_inventory(self) -> Any:
        """Get platform inventory information."""
        raise NotImplementedError()

    def get_firmware_versions(self) -> dict[str, Any]:
        """Get firmware versions for all components."""
        raise NotImplementedError()

    def reboot(self) -> None:
        """Reboot the device."""
        raise NotImplementedError()

    def diag_get_version(self) -> object:
        raise NotImplementedError()

    def diag_get_interfaces(self) -> object:
        raise NotImplementedError()

    def diag_get_bgp_summary(self) -> object:
        raise NotImplementedError()

    def diag_get_lldp_neighbors(self) -> object:
        raise NotImplementedError()

    def diag_get_platform(self) -> object:
        raise NotImplementedError()

    def diag_get_route_table(self) -> object:
        raise NotImplementedError()

    def diag_get_vlan(self) -> object:
        raise NotImplementedError()

    def diag_get_vrf(self) -> object:
        raise NotImplementedError()

    def diag_get_arp_table(self) -> object:
        raise NotImplementedError()

    def diag_get_mac_table(self) -> object:
        raise NotImplementedError()

    def diag_get_mlag(self) -> object:
        raise NotImplementedError()

    def diag_get_spanning_tree(self) -> object:
        raise NotImplementedError()

    def diag_get_port_channels(self) -> object:
        raise NotImplementedError()

    def diag_get_isis_neighbors(self) -> object:
        raise NotImplementedError()

    def diag_get_isis_interfaces(self) -> object:
        raise NotImplementedError()

    def diag_get_isis_database(self) -> object:
        raise NotImplementedError()

    def diag_get_mpls_interfaces(self) -> object:
        raise NotImplementedError()

    def diag_get_mpls_rsvp_neighbors(self) -> object:
        raise NotImplementedError()

    def diag_get_mac_security(self) -> object:
        raise NotImplementedError()

    def diag_get_mac_security_counters(self) -> object:
        raise NotImplementedError()

    def diag_get_vrrp(self) -> object:
        raise NotImplementedError()

    def diag_get_inventory(self) -> object:
        raise NotImplementedError()

    def diag_get_system_health(self) -> object:
        raise NotImplementedError()

    def diag_get_interface_counters(self) -> object:
        raise NotImplementedError()

    def diag_get_interface_mac(self) -> object:
        raise NotImplementedError()

    def diag_get_platform_environment(self) -> object:
        raise NotImplementedError()

    def diag_get_platform_transceiver(self) -> object:
        raise NotImplementedError()

    def run_diagnostic_command(self, name: str) -> str:
        """Run a named diagnostic command and return JSON-formatted output.

        Dispatches to the appropriate diag_get_* method for the given command
        name and serialises the result as indented JSON. Supported command names
        vary by platform — see the diagnostics catalog for the full list.

        Raises:
            NetworkDeviceException: If the command name is unknown or the
                platform does not implement it.
        """
        dispatch: dict[str, Callable[[], object]] = {
            "show_version": self.diag_get_version,
            "show_interfaces": self.diag_get_interfaces,
            "show_bgp_summary": self.diag_get_bgp_summary,
            "show_lldp_neighbors": self.diag_get_lldp_neighbors,
            "show_platform": self.diag_get_platform,
            "show_route_table": self.diag_get_route_table,
            "show_vlan": self.diag_get_vlan,
            "show_vrf": self.diag_get_vrf,
            "show_arp_table": self.diag_get_arp_table,
            "show_mac_table": self.diag_get_mac_table,
            "show_mlag": self.diag_get_mlag,
            "show_spanning_tree": self.diag_get_spanning_tree,
            "show_port_channels": self.diag_get_port_channels,
            "show_isis_neighbors": self.diag_get_isis_neighbors,
            "show_isis_interfaces": self.diag_get_isis_interfaces,
            "show_isis_database": self.diag_get_isis_database,
            "show_mpls_interfaces": self.diag_get_mpls_interfaces,
            "show_mpls_rsvp_neighbors": self.diag_get_mpls_rsvp_neighbors,
            "show_mac_security": self.diag_get_mac_security,
            "show_mac_security_counters": self.diag_get_mac_security_counters,
            "show_vrrp": self.diag_get_vrrp,
            "show_inventory": self.diag_get_inventory,
            "show_system_health": self.diag_get_system_health,
            "show_interface_counters": self.diag_get_interface_counters,
            "show_interface_mac": self.diag_get_interface_mac,
            "show_platform_environment": self.diag_get_platform_environment,
            "show_platform_transceiver": self.diag_get_platform_transceiver,
        }
        if name not in dispatch:
            raise NetworkDeviceException(
                f"Diagnostic command '{name}' is not supported on this platform. "
                f"Supported: {sorted(dispatch)}"
            )
        try:
            result = dispatch[name]()
        except NotImplementedError as error:
            raise NetworkDeviceException(
                f"Diagnostic command '{name}' is not implemented for {type(self).__name__}."
            ) from error
        return json.dumps(result, indent=2)

    def get_tech_support_bundle(
        self, heartbeat_fn: Callable[[], None] | None = None
    ) -> tuple[bytes, str]:
        """Generate and retrieve a full platform tech-support bundle.

        Returns:
            A tuple of (raw bundle bytes, full cl-support command output text).
        """
        raise NotImplementedError()

    @staticmethod
    def from_device_data(device_data: NetworkDeviceData) -> NetworkConnection:
        """Return a NetworkConnection for a given device."""
        config = load_config()
        connection: NetworkConnection | None = None
        if config["device"].getboolean("mock"):
            connection = MockNetworkConnection(device_data.host, site=device_data.site)
        elif device_data.platform == Platform.ARISTA_EOS:
            connection = AristaConnection(device_data.host, site=device_data.site)
        elif device_data.platform == Platform.CUMULUS_LINUX:
            connection = CumulusConnection(device_data.host, site=device_data.site)
        elif device_data.platform == Platform.NV_OS:
            connection = NVOSConnection(device_data.host, site=device_data.site)
        elif device_data.platform == Platform.MLNX_OS:
            connection = MellanoxConnection(device_data.host, site=device_data.site)
        elif device_data.platform == Platform.JUNIPER_JUNOS:
            connection = JuniperConnection(device_data.host, site=device_data.site)
        else:
            raise NotImplementedError(f"No handler implemented for platform {device_data.platform}")
        return connection


class MockNetworkConnection(NetworkConnection):
    """Mock Network Connection for Local Dev."""

    def __init__(
        self,
        host: str,
        port: int = 443,
        username: str | None = None,
        password: str | None = None,
        site: str | None = None,
    ) -> None:
        """Initialize a Mock Network Connection."""
        super().__init__(host, port, username, password, site)

    def get_running_configuration(self) -> str:
        """Load the running configuration for a given device."""
        # TODO: set up some more realistic mock data
        return "Mock Network Config"

    def get_mac_table(self) -> DeviceMacTable:
        """Get the device MAC table."""
        return DeviceMacTable()

    def get_arp_table(self) -> DeviceArpTable:
        """Get the device ARP table."""
        return DeviceArpTable()

    def get_interface_connections(self) -> DeviceNeighborData:
        """Get interface connections from LLDP."""
        return DeviceNeighborData()

    def perform_candidate_diff(self, new_configuration: str, partial: bool = False) -> str:
        """Load the candidate configuration and return the diff."""
        # TODO: set up some more realistic mock data
        return "Mock Network Diff"

    def get_hostname(self) -> str:
        """Get the system hostname."""
        return "MockHostName"

    def commit_candidate_config(
        self,
        new_configuration: str,
        approved_diff: str,
        partial: bool = False,
        *,
        commit_confirm: bool = True,
    ) -> None:
        """Load the candidate configuration and commit."""

    def get_platform(self) -> Any:
        """Get the platform information."""
        return {"mock": "platform data"}

    def get_platform_environment_fan(self) -> Any:
        """Get platform fan information."""
        return {"mock": "fan data"}

    def get_platform_environment_led(self) -> Any:
        """Get platform LED information."""
        return {"mock": "led data"}

    def get_platform_environment_psu(self) -> Any:
        """Get platform PSU information."""
        return {"mock": "psu data"}

    def get_platform_environment_voltage(self) -> Any:
        """Get platform voltage information."""
        return {"mock": "voltage data"}

    def get_platform_inventory(self) -> Any:
        """Get platform inventory information."""
        return {"mock": "inventory data"}

    def diag_get_version(self) -> object:
        return {"mock": True, "command": "show_version"}

    def diag_get_interfaces(self) -> object:
        return {"mock": True, "command": "show_interfaces"}

    def diag_get_bgp_summary(self) -> object:
        return {"mock": True, "command": "show_bgp_summary"}

    def diag_get_lldp_neighbors(self) -> object:
        return {"mock": True, "command": "show_lldp_neighbors"}

    def diag_get_platform(self) -> object:
        return {"mock": True, "command": "show_platform"}

    def diag_get_route_table(self) -> object:
        return {"mock": True, "command": "show_route_table"}

    def diag_get_vlan(self) -> object:
        return {"mock": True, "command": "show_vlan"}

    def diag_get_vrf(self) -> object:
        return {"mock": True, "command": "show_vrf"}

    def diag_get_arp_table(self) -> object:
        return {"mock": True, "command": "show_arp_table"}

    def diag_get_mac_table(self) -> object:
        return {"mock": True, "command": "show_mac_table"}

    def diag_get_mlag(self) -> object:
        return {"mock": True, "command": "show_mlag"}

    def diag_get_spanning_tree(self) -> object:
        return {"mock": True, "command": "show_spanning_tree"}

    def diag_get_port_channels(self) -> object:
        return {"mock": True, "command": "show_port_channels"}

    def diag_get_isis_neighbors(self) -> object:
        return {"mock": True, "command": "show_isis_neighbors"}

    def diag_get_isis_interfaces(self) -> object:
        return {"mock": True, "command": "show_isis_interfaces"}

    def diag_get_isis_database(self) -> object:
        return {"mock": True, "command": "show_isis_database"}

    def diag_get_mpls_interfaces(self) -> object:
        return {"mock": True, "command": "show_mpls_interfaces"}

    def diag_get_mpls_rsvp_neighbors(self) -> object:
        return {"mock": True, "command": "show_mpls_rsvp_neighbors"}

    def diag_get_mac_security(self) -> object:
        return {"mock": True, "command": "show_mac_security"}

    def diag_get_mac_security_counters(self) -> object:
        return {"mock": True, "command": "show_mac_security_counters"}

    def diag_get_vrrp(self) -> object:
        return {"mock": True, "command": "show_vrrp"}

    def diag_get_inventory(self) -> object:
        return {"mock": True, "command": "show_inventory"}

    def diag_get_system_health(self) -> object:
        return {"mock": True, "command": "show_system_health"}

    def diag_get_interface_counters(self) -> object:
        return {"mock": True, "command": "show_interface_counters"}

    def diag_get_interface_mac(self) -> object:
        return {"mock": True, "command": "show_interface_mac"}

    def diag_get_platform_environment(self) -> object:
        return {"mock": True, "command": "show_platform_environment"}

    def diag_get_platform_transceiver(self) -> object:
        return {"mock": True, "command": "show_platform_transceiver"}

    def get_tech_support_bundle(
        self, heartbeat_fn: Callable[[], None] | None = None
    ) -> tuple[bytes, str]:
        """Return a predictable stub bundle for unit testing."""
        return (
            b"[mock tech-support bundle]",
            "Mock cl-support output\nSaved cl_support output to /var/support/mock_bundle.txz.",
        )


class AristaConnection(NetworkConnection):
    """Arista Device Connection."""

    def __init__(
        self,
        host: str,
        port: int = 443,
        username: str | None = None,
        password: str | None = None,
        site: str | None = None,
    ) -> None:
        """Initialize an Arista Connection."""
        super().__init__(host, port, username, password, site)
        self._node = self._connect()
        self._session_id: str | None = None

    def _connect(self) -> Node:
        # Until we get to a point where we can load and rotate
        # https certs on Aristas, these are self-signed by default.
        # Additionally, out of the box, Arista does not support
        # the set of ciphers required by python3.10+
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        ctx.set_ciphers("DEFAULT")

        def connect_with_password(password: str) -> Node:
            return pyeapi.connect(
                transport="https",
                host=self._host,
                port=self._port,
                username=self._username,
                password=password,
                enablepwd=password,
                return_node=True,
                context=ctx,
                timeout=300,
            )

        return self._try_passwords_with_callback(
            connect_with_password,
            (pyeapi.eapilib.ConnectionError, pyeapi.eapilib.CommandError),
        )

    def get_running_configuration(self) -> str:
        """Load the running configuration for a given device."""
        response = self._node.enable("show running-config sanitized", encoding="text")
        return cast(str, response[0]["result"]["output"])

    def get_mac_table(self) -> DeviceMacTable:
        """Get the device MAC table."""
        response = self._node.enable("show mac address-table")
        result = DeviceMacTable(by_interface={}, by_mac={})
        try:
            for row in response[0]["result"]["unicastTable"]["tableEntries"]:
                if not row["interface"]:
                    continue
                entry = DeviceMacEntry.from_eapi(row)
                if entry.interface not in result.by_interface:
                    result.by_interface[entry.interface] = []
                if entry.mac not in result.by_interface[entry.interface]:
                    result.by_interface[entry.interface].append(entry.mac)
                if entry.mac in result.by_mac:
                    logger.warning(
                        "Duplicate MAC address %s on device %s: using newest entry",
                        entry.mac,
                        self._host,
                    )
                    if entry.age > result.by_mac[entry.mac].age:
                        continue
                result.by_mac[entry.mac] = entry
        except KeyError as exc:
            raise NetworkDeviceException(
                "Failed to parse JSON output of 'show mac address-table'."
            ) from exc

        return result

    def get_arp_table(self) -> DeviceArpTable:
        """Get the device ARP table."""
        response = self._node.enable("show ip arp")
        return DeviceArpTable.from_eapi(response[0]["result"])

    def get_lldp_data(self, interface_name: str) -> InterfaceNeighborData | None:
        response = self._node.enable(
            f"show lldp neighbors {interface_name} detail", encoding="json"
        )
        for interface, neighbor in response[0]["result"]["lldpNeighbors"].items():
            if len(neighbor["lldpNeighborInfo"]) > 1:
                raise NetworkDeviceException(
                    f"Received multiple LLDP neighbors on interface {interface} from {self._host}"
                )
            if neighbor["lldpNeighborInfo"]:
                return InterfaceNeighborData.from_eapi(neighbor)
        return None

    def get_interface_connections(self) -> DeviceNeighborData:
        """Get all interface connections from LLDP."""
        response = self._node.enable("show lldp neighbors detail", encoding="json")
        neighbors = {}
        for interface, neighbor in response[0]["result"]["lldpNeighbors"].items():
            if len(neighbor["lldpNeighborInfo"]) > 1:
                raise NetworkDeviceException(
                    f"Received multiple LLDP neighbors on interface {interface} from {self._host}"
                )
            if neighbor["lldpNeighborInfo"]:
                neighbors[interface] = InterfaceNeighborData.from_eapi(neighbor)

        link_states = {}
        response = self._node.enable("show interfaces status", encoding="json")
        for interface, data in response[0]["result"]["interfaceStatuses"].items():
            link_states[interface] = data["linkStatus"] == "connected"

        return DeviceNeighborData(neighbors=neighbors, link_states=link_states)

    def _extract_banner_commands(self, new_configuration: str) -> tuple[str, list[tuple[str, str]]]:
        """Extract banners into multiline commands."""
        pattern = re.compile(r"(banner \w+)(.*?)EOF", flags=re.S)
        matches = pattern.findall(new_configuration)
        modified_configuration = pattern.sub("", new_configuration)
        return modified_configuration, matches

    def _load_candidate_config(self, new_configuration: str, partial: bool = False) -> None:
        self._session_id = str(uuid4())

        config_commands: list[str | dict[str, str]] = [
            f"configure session {self._session_id}",
            "rollback clean-config" if not partial else "",
        ]
        configuration, banner_commands = self._extract_banner_commands(new_configuration)
        multiline_commands = [{"cmd": cmd[0], "input": cmd[1]} for cmd in banner_commands]
        config_commands.extend(multiline_commands)
        config_commands.extend(
            [cmd for cmd in configuration.splitlines() if cmd.strip() not in ["!", ""]]
        )
        if (
            not isinstance(config_commands[-1], str) or config_commands[-1].strip() != "end"  # type: ignore[union-attr]
        ):
            config_commands.append("end")
        try:
            self._node.run_commands(config_commands)
        except pyeapi.eapilib.CommandError as exc:
            raise ConfigSyntaxException("Invalid configuration supplied.") from exc
        except Exception as exc:  # pylint disable=broad-except
            raise NetworkDeviceException("Failed to run commands against the device.") from exc

    def _abort(self) -> None:
        # Clean up the config session if present
        if self._session_id is None:
            # Nothing to clean up
            return
        try:
            sessions = self._node.enable("show configuration sessions")
            if self._session_id in sessions[0]["result"]["sessions"]:
                self._node.enable(f"configure session {self._session_id} abort")
        except Exception as exc:  # pylint disable=broad-except
            raise NetworkDeviceException(
                f"Failed to cleanup session {self._session_id}, resolve manually."
            ) from exc

    def _diff(self) -> str:
        diff = self._node.enable(
            f"show session-config named {self._session_id} diffs", encoding="text"
        )[0]["result"]["output"]
        return cast(str, diff)

    def _diff_eq(self, diff_a: str, diff_b: str) -> bool:
        # Arista session diffs include the session ID in the output
        # strip those lines when comparing
        if diff_b == "":
            # Previous run succeeded to apply but failed on copy run start
            return True
        pattern = re.compile(r"session:/.*?-session-config")
        return pattern.sub("", diff_a) == pattern.sub("", diff_b)

    def perform_candidate_diff(self, new_configuration: str, partial: bool = False) -> str:
        """Load the candidate configuration and perform a diff."""
        try:
            self._load_candidate_config(new_configuration)
            return self._diff()
        except ConfigSyntaxException as exc:
            raise exc
        except Exception as exc:  # pylint: disable=broad-except
            raise NetworkDeviceException(f"Failed to diff session {self._session_id}") from exc
        finally:
            self._abort()

    def commit_candidate_config(
        self,
        new_configuration: str,
        approved_diff: str,
        partial: bool = False,
        *,
        commit_confirm: bool = True,
    ) -> None:
        """Load the candidate configuration and commit.

        When commit_confirm is True, uses commit timer so changes roll back if not
        confirmed; we then confirm to make permanent. When False, commits directly
        (use for changes that cause brief interruption, e.g. IP change ahead of
        upstream VLAN change).
        """
        try:
            self._load_candidate_config(new_configuration)
            diff = self._diff()
            if not self._diff_eq(diff, approved_diff):
                raise DiffChangedException("Diff has changed since approval, aborting.")
            if commit_confirm:
                # commit timer HH:MM:SS = roll back unless confirmed; commit applies
                m, s = divmod(COMMIT_CONFIRM_ROLLBACK_SECONDS, 60)
                h, m = divmod(m, 60)
                timer_str = f"{h:02d}:{m:02d}:{s:02d}"
                self._node.run_commands(
                    [
                        f"configure session {self._session_id}",
                        f"commit timer {timer_str}",
                        "commit",
                    ]
                )
                # Confirm (make permanent); from exec: configure session <name> commit
                self._node.enable(f"configure session {self._session_id} commit")
            else:
                self._node.enable(f"configure session {self._session_id} commit")
            self._node.enable("copy running-config startup-config")
        except ConfigSyntaxException as exc:
            raise exc
        except Exception as exc:  # pylint: disable=broad-except
            raise NetworkDeviceException(f"Failed to commit session {self._session_id}") from exc
        finally:
            self._abort()

    def get_hostname(self) -> str:
        """Get the system hostname."""
        try:
            return str(self._node.enable("show hostname")[0]["result"]["hostname"])
        except ValueError as error:
            raise ApplicationError(
                f"No hostname configured for {self._host}",
                non_retryable=True,
            ) from error

    def get_uptime(self) -> int:
        """Get the device uptime in seconds."""
        response = self._node.enable("show uptime")
        return int(response[0]["result"]["upTime"])

    # ------------------------------------------------------------------
    # Diagnostic commands — all via eAPI JSON-RPC (HTTPS port 443).
    # Optional features (BGP, ISIS, MPLS, MACsec, MLAG, VRRP) catch
    # CommandError and return a sentinel dict so the workflow never fails
    # on a device where that protocol is not configured.
    # ------------------------------------------------------------------

    def diag_get_version(self) -> object:
        return self._node.enable("show version detail", encoding="json")[0]["result"]

    def diag_get_interfaces(self) -> object:
        return self._node.enable("show interfaces status", encoding="json")[0]["result"]

    def diag_get_bgp_summary(self) -> object:
        try:
            return self._node.enable("show ip bgp summary", encoding="json")[0]["result"]
        except pyeapi.eapilib.CommandError:
            return {"error": "BGP not configured on this device"}

    def diag_get_lldp_neighbors(self) -> object:
        return self._node.enable("show lldp neighbors detail", encoding="json")[0]["result"]

    def diag_get_route_table(self) -> object:
        return self._node.enable("show ip route summary", encoding="json")[0]["result"]

    def diag_get_vlan(self) -> object:
        return self._node.enable("show vlan", encoding="json")[0]["result"]

    def diag_get_vrf(self) -> object:
        return self._node.enable("show vrf", encoding="json")[0]["result"]

    def diag_get_arp_table(self) -> object:
        return self._node.enable("show ip arp", encoding="json")[0]["result"]

    def diag_get_mac_table(self) -> object:
        return self._node.enable("show mac address-table", encoding="json")[0]["result"]

    def diag_get_inventory(self) -> object:
        return self._node.enable("show inventory", encoding="json")[0]["result"]

    def diag_get_mlag(self) -> object:
        try:
            return self._node.enable("show mlag detail", encoding="json")[0]["result"]
        except pyeapi.eapilib.CommandError:
            return {"error": "MLAG not configured on this device"}

    def diag_get_spanning_tree(self) -> object:
        return self._node.enable("show spanning-tree", encoding="json")[0]["result"]

    def diag_get_port_channels(self) -> object:
        return self._node.enable("show port-channel dense", encoding="json")[0]["result"]

    def diag_get_isis_neighbors(self) -> object:
        try:
            return self._node.enable("show isis neighbors", encoding="json")[0]["result"]
        except pyeapi.eapilib.CommandError:
            return {"error": "IS-IS not configured on this device"}

    def diag_get_isis_interfaces(self) -> object:
        try:
            return self._node.enable("show isis interface brief", encoding="json")[0]["result"]
        except pyeapi.eapilib.CommandError:
            return {"error": "IS-IS not configured on this device"}

    def diag_get_isis_database(self) -> object:
        try:
            return self._node.enable("show isis database", encoding="json")[0]["result"]
        except pyeapi.eapilib.CommandError:
            return {"error": "IS-IS not configured on this device"}

    def diag_get_mpls_interfaces(self) -> object:
        try:
            return self._node.enable("show mpls interface", encoding="json")[0]["result"]
        except pyeapi.eapilib.CommandError:
            # JSON not supported on this EOS version; return raw text
            try:
                return {
                    "output": self._node.enable("show mpls interface", encoding="text")[0][
                        "result"
                    ]["output"]
                }
            except pyeapi.eapilib.CommandError:
                return {"error": "MPLS not configured on this device"}

    def diag_get_mpls_rsvp_neighbors(self) -> object:
        try:
            return {
                "output": self._node.enable("show mpls rsvp neighbor summary", encoding="text")[0][
                    "result"
                ]["output"]
            }
        except pyeapi.eapilib.CommandError:
            return {"error": "MPLS RSVP not configured on this device"}

    def diag_get_mac_security(self) -> object:
        try:
            return self._node.enable("show mac security interface", encoding="json")[0]["result"]
        except pyeapi.eapilib.CommandError:
            return {"error": "MACsec not configured on this device"}

    def diag_get_mac_security_counters(self) -> object:
        try:
            return self._node.enable("show mac security counters", encoding="json")[0]["result"]
        except pyeapi.eapilib.CommandError:
            return {"error": "MACsec not configured on this device"}

    def diag_get_vrrp(self) -> object:
        try:
            return self._node.enable("show vrrp", encoding="json")[0]["result"]
        except pyeapi.eapilib.CommandError:
            return {"error": "VRRP not configured on this device"}


def _parse_cl_support_path(output: str) -> str | None:
    """Return the /var/support/ bundle path from cl-support output, or None."""
    match = re.search(r"/var/support/\S+", output)
    return match.group().rstrip(".") if match else None


class CumulusConnection(NetworkConnection):
    """Cumulus Device Connection."""

    def __init__(
        self,
        host: str,
        port: int = 8765,
        username: str | None = None,
        password: str | None = None,
        site: str | None = None,
    ) -> None:
        """Initialize a Cumulus Connection."""
        super().__init__(host, port, username, password, site)
        retry = Retry(total=5, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        self._session = requests.Session()
        self._session.mount("https://", adapter=HTTPAdapter(max_retries=retry))
        self._session.headers = {"Content-Type": "application/json"}
        self._session.verify = False
        self._base_url = f"https://{host}:{port}/nvue_v1/"
        self._authenticated = False

    def _make_request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> requests.Response:
        """Make an HTTP request with automatic password rotation on auth failure.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            url: URL to request
            **kwargs: Additional arguments to pass to requests (params, json, data, timeout, etc.)

        Returns:
            requests.Response object

        Raises:
            NetworkDeviceException: If all password attempts fail or other errors occur
        """

        def try_request_with_password(password: str) -> requests.Response:
            self._session.auth = (self._username, password)
            rsp = self._session.request(method, url, **kwargs)
            if rsp.status_code in (401, 403):
                raise NetworkDeviceException(f"Authentication failed: HTTP {rsp.status_code}")
            return rsp

        if self._authenticated:
            rsp = self._session.request(method, url, **kwargs)
            if rsp.status_code not in (401, 403):
                return rsp
            logger.info(
                "Cached password no longer valid for %s, retrying with available passwords",
                self._host,
            )
            self._authenticated = False

        # Try with password rotation
        rsp = self._try_passwords_with_callback(
            try_request_with_password,
            (NetworkDeviceException,),
        )
        self._authenticated = True
        return cast(requests.Response, rsp)

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        timeout: int = 30,
        raise_on_failure: bool = True,
    ) -> requests.Response:
        """Get from the device."""
        try:
            rsp = self._make_request("GET", url, params=params, timeout=timeout)
        except requests.exceptions.Timeout as error:
            msg = f"Timed out getting from {url} with params: {params}"
            logger.exception(msg)
            raise NetworkDeviceException(msg) from error
        if rsp.status_code != 200 and raise_on_failure:
            msg = (
                f"Failed to get from {url} with params: {params} :"
                f" HTTP{rsp.status_code}: {rsp.text}"
            )
            logger.exception(msg)
            raise NetworkDeviceException(msg)
        return rsp

    def post(
        self, url: str, json: Any = None, data: Any = None, timeout: int = 30
    ) -> requests.Response:
        """Post to the device."""
        try:
            return self._make_request("POST", url, json=json, data=data, timeout=timeout)
        except requests.exceptions.Timeout as error:
            msg = f"Timed out posting to {url}"
            logger.exception(msg)
            raise NetworkDeviceException(msg) from error

    def patch(
        self, url: str, json: Any = None, data: Any = None, params: Any = None, timeout: int = 30
    ) -> requests.Response:
        """Patch to the device."""
        try:
            return self._make_request(
                "PATCH", url, json=json, data=data, params=params, timeout=timeout
            )
        except requests.exceptions.Timeout as error:
            msg = f"Timed out patching {url}"
            logger.exception(msg)
            raise NetworkDeviceException(msg) from error

    def delete(self, url: str, params: Any = None, timeout: int = 30) -> requests.Response:
        """Delete from the device."""
        try:
            return self._make_request("DELETE", url, params=params, timeout=timeout)
        except requests.exceptions.Timeout as error:
            msg = f"Timed out deleting {url}"
            logger.exception(msg)
            raise NetworkDeviceException(msg) from error

    def get_running_configuration(self) -> str:
        """Load the running configuration for a given device."""
        # https://docs.nvidia.com/networking-ethernet-software/cumulus-linux-56/System-Configuration/NVIDIA-User-Experience-NVUE/NVUE-API/#view-a-configuration
        rsp = self.get(self._base_url, params={"rev": "applied", "filled": "false"})
        json_config = rsp.json()
        # Convert to YAML to more closely match startup.yaml (still won't quite match)
        # ruamel.yaml is VERY opinionated about dumping to a string apparently
        # https://yaml.readthedocs.io/en/latest/example/#output-of-dump-as-a-string
        yaml_config_stream = StringIO()
        YAML().dump(json_config, yaml_config_stream)
        return yaml_config_stream.getvalue()

    def get_interfaces(self, state_only: bool = True) -> Any:
        """
        Get all interfaces.

        Recommend to stick with state_only due to connection issues observed
        with large bodies in the response. GET from an individual interfaces
        for more detailed data.
        """
        includes = [
            "/*/link/state",
            "/*/link/oper-status",
            "/*/type",
        ]
        return (
            self.get(f"{self._base_url}interface", params={"include": includes}).json()
            if state_only
            else self.get(f"{self._base_url}interface").json()
        )

    def get_ts_info(self, interface: str) -> Any:
        """Get the troubleshooting info for an interface."""
        return self.get(
            f"{self._base_url}interface/{interface}",
            params={"include": ["/link/troubleshooting-info"]},
        ).json()

    @staticmethod
    def flatten_config(config: str) -> list[str]:
        """Flatten the configuration."""
        config_obj = YAML().load(config)
        if not config_obj:
            return []
        set_config = config_obj[0].get("set")
        unset_config = config_obj[0].get("unset")
        commands = []
        if set_config:
            commands.extend([f"nv set {cmd}" for cmd in CumulusConnection._flatten(set_config, [])])
        if unset_config:
            commands.extend(
                [f"nv unset {cmd}" for cmd in CumulusConnection._flatten(unset_config, [])]
            )
        return commands

    def _load_candidate(self, new_configuration: str, partial: bool = False) -> str:
        # https://docs.nvidia.com/networking-ethernet-software/cumulus-linux-56/System-Configuration/NVIDIA-User-Experience-NVUE/NVUE-API/#replace-an-entire-configuration

        # Need to do some conversion as the startup.yaml begins with -set:
        # which is irrelevant to the API calls
        try:
            config_obj = YAML().load(new_configuration)
            config_obj = config_obj[0]["set"]
        except (KeyError, IndexError, YAMLError) as exc:
            raise ConfigSyntaxException("Invalid yaml loaded from the Config Store.") from exc

        try:
            # Create a revision
            rsp = self.post(f"{self._base_url}revision")
            rsp.raise_for_status()
            revision = list(rsp.json().keys())[0]

            if not partial:
                # Clear the root config for our revision
                rsp = self._session.delete(self._base_url, params={"rev": revision})
                rsp.raise_for_status()

            # Apply the full new configuration object
            rsp = self._session.patch(self._base_url, json=config_obj, params={"rev": revision})
            if rsp.status_code == 400:
                raise ConfigSyntaxException(ConfigSyntaxException.format_nvue_error(rsp.json()))
            rsp.raise_for_status()

            # return the revision ID for diff or commit
            return cast(str, revision)
        except requests.HTTPError as exc:
            raise NetworkDeviceException("Failed to load candidate configuration.") from exc

    def _get_revision_state(self, revision: str) -> tuple[str, dict[str, Any] | None]:
        rsp = self._session.get(f"{self._base_url}revision/{revision}")
        rsp.raise_for_status()
        state = rsp.json()["state"]
        transition = rsp.json().get("transition")
        return cast(str, state), transition

    def _get_diff(self, revision: str) -> str:
        # Need to diff in both directions
        removed_rsp = self.get(
            self._base_url,
            params={"rev": "applied", "diff": revision, "filled": "false"},
            raise_on_failure=False,
        )
        removed_rsp.raise_for_status()
        removed = removed_rsp.json()

        added_rsp = self.get(
            self._base_url,
            params={"rev": revision, "diff": "applied", "filled": "false"},
            raise_on_failure=False,
        )
        added_rsp.json()
        added = added_rsp.json()

        cli_diff = []

        if removed:
            cli_diff.extend([f"nv unset {cmd}" for cmd in CumulusConnection._flatten(removed, [])])

        if added:
            cli_diff.extend([f"nv set {cmd}" for cmd in CumulusConnection._flatten(added, [])])

        return "\n".join(cli_diff)

    @staticmethod
    def _flatten(
        json_diff: dict[str, Any], commands: list[str], path: list[str] | None = None
    ) -> list[str]:
        path = path or []
        for key, val in json_diff.items():
            new_path = deepcopy(path)
            new_path.append(key)
            if isinstance(val, dict):
                if val:
                    CumulusConnection._flatten(val, commands, new_path)
                else:
                    # Handle empty dictionary case
                    commands.append(" ".join(new_path))
            elif val is None:
                # No need to include it at all
                # this happens if a config line was null
                # and now has a value or vice versa, it's enough
                # to show the associated opposite command (e.g. set/unset)
                pass
            else:
                # Base case
                new_path.append(str(val))
                commands.append(" ".join(new_path))

        return commands

    def _apply_config(self, revision: str, *, commit_confirm: bool = True) -> None:
        """Apply revision. If commit_confirm, use rollback-unless-confirmed; else apply directly."""
        if commit_confirm:
            data = {
                "state": "apply",
                "auto-prompt": {"confirm": "confirm_yes", "ays": "ays_yes"},
                "state-controls": {"confirm": COMMIT_CONFIRM_ROLLBACK_SECONDS},
            }
        else:
            data = {"state": "apply", "auto-prompt": {"ays": "ays_yes"}}
        rsp = self.patch(f"{self._base_url}revision/{revision}", json=data)
        rsp.raise_for_status()

    def _confirm_apply(self, revision: str) -> None:
        """Confirm the revision in ays state (cancel pending rollback). Verifies device is still reachable."""
        data = {
            "state": "apply",
            "auto-prompt": {"ays": "ays_yes"},
        }
        rsp = self.patch(f"{self._base_url}revision/{revision}", json=data)
        rsp.raise_for_status()

    def _save_applied_config(self) -> None:
        data = {"state": "save", "auto-prompt": {"ays": "ays_yes"}}
        rsp = self.patch(f"{self._base_url}revision/applied", json=data)
        rsp.raise_for_status()

    def perform_candidate_diff(self, new_configuration: str, partial: bool = False) -> str:
        """Load the candidate configuration and return the diff."""
        try:
            revision = self._load_candidate(new_configuration, partial)
            return self._get_diff(revision)
        except requests.HTTPError as exc:
            raise NetworkDeviceException("Failed to perform candidate diff.") from exc

    def _get_ignore_fail_error_message(
        self,
        revision: str,
        transition_data: dict[str, Any] | None,
    ) -> str:
        """Build manual-intervention error message for ignore_fail apply state."""
        if transition_data:
            error_details = ConfigApplyFailureException.format_nvue_apply_error(transition_data)
        else:
            error_details = "Config apply failed with ignore_fail state"
        return (
            f"{error_details}\n\n"
            f"MANUAL INTERVENTION REQUIRED:\n"
            f"You can try manually applying the configuration on "
            f"the switch:\n\n"
            f"  nv config apply {revision}\n\n"
            f"If successful, this workflow stage will "
            f"automatically retry and complete. If the manual "
            f"apply also fails, further investigation of the "
            f"configuration or device state is required."
        )

    def commit_candidate_config(
        self,
        new_configuration: str,
        approved_diff: str,
        partial: bool = False,
        *,
        commit_confirm: bool = True,
    ) -> None:
        """Load the candidate configuration and commit.

        When commit_confirm is True, applies with rollback-unless-confirmed then
        confirms. When False, applies directly (use for changes that cause brief
        interruption, e.g. IP change ahead of upstream VLAN change).
        """
        try:
            revision = self._load_candidate(new_configuration, partial)
            diff = self._get_diff(revision)

            if not diff:
                # A previous run succeeded to apply the config
                # but may have had issues validating the apply
                # consider it fully applied now and save if
                # it is not saved
                state = self._get_revision_state("applied")[0]
                if "saved" not in state:
                    self._save_applied_config()
                return

            if diff != approved_diff:
                raise DiffChangedException("Diff has changed since approval, aborting.")

            self._apply_config(revision, commit_confirm=commit_confirm)

            # Monitor until state is ays (awaiting confirm) or applied
            state = ""
            transition_data: dict[str, Any] | None = None
            while "ays" not in state and "applied" not in state:
                state, transition_data = self._get_revision_state(revision)
                if "invalid" in state:
                    msg = f"Invalid config: {json.dumps(transition_data)}"
                    raise InvalidConfigException(
                        msg,
                        non_retryable=True,
                    )
                if "ignore_fail" in state:
                    raise ConfigApplyFailureException(
                        self._get_ignore_fail_error_message(revision, transition_data),
                        non_retryable=True,
                    )
                time.sleep(1)

            if commit_confirm:
                # Confirm apply (cancel pending rollback); verifies device is still reachable.
                # All requests (_apply_config, _get_revision_state, _confirm_apply, _save) go
                # through _make_request, so 401 on any step (e.g. after password rotation) will
                # trigger password iteration via _try_passwords_with_callback.
                self._confirm_apply(revision)

            # If config auto-save is set in the device config,
            # state will be applied_and_saved
            # no need for an explicit save call
            if "saved" not in state:
                # Save the applied configuration to persist on reboot
                self._save_applied_config()
        except requests.HTTPError as exc:
            raise NetworkDeviceException("Failed to apply candidate configuration.") from exc

    def get_bridge_domains(self) -> Any:
        """Get all bridge domains."""
        return self.get(f"{self._base_url}bridge/domain").json()

    def get_mac_table(self) -> DeviceMacTable:
        """Get MAC addresses from all bridge domains."""
        result = DeviceMacTable()
        for domain in self.get_bridge_domains():
            macs = self.get(f"{self._base_url}bridge/domain/{domain}/mac-table").json()
            for _, entry in macs.items():
                new_entry = DeviceMacEntry.from_nvue(entry)
                if new_entry.interface == domain:
                    # Skip SVI MAC addresses which can have multiple entries
                    continue
                # Skip the local MAC address, which will be in the table
                # with no VLAN set as seen below
                # 1 7c:c2:55:90:03:e7  997   swp3
                # 2 b0:cf:0e:66:96:7e        swp3 permanent
                if not new_entry.vlan:
                    continue
                if new_entry.mac in result.by_mac:
                    logger.warning(
                        "Duplicate MAC address %s on device %s: using newest entry",
                        new_entry.mac,
                        self._host,
                    )
                    if new_entry.age > result.by_mac[new_entry.mac].age:
                        continue
                result.by_mac[new_entry.mac] = new_entry
                if (
                    new_entry.interface in result.by_interface
                    and new_entry.mac not in result.by_interface[new_entry.interface]
                ):
                    result.by_interface[new_entry.interface].append(new_entry.mac)
                else:
                    result.by_interface[new_entry.interface] = [new_entry.mac]
        return result

    def get_arp_table(self) -> DeviceArpTable:
        """Get the device ARP table."""
        result = {}
        for interface, data in self.get_interfaces().items():
            if data.get("type") not in ["swp", "eth"]:
                # We only care about physical interfaces
                continue
            url = f"{self._base_url}interface/{interface}/ip/neighbor"
            rsp = self.get(url, raise_on_failure=False)
            if rsp.status_code == 200:
                result[interface] = rsp.json()
            elif rsp.status_code != 404:
                # 404 means the interface didn't have any neighbor info
                raise NetworkDeviceException(f"Error getting from url {url}: {rsp.text}")
        return DeviceArpTable.from_nvue(result)

    def get_lldp_data(self, interface_name: str) -> InterfaceNeighborData | None:
        url = f"{self._base_url}interface/{interface_name}/lldp"
        rsp = self.get(url, raise_on_failure=False, timeout=10)
        if rsp.status_code == 200:
            data = rsp.json()
            if data.get("neighbor"):
                if len(data["neighbor"]) != 1:
                    # Pull the entry with the youngest age
                    newest = min(data["neighbor"].values(), key=lambda x: int(x["age"]))
                    return InterfaceNeighborData.from_nvue(
                        {k: v for k, v in data["neighbor"].items() if v == newest}
                    )
                else:
                    return InterfaceNeighborData.from_nvue(data["neighbor"])
        elif rsp.status_code != 404:
            # 404 means no LLDP info for the interface
            raise NetworkDeviceException(f"Error getting from url {url}: {rsp.text}")
        return None

    def _get_all_lldp_data(self) -> dict[str, InterfaceNeighborData]:
        """Get all LLDP data for the device."""
        result = {}
        rsp = self.get(f"{self._base_url}interface", params={"include": "/*/lldp/neighbor"})
        if rsp.status_code == 404:
            return {}
        try:
            rsp.raise_for_status()
        except requests.HTTPError as exc:
            raise NetworkDeviceException(f"Error getting from url {rsp.url}: {rsp.text}") from exc

        for interface, data in rsp.json().items():
            if data.get("lldp", {}).get("neighbor"):
                neighbors = data["lldp"]["neighbor"]
                newest = min(neighbors.values(), key=lambda x: int(x["age"]))
                result[interface] = InterfaceNeighborData.from_nvue(
                    {k: v for k, v in neighbors.items() if v == newest}
                )
        return result

    def get_interface_connections(self) -> DeviceNeighborData:
        """Get all interface connections from LLDP."""
        neighbors = {}
        link_states = {}
        ts_info: dict[str, str] = {}
        lldp_data = self._get_all_lldp_data()
        for interface, link in self.get_interfaces().items():
            if link.get("type") not in ["swp", "eth"]:
                # We only care about physical interfaces
                continue
            # 5.11 splits out admin and oper status
            if link["link"].get("oper-status"):
                link_states[interface] = link["link"]["oper-status"] == "up"
            elif link["link"].get("state"):
                link_states[interface] = [*link["link"]["state"]][0] == "up"
            else:
                raise NetworkDeviceException(
                    f"No link state information for interface {interface} on device {self._host}"
                )

            if link_states[interface]:
                neighbor_data = lldp_data.get(interface)
                if neighbor_data:
                    neighbors[interface] = neighbor_data
            # Disabling due to performance issues
            # else:
            #     info = self.get_ts_info(interface)
            #     if info.get("link") and info["link"].get("troubleshooting-info"):
            #         ts_info[interface] = info["link"]["troubleshooting-info"]

        return DeviceNeighborData(
            neighbors=neighbors,
            link_states=link_states,
            ts_info=ts_info,
        )

    def _get_system(self) -> Any:
        """Get the system data."""
        return self.get(f"{self._base_url}system").json()

    def get_hostname(self) -> str:
        """Get the system hostname."""
        try:
            return str(self._get_system()["hostname"])
        except ValueError as error:
            raise ApplicationError(
                f"No hostname configured for {self._host}",
                non_retryable=True,
            ) from error

    def execute_ztp(self) -> None:
        """Execute ZTP on the device."""
        # For Cumulus 5.11+ only, the best method is to factory reset the device
        payload = {"@reset": {"state": "start", "parameters": {"force": True}}}
        rsp = self.post(f"{self._base_url}system/factory-default", json=payload)
        rsp.raise_for_status()

    def get_running_image(self) -> str:
        """Get the running image on the device."""
        rsp = self._get_system()
        # 5.11.x stores product-release at the top level
        if "product-release" in rsp:
            return cast(str, rsp["product-release"])
        # 5.14.0 stores product-release in the version object
        if rsp.get("version", {}).get("product-release"):
            return cast(str, rsp["version"]["product-release"])
        raise NetworkDeviceException(
            "Unable to determine running image on the device.", non_retryable=True
        )

    def get_ztp_status(self) -> str:
        """Get the ZTP status of the device."""
        rsp = self.get(f"{self._base_url}system/ztp")
        return cast(str, rsp.json()["status"])

    def get_uptime(self) -> int:
        """Get the device uptime in seconds."""
        rsp = self._get_system()
        return int(rsp["uptime"])

    def get_platform(self) -> Any:
        """Get the platform information."""
        rsp = self.get(f"{self._base_url}platform", timeout=10)
        return rsp.json()

    def get_platform_environment_fan(self) -> Any:
        """Get platform fan information."""
        rsp = self.get(f"{self._base_url}platform/environment/fan", timeout=10)
        return rsp.json()

    def get_platform_environment_led(self) -> Any:
        """Get platform LED information."""
        rsp = self.get(f"{self._base_url}platform/environment/led", timeout=10)
        return rsp.json()

    def get_platform_environment_psu(self) -> Any:
        """Get platform PSU information."""
        rsp = self.get(f"{self._base_url}platform/environment/psu", timeout=10)
        return rsp.json()

    def get_platform_environment_voltage(self) -> Any:
        """Get platform voltage information."""
        rsp = self.get(f"{self._base_url}platform/environment/voltage", timeout=10)
        return rsp.json()

    def get_platform_inventory(self) -> Any:
        """Get platform inventory information."""
        rsp = self.get(f"{self._base_url}platform/inventory", timeout=10)
        return rsp.json()

    def get_firmware_versions(self) -> dict[str, Any]:
        """Get firmware versions for all components."""
        rsp = self.get(f"{self._base_url}platform/firmware", timeout=30)
        return cast(dict[str, Any], rsp.json())

    def reboot(self) -> None:
        """Reboot the device."""
        payload = {"@reboot": {"state": "start", "parameters": {"no-confirm": True}}}
        rsp = self.post(f"{self._base_url}system", json=payload)
        rsp.raise_for_status()

    def diag_get_version(self) -> object:
        # GET /nvue_v1/system — hostname, OS version, uptime, build date
        return self._get_system()

    def diag_get_interfaces(self) -> object:
        # GET /nvue_v1/interface filtered to link/state, oper-status, and type only.
        # Full interface responses crash switches with many interfaces (large body).
        # Uses the same state_only filter as cable validation (get_interfaces).
        return self.get_interfaces(state_only=True)

    def diag_get_bgp_summary(self) -> object:
        # GET /nvue_v1/vrf — all VRFs with BGP neighbor state filtered in
        rsp = self.get(
            f"{self._base_url}vrf",
            params={"include": ["/*/router/bgp/neighbor"]},
            raise_on_failure=False,
        )
        if rsp.status_code == 404:
            return {"bgp": "not configured"}
        rsp.raise_for_status()
        return rsp.json()

    def diag_get_lldp_neighbors(self) -> object:
        # GET /nvue_v1/interface — filtered to only LLDP neighbor data per interface
        rsp = self.get(
            f"{self._base_url}interface",
            params={"include": ["/*/lldp"]},
        )
        return rsp.json()

    def diag_get_platform(self) -> object:
        # GET /nvue_v1/platform — hardware model, serial, component firmware
        return self.get_platform()

    def diag_get_route_table(self) -> object:
        # GET /nvue_v1/vrf — all VRFs with routing table (RIB) filtered in
        rsp = self.get(
            f"{self._base_url}vrf",
            params={"include": ["/*/router/rib"]},
            raise_on_failure=False,
        )
        if rsp.status_code == 404:
            return {"rib": "not available"}
        rsp.raise_for_status()
        return rsp.json()

    def diag_get_vlan(self) -> object:
        # GET /nvue_v1/bridge/domain — all bridge domains with VLAN membership
        # Equivalent to: nv show bridge port-vlan
        rsp = self.get(f"{self._base_url}bridge/domain", raise_on_failure=False)
        if rsp.status_code == 404:
            return {"error": "No bridge domains configured"}
        rsp.raise_for_status()
        return rsp.json()

    def diag_get_mac_table(self) -> object:
        # GET /nvue_v1/bridge/domain/br_default/mac-table
        # Equivalent to: nv show bridge domain br_default mac-table / net show bridge macs
        rsp = self.get(
            f"{self._base_url}bridge/domain/br_default/mac-table",
            raise_on_failure=False,
        )
        if rsp.status_code == 404:
            return {"error": "Bridge domain br_default not configured or MAC table empty"}
        rsp.raise_for_status()
        return rsp.json()

    def diag_get_mlag(self) -> object:
        # GET /nvue_v1/mlag
        # Equivalent to: nv show clag / net show clag
        rsp = self.get(f"{self._base_url}mlag", raise_on_failure=False)
        if rsp.status_code == 404:
            return {"error": "MLAG not configured on this device"}
        rsp.raise_for_status()
        return rsp.json()

    def diag_get_system_health(self) -> object:
        # GET /nvue_v1/system/health
        # Equivalent to: nv show system health
        rsp = self.get(f"{self._base_url}system/health", raise_on_failure=False)
        if rsp.status_code == 404:
            return {"error": "System health endpoint not available on this NVUE version"}
        rsp.raise_for_status()
        return rsp.json()

    def diag_get_interface_counters(self) -> object:
        # GET /nvue_v1/interface?include=/*/counters
        # Equivalent to: nv show interface --view counters
        rsp = self.get(
            f"{self._base_url}interface",
            params={"include": ["/*/counters"]},
        )
        return rsp.json()

    def diag_get_interface_mac(self) -> object:
        # GET /nvue_v1/interface?include=/*/link/mac
        # Equivalent to: nv show interface mac
        rsp = self.get(
            f"{self._base_url}interface",
            params={"include": ["/*/link/mac"]},
        )
        return rsp.json()

    def diag_get_platform_environment(self) -> object:
        # GET /nvue_v1/platform/environment
        # Equivalent to: nv show platform environment / net show system sensors
        rsp = self.get(f"{self._base_url}platform/environment")
        return rsp.json()

    def diag_get_platform_transceiver(self) -> object:
        # GET /nvue_v1/platform/transceiver
        # Equivalent to: nv show platform transceiver
        rsp = self.get(f"{self._base_url}platform/transceiver", raise_on_failure=False)
        if rsp.status_code == 404:
            return {"error": "Transceiver data not available on this device"}
        rsp.raise_for_status()
        return rsp.json()

    def send_ssh_command(
        self,
        command: str,
        password: str,
        read_timeout: int = 900,
    ) -> str:
        """Execute a privileged shell command on the device via SSH and return its output.

        Uses netmiko (linux device type) with enable() for sudo access, mirroring
        the pattern used by MellanoxConnection. This is the single seam to replace
        when a dedicated nv-config-manager SSH service is available in future — callers such as
        get_tech_support_bundle need not change.

        heartbeat_fn, if provided, is called during quiet stretches of output to
        satisfy the Temporal activity heartbeat window.

        Returns:
            The full combined stdout/stderr output of the command as a string.
        """
        device = {
            "device_type": "linux",
            "host": self._host,
            "port": 22,
            "username": self._username,
            "password": password,
            "secret": password,
            "global_delay_factor": 2,
        }
        with ConnectHandler(**device) as conn:
            conn.enable()
            output = conn.send_command(
                command,
                expect_string=r"#",
                read_timeout=read_timeout,
                strip_prompt=False,
                strip_command=False,
            )
            return str(output)

    def _start_heartbeat_thread(
        self, heartbeat_fn: Callable[[], None] | None
    ) -> tuple[threading.Event, threading.Thread]:
        """Start a background thread that calls heartbeat_fn every 15 s.

        Copies the current contextvars context so that activity.heartbeat()
        works from the thread (threading.Thread does not inherit contextvars).
        """
        stop_event = threading.Event()

        def _beat() -> None:
            while not stop_event.wait(15):
                if heartbeat_fn:
                    try:
                        heartbeat_fn()
                    except Exception:
                        pass

        ctx = contextvars.copy_context()
        thread = threading.Thread(target=ctx.run, args=(_beat,), daemon=True)
        thread.start()
        return stop_event, thread

    def _sftp_download(
        self,
        password: str,
        remote_path: str,
        heartbeat_fn: Callable[[], None] | None,
    ) -> bytes:
        """Open a fresh paramiko SSH connection and download remote_path over SFTP."""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(
                hostname=self._host,
                port=22,
                username=self._username,
                password=password,
                timeout=30,
                banner_timeout=30,
                auth_timeout=30,
                allow_agent=False,
                look_for_keys=False,
            )
            last_hb = [time.monotonic()]

            def _progress(transferred: int, total: int) -> None:
                if heartbeat_fn and time.monotonic() - last_hb[0] >= 10:
                    try:
                        heartbeat_fn()
                    except Exception:
                        pass
                    last_hb[0] = time.monotonic()

            buf = BytesIO()
            sftp = ssh.open_sftp()
            try:
                # 45-second per-read timeout so a stalled transfer surfaces as
                # a clear error rather than a silent heartbeat timeout.
                ch = sftp.get_channel()
                if ch is not None:
                    ch.settimeout(45)
                sftp.getfo(remote_path, buf, callback=_progress)
            finally:
                sftp.close()
            return buf.getvalue()
        finally:
            ssh.close()

    def get_tech_support_bundle(
        self, heartbeat_fn: Callable[[], None] | None = None
    ) -> tuple[bytes, str]:
        """Generate a cl-support bundle and return its content and command log.

        cl-support is a native Cumulus Linux system command — not exposed via
        the NVUE REST API. SSH is used only for this operation; the same device
        credentials are reused (via send_ssh_command / _sftp_download).

        -M requests a "mini" bundle: useful diagnostics without large packet
        captures. The tarball is retrieved over SFTP to avoid base64 overhead.

        heartbeat_fn, if provided, is called every ~15 s in a background thread
        and on each SFTP chunk, keeping the Temporal heartbeat window satisfied.

        Returns:
            (raw bundle bytes, full cl-support command output text)
        """

        def run_with_password(password: str) -> tuple[bytes, str]:
            stop_hb, hb = self._start_heartbeat_thread(heartbeat_fn)
            if heartbeat_fn:
                try:
                    heartbeat_fn()
                except Exception:
                    pass
            try:
                cl_support_log = self.send_ssh_command(
                    "cl-support -M", password=password, read_timeout=900
                )
                bundle_path = _parse_cl_support_path(cl_support_log)
                if not bundle_path:
                    raise NetworkDeviceException(
                        f"cl-support completed but no bundle path found in output:\n{cl_support_log}"
                    )
                content = self._sftp_download(password, bundle_path, heartbeat_fn)
                return content, cl_support_log
            finally:
                stop_hb.set()
                hb.join(timeout=2)

        return cast(
            tuple[bytes, str],
            self._try_passwords_with_callback(
                run_with_password,
                (paramiko.AuthenticationException, NetmikoAuthenticationException),
            ),
        )


# Identical to Cumulus but defaults to port 443
class NVOSConnection(CumulusConnection):
    """NVOS Device Connection."""

    def __init__(
        self,
        host: str,
        port: int = 443,
        username: str | None = None,
        password: str | None = None,
        site: str | None = None,
    ) -> None:
        """Initialize a NVOS Connection."""
        super().__init__(host, port, username, password, site)


class MellanoxConnection(NetworkConnection):
    """Mellanox device connection."""

    def __init__(
        self,
        host: str,
        port: int = 22,
        username: str | None = None,
        password: str | None = None,
        site: str | None = None,
    ) -> None:
        """Initialize connection."""
        super().__init__(host, port, username, password, site)
        self.client: BaseConnection | None = None

    def _connect(self) -> BaseConnection:
        """Connect to the device with password rotation support."""

        def connect_with_password(password: str) -> BaseConnection:
            device = {
                "device_type": "mellanox_mlnxos",
                "host": self._host,
                "username": self._username,
                "password": password,
            }
            return ConnectHandler(**device)

        return self._try_passwords_with_callback(
            connect_with_password,
            (NetmikoAuthenticationException,),
        )

    def execute_command(self, command: str) -> str:
        """Execute a command on the device."""
        if not self.client:
            self.client = self._connect()
        output = self.client.send_command(command)
        return str(output)

    def execute_enable_command(self, command: str, timeout: int = 10) -> str:
        """Execute a command in enable mode."""
        if not self.client:
            self.client = self._connect()
        self.client.enable()
        output = self.client.send_command(command, expect_string=r"#", read_timeout=timeout)
        return str(output)

    def execute_configure_command(self, command: str, timeout: int = 10) -> str:
        """Execute a command in configure mode."""
        if not self.client:
            self.client = self._connect()
        self.client.enable()
        self.client.config_mode()
        output = self.client.send_command(command, expect_string=r"#", read_timeout=timeout)
        return str(output)

    def __del__(self) -> None:
        """Clean up the connection."""
        if self.client:
            self.client.disconnect()

    def _get_diff(self, current_config: str, new_configuration: str) -> str:
        """Get the diff between the current and new configuration in git style."""
        current_config_lines = [
            line.strip()
            for line in current_config.splitlines()
            if not line.startswith("#") and line.strip()
        ]
        new_config_lines = [
            line.strip()
            for line in new_configuration.splitlines()
            if not line.startswith("#") and line.strip()
        ]
        diff = []
        current_set = set(current_config_lines)
        new_set = set(new_config_lines)

        for line in current_config_lines:
            if line not in new_set:
                diff.append(f"- {line}")

        for line in new_config_lines:
            if line not in current_set:
                diff.append(f"+ {line}")

        return "\n".join(diff)

    def perform_candidate_diff(self, new_configuration: str, partial: bool = False) -> str:
        """Load the candidate configuration and return the diff."""
        try:
            current_config = self.execute_enable_command("show running-config")
            diff = self._get_diff(current_config, new_configuration)
            return diff
        except Exception as e:
            raise NetworkDeviceException("Failed to perform candidate diff.") from e

    def commit_candidate_config(
        self,
        new_configuration: str,
        approved_diff: str,
        partial: bool = False,
        *,
        commit_confirm: bool = True,
    ) -> None:
        """Load the candidate configuration and commit."""
        try:
            diff = self.perform_candidate_diff(new_configuration, partial)
            if diff != approved_diff:
                raise DiffChangedException("Diff has changed since approval, aborting.")
            for line in diff.splitlines():
                if line.startswith("-"):
                    line = "no " + line.strip("- ")
                elif line.startswith("+"):
                    line = line.strip("+ ")
                self.execute_configure_command(line)
            self.execute_configure_command("write memory")
        except Exception as e:
            raise NetworkDeviceException("Failed to commit candidate configuration.") from e

    def get_running_configuration(self) -> str:
        """Load the running configuration for a given device."""
        response = self.execute_enable_command("show running-config")
        return response


class JuniperConnection(NetworkConnection):
    """Juniper Junos device connection over NETCONF (PyEZ).

    Uses junos-eznc (PyEZ) over SSH/NETCONF (default port 830). PyEZ provides
    native candidate / diff / commit-confirmed / rollback semantics, so the
    config workflow maps directly onto perform_candidate_diff and
    commit_candidate_config without hand-rolling RPC batches.

    Config is applied as the full desired state via Junos ``load update``.
    """

    # Junos commit-confirmed timeout is expressed in minutes, not seconds. Round
    # up so the rollback window is never shorter than the requested seconds.
    _COMMIT_CONFIRM_ROLLBACK_MINUTES = max(1, (COMMIT_CONFIRM_ROLLBACK_SECONDS + 59) // 60)

    # Ceiling for a single RPC / commit so a stuck device surfaces an error
    # instead of hanging the activity indefinitely.
    _RPC_TIMEOUT_SECONDS = 300

    def __init__(
        self,
        host: str,
        port: int = 830,
        username: str | None = None,
        password: str | None = None,
        site: str | None = None,
    ) -> None:
        """Initialize a Juniper Connection; the NETCONF session opens lazily."""
        super().__init__(host, port, username, password, site)
        self._device: Device | None = None

    # ------------------------------------------------------------------
    # Connection management — NETCONF with password rotation.
    # ------------------------------------------------------------------

    def _connect(self) -> Device:
        """Open a NETCONF session, rotating passwords on authentication failure.

        Only genuine authentication failures trigger password rotation. A probe
        failure (the port is not reachable) or any other connection error is
        raised immediately with a clear message, since retrying with a different
        password would not help.
        """

        def connect_with_password(password: str) -> Device:
            device = Device(
                host=self._host,
                user=self._username,
                passwd=password,
                port=self._port,
                gather_facts=False,
                auto_probe=5,
            )
            device.open()
            return device

        try:
            return cast(
                Device,
                self._try_passwords_with_callback(connect_with_password, (ConnectAuthError,)),
            )
        except ProbeError as error:
            raise NetworkDeviceException(
                f"Cannot reach NETCONF on {self._host}:{self._port}."
            ) from error
        except ConnectError as error:
            raise NetworkDeviceException(
                f"Failed to connect to NETCONF on {self._host}:{self._port}: {error}"
            ) from error

    def _get_device(self) -> Device:
        """Return the open PyEZ device, connecting on first use."""
        if self._device is None:
            self._device = self._connect()
        return self._device

    def close(self) -> None:
        """Close the NETCONF session if it is open."""
        device = getattr(self, "_device", None)
        if device is not None:
            try:
                device.close()
            except Exception:  # noqa: BLE001 - cleanup must not raise
                logger.debug("Error closing NETCONF session to %s", self._host, exc_info=True)
            self._device = None

    def __enter__(self) -> JuniperConnection:
        """Enter a context that closes the NETCONF session on exit."""
        return self

    def __exit__(self, *exc: object) -> None:
        """Close the NETCONF session when leaving the context."""
        self.close()

    def __del__(self) -> None:
        """Best-effort cleanup of the NETCONF session on garbage collection."""
        self.close()

    def _rpc(self, rpc_name: str, params: dict[str, Any] | None = None) -> Any:
        """Run an operational RPC and return its JSON (dict) representation.

        rpc_name accepts either Junos style (get-software-information) or Python
        style (get_software_information). Empty or truthy flag parameters (for
        example ``terse``) are sent as boolean flags.
        """
        device = self._get_device()
        try:
            rpc_method = getattr(device.rpc, rpc_name.replace("-", "_"))
        except AttributeError as error:
            raise NetworkDeviceException(f"Unknown RPC '{rpc_name}' for {self._host}") from error
        kwargs: dict[str, Any] = {}
        for key, value in (params or {}).items():
            flag = value in ("", "true", "True", True)
            kwargs[key.replace("-", "_")] = True if flag else value
        try:
            return rpc_method({"format": "json"}, **kwargs)
        except RpcError as error:
            raise NetworkDeviceException(
                f"RPC {rpc_name} failed on {self._host}: {error}"
            ) from error

    def _get_fact(self, name: str) -> Any:
        """Return a PyEZ fact, or None when the device does not report one.

        The PyEZ fact cache swallows RPC and transport errors and caches None in
        their place, so an empty fact is re-checked against a live RPC to tell a
        value the device does not have from one that failed to read.
        """
        device = self._get_device()
        value = device.facts.get(name)
        if value:
            return value
        try:
            device.rpc.get_software_information()
        except (RpcError, ConnectError) as error:
            raise NetworkDeviceException(
                f"Failed to read the {name} fact from {self._host}: {error}"
            ) from error
        return None

    def _get_config(self, fmt: str) -> str:
        """Return the committed configuration in the requested format."""
        device = self._get_device()
        try:
            result = device.rpc.get_config(options={"format": fmt, "database": "committed"})
        except RpcError as error:
            raise NetworkDeviceException(
                f"Failed to read configuration from {self._host}: {error}"
            ) from error
        if isinstance(result, str):
            return result
        # set/text formats return an lxml element whose text holds the config.
        return getattr(result, "text", "") or ""

    def _load_full_config(self, cu: Config, new_configuration: str) -> None:
        """Load the complete desired-state config via Junos ``load update``."""
        try:
            cu.load(new_configuration, format="text", update=True)
        except ConfigLoadError as error:
            raise ConfigSyntaxException(
                f"Invalid configuration for {self._host}: {error}"
            ) from error

    @staticmethod
    def _reject_partial(partial: bool) -> None:
        """Reject partial applies; JuniperConnection supports full desired state only."""
        if partial:
            raise NetworkDeviceException(
                "Partial configuration is not supported for JuniperConnection; "
                "supply the full desired-state configuration.",
                non_retryable=True,
            )

    def _commit(self, cu: Config, commit_confirm: bool) -> None:
        """Commit the candidate, optionally with a rollback timer."""
        if commit_confirm:
            cu.commit(
                confirm=self._COMMIT_CONFIRM_ROLLBACK_MINUTES,
                timeout=self._RPC_TIMEOUT_SECONDS,
            )
        else:
            cu.commit(timeout=self._RPC_TIMEOUT_SECONDS)

    # ------------------------------------------------------------------
    # Read operations.
    # ------------------------------------------------------------------

    def get_running_configuration(self) -> str:
        """Return the running configuration in hierarchical (curly-brace) text.

        Text is the full desired-state format consumed by ``load update``, so a
        stored backup can be re-applied through the full-config path.
        """
        return self._get_config("text").strip() + "\n"

    def get_configuration_text(self) -> str:
        """Return the running configuration in hierarchical (curly-brace) text."""
        return self._get_config("text")

    def get_hostname(self) -> str:
        """Get the system hostname."""
        hostname = self._get_fact("hostname")
        if not hostname:
            raise ApplicationError(
                f"No hostname returned for {self._host}",
                non_retryable=True,
            )
        return str(hostname)

    def get_running_image(self) -> str:
        """Get the running Junos version on the device."""
        version = self._get_fact("version")
        if not version:
            raise NetworkDeviceException(
                f"Unable to determine running image on {self._host}.", non_retryable=True
            )
        return str(version)

    def get_uptime(self) -> int:
        """Get the device uptime in seconds."""
        data = self._rpc("get-system-uptime-information")
        try:
            uptime = data["system-uptime-information"][0]["uptime-information"][0]["up-time"][0]
            return int(uptime["attributes"]["junos:seconds"])
        except (KeyError, IndexError, TypeError, ValueError) as error:
            raise NetworkDeviceException(f"Unable to determine uptime on {self._host}.") from error

    # ------------------------------------------------------------------
    # Configuration operations.
    # ------------------------------------------------------------------

    def perform_candidate_diff(self, new_configuration: str, partial: bool = False) -> str:
        """Load the full desired-state candidate and return the diff versus active."""
        self._reject_partial(partial)
        device = self._get_device()
        try:
            with Config(device, mode="exclusive") as cu:
                self._load_full_config(cu, new_configuration)
                diff = cu.diff()
                cu.rollback()
        except ConfigSyntaxException:
            raise
        except (LockError, UnlockError, RpcError, ConnectError) as error:
            raise NetworkDeviceException(
                f"Failed to perform candidate diff on {self._host}: {error}"
            ) from error
        return diff or ""

    def commit_candidate_config(
        self,
        new_configuration: str,
        approved_diff: str,
        partial: bool = False,
        *,
        commit_confirm: bool = True,
    ) -> None:
        """Load the full desired-state candidate and commit."""
        self._reject_partial(partial)
        device = self._get_device()
        try:
            with Config(device, mode="exclusive") as cu:
                self._load_full_config(cu, new_configuration)
                diff = cu.diff()
                if diff and diff != approved_diff:
                    cu.rollback()
                    raise DiffChangedException("Diff has changed since approval, aborting.")
                if diff:
                    self._commit(cu, commit_confirm)
                else:
                    cu.rollback()
        except (ConfigSyntaxException, DiffChangedException):
            raise
        except (CommitError, LockError, UnlockError, RpcError, ConnectError) as error:
            raise NetworkDeviceException(
                f"Failed to apply candidate configuration on {self._host}: {error}"
            ) from error

        if commit_confirm:
            # Confirm the pending commit to cancel the rollback timer.
            self._confirm_commit()

    def _confirm_commit(self) -> None:
        """Confirm a pending commit-confirmed, cancelling its rollback timer."""
        device = self._get_device()
        try:
            with Config(device, mode="exclusive") as cu:
                cu.commit(timeout=self._RPC_TIMEOUT_SECONDS)
        except (CommitError, LockError, UnlockError, RpcError, ConnectError) as error:
            raise NetworkDeviceException(
                f"Failed to confirm commit on {self._host}: {error}"
            ) from error

    # ------------------------------------------------------------------
    # Rollback to a numbered revision (Junos keeps rollback 0-49).
    # ------------------------------------------------------------------

    def get_rollback_diff(self, rollback_id: int = 1) -> str:
        """Return the diff between the active config and a numbered rollback."""
        device = self._get_device()
        try:
            with Config(device, mode="exclusive") as cu:
                diff = cu.diff(rb_id=rollback_id)
                cu.rollback()
        except (LockError, UnlockError, RpcError, ConnectError, ValueError) as error:
            raise NetworkDeviceException(
                f"Failed to read rollback {rollback_id} diff on {self._host}: {error}"
            ) from error
        return diff or ""

    def rollback_configuration(self, rollback_id: int = 1, *, commit_confirm: bool = True) -> None:
        """Roll back to a numbered rollback revision and commit (instant rollback)."""
        device = self._get_device()
        try:
            with Config(device, mode="exclusive") as cu:
                cu.rollback(rb_id=rollback_id)
                if cu.diff():
                    self._commit(cu, commit_confirm)
                else:
                    cu.rollback()
        except (CommitError, LockError, UnlockError, RpcError, ConnectError, ValueError) as error:
            raise NetworkDeviceException(
                f"Failed to roll back to revision {rollback_id} on {self._host}: {error}"
            ) from error
        if commit_confirm:
            self._confirm_commit()

    # ------------------------------------------------------------------
    # Rescue configuration (a named checkpoint of the active config).
    # ------------------------------------------------------------------

    def save_rescue_configuration(self) -> None:
        """Save the current active config as the rescue checkpoint."""
        device = self._get_device()
        try:
            Config(device).rescue(action="save")
        except (RpcError, ConnectError) as error:
            raise NetworkDeviceException(
                f"Failed to save rescue configuration on {self._host}: {error}"
            ) from error

    def get_rescue_configuration(self) -> str | None:
        """Return the saved rescue configuration, or None if none is set."""
        device = self._get_device()
        try:
            result = Config(device).rescue(action="get", format="text")
        except (RpcError, ConnectError) as error:
            raise NetworkDeviceException(
                f"Failed to read rescue configuration on {self._host}: {error}"
            ) from error
        return result if result else None

    def delete_rescue_configuration(self) -> None:
        """Delete the saved rescue configuration."""
        device = self._get_device()
        try:
            Config(device).rescue(action="delete")
        except (RpcError, ConnectError) as error:
            raise NetworkDeviceException(
                f"Failed to delete rescue configuration on {self._host}: {error}"
            ) from error

    def rollback_to_rescue(self, *, commit_confirm: bool = True) -> None:
        """Roll back to the saved rescue configuration and commit."""
        device = self._get_device()
        try:
            with Config(device, mode="exclusive") as cu:
                cu.rescue(action="reload")
                if cu.diff():
                    self._commit(cu, commit_confirm)
                else:
                    cu.rollback()
        except (CommitError, LockError, UnlockError, RpcError, ConnectError) as error:
            raise NetworkDeviceException(
                f"Failed to roll back to rescue configuration on {self._host}: {error}"
            ) from error
        if commit_confirm:
            self._confirm_commit()

    # ------------------------------------------------------------------
    # Diagnostic commands — operational RPCs returning JSON.
    # ------------------------------------------------------------------

    def diag_get_version(self) -> object:
        return self._rpc("get-software-information")

    def diag_get_interfaces(self) -> object:
        return self._rpc("get-interface-information", params={"terse": True})

    def diag_get_lldp_neighbors(self) -> object:
        return self._rpc("get-lldp-neighbors-information")

    def diag_get_route_table(self) -> object:
        return self._rpc("get-route-summary-information")

    def diag_get_arp_table(self) -> object:
        return self._rpc("get-arp-table-information")
