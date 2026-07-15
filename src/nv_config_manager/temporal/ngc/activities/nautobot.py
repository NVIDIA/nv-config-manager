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
from typing import Any, ClassVar, cast

import netaddr
from pydantic import BaseModel, computed_field
from temporalio import activity
from temporalio.exceptions import ApplicationError

from nv_config_manager.common.log import LogCategory, get_logger
from nv_config_manager.temporal.client.nautobot import (
    OVERLAYS_PLUGIN_BASE,
    DeviceVrfInfo,
    NautobotClient,
)
from nv_config_manager.temporal.common.mixins.device import (
    HostDeviceData,
    InterfaceData,
    NetworkDeviceData,
    Platform,
)

logger = get_logger(__name__, category=LogCategory.NAUTOBOT)
logger.setLevel(logging.INFO)

SPECTRUMX_ISOLATION_TYPE = "spectrum_x_vrf"
VXLAN_L3_VNI_TYPE = "l3"
DEFAULT_STATUS_NAME = "Active"
OVERLAY_ASSIGNMENTS_PATH = f"{OVERLAYS_PLUGIN_BASE}/overlay-assignments/"
VRF_DEVICE_ASSIGNMENTS_PATH = "ipam/vrf-device-assignments/"


def _vni_from_rd(route_distinguisher: str) -> int:
    """Derive the VNI from a route distinguisher of the form ``*:<vni>``."""
    parts = route_distinguisher.split(":")
    if len(parts) != 2 or not parts[1].isdigit():
        raise ValueError(f"Invalid route distinguisher {route_distinguisher!r}, expected '*:<vni>'")
    return int(parts[1])


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
    managed_only: bool | None = None
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
            managed_only=activity_input.managed_only,
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
                id
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
        namespaces = [namespace["id"] for namespace in results["data"]["namespaces"]]
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

        assigned_numbers = {
            int(rd.split(":")[1]) for rd in route_distinguishers if re.match(r"\*:\d+", rd)
        }

        available_numbers = (
            set(range(activity_input.rd_min, activity_input.rd_max + 1)) - assigned_numbers
        )
        if not available_numbers:
            raise ApplicationError(f"Namespaces {namespaces} out of space for new RDs")
        route_distinguisher = f"*:{min(available_numbers)}"
    return GetAvailableRouteDistinguishersOutput(
        route_distinguisher=route_distinguisher,
        namespaces=namespaces,
    )


class Vrf(BaseModel):
    """VRF Data."""

    QUERY_BY_IDS: ClassVar[str] = """
query ($ids: [String]!) {
  vrfs(id: $ids) {
    id
    name
    rd
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
"""
    name: str
    namespace: str
    site: str
    id: str
    rd: str
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
            interfaces=[
                ":".join((intf["device"]["name"], intf["name"])) for intf in data["interfaces"]
            ],
        )


class ProvisionVrfInput(BaseModel):
    """Provision VRF Activity Input."""

    namespaces: list[str]
    route_distinguisher: str
    overlay_id: str
    site: str
    tenant: str


