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
"""Nautobot Activities."""

from __future__ import annotations

import logging
import re
from typing import Any, ClassVar

import netaddr
from pydantic import BaseModel, computed_field
from temporalio import activity
from temporalio.exceptions import ApplicationError

from nv_config_manager.common.log import LogCategory, get_logger
from nv_config_manager.temporal.client.nautobot import DeviceVrfInfo, NautobotClient
from nv_config_manager.temporal.common.mixins.device import (
    HostDeviceData,
    InterfaceData,
    NetworkDeviceData,
    Platform,
)

logger = get_logger(__name__, category=LogCategory.NAUTOBOT)
logger.setLevel(logging.INFO)


class GetNetworkDeviceInput(BaseModel):
    """Get network device input."""

    device_id: str


class GetNetworkDeviceOutput(BaseModel):
    """Get network device output."""

    device: NetworkDeviceData


@activity.defn
async def get_network_device(
    activity_input: GetNetworkDeviceInput,
) -> GetNetworkDeviceOutput:
    """Get network device data."""
    client = NautobotClient()
    async with client:
        device = await client.get_network_device(activity_input.device_id)
    return GetNetworkDeviceOutput(device=device)


class GetHostDeviceInput(BaseModel):
    """Get host device input."""

    device_id: str


class GetHostDeviceOutput(BaseModel):
    """Get host device output."""

    device: HostDeviceData


@activity.defn
async def get_host_device(
    activity_input: GetHostDeviceInput,
) -> GetHostDeviceOutput:
    """Get host device data."""
    client = NautobotClient()
    async with client:
        device = await client.get_host_device(activity_input.device_id)
    return GetHostDeviceOutput(device=device)


class GetNetworkDevicesInput(BaseModel):
    """Get network devices input."""

    site: str | None = None
    roles: list[str] | None = None
    status: list[str] | None = None
    tenant: str | None = None
    device_type_ids: list[str] | None = None
    mac_addresses: list[str] | None = None
    device_ids: list[str] | None = None
    render_enabled: bool | None = None
    deploy_enabled: bool | None = None
    backup_enabled: bool | None = None
    ztp_enabled: bool | None = None
    platforms: list[Platform] | None = None


class GetNetworkDevicesOutput(BaseModel):
    """Get network devices output."""

    devices: list[NetworkDeviceData]


@activity.defn
async def get_network_devices(
    activity_input: GetNetworkDevicesInput,
) -> GetNetworkDevicesOutput:
    """Get network devices for a specific site."""
    client = NautobotClient()
    async with client:
        devices = await client.get_network_devices(
            site=activity_input.site,
            role=activity_input.roles,
            status=activity_input.status,
            tenant=activity_input.tenant,
            device_type_id=activity_input.device_type_ids,
            mac_address=activity_input.mac_addresses,
            device_ids=activity_input.device_ids,
            render_enabled=activity_input.render_enabled,
            deploy_enabled=activity_input.deploy_enabled,
            backup_enabled=activity_input.backup_enabled,
            ztp_enabled=activity_input.ztp_enabled,
            platform=activity_input.platforms,
        )
    return GetNetworkDevicesOutput(devices=devices)


class GetHostDevicesInput(BaseModel):
    """Get host devices input."""

    site: str | None = None
    roles: list[str] | None = None
    status: list[str] | None = None
    tenant: str | None = None
    device_type_ids: list[str] | None = None
    mac_addresses: list[str] | None = None


class GetHostDevicesOutput(BaseModel):
    """Get host devices output."""

    devices: list[HostDeviceData]


@activity.defn
async def get_host_devices(
    activity_input: GetHostDevicesInput,
) -> GetHostDevicesOutput:
    """Get host devices."""
    client = NautobotClient()
    async with client:
        devices = await client.get_host_devices(
            site=activity_input.site,
            role=activity_input.roles,
            status=activity_input.status,
            tenant=activity_input.tenant,
            device_type_id=activity_input.device_type_ids,
            mac_address=activity_input.mac_addresses,
        )
    return GetHostDevicesOutput(devices=devices)


class HostInterface(BaseModel):
    """Host Interface Data."""

    name: str
    mac: str


class HostData(BaseModel):
    """Host Data."""

    interfaces: list[HostInterface]
    name: str
    tenant: str
    device_id: str
    url: str
    alias: str | None = None


