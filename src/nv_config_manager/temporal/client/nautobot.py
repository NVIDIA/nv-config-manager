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
"""Nautobot Client for Temporal workflows.

Extends the base NautobotClient with temporal-specific methods for
device queries, workflow integration, and NVIDIA Config Manager plugin interactions.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any, cast

from pydantic import BaseModel
from temporalio.exceptions import ApplicationError

from nv_config_manager.common.client import NautobotClient as BaseNautobotClient
from nv_config_manager.common.client import NautobotException
from nv_config_manager.common.config import load_config
from nv_config_manager.common.log import LogCategory, get_logger
from nv_config_manager.temporal.common.mixins.device import (
    HostDeviceData,
    InterfaceData,
    NetworkDeviceData,
    Platform,
)

logger = get_logger(__name__, category=LogCategory.NAUTOBOT)
logger.setLevel(logging.INFO)

# Re-export for backward compatibility
__all__ = ["NautobotClient", "NautobotException"]

CONFIG_MANAGER_BACKUP_CONFIG_PATH = "plugins/nv-config-manager/backupconfig"

# REST API base path for the nautobot_app_overlays plugin (Overlay/VXLAN models).
OVERLAYS_PLUGIN_BASE = "plugins/overlays"


class DeviceVrfInfo(BaseModel):
    """Device VRF Information."""

    vrf_id: str
    vrf_name: str


class NautobotClient(BaseNautobotClient):
    """Async Nautobot Client for Temporal workflows.

    Extends the base NautobotClient with methods specific to temporal
    workflows, including device queries, NVIDIA Config Manager plugin interactions, and
    VRF management.
    """

    def __init__(self) -> None:
        """Initialize the nautobot client from config."""
        # Lazy import to avoid circular dependency with nv_config_manager.common.config
        from nv_config_manager.common.config import parse_verify_param

        config = load_config()
        super().__init__(
            nautobot_url=config["nautobot"]["server"],
            token=config["nautobot"]["token"],
            verify=parse_verify_param(config["nautobot"]),
        )

    async def graphql_query(
        self, query: str, variables: dict[str, Any] | None = None, timeout: int | None = 10
    ) -> dict[str, Any]:
        """Execute a graphql query with Temporal-specific error handling."""
        logger.info(
            "%s: Sending graphql query with variables %s",
            self.graphql_endpoint,
            variables,
        )
        try:
            return await super().graphql_query(query, variables, timeout)
        except NautobotException as e:
            raise ApplicationError(str(e)) from e

    async def get_device(self, fields: str, device_id: str) -> Any:
        """Query device by device UUID."""
        query = (
            """
            query ($id: ID!) {
              device(id: $id) {
        """
            f"{fields}"
            """
              }
            }
        """
        )
        data = await self.graphql_query(query, {"id": device_id})
        return data["data"]["device"]

    async def get_network_device(self, device_id: str) -> NetworkDeviceData:
        """Get a network device by ID."""
        fields = """
              id
              name
              rack {
                name
              }
              position
              role {
                name
              }
              platform {
                name
              }
              device_type {
                model
              }
              primary_ip4{
                host
              }
              primary_ip6{
                host
              }
              config_context
              location {
                name
                location_type {
                  name
                }
                parent {
                  name
                  location_type {
                    name
                  }
                  parent {
                    name
                    location_type {
                      name
                    }
                  }
                }
              }
              configmanagerdevicestatus {
                render_enabled
                deploy_enabled
                backup_enabled
                ztp_enabled
              }
          """

        device = await self.get_device(fields, device_id)
        return NetworkDeviceData.from_nautobot_graphql(device)

    async def get_host_device(self, device_id: str) -> HostDeviceData:
        """Get a host device by ID."""
        fields = """
              id
              name
              rack {
                name
              }
              position
              role {
                name
              }
              device_type {
                model
              }
              location {
                name
                location_type {
                  name
                }
                parent {
                  name
                  location_type {
                    name
                  }
                  parent {
                    name
                    location_type {
                      name
                    }
                  }
                }
              }
              device_bays {
                id
                name
                installed_device {
                  id
                }
              }
              interfaces {
                id
                name
                mac_address
                device {
                  name
                }
              }
          """

        device = await self.get_device(fields, device_id)
        return HostDeviceData.from_nautobot_graphql(device)

    @staticmethod
    def _normalize_to_list(value: str | list[str]) -> list[str]:
        """Convert a single value or list to a list."""
        return [value] if isinstance(value, str) else value

    def _build_device_filter_variables(
        self,
        site: str | list[str] | None,
        status: str | list[str] | None,
        role: str | list[str] | None,
        tenant: str | list[str] | None,
        device_type_id: str | list[str] | None,
        mac_address: str | list[str] | None,
        device_ids: str | list[str] | None,
        platform: Platform | list[Platform] | None,
    ) -> dict[str, list[str]]:
        """Build variables dictionary for device filtering."""
        variables: dict[str, list[str]] = {}

        if site:
            variables["site"] = self._normalize_to_list(site)
        if status:
            variables["status"] = self._normalize_to_list(status)
        if role:
            variables["role"] = self._normalize_to_list(role)
        if tenant:
            variables["tenant"] = self._normalize_to_list(tenant)
        if device_type_id:
            variables["device_type_id"] = self._normalize_to_list(device_type_id)
        if mac_address:
            variables["mac_address"] = self._normalize_to_list(mac_address)
        if device_ids:
            variables["device_ids"] = self._normalize_to_list(device_ids)
        if platform:
            variables["platform"] = (
                [p.nautobot_name for p in platform]
                if isinstance(platform, list | tuple)
                else [platform.nautobot_name]
            )

        if not variables:
            raise NautobotException("Must apply at least one filter.")

        return variables

    @staticmethod
    def _deduplicate_devices(devices_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove duplicate devices and raise error if duplicates found."""
        device_names: set[str] = set()
        duplicates: set[str] = set()
        unique_devices: list[dict[str, Any]] = []

        for device_data in devices_data:
            device_name = device_data["name"]
            if device_name in device_names:
                duplicates.add(device_name)
            else:
                device_names.add(device_name)
                unique_devices.append(device_data)

        if duplicates:
            raise NautobotException(f"Duplicate device names in nautobot: {duplicates}")

        return unique_devices

    async def get_devices(  # pylint: disable=too-many-arguments
        self,
        fields: str,
        site: str | list[str] | None = None,
        status: str | list[str] | None = None,
        role: str | list[str] | None = None,
        tenant: str | list[str] | None = None,
        device_type_id: str | list[str] | None = None,
        mac_address: str | list[str] | None = None,
        device_ids: str | list[str] | None = None,
        platform: Platform | list[Platform] | None = None,
    ) -> list[dict[str, Any]]:
        """Return a filtered list of devices."""
        variables = self._build_device_filter_variables(
            site, status, role, tenant, device_type_id, mac_address, device_ids, platform
        )

        query = (
            """
            query (
              $site: [String],
              $status: [String],
              $role: [String],
              $tenant: [String],
              $device_type_id: [String],
              $mac_address: [String],
              $device_ids: [String],
              $platform: [String]
            ) {
              devices(
                location: $site,
                status: $status,
                role: $role,
                tenant: $tenant,
                device_type: $device_type_id,
                mac_address: $mac_address,
                id: $device_ids,
                platform: $platform
              ) {
        """
            f"{fields}"
            """
              }
            }
        """
        )

        data = await self.graphql_query(query, variables)
        return self._deduplicate_devices(data["data"]["devices"])

    async def get_network_devices(self, **kwargs: Any) -> list[NetworkDeviceData]:
        """Get network devices."""
        fields = """
                id
                name
                rack {
                  name
                }
                position
                role {
                  name
                }
                tenant {
                  name
                }
                device_type {
                  model
                }
                platform {
                  name
                }
                location {
                  name
                  location_type {
                    name
                  }
                  parent {
                    name
                    location_type {
                      name
                    }
                    parent {
                      name
                      location_type {
                        name
                      }
                    }
                  }
                }
                primary_ip4 {
                  host
                }
                primary_ip6 {
                  host
                }
                config_context
                configmanagerdevicestatus {
                  render_enabled
                  deploy_enabled
                  backup_enabled
                  ztp_enabled
                }
        """
        # Remove filtering parameters that are not supported by get_devices
        device_status_filters = {
            "render_enabled": kwargs.pop("render_enabled", None),
            "deploy_enabled": kwargs.pop("deploy_enabled", None),
            "backup_enabled": kwargs.pop("backup_enabled", None),
            "ztp_enabled": kwargs.pop("ztp_enabled", None),
        }

        device_data_list = await self.get_devices(fields, **kwargs)
        devices = [NetworkDeviceData.from_nautobot_graphql(data) for data in device_data_list]
        if device_status_filters.get("render_enabled") is not None:
            devices = [
                device
                for device in devices
                if device.render_enabled == device_status_filters["render_enabled"]
            ]
        if device_status_filters.get("deploy_enabled") is not None:
            devices = [
                device
                for device in devices
                if device.deploy_enabled == device_status_filters["deploy_enabled"]
            ]
        if device_status_filters.get("backup_enabled") is not None:
            devices = [
                device
                for device in devices
                if device.backup_enabled == device_status_filters["backup_enabled"]
            ]
        if device_status_filters.get("ztp_enabled") is not None:
            devices = [
                device
                for device in devices
                if device.ztp_enabled == device_status_filters["ztp_enabled"]
            ]
        return devices

    async def get_host_devices(self, **kwargs: Any) -> list[HostDeviceData]:
        """Get host devices."""

        fields = """
                id
                name
                rack {
                  name
                }
                position
                role {
                  name
                }
                tenant {
                  name
                }
                device_type {
                  model
                }
                location {
                  name
                  location_type {
                    name
                  }
                  parent {
                    name
                    location_type {
                      name
                    }
                    parent {
                      name
                      location_type {
                        name
                      }
                    }
                  }
                }
                device_bays {
                  id
                  name
                  installed_device {
                    id
                  }
                }
                interfaces {
                  id
                  name
                  mac_address
                  device {
                    name
                  }
                }
        """
        device_data_list = await self.get_devices(fields, **kwargs)
        return [HostDeviceData.from_nautobot_graphql(data) for data in device_data_list]

    async def get_interfaces_by_mac(self, mac_addresses: list[str]) -> list[InterfaceData]:
        """Get a list of interfaces by MAC addresses."""
        query = """
              query($mac_address: [String]) {
                interfaces(mac_address: $mac_address) {
                  id
                  name
                  mac_address
                  device {
                    name
                  }
                  module {
                    device {
                      name
                    }
                  }
                }
              }
        """
        interfaces = []
        data = await self.graphql_query(query, {"mac_address": mac_addresses})
        for interface_data in data["data"]["interfaces"]:
            try:
                interfaces.append(InterfaceData.from_nautobot_graphql(interface_data))
            except ApplicationError:
                logger.exception("Error parsing interface %s", interface_data["id"])
                continue
        return interfaces

    async def get_device_interfaces(self, device_id: str) -> list[InterfaceData]:
        """Get interfaces for a device."""
        query = """
              query ($device_id: [String]) {
                interfaces(device_id: $device_id) {
                  id
                  device {
                    name
                  }
                  mac_address
                  name
                  ip_addresses {
                    address
                  }
                  vrf {
                    id
                    name
                  }
                }
              }
              """
        data = await self.graphql_query(query, {"device_id": [device_id]})
        return [InterfaceData.from_nautobot_graphql(intf) for intf in data["data"]["interfaces"]]

    async def get_device_vrfs(self, device_id: str) -> list[DeviceVrfInfo]:
        """Get VRFs assigned to a device."""
        query = """
              query ($device_id: ID!) {
                device(id: $device_id) {
                  vrfs {
                    id
                    name
                  }
                }
              }
              """
        data = await self.graphql_query(query, {"device_id": device_id})
        device_data = data["data"]["device"]
        if not device_data:
            raise ApplicationError(f"Device {device_id} not found")

        return [
            DeviceVrfInfo(vrf_id=vrf["id"], vrf_name=vrf["name"]) for vrf in device_data["vrfs"]
        ]

    async def load_config_manager_plugin_backup_config(self, device_id: str) -> dict[str, Any]:
        """Load the most recent NVIDIA Config Manager backup data."""
        session = await self._ensure_session()
        async with session.get(
            f"{self.rest_endpoint}{CONFIG_MANAGER_BACKUP_CONFIG_PATH}/{device_id}/",
        ) as rsp:
            if rsp.status == 404:
                # No existing backup to reference
                return {}
            rsp.raise_for_status()
            return cast(dict[str, Any], await rsp.json())

    async def update_config_manager_plugin_backup_config(  # pylint: disable=too-many-arguments
        self,
        device_id: str,
        config_store_instance: str,
        commit_id: str | int,
        path: str,
        user: str,
        commit_message: str,
        workflow_id: str,
        deployed_commit_id: str | int | None = None,
    ) -> None:
        """Update NVIDIA Config Manager NB Plugin with backup metadata."""
        # TODO: Include config target and type enum
        data = {
            "device_id": device_id,
            "config_store_instance": config_store_instance,
            "path": path,
            "commit_id": commit_id,
            "updated": datetime.now(UTC).isoformat(),
            "updated_by": user,
            "commit_message": commit_message,
            "workflow_id": workflow_id,
            # Plugin has a not-null constraint on this field, empty string is valid
            "deployed_commit_id": deployed_commit_id or "",
        }
        session = await self._ensure_session()
        async with session.post(
            f"{self.rest_endpoint}{CONFIG_MANAGER_BACKUP_CONFIG_PATH}/",
            json=data,
        ) as rsp:
            rsp.raise_for_status()

    async def update_interface(self, interface_id: str, data: Any) -> InterfaceData:
        """Update an interface resource."""
        patch_data = await self.patch(path=f"dcim/interfaces/{interface_id}/", data=data)
        return InterfaceData.from_nautobot_graphql(patch_data)

    async def update_host_device(self, device_id: str, data: Any) -> HostDeviceData:
        """Update a host device resource."""
        patch_data = await self.patch(path=f"dcim/devices/{device_id}/", data=data)
        return HostDeviceData.from_nautobot_graphql(patch_data)

    async def create_vrf(self, data: Any) -> Any:
        """Create a VRF resource."""
        return await self.post("ipam/vrfs/", data=data)

    async def delete_vrf(self, uuid: str) -> None:
        """Delete a VRF resource."""
        await self.delete(f"ipam/vrfs/{uuid}/")

    async def assign_vrf_to_device(self, device_id: str, vrf_id: str) -> Any:
        """Assign a VRF to a device."""
        return await self.post(
            "ipam/vrf-device-assignments/", data={"device": device_id, "vrf": vrf_id}
        )

    async def lookup_id_by_name(self, path: str, name: str) -> str | None:
        """Return the UUID of a Nautobot object matched by name, or None if not found.

        Raises NautobotException if more than one object matches, to prevent silently
        binding to the wrong ID when names are not globally unique.
        """
        data = await self.get(path, params={"name": name})
        results = data.get("results", [])
        if len(results) > 1:
            raise NautobotException(
                f"Ambiguous name '{name}' at {path}: {len(results)} objects match"
            )
        return cast(str, results[0]["id"]) if results else None

    async def create_overlay(self, data: Any) -> Any:
        """Create an Overlay in the overlays plugin."""
        return await self.post(f"{OVERLAYS_PLUGIN_BASE}/overlays/", data=data)

    async def find_overlay(self, name: str, location_id: str) -> dict[str, Any] | None:
        """Return an existing Overlay matching name + location, or None."""
        data = await self.get(
            f"{OVERLAYS_PLUGIN_BASE}/overlays/",
            params={"name": name, "location": location_id},
        )
        results = data.get("results", [])
        return cast(dict[str, Any], results[0]) if results else None

    async def get_overlay(self, overlay_id: str) -> dict[str, Any]:
        """Get an Overlay by ID, including its related VXLANs and assignments."""
        return cast(
            dict[str, Any],
            await self.get(f"{OVERLAYS_PLUGIN_BASE}/overlays/{overlay_id}/", params={"depth": 1}),
        )

    async def delete_overlay(self, overlay_id: str) -> None:
        """Delete an Overlay."""
        await self.delete(f"{OVERLAYS_PLUGIN_BASE}/overlays/{overlay_id}/")

    async def create_vxlan(self, data: Any) -> Any:
        """Create a VXLAN in the overlays plugin."""
        return await self.post(f"{OVERLAYS_PLUGIN_BASE}/vxlans/", data=data)

    async def get_vxlans_by_vnid(self, vnid: int) -> list[dict[str, Any]]:
        """Return overlay-plugin VXLANs with the given VNI (namespace resolved via depth)."""
        data = await self.get(f"{OVERLAYS_PLUGIN_BASE}/vxlans/", params={"vnid": vnid, "depth": 1})
        return cast(list[dict[str, Any]], data.get("results", []))

    async def get_vxlans_by_overlay(self, overlay_id: str) -> list[dict[str, Any]]:
        """Return overlay-plugin VXLANs bound to the given overlay."""
        data = await self.get(f"{OVERLAYS_PLUGIN_BASE}/vxlans/", params={"overlay": overlay_id})
        return cast(list[dict[str, Any]], data.get("results", []))

    async def delete_vxlan(self, vxlan_id: str) -> None:
        """Delete a VXLAN."""
        await self.delete(f"{OVERLAYS_PLUGIN_BASE}/vxlans/{vxlan_id}/")

    async def merge_config_context(self, device_id: str, data: Any) -> None:
        """Merge config context data with existing data."""
        device_data = await self.get(f"dcim/devices/{device_id}/", params={"depth": 1})
        config_context = device_data.get("local_config_context_data") or {}
        config_context.update(data)
        await self.patch(
            f"dcim/devices/{device_id}/",
            data={"local_config_context_data": config_context},
        )