@activity.defn
async def provision_vrf(
    activity_input: ProvisionVrfInput,
) -> None:
    """Provision the SpectrumX overlay, VRFs, and L3 VXLANs for a VPC.

    Finds or creates the (location-scoped) SpectrumX overlay, then creates one VRF
    and one L3 VXLAN per namespace, binding each VRF and VXLAN to the overlay.
    Resources created in this call are rolled back on failure; the overlay is left
    in place since it is found-or-created and may be shared.
    """
    client = NautobotClient()
    vni = _vni_from_rd(activity_input.route_distinguisher)
    vrf_name = f"SpXTenant{vni}"
    overlay_name = activity_input.overlay_id
    vrfs_created: list[Any] = []
    vxlans_created: list[Any] = []
    assignments_created: list[Any] = []
    async with client:
        status_id = await client.lookup_id_by_name("extras/statuses/", DEFAULT_STATUS_NAME)
        if not status_id:
            raise ApplicationError(f"Status '{DEFAULT_STATUS_NAME}' not found in Nautobot")
        location_id = activity_input.site
        tenant_id = await client.lookup_id_by_name("tenancy/tenants/", activity_input.tenant)
        if not tenant_id:
            raise ApplicationError(f"Tenant '{activity_input.tenant}' not found in Nautobot")

        overlay = await client.find_overlay(overlay_name, location_id)
        if overlay:
            existing_tenant = (overlay.get("tenant") or {}).get("id")
            if existing_tenant != tenant_id:
                raise ApplicationError(
                    f"Overlay '{overlay_name}' exists but belongs to tenant "
                    f"{existing_tenant!r}, expected {tenant_id!r}"
                )
            overlay_id = overlay["id"]
            logger.info("Reusing existing overlay %s (%s)", overlay_name, overlay_id)
        else:
            overlay = await client.create_overlay(
                data={
                    "name": overlay_name,
                    "location": location_id,
                    "tenant": tenant_id,
                    "isolation_type": SPECTRUMX_ISOLATION_TYPE,
                    "status": status_id,
                }
            )
            overlay_id = overlay["id"]
            logger.info("Created overlay %s (%s)", overlay_name, overlay_id)

        try:
            for namespace in activity_input.namespaces:
                vrf = await client.create_vrf(
                    data={
                        "name": vrf_name,
                        "rd": activity_input.route_distinguisher,
                        "namespace": namespace,
                        "tenant": tenant_id,
                    }
                )
                vrfs_created.append(vrf)
                assignment = await _create_overlay_assignment(
                    client,
                    target_overlay_id=str(overlay_id),
                    assigned_object_type="ipam.vrf",
                    assigned_object_id=str(vrf["id"]),
                    status_id=status_id,
                )
                assignments_created.append(assignment)
                vxlan = await client.create_vxlan(
                    data={
                        "vnid": vni,
                        "name": vrf_name,
                        "vni_type": VXLAN_L3_VNI_TYPE,
                        "namespace": namespace,
                        "vrf": vrf["id"],
                        "overlay": overlay_id,
                        "status": status_id,
                    }
                )
                vxlans_created.append(vxlan)
        except Exception as error:
            logger.exception("Failed to provision VPC", exc_info=error)
            for vxlan in vxlans_created:
                try:
                    await client.delete_vxlan(vxlan["id"])
                except Exception:
                    logger.exception("Failed to delete vxlan %s during rollback", vxlan["id"])
            for assignment in assignments_created:
                try:
                    await client.delete(f"{OVERLAY_ASSIGNMENTS_PATH}{assignment['id']}/")
                except Exception:
                    logger.exception(
                        "Failed to delete overlay assignment %s during rollback",
                        assignment["id"],
                    )
            for vrf in vrfs_created:
                try:
                    await client.delete_vrf(vrf["id"])
                except Exception:
                    logger.exception("Failed to delete vrf %s during rollback", vrf["id"])
            raise ApplicationError("Failed to provision VPC") from error


class QueryVRFByVPCInput(BaseModel):
    """Query VRF Activity Input."""

    overlay_id: str
    site: str
    namespace_tag: str
    namespace: str | None = None


@activity.defn
async def get_vrfs_by_overlay_id(activity_input: QueryVRFByVPCInput) -> list[Vrf] | None:
    """Get VRFs for an overlay by looking up overlay → vxlans → VRF IDs → GraphQL."""
    client = NautobotClient()
    async with client:
        overlay = await client.find_overlay(activity_input.overlay_id, activity_input.site)
        if not overlay:
            return None
        vxlans = await client.get_vxlans_by_overlay(overlay["id"], depth=1)
        if activity_input.namespace:
            vxlans = [
                v for v in vxlans if v.get("namespace", {}).get("name") == activity_input.namespace
            ]
        vrf_ids = [v["vrf"]["id"] for v in vxlans if v.get("vrf")]
        if not vrf_ids:
            return None
        rsp = await client.graphql_query(Vrf.QUERY_BY_IDS, {"ids": vrf_ids})
        vrfs = [Vrf.from_nautobot_graphql(v) for v in rsp["data"]["vrfs"]]
    return vrfs if vrfs else None


class VrfDeletionActivityInput(BaseModel):
    """VRF Deletion Activity Input."""

    vrf_id: str
    vnid: int