@activity.defn
async def get_host_data_by_macs(mac_addresses: list[str]) -> list[HostData]:
    """Load host data from list of mac addresses."""
    query = """
query ($macs: [String]!) {
  devices(mac_address: $macs) {
    id
    name
    cf_alias
    tenant {
      name
    }
    interfaces {
      name
      mac_address
    }
  }
}
    """
    client = NautobotClient()
    async with client:
        data = await client.graphql_query(query, {"macs": mac_addresses})
        hosts = []
        for device in data["data"]["devices"]:
            interfaces = []
            for intf in device["interfaces"]:
                # Used for joining with device data,
                # interfaces with no mac set are not relevant
                if not intf["mac_address"]:
                    continue
                interfaces.append(
                    HostInterface(name=intf["name"], mac=str(netaddr.EUI(intf["mac_address"])))
                )
            hosts.append(
                HostData(
                    interfaces=interfaces,
                    name=device["name"],
                    tenant=device["tenant"]["name"],
                    device_id=device["id"],
                    alias=device["cf_alias"],
                    url=client.get_device_ui_url(device["id"]),
                )
            )
    return hosts


@activity.defn
async def get_host_data_by_names(device_names: list[str]) -> list[HostData]:
    """Load host data from list of device names."""
    query = """
query ($names: [String]!) {
  devices(name: $names) {
    id
    name
    cf_alias
    tenant {
      name
    }
  }
}
    """
    client = NautobotClient()
    async with client:
        data = await client.graphql_query(query, {"names": device_names})
        hosts = []
        for device in data["data"]["devices"]:
            hosts.append(
                HostData(
                    interfaces=[],  # Empty list since we don't need interface data for LLDP neighbors
                    name=device["name"],
                    tenant=device["tenant"]["name"],
                    device_id=device["id"],
                    alias=device["cf_alias"],
                    url=client.get_device_ui_url(device["id"]),
                )
            )
    return hosts


class GetAvailableRouteDistinguishersInput(BaseModel):
    """Get Available Route Distinguishers Activity Input."""

    site: str
    namespace_tag: str
    rd_min: int
    rd_max: int


class GetAvailableRouteDistinguishersOutput(BaseModel):
    """Get Available Route Distinguishers Activity Output."""

    route_distinguisher: str
    namespaces: list[str]


@activity.defn
async def get_available_route_distinguishers(
    activity_input: GetAvailableRouteDistinguishersInput,
) -> GetAvailableRouteDistinguishersOutput:
    """Get Available Route Distinguishers Activity."""
    namespace_query = """
        query ($tag: String, $location: String) {
            namespaces(location: $location, tags: [$tag]) {
                name
                vrfs {
                    rd
                }
            }
        }
    """
    client = NautobotClient()
    async with client:
        results = await client.graphql_query(
            namespace_query,
            {
                "tag": activity_input.namespace_tag,
                "location": activity_input.site,
            },
        )
        namespaces = [namespace["name"] for namespace in results["data"]["namespaces"]]
        if not namespaces:
            raise ApplicationError(
                f"No namespaces for site {activity_input.site} and "
                f"tag {activity_input.namespace_tag}."
            )
        logger.info("Found namespaces: %s", namespaces)

        route_distinguishers = {
            vrf["rd"]
            for namespace in results["data"]["namespaces"]
            for vrf in namespace["vrfs"]
            if vrf.get("rd")
        }
        logger.info("Found RDs: %s", route_distinguishers)

        assigned_numbers = sorted(
            [int(rd.split(":")[1]) for rd in route_distinguishers if re.match(r"\*:\d+", rd)]
        )

        if not assigned_numbers or assigned_numbers[-1] < activity_input.rd_min:
            route_distinguisher = f"*:{activity_input.rd_min}"
        elif assigned_numbers[-1] >= activity_input.rd_max:
            # TODO: Reclaim any gaps in the range
            raise ApplicationError(f"Namespaces {namespaces} out of space for new RDs")
        else:
            route_distinguisher = f"*:{assigned_numbers[-1] + 1}"
    return GetAvailableRouteDistinguishersOutput(
        route_distinguisher=route_distinguisher,
        namespaces=namespaces,
    )


