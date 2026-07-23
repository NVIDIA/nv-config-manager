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
"""Common Device Workflow Models/Utils."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, ClassVar

import netaddr
from pydantic import BaseModel, computed_field
from temporalio.exceptions import ApplicationError

from nv_config_manager.temporal.common.mixins.base import BaseMixin
from nv_config_manager.temporal.common.search_attributes import (
    DEVICE_ID_SEARCH_ATTRIBUTE,
    DEVICE_NAME_SEARCH_ATTRIBUTE,
    DEVICE_PLATFORM_SEARCH_ATTRIBUTE,
    DEVICE_ROLE_SEARCH_ATTRIBUTE,
    SITE_SEARCH_ATTRIBUTE,
    upsert_missing_search_attributes,
)


class Platform(StrEnum):
    """Network device platform types."""

    ARISTA_EOS = "arista-eos"
    CUMULUS_LINUX = "cumulus-linux"
    NV_OS = "nv-os"
    MLNX_OS = "mlnx-os"
    JUNIPER_JUNOS = "juniper-junos"
    UFM = "ufm"

    @property
    def nautobot_name(self) -> str:
        """Return the Nautobot display name for this platform."""
        _nautobot_names = {
            Platform.ARISTA_EOS: "Arista EOS",
            Platform.CUMULUS_LINUX: "Cumulus Linux",
            Platform.NV_OS: "NV-OS",
            Platform.MLNX_OS: "MLNX-OS",
            Platform.JUNIPER_JUNOS: "Juniper Junos",
            Platform.UFM: "UFM",
        }
        return _nautobot_names[self]


class DeviceBayData(BaseModel):
    """Device bay data."""

    name: str
    id: str
    installed_device_id: str | None

    @staticmethod
    def from_nautobot_graphql(bay: dict[str, Any]) -> DeviceBayData:
        """Craft object from graphql output."""
        return DeviceBayData(
            id=bay["id"],
            name=bay["name"],
            installed_device_id=bay["installed_device"].get("id"),
        )


class InterfaceData(BaseModel):
    """Device interface data."""

    name: str
    id: str
    host: str
    mac_address: str | None
    vrf_id: str | None

    @staticmethod
    def from_nautobot_graphql(interface: dict[str, Any]) -> InterfaceData:
        """Craft object from graphql output."""
        device = None
        if interface["device"]:
            device = interface["device"]
        elif interface["module"]:
            device = interface["module"]["device"]
        if not device:
            raise ApplicationError(f"Interface {interface['id']} has no device associated.")
        return InterfaceData(
            id=interface["id"],
            name=interface["name"],
            host=device["name"] if device.get("name") else device.get("id"),
            mac_address=(
                str(netaddr.EUI(interface["mac_address"])) if interface["mac_address"] else None
            ),
            vrf_id=interface["vrf"].get("id") if interface.get("vrf") else None,
        )


class DeviceData(BaseModel):
    """Device data needed for backup and deployment execution."""

    id: str
    name: str
    rack: str | None = None
    position: int | None = None
    role: str
    site: str
    device_type: str

    # Fields to include in markdown table output
    markdown_fields: ClassVar[list[str]] = ["name", "role", "site", "rack", "position"]

    @staticmethod
    def _slugify(name: str) -> str:
        # Nautobot 2.x drops the use of slugs, so for consistency
        # we'll make our own slugs
        return name.lower().replace(" ", "-")

    @staticmethod
    def _extract_site(device: dict[str, Any]) -> str:
        location = device["location"]
        while location:
            if location["location_type"]["name"] == "Site":
                return str(location["name"])
            location = location.get("parent")
        raise ApplicationError(
            f"Could not identify site for {device['name']}, check graphql depth."
        )


class NetworkDeviceData(DeviceData):
    """Network device data."""

    platform: Platform
    primary_ip4: str | None
    primary_ip6: str | None
    config_context: dict[str, Any] | None = None
    render_enabled: bool = False
    deploy_enabled: bool = False
    backup_enabled: bool = False
    ztp_enabled: bool = False

    # Fields to include in markdown table output
    markdown_fields: ClassVar[list[str]] = [
        "name",
        "platform",
        "role",
        "site",
        "rack",
        "position",
    ]

    @computed_field  # type: ignore[misc]
    @property
    def backup_path(self) -> str:
        """
        Generate the path to the backup configuration.
        """
        # Matches the same logic as intended for now
        return self.intended_config_path

    @computed_field  # type: ignore[misc]
    @property
    def intended_config_path(self) -> str:
        """Generate the path to the intended configuration."""
        return f"{self.id}/{self.intended_config_file}"

    @computed_field  # type: ignore[misc]
    @property
    def intended_config_file(self) -> str:
        """Generate the file name for the intended configuration."""
        if self.platform == Platform.ARISTA_EOS:
            return "full-config"
        if self.platform == Platform.CUMULUS_LINUX:
            return "startup.yaml"
        if self.platform == Platform.NV_OS:
            return "startup.yaml"
        if self.platform == Platform.MLNX_OS:
            return "full-config"
        if self.platform == Platform.JUNIPER_JUNOS:
            # Junos `set` format round-trips through load-configuration
            # (action="set"), so the stored backup can be re-applied directly.
            return "config.set"
        if self.platform == Platform.UFM:
            return ""
        raise NotImplementedError(f"No configuration path implemented for platform {self.platform}")

    @computed_field  # type: ignore[misc]
    @property
    def tenant_config_file(self) -> str:
        """Generate the file name for the tenant configuration."""
        if self.platform == Platform.CUMULUS_LINUX:
            return "tenant.yaml"
        # For other platforms, return an empty string as tenant config is not applicable
        return ""

    @computed_field  # type: ignore[misc]
    @property
    def tenant_config_path(self) -> str:
        """Generate the path to the tenant configuration."""
        if not self.tenant_config_file:
            return ""
        return f"{self.id}/{self.tenant_config_file}"

    @computed_field  # type: ignore[misc]
    @property
    def backup_file(self) -> str:
        """Generate the file name for the backup configuration."""
        return self.intended_config_file

    @computed_field  # type: ignore[misc]
    @property
    def host(self) -> str:
        """Return the login IP to use for the device."""
        host = self.primary_ip4 if self.primary_ip4 else self.primary_ip6
        if host is None:
            # Impossible to reach if from_graphql is used, but satisfies type checking
            raise ApplicationError(f"No primary IPv4 or IPv6 IP set for {self.name} in nautobot.")
        return host

    @staticmethod
    def _from_nautobot_graphql_v2(device: dict[str, Any]) -> NetworkDeviceData:
        """Craft object from graphql output."""
        site = NetworkDeviceData._extract_site(device)
        # Rack can be set to Null in NB
        rack = device["rack"].get("name") if device.get("rack") else None

        device_data = NetworkDeviceData(
            id=device["id"],
            name=device["name"],
            rack=rack,
            position=device.get("position"),
            role=NetworkDeviceData._slugify(device["role"]["name"]),
            platform=Platform(NetworkDeviceData._slugify(device["platform"]["name"])),
            device_type=NetworkDeviceData._slugify(device["device_type"]["model"]),
            site=site,
            primary_ip4=(device["primary_ip4"]["host"] if device["primary_ip4"] else None),
            primary_ip6=(device["primary_ip6"]["host"] if device["primary_ip6"] else None),
            config_context=device.get("config_context"),
            render_enabled=device["configmanagerdevicestatus"]["render_enabled"]
            if device["configmanagerdevicestatus"]
            else False,
            deploy_enabled=device["configmanagerdevicestatus"]["deploy_enabled"]
            if device["configmanagerdevicestatus"]
            else False,
            backup_enabled=device["configmanagerdevicestatus"]["backup_enabled"]
            if device["configmanagerdevicestatus"]
            else False,
            ztp_enabled=device["configmanagerdevicestatus"]["ztp_enabled"]
            if device["configmanagerdevicestatus"]
            else False,
        )
        if not (device_data.primary_ip4 or device_data.primary_ip6):
            raise ApplicationError(
                f"No primary IPv4 or IPv6 IP set for {device_data.name} in nautobot."
            )
        return device_data

    @staticmethod
    def from_nautobot_graphql(device: dict[str, Any]) -> NetworkDeviceData:
        """Craft object from graphql output."""
        return NetworkDeviceData._from_nautobot_graphql_v2(device)


class HostDeviceData(DeviceData):
    """Host device data."""

    serial: str | None
    device_bays: list[DeviceBayData]
    interfaces: list[InterfaceData]

    @staticmethod
    def _from_nautobot_graphql_v2(device: dict[str, Any]) -> HostDeviceData:
        # Traverse the location object until we find the parent
        site = HostDeviceData._extract_site(device)
        # Rack can be set to Null in NB
        rack = device["rack"].get("name") if device.get("rack") else None

        return HostDeviceData(
            id=device["id"],
            name=device["name"],
            rack=rack,
            position=device.get("position"),
            role=HostDeviceData._slugify(device["role"]["name"]),
            device_type=HostDeviceData._slugify(device["device_type"]["model"]),
            site=site,
            device_bays=[DeviceBayData.from_nautobot_graphql(bay) for bay in device["device_bays"]],
            interfaces=[
                InterfaceData.from_nautobot_graphql(interface) for interface in device["interfaces"]
            ],
            serial=device["serial"] if device.get("serial") else None,
        )

    @staticmethod
    def from_nautobot_graphql(device: dict[str, Any]) -> HostDeviceData:
        """Craft object from graphql output."""
        return HostDeviceData._from_nautobot_graphql_v2(device)


class DeviceMixin(BaseMixin):
    """Device based workflow mix-in."""

    @staticmethod
    def attach_device_search_attributes(device: DeviceData) -> None:
        """Attach Device Metadata in search attributes."""
        attrs = {
            DEVICE_ID_SEARCH_ATTRIBUTE: [device.id],
            DEVICE_ROLE_SEARCH_ATTRIBUTE: [device.role],
            SITE_SEARCH_ATTRIBUTE: [device.site],
            DEVICE_NAME_SEARCH_ATTRIBUTE: [device.name],
        }
        if isinstance(device, NetworkDeviceData):
            attrs[DEVICE_PLATFORM_SEARCH_ATTRIBUTE] = [device.platform]
        upsert_missing_search_attributes(attrs)