@activity.defn
async def delete_vrf(activity_input: VrfDeletionActivityInput) -> None:
    """Delete a VRF, its overlay assignments, and the L3 VXLAN bound to it.

    VXLANs are fetched by VNI then filtered to those whose vrf.id matches
    vrf_id (the VRF FK is SET_NULL on VRF deletion, so they are removed
    explicitly to keep the overlay clean).
    """
    client = NautobotClient()
    async with client:
        vxlans = await client.get_vxlans_by_vnid(activity_input.vnid)
        for vxlan in vxlans:
            if (vxlan.get("vrf") or {}).get("id") == activity_input.vrf_id:
                await client.delete_vxlan(vxlan["id"])
        assignments = await _get_overlay_assignments(client, activity_input.vrf_id)
        await _delete_overlay_assignments(
            client,
            [str(assignment["id"]) for assignment in assignments],
        )
        await client.delete_vrf(activity_input.vrf_id)


class DeleteOverlayInput(BaseModel):
    """Delete Overlay Activity Input."""

    overlay_id: str
    site: str


class DeleteOverlayOutput(BaseModel):
    """Delete Overlay Activity Output."""

    deleted: bool
    overlay_name: str


@activity.defn
async def delete_overlay(activity_input: DeleteOverlayInput) -> DeleteOverlayOutput:
    """Delete the SpectrumX overlay and its assignments if no VXLANs remain."""
    overlay_name = activity_input.overlay_id
    client = NautobotClient()
    async with client:
        overlay = await client.find_overlay(overlay_name, activity_input.site)
        if not overlay:
            return DeleteOverlayOutput(deleted=False, overlay_name=overlay_name)

        remaining_vxlans = await client.get_vxlans_by_overlay(overlay["id"])
        if remaining_vxlans:
            logger.info("Overlay %s still has VXLANs, leaving in place", overlay_name)
            return DeleteOverlayOutput(deleted=False, overlay_name=overlay_name)

        # OverlayAssignment.overlay uses on_delete=CASCADE, so deleting the
        # overlay also removes its device, interface, and VRF assignments.
        await client.delete_overlay(overlay["id"])
        return DeleteOverlayOutput(deleted=True, overlay_name=overlay_name)


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
    """Set the VRF assigned to an interface."""

    interface_id: str
    vrf_id: str | None


@activity.defn
async def assign_vrf_to_interface(
    activity_input: AssignVrfToInterfaceInput,
) -> None:
    """Set or clear the VRF assigned to an interface."""
    client = NautobotClient()
    async with client:
        await client.update_interface(
            activity_input.interface_id, data={"vrf": activity_input.vrf_id}
        )


class ReconcileSpXOverlayAssignmentsInput(BaseModel):
    """Spectrum-X overlay assignments to reconcile in Nautobot."""

    overlay_id: str | None
    site: str
    device_id: str
    interface_ids: list[str]
    device_interface_ids: list[str]


class ReconcileSpXOverlayAssignmentsOutput(BaseModel):
    """Result of reconciling Spectrum-X overlay assignments."""

    created: int
    removed: int


def _related_object_id(value: Any) -> str | None:
    """Extract a related object's ID from a Nautobot REST value."""
    if isinstance(value, dict):
        object_id = value.get("id")
        return str(object_id) if object_id else None
    return str(value) if value else None


async def _get_overlay_assignments(
    client: NautobotClient,
    assigned_object_id: str,
) -> list[dict[str, Any]]:
    """Fetch all overlay-plugin assignments for a Nautobot object."""
    return await client.get_all(
        OVERLAY_ASSIGNMENTS_PATH,
        params={"assigned_object_id": assigned_object_id, "depth": 1},
    )


def _has_overlay_assignment(assignments: list[dict[str, Any]], overlay_id: str) -> bool:
    """Return whether the object is already assigned to the target overlay."""
    return any(
        _related_object_id(assignment.get("overlay")) == overlay_id for assignment in assignments
    )


async def _get_assignment_overlay_isolation_type(
    client: NautobotClient,
    assignment: dict[str, Any],
) -> str | None:
    """Return the overlay isolation type for an overlay assignment."""
    assignment_overlay = assignment.get("overlay")
    if isinstance(assignment_overlay, dict) and assignment_overlay.get("isolation_type"):
        return str(assignment_overlay["isolation_type"])

    assignment_overlay_id = _related_object_id(assignment_overlay)
    if not assignment_overlay_id:
        return None

    overlay_details = await client.get_overlay(assignment_overlay_id)
    isolation_type = overlay_details.get("isolation_type")
    return str(isolation_type) if isolation_type else None