class Vrf(BaseModel):
    """VRF Data."""

    QUERY_BY_VPC_ID: ClassVar[str] = """
query ($vpc_id: String!, $location: String!, $namespace_tag: [String]!) {
  namespaces(location: $location, tags: $namespace_tag) {
    vrfs(cf_forge_vpc_id: $vpc_id) {
      id
      name
      rd
      cf_forge_vpc_id
      namespace {
        name
        location {
          name
        }
      }
      interfaces {
        name
        device {
          name
        }
      }
    }
  }
}
"""
    name: str
    namespace: str
    site: str
    id: str
    rd: str
    vpc_id: str | None
    interfaces: list[str]

    @computed_field  # type: ignore[prop-decorator]
    @property
    def interface_count(self) -> int:
        """Count of interfaces tied to this VRF."""
        return len(self.interfaces)

    @staticmethod
    def from_nautobot_graphql(data: dict[str, Any]) -> Vrf:
        return Vrf(
            name=data["name"],
            namespace=data["namespace"]["name"],
            site=data["namespace"]["location"]["name"],
            id=data["id"],
            rd=data["rd"],
            vpc_id=data["cf_forge_vpc_id"],
            interfaces=[
                ":".join((intf["device"]["name"], intf["name"])) for intf in data["interfaces"]
            ],
        )


class ProvisionVrfInput(BaseModel):
    """Provision VRF Activity Input."""

    namespaces: list[str]
    route_distinguisher: str
    vpc_id: str


@activity.defn
async def provision_vrf(
    activity_input: ProvisionVrfInput,
) -> None:
    """Provision VRF Activity."""
    client = NautobotClient()
    vrfs_created = []
    vni = int(activity_input.route_distinguisher.split(":")[1])
    async with client:
        try:
            for namespace in activity_input.namespaces:
                vrfs_created.append(
                    await client.create_vrf(
                        data={
                            "name": f"SpXTenant{vni}",
                            "rd": activity_input.route_distinguisher,
                            "namespace": namespace,
                            "custom_fields": {"forge_vpc_id": activity_input.vpc_id},
                        }
                    )
                )
        except Exception as error:
            logger.exception("Failed to create VRFs", exc_info=error)
            for vrf in vrfs_created:
                await client.delete_vrf(vrf["id"])
            raise ApplicationError("Failed to create VRFs") from error


class QueryVRFByVPCInput(BaseModel):
    """Query VRF Activity Input."""

    vpc_id: str
    site: str
    namespace_tag: str


@activity.defn
async def get_vrfs_by_vpc_id(activity_input: QueryVRFByVPCInput) -> list[Vrf] | None:
    """Get VRF by VPC ID."""
    client = NautobotClient()
    async with client:
        rsp = await client.graphql_query(
            Vrf.QUERY_BY_VPC_ID,
            {
                "vpc_id": activity_input.vpc_id,
                "location": activity_input.site,
                "namespace_tag": [activity_input.namespace_tag],
            },
        )
        vrfs = []
        for namespace in rsp["data"]["namespaces"]:
            for vrf in namespace["vrfs"]:
                vrfs.append(Vrf.from_nautobot_graphql(vrf))
    return vrfs


class VrfDeletionActivityInput(BaseModel):
    """VRF Deletion Activity Input."""

    vrf_id: str


@activity.defn
async def delete_vrf(activity_input: VrfDeletionActivityInput) -> None:
    """Delete VRF."""
    client = NautobotClient()
    async with client:
        await client.delete_vrf(activity_input.vrf_id)


class SwitchPortByMacActivityInput(BaseModel):
    """Switch Port by MAC Address Input."""

    remote_mac_address: str


class SwitchPortByMacActivityOutput(BaseModel):
    """Switch Port Output."""

    device: NetworkDeviceData
    interface: str


@activity.defn
async def get_switch_port_by_remote_mac_address(
    activity_input: SwitchPortByMacActivityInput,
) -> SwitchPortByMacActivityOutput:
    """Get Switch Port by Remote MAC Address."""
    query = """
        query ($mac: [String!]) {
            interfaces(mac_address: $mac) {
                connected_interface {
                    name
                    device {
                        id
                    }
                }
            }
        }
    """
    client = NautobotClient()
    async with client:
        data = await client.graphql_query(query, {"mac": [activity_input.remote_mac_address]})
        if not data["data"]["interfaces"]:
            raise ApplicationError(
                f"No interfaces found for MAC {activity_input.remote_mac_address}"
            )
        interface = data["data"]["interfaces"][0]
        try:
            device = await client.get_network_device(
                interface["connected_interface"]["device"]["id"]
            )
            return SwitchPortByMacActivityOutput(
                device=device,
                interface=interface["connected_interface"]["name"],
            )
        except KeyError as error:
            raise ApplicationError(
                f"No connected interface found for MAC {activity_input.remote_mac_address}"
            ) from error


class CheckRecordedConfigDriftInput(BaseModel):
    """Check Recorded Config Drift Input."""

    device_id: str


@activity.defn
async def check_recorded_config_drift(
    activity_input: CheckRecordedConfigDriftInput,
) -> bool:
    """Check Recorded Config Drift."""
    client = NautobotClient()
    query = """
query ($id: ID!) {
  config_manager_device(id: $id) {
    intended_config {
      commit_id
    }
    backup_config{
      deployed_commit_id
    }
  }
}
"""
    async with client:
        data = await client.graphql_query(query, {"id": activity_input.device_id})
        intended_commit_id = (
            data["data"]["config_manager_device"]["intended_config"]["commit_id"]
            if data["data"]["config_manager_device"]["intended_config"]
            else None
        )
        deployed_commit_id = (
            data["data"]["config_manager_device"]["backup_config"]["deployed_commit_id"]
            if data["data"]["config_manager_device"]["backup_config"]
            else None
        )
    return intended_commit_id != deployed_commit_id


class GetDeviceVrfsInput(BaseModel):
    """Get Device VRFs Input."""

    device_id: str


class GetDeviceVrfsOutput(BaseModel):
    """Get Device VRFs Output."""

    vrfs: list[DeviceVrfInfo]


@activity.defn(name="get_device_vrfs")
async def get_device_vrfs(
    activity_input: GetDeviceVrfsInput,
) -> GetDeviceVrfsOutput:
    """Get VRFs assigned to a device."""
    client = NautobotClient()
    async with client:
        vrfs = await client.get_device_vrfs(activity_input.device_id)
    return GetDeviceVrfsOutput(vrfs=vrfs)


class AssignVrfToDeviceInput(BaseModel):
    """Assign VRF to Device Input."""

    device_id: str
    vrf_id: str


@activity.defn
async def assign_vrf_to_device(
    activity_input: AssignVrfToDeviceInput,
) -> None:
    """Assign a VRF to a device."""
    client = NautobotClient()
    async with client:
        await client.assign_vrf_to_device(activity_input.device_id, activity_input.vrf_id)


class GetDeviceInterfacesInput(BaseModel):
    """Get Device Interfaces Input."""

    device_id: str
    interface_names: list[str] | None = None


class GetDeviceInterfacesOutput(BaseModel):
    """Get Device Interfaces Output."""

    interfaces: list[InterfaceData]


@activity.defn
async def get_device_interfaces(
    activity_input: GetDeviceInterfacesInput,
) -> GetDeviceInterfacesOutput:
    """Get interfaces for a device by name."""
    client = NautobotClient()
    async with client:
        interfaces = await client.get_device_interfaces(device_id=activity_input.device_id)

    if activity_input.interface_names:
        filtered = [intf for intf in interfaces if intf.name in activity_input.interface_names]

        found_names = {intf.name for intf in filtered}
        missing = set[str](activity_input.interface_names) - found_names
        if missing:
            raise ApplicationError(
                f"Interfaces not found on device {activity_input.device_id}: "
                f"{', '.join(sorted(missing))}"
            )

        interfaces = filtered

    return GetDeviceInterfacesOutput(interfaces=interfaces)


class AssignVrfToInterfaceInput(BaseModel):
    """Assign VRF to Interface Input."""

    interface_id: str
    vrf_id: str


@activity.defn
async def assign_vrf_to_interface(
    activity_input: AssignVrfToInterfaceInput,
) -> None:
    """Assign a VRF to an interface."""
    client = NautobotClient()
    async with client:
        await client.update_interface(
            activity_input.interface_id, data={"vrf": activity_input.vrf_id}
        )