async def _stale_spectrumx_assignment_ids(
    client: NautobotClient,
    assignments: list[dict[str, Any]],
    target_overlay_id: str | None,
) -> list[str]:
    """Return stale Spectrum-X assignment IDs, preserving other overlay types."""
    stale_assignment_ids: list[str] = []
    for assignment in assignments:
        assignment_overlay_id = _related_object_id(assignment.get("overlay"))
        if assignment_overlay_id == target_overlay_id:
            continue

        isolation_type = await _get_assignment_overlay_isolation_type(client, assignment)
        if isolation_type == SPECTRUMX_ISOLATION_TYPE:
            stale_assignment_ids.append(str(assignment["id"]))

    return stale_assignment_ids


async def _lookup_overlay_assignment_status_id(client: NautobotClient) -> str:
    """Return the default status ID used for new overlay assignments."""
    status_id = await client.lookup_id_by_name("extras/statuses/", DEFAULT_STATUS_NAME)
    if status_id is None:
        raise ApplicationError(f"Status {DEFAULT_STATUS_NAME} not found for overlay assignment")
    return status_id


async def _create_overlay_assignment(
    client: NautobotClient,
    *,
    target_overlay_id: str,
    assigned_object_type: str,
    assigned_object_id: str,
    status_id: str,
) -> dict[str, Any]:
    """Create an overlay assignment for a Nautobot object."""
    return cast(
        dict[str, Any],
        await client.post(
            OVERLAY_ASSIGNMENTS_PATH,
            data={
                "overlay": target_overlay_id,
                "assigned_object_type": assigned_object_type,
                "assigned_object_id": assigned_object_id,
                "status": status_id,
            },
        ),
    )


async def _delete_overlay_assignments(
    client: NautobotClient,
    assignment_ids: list[str],
) -> int:
    """Delete the given overlay assignments and return the count removed."""
    for assignment_id in assignment_ids:
        await client.delete(f"{OVERLAY_ASSIGNMENTS_PATH}{assignment_id}/")
    return len(assignment_ids)


@activity.defn
async def reconcile_spx_overlay_assignments(
    activity_input: ReconcileSpXOverlayAssignmentsInput,
) -> ReconcileSpXOverlayAssignmentsOutput:
    """Make overlay-plugin assignments match Spectrum-X device and port intent.

    An interface can belong to only one Spectrum-X VRF, so stale Spectrum-X
    assignments are removed when a port moves between overlays. Omitting the
    target overlay removes the selected ports' Spectrum-X assignments. Device
    assignments are removed when no interface on the device uses their overlay.
    """
    client = NautobotClient()
    created = 0
    removed = 0
    status_id: str | None = None
    target_overlay_id: str | None = None

    async with client:
        if activity_input.overlay_id is not None:
            overlay = await client.find_overlay(activity_input.overlay_id, activity_input.site)
            if not overlay:
                raise ApplicationError(
                    f"Overlay {activity_input.overlay_id} not found in site {activity_input.site}"
                )
            if overlay.get("isolation_type") != SPECTRUMX_ISOLATION_TYPE:
                raise ApplicationError(
                    f"Overlay {activity_input.overlay_id} in site {activity_input.site} "
                    f"is not a {SPECTRUMX_ISOLATION_TYPE} overlay"
                )
            target_overlay_id = str(overlay["id"])

        device_assignments = await _get_overlay_assignments(client, activity_input.device_id)
        if target_overlay_id is not None and not _has_overlay_assignment(
            device_assignments, target_overlay_id
        ):
            status_id = await _lookup_overlay_assignment_status_id(client)
            await _create_overlay_assignment(
                client,
                target_overlay_id=target_overlay_id,
                assigned_object_type="dcim.device",
                assigned_object_id=activity_input.device_id,
                status_id=status_id,
            )
            created += 1

        assignments_by_interface: dict[str, list[dict[str, Any]]] = {}
        for interface_id in activity_input.interface_ids:
            interface_assignments = await _get_overlay_assignments(client, interface_id)
            assignments_by_interface[interface_id] = interface_assignments
            stale_assignment_ids = await _stale_spectrumx_assignment_ids(
                client,
                interface_assignments,
                target_overlay_id,
            )

            if target_overlay_id is not None and not _has_overlay_assignment(
                interface_assignments, target_overlay_id
            ):
                if status_id is None:
                    status_id = await _lookup_overlay_assignment_status_id(client)
                await _create_overlay_assignment(
                    client,
                    target_overlay_id=target_overlay_id,
                    assigned_object_type="dcim.interface",
                    assigned_object_id=interface_id,
                    status_id=status_id,
                )
                created += 1
                interface_assignments.append(
                    {"id": "created", "overlay": {"id": target_overlay_id}}
                )

            removed += await _delete_overlay_assignments(
                client,
                stale_assignment_ids,
            )
            assignments_by_interface[interface_id] = [
                assignment
                for assignment in interface_assignments
                if str(assignment["id"]) not in stale_assignment_ids
            ]

        # Always rebuild the complete active interface state. On an activity
        # retry, selected-interface deletions from an earlier attempt may
        # already be absent, but any now-unused device assignment must still be
        # discovered and removed.
        for interface_id in activity_input.device_interface_ids:
            if interface_id not in assignments_by_interface:
                assignments_by_interface[interface_id] = await _get_overlay_assignments(
                    client, interface_id
                )

        active_overlay_ids = {
            overlay_id
            for assignments in assignments_by_interface.values()
            for assignment in assignments
            if (overlay_id := _related_object_id(assignment.get("overlay"))) is not None
        }
        for assignment in device_assignments:
            overlay_id = _related_object_id(assignment.get("overlay"))
            if overlay_id is None or overlay_id in active_overlay_ids:
                continue
            isolation_type = await _get_assignment_overlay_isolation_type(client, assignment)
            if isolation_type != SPECTRUMX_ISOLATION_TYPE:
                continue
            removed += await _delete_overlay_assignments(client, [str(assignment["id"])])

    return ReconcileSpXOverlayAssignmentsOutput(created=created, removed=removed)


class RemoveUnmappedDeviceVrfsInput(BaseModel):
    """Device whose VRF associations should be reconciled with its interfaces."""

    device_id: str
    vrf_ids: list[str]


class RemoveUnmappedDeviceVrfsOutput(BaseModel):
    """VRF associations removed because no device interface used them."""

    removed_vrf_ids: list[str]


@activity.defn
async def remove_unmapped_device_vrfs(
    activity_input: RemoveUnmappedDeviceVrfsInput,
) -> RemoveUnmappedDeviceVrfsOutput:
    """Remove affected device/VRF associations that have no interface mappings."""
    if not activity_input.vrf_ids:
        return RemoveUnmappedDeviceVrfsOutput(removed_vrf_ids=[])

    client = NautobotClient()
    removed_vrf_ids: list[str] = []

    async with client:
        interfaces = await client.get_device_interfaces(activity_input.device_id)
        mapped_vrf_ids = {interface.vrf_id for interface in interfaces if interface.vrf_id}

        for vrf_id in dict.fromkeys(activity_input.vrf_ids):
            if vrf_id in mapped_vrf_ids:
                continue

            assignments = await client.get_all(
                VRF_DEVICE_ASSIGNMENTS_PATH,
                params={"device": activity_input.device_id, "vrf": vrf_id},
            )
            matching_assignment_ids = [
                str(assignment["id"])
                for assignment in assignments
                if _related_object_id(assignment.get("device")) == activity_input.device_id
                and _related_object_id(assignment.get("vrf")) == vrf_id
            ]
            for assignment_id in matching_assignment_ids:
                await client.delete(f"{VRF_DEVICE_ASSIGNMENTS_PATH}{assignment_id}/")

            # The output represents the requested VRFs now reconciled as
            # unmapped, including associations deleted by an earlier partial
            # attempt. This keeps the activity result stable across retries.
            removed_vrf_ids.append(vrf_id)

    return RemoveUnmappedDeviceVrfsOutput(removed_vrf_ids=removed_vrf_ids)
