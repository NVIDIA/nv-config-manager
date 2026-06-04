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
"""SpX Overlay Workflows."""

import asyncio
from datetime import timedelta

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

from nv_config_manager.temporal.common.decorators.workflow import run_nv_config_manager_workflow
from nv_config_manager.temporal.common.mixins.metadata import WorkflowMetadataMixin
from nv_config_manager.temporal.common.mixins.stage import (
    StageInput,
    StageMixin,
    StageOutput,
    StateEnum,
    stage_executor,
)

with workflow.unsafe.imports_passed_through():
    from nv_config_manager.temporal.client.nautobot import DeviceVrfInfo
    from nv_config_manager.temporal.common.mixins.archive import ArchiveMixin
    from nv_config_manager.temporal.common.mixins.device import DeviceMixin, NetworkDeviceData
    from nv_config_manager.temporal.ngc.activities.deploy import (
        WaitForTenantRenderInput,
        wait_for_tenant_render,
    )
    from nv_config_manager.temporal.ngc.activities.nautobot import (
        AssignVrfToDeviceInput,
        AssignVrfToInterfaceInput,
        DeleteOverlayInput,
        GetAvailableRouteDistinguishersInput,
        GetDeviceInterfacesInput,
        GetDeviceVrfsInput,
        GetNetworkDeviceInput,
        ProvisionVrfInput,
        QueryVRFByVPCInput,
        Vrf,
        VrfDeletionActivityInput,
        _vni_from_rd,
        assign_vrf_to_device,
        assign_vrf_to_interface,
        delete_overlay,
        delete_vrf,
        get_available_route_distinguishers,
        get_device_interfaces,
        get_device_vrfs,
        get_network_device,
        get_vrfs_by_vpc_id,
        provision_vrf,
    )
    from nv_config_manager.temporal.ngc.activities.render import (
        ExecuteRenderInput,
        execute_render,
    )
    from nv_config_manager.temporal.ngc.workflows.deploy import (
        TenantDeployInput,
        TenantDeployWorkflow,
    )


RD_MIN = 60000


RD_MAX = 65000


NAMESPACE_TAG = "spectrumx"


DEFAULT_ACTIVITY_RETRY_POLICY = RetryPolicy(
    maximum_attempts=3,
)


class SpXOverlayCreationInput(BaseModel):
    """SpX Overlay Creation Workflow Input Definition."""

    site: str
    vpc_id: str
    tenant: str
    namespace_tag: str = NAMESPACE_TAG
    rd_min: int = RD_MIN
    rd_max: int = RD_MAX


class SpXOverlayCreationWorkflowOutput(BaseModel):
    """SpX Overlay Creation Workflow Output Definition."""

    created_vrfs: list[Vrf]
    existing_vrfs: list[Vrf]


@workflow.defn
class SpXOverlayCreationWorkflow(WorkflowMetadataMixin, StageMixin, ArchiveMixin):
    """SpX Overlay creation workflow for network virtualization."""

    # Workflow metadata
    workflow_name = "SpX Overlay Creation"
    workflow_description = (
        "Create a SpX Overlay with route distinguisher assignment and VRF/VXLAN provisioning"
    )
    workflow_input_class = SpXOverlayCreationInput
    workflow_api_endpoint = "/ngc/spx_overlay_creation"
    workflow_namespace = "ngc"

    def __init__(self) -> None:
        """Initialize workflow."""
        StageMixin.__init__(self)
        self.define_stage(
            name="create_spx_overlay",
            description="Assign an RD and create VRF.",
            requires_approval=False,
            depends_on=[],
        )

    class CreateSpXOverlayStageInput(StageInput):
        """Create VPC Stage Input."""

        namespace_tag: str
        vpc_id: str
        site: str
        tenant: str
        rd_min: int
        rd_max: int

    class CreateSpXOverlayStageOutput(StageOutput):
        """Create VPC Stage Output."""

        created_vrfs: list[Vrf]
        existing_vrfs: list[Vrf]

    @stage_executor("create_spx_overlay")
    async def create_spx_overlay(
        self, stage_input: CreateSpXOverlayStageInput
    ) -> CreateSpXOverlayStageOutput:
        """Create VPC Stage."""
        # Ensure no existing VRFs with this VPC ID
        existing_vrfs = await workflow.execute_activity(
            get_vrfs_by_vpc_id,
            QueryVRFByVPCInput(
                vpc_id=stage_input.vpc_id,
                namespace_tag=stage_input.namespace_tag,
                site=stage_input.site,
            ),
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )
        if existing_vrfs:
            return self.CreateSpXOverlayStageOutput(
                created_vrfs=[],
                existing_vrfs=existing_vrfs,
                display=(
                    f"VRFs already exists for VPC ID {stage_input.vpc_id}:\n "
                    f"{self.markdown_table(existing_vrfs, exclude={'interfaces'})}"
                ),
            )
        rd_results = await workflow.execute_activity(
            get_available_route_distinguishers,
            GetAvailableRouteDistinguishersInput(
                site=stage_input.site,
                namespace_tag=stage_input.namespace_tag,
                rd_min=stage_input.rd_min,
                rd_max=stage_input.rd_max,
            ),
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )
        await workflow.execute_activity(
            provision_vrf,
            ProvisionVrfInput(
                namespaces=rd_results.namespaces,
                route_distinguisher=rd_results.route_distinguisher,
                vpc_id=stage_input.vpc_id,
                site=stage_input.site,
                tenant=stage_input.tenant,
            ),
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )
        created_vrfs = await workflow.execute_activity(
            get_vrfs_by_vpc_id,
            QueryVRFByVPCInput(
                vpc_id=stage_input.vpc_id,
                namespace_tag=stage_input.namespace_tag,
                site=stage_input.site,
            ),
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )
        if created_vrfs:
            return self.CreateSpXOverlayStageOutput(
                created_vrfs=created_vrfs,
                existing_vrfs=[],
                display=(
                    f"Created VRFs:\n{self.markdown_table(created_vrfs, exclude={'interfaces'})}"
                ),
            )
        raise ApplicationError("Failed to create VRFs")

    @run_nv_config_manager_workflow
    async def run(  # type: ignore[override, ty:invalid-method-override]  # pyright: ignore
        self, workflow_input: SpXOverlayCreationInput
    ) -> SpXOverlayCreationWorkflowOutput:
        """Execute the VPC Creation workflow."""
        self.set_input(workflow_input)
        vrf_output = await self.create_spx_overlay(
            self.CreateSpXOverlayStageInput(
                namespace_tag=workflow_input.namespace_tag,
                vpc_id=workflow_input.vpc_id,
                site=workflow_input.site,
                tenant=workflow_input.tenant,
                rd_min=workflow_input.rd_min,
                rd_max=workflow_input.rd_max,
            )
        )

        await self.archive_results()
        return SpXOverlayCreationWorkflowOutput(
            created_vrfs=vrf_output.created_vrfs, existing_vrfs=vrf_output.existing_vrfs
        )


class SpXOverlayDeletionInput(BaseModel):
    """SpX Overlay Deletion Workflow Input Definition."""

    site: str
    vpc_id: str
    namespace_tag: str = NAMESPACE_TAG


class SpXOverlayDeletionWorkflowOutput(BaseModel):
    """SpX Overlay Deletion Workflow Output Definition."""

    deleted_vrfs: list[Vrf]
    in_use_vrfs: list[Vrf]


@workflow.defn
class SpXOverlayDeletionWorkflow(WorkflowMetadataMixin, StageMixin, ArchiveMixin):
    """SpX Overlay deletion workflow for network virtualization cleanup."""

    # Workflow metadata
    workflow_name = "SpX Overlay Deletion"
    workflow_description = (
        "Delete a SpX Overlay and its associated VRFs/VXLANs with validation checks"
    )
    workflow_input_class = SpXOverlayDeletionInput
    workflow_api_endpoint = "/ngc/spx_overlay_deletion"
    workflow_namespace = "ngc"

    def __init__(self) -> None:
        """Initialize workflow."""
        StageMixin.__init__(self)
        self.define_stage(
            name="delete_spx_overlay",
            description="Validate and delete Nautobot VRFs tied to the VPC.",
            requires_approval=False,
            depends_on=[],
        )

    class DeleteSpXOverlayStageInput(StageInput):
        """Create VPC Stage Input."""

        vpc_id: str
        site: str
        namespace_tag: str = NAMESPACE_TAG

    class DeleteSpXOverlayStageOutput(StageOutput):
        """Create VPC Stage Output."""

        deleted_vrfs: list[Vrf]
        in_use_vrfs: list[Vrf]

    @stage_executor("delete_spx_overlay")
    async def delete_spx_overlay(
        self, stage_input: DeleteSpXOverlayStageInput
    ) -> DeleteSpXOverlayStageOutput:
        """Delete VPC Stage."""
        existing_vrfs = await workflow.execute_activity(
            get_vrfs_by_vpc_id,
            QueryVRFByVPCInput(
                vpc_id=stage_input.vpc_id,
                namespace_tag=stage_input.namespace_tag,
                site=stage_input.site,
            ),
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )
        if not existing_vrfs:
            return self.DeleteSpXOverlayStageOutput(
                deleted_vrfs=[],
                in_use_vrfs=[],
                display=f"No VRFs exist for VPC ID {stage_input.vpc_id}",
            )

        in_use_vrfs = [vrf for vrf in existing_vrfs if vrf.interface_count > 0]
        if in_use_vrfs:
            return self.DeleteSpXOverlayStageOutput(
                in_use_vrfs=in_use_vrfs,
                deleted_vrfs=[],
                display=(
                    f"Unable to delete VPC {stage_input.vpc_id}, "
                    f"the following VRFs are in use:\n "
                    f"{self.markdown_table(in_use_vrfs, exclude={'interfaces'})}"
                ),
            )

        # Delete VRFs and their bound VXLANs
        tasks = []
        for vrf in existing_vrfs:
            task = workflow.execute_activity(
                delete_vrf,
                VrfDeletionActivityInput(
                    vrf_id=vrf.id,
                    vnid=_vni_from_rd(vrf.rd),
                    namespace=vrf.namespace,
                ),
                start_to_close_timeout=timedelta(minutes=1),
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            )
            tasks.append(task)
        await asyncio.gather(*tasks)

        # Clean up the SpectrumX overlay if no VXLANs/assignments remain
        overlay_result = await workflow.execute_activity(
            delete_overlay,
            DeleteOverlayInput(
                vnid=_vni_from_rd(existing_vrfs[0].rd),
                site=stage_input.site,
            ),
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )

        overlay_message = (
            f"Deleted overlay {overlay_result.overlay_name}"
            if overlay_result.deleted
            else f"Left overlay {overlay_result.overlay_name} in place"
        )
        return self.DeleteSpXOverlayStageOutput(
            deleted_vrfs=existing_vrfs,
            in_use_vrfs=[],
            display=(
                f"VRFs deleted for VPC ID {stage_input.vpc_id}:\n "
                f"{self.markdown_table(existing_vrfs, exclude={'interfaces'})}\n"
                f"{overlay_message}"
            ),
        )

    @run_nv_config_manager_workflow
    async def run(  # type: ignore[override, ty:invalid-method-override]  # pyright: ignore
        self, workflow_input: SpXOverlayDeletionInput
    ) -> SpXOverlayDeletionWorkflowOutput:
        """Execute the VPC Deletion workflow."""
        self.set_input(workflow_input)
        vrf_output = await self.delete_spx_overlay(
            self.DeleteSpXOverlayStageInput(
                vpc_id=workflow_input.vpc_id,
                site=workflow_input.site,
                namespace_tag=workflow_input.namespace_tag,
            )
        )

        await self.archive_results()
        return SpXOverlayDeletionWorkflowOutput(
            deleted_vrfs=vrf_output.deleted_vrfs, in_use_vrfs=vrf_output.in_use_vrfs
        )


class SpXOverlayAssignmentInput(BaseModel):
    """SpX Overlay Assignment Workflow Input Definition."""

    vpc_id: str
    device: str | NetworkDeviceData
    port_names: list[str]
    site: str
    namespace_tag: str = NAMESPACE_TAG


class SpXOverlayAssignmentWorkflowOutput(BaseModel):
    """SpX Overlay Assignment Workflow Output Definition."""

    assigned_ports: list[str]
    vrf_assigned: bool
    vrf: DeviceVrfInfo


@workflow.defn
class SpXOverlayAssignmentWorkflow(WorkflowMetadataMixin, StageMixin, DeviceMixin, ArchiveMixin):
    """SpX Overlay assignment workflow for assigning VRFs to devices and ports."""

    # Workflow metadata
    workflow_name = "SpX Overlay Assignment"
    workflow_description = "Assign a SpX Overlay/VRF to a device and its specified ports"
    workflow_input_class = SpXOverlayAssignmentInput
    workflow_api_endpoint = "/ngc/spx_overlay_assignment"
    workflow_namespace = "ngc"

    def __init__(self) -> None:
        """Initialize workflow."""
        StageMixin.__init__(self)
        self.define_stage(
            name="get_device_and_vrf",
            description="Get device and VRF information from Nautobot.",
            requires_approval=False,
            depends_on=[],
        )
        self.define_stage(
            name="assign_vrf_to_device",
            description="Check if VRF is assigned to device, and assign if not.",
            requires_approval=False,
            depends_on=["get_device_and_vrf"],
        )
        self.define_stage(
            name="assign_vrf_to_ports",
            description="Assign VRF to specified ports on the device.",
            requires_approval=False,
            depends_on=["assign_vrf_to_device"],
        )

    class GetDeviceAndVrfStageInput(StageInput):
        """Get Device and VRF Stage Input."""

        vpc_id: str
        device: str | NetworkDeviceData
        site: str
        namespace_tag: str

    class GetDeviceAndVrfStageOutput(StageOutput):
        """Get Device and VRF Stage Output."""

        device: NetworkDeviceData
        vrf: Vrf

    @stage_executor("get_device_and_vrf")
    async def get_device_and_vrf(
        self, stage_input: GetDeviceAndVrfStageInput
    ) -> GetDeviceAndVrfStageOutput:
        """Get Device and VRF Stage."""
        if isinstance(stage_input.device, str):
            device_output = await workflow.execute_activity(
                get_network_device,
                GetNetworkDeviceInput(device_id=stage_input.device),
                start_to_close_timeout=timedelta(minutes=1),
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            )
            device = device_output.device
        else:
            device = stage_input.device

        vrfs = await workflow.execute_activity(
            get_vrfs_by_vpc_id,
            QueryVRFByVPCInput(
                vpc_id=stage_input.vpc_id,
                namespace_tag=stage_input.namespace_tag,
                site=stage_input.site,
            ),
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )

        if not vrfs:
            raise ApplicationError(
                f"No VRF found for VPC ID {stage_input.vpc_id} in site {stage_input.site}"
            )
        if len(vrfs) > 1:
            raise ApplicationError(
                f"Multiple VRFs found for VPC ID {stage_input.vpc_id} in site {stage_input.site}"
            )

        return self.GetDeviceAndVrfStageOutput(
            device=device,
            vrf=vrfs[0],
            display=f"Found device: {device.name} and VRF: {vrfs[0].name}",
        )

    class AssignVrfToDeviceStageInput(StageInput):
        """Assign VRF to Device Stage Input."""

        device_id: str
        vrf_id: str
        vrf_name: str

    class AssignVrfToDeviceStageOutput(StageOutput):
        """Assign VRF to Device Stage Output."""

        already_assigned: bool

    @stage_executor("assign_vrf_to_device")
    async def assign_vrf_to_device_stage(
        self, stage_input: AssignVrfToDeviceStageInput
    ) -> AssignVrfToDeviceStageOutput:
        """Assign VRF to Device Stage."""
        device_vrfs = await workflow.execute_activity(
            get_device_vrfs,
            GetDeviceVrfsInput(device_id=stage_input.device_id),
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )

        already_assigned = stage_input.vrf_id in {vrf.vrf_id for vrf in device_vrfs.vrfs}

        if not already_assigned:
            await workflow.execute_activity(
                assign_vrf_to_device,
                AssignVrfToDeviceInput(
                    device_id=stage_input.device_id,
                    vrf_id=stage_input.vrf_id,
                ),
                start_to_close_timeout=timedelta(minutes=1),
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            )
            display = f"VRF {stage_input.vrf_name} assigned to device"
        else:
            display = f"VRF {stage_input.vrf_name} already assigned to device"

        return self.AssignVrfToDeviceStageOutput(
            already_assigned=already_assigned,
            display=display,
        )

    class AssignVrfToPortsStageInput(StageInput):
        """Assign VRF to Ports Stage Input."""

        device_id: str
        vrf_id: str
        vrf_name: str
        port_names: list[str]

    class AssignVrfToPortsStageOutput(StageOutput):
        """Assign VRF to Ports Stage Output."""

        assigned_ports: list[str]
        already_assigned_ports: list[str]

    @stage_executor("assign_vrf_to_ports")
    async def assign_vrf_to_ports_stage(
        self, stage_input: AssignVrfToPortsStageInput
    ) -> AssignVrfToPortsStageOutput:
        """Assign VRF to Ports Stage."""
        interfaces_output = await workflow.execute_activity(
            get_device_interfaces,
            GetDeviceInterfacesInput(
                device_id=stage_input.device_id,
                interface_names=stage_input.port_names,
            ),
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )

        tasks = []
        assigned_ports = []
        already_assigned_ports = []
        for interface in interfaces_output.interfaces:
            if interface.vrf_id == stage_input.vrf_id:
                already_assigned_ports.append(interface.name)
                continue
            task = workflow.execute_activity(
                assign_vrf_to_interface,
                AssignVrfToInterfaceInput(
                    interface_id=interface.id,
                    vrf_id=stage_input.vrf_id,
                ),
                start_to_close_timeout=timedelta(minutes=1),
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            )
            tasks.append(task)
            assigned_ports.append(interface.name)

        await asyncio.gather(*tasks)

        return self.AssignVrfToPortsStageOutput(
            assigned_ports=assigned_ports,
            already_assigned_ports=already_assigned_ports,
            display=(
                f"VRF {stage_input.vrf_name} assigned "
                f"to ports: {', '.join(assigned_ports)}\n"
                f"Ports already assigned: {', '.join(already_assigned_ports)}"
            ),
        )

    @run_nv_config_manager_workflow
    async def run(  # type: ignore[override, ty:invalid-method-override]  # pyright: ignore
        self, workflow_input: SpXOverlayAssignmentInput
    ) -> SpXOverlayAssignmentWorkflowOutput:
        """Execute the VPC Assignment workflow."""
        self.set_input(workflow_input)

        device_vrf_output = await self.get_device_and_vrf(
            self.GetDeviceAndVrfStageInput(
                vpc_id=workflow_input.vpc_id,
                device=workflow_input.device,
                site=workflow_input.site,
                namespace_tag=workflow_input.namespace_tag,
            )
        )
        DeviceMixin.attach_device_search_attributes(device_vrf_output.device)

        device_output = await self.assign_vrf_to_device_stage(
            self.AssignVrfToDeviceStageInput(
                device_id=device_vrf_output.device.id,
                vrf_id=device_vrf_output.vrf.id,
                vrf_name=device_vrf_output.vrf.name,
            )
        )

        ports_output = await self.assign_vrf_to_ports_stage(
            self.AssignVrfToPortsStageInput(
                device_id=device_vrf_output.device.id,
                vrf_id=device_vrf_output.vrf.id,
                vrf_name=device_vrf_output.vrf.name,
                port_names=workflow_input.port_names,
            )
        )

        await self.archive_results()
        return SpXOverlayAssignmentWorkflowOutput(
            assigned_ports=ports_output.assigned_ports,
            vrf_assigned=not device_output.already_assigned,
            vrf=DeviceVrfInfo(
                vrf_id=device_vrf_output.vrf.id,
                vrf_name=device_vrf_output.vrf.name,
            ),
        )


class SpXOverlayTenantChangeInput(BaseModel):
    """SpX Overlay Tenant Change Workflow Input Definition."""

    vpc_id: str
    device_id: str
    port_names: list[str]
    site: str
    namespace_tag: str = NAMESPACE_TAG


class SpXOverlayTenantChangeWorkflowOutput(BaseModel):
    """SpX Overlay Tenant Change Workflow Output Definition."""

    assigned_ports: list[str]
    vrf_assigned: bool
    vrf: DeviceVrfInfo | None
    device_deployed: str | None


@workflow.defn
class SpXOverlayTenantChangeWorkflow(WorkflowMetadataMixin, StageMixin, DeviceMixin, ArchiveMixin):
    """SpX Overlay tenant change workflow for assigning overlays and deploying tenant config."""

    workflow_name = "SpX Overlay Tenant Change"
    workflow_description = "Assign a SpX Overlay to a device and deploy tenant configuration"
    workflow_input_class = SpXOverlayTenantChangeInput
    workflow_api_endpoint = "/ngc/spx_overlay_tenant_change"
    workflow_namespace = "ngc"

    def __init__(self) -> None:
        """Initialize workflow."""
        StageMixin.__init__(self)
        self.define_stage(
            name="get_device",
            description="Get device information from Nautobot",
            requires_approval=False,
            depends_on=[],
        )

        self.define_stage(
            name="assign_spx_overlay",
            description="Assign VPC to device and ports",
            requires_approval=False,
            depends_on=["get_device"],
        )

        self.define_stage(
            name="render_tenant_config",
            description="Render tenant configuration",
            requires_approval=False,
            depends_on=["assign_spx_overlay"],
        )

        self.define_stage(
            name="wait_for_render",
            description="Wait for tenant render to be updated",
            requires_approval=False,
            depends_on=["render_tenant_config"],
        )

        self.define_stage(
            name="deploy",
            description="Deploy tenant configuration to device",
            requires_approval=False,
            depends_on=["wait_for_render"],
        )

    class GetDeviceStageInput(StageInput):
        """Get Device Stage Input."""

        device_id: str

    class GetDeviceStageOutput(StageOutput):
        """Get Device Stage Output."""

        device: NetworkDeviceData

    @stage_executor("get_device")
    async def get_device_stage(self, stage_input: GetDeviceStageInput) -> GetDeviceStageOutput:
        """Get device information from Nautobot."""
        device_output = await workflow.execute_activity(
            get_network_device,
            GetNetworkDeviceInput(device_id=stage_input.device_id),
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )
        return self.GetDeviceStageOutput(
            device=device_output.device,
            display=f"Retrieved device: {device_output.device.name}",
        )

    class AssignSpXOverlayStageInput(StageInput):
        """Assign VPC Stage Input."""

        vpc_id: str
        device: NetworkDeviceData
        port_names: list[str]
        site: str
        namespace_tag: str

    class AssignSpXOverlayStageOutput(StageOutput):
        """Assign SpX Overlay Stage Output."""

        assigned_ports: list[str]
        vrf_assigned: bool
        vrf: DeviceVrfInfo
        overlay_name: str
        vxlan_name: str

    @stage_executor("assign_spx_overlay")
    async def assign_spx_overlay_stage(
        self, stage_input: AssignSpXOverlayStageInput
    ) -> AssignSpXOverlayStageOutput:
        """Assign SpX Overlay to device and ports."""
        result = await workflow.execute_child_workflow(
            SpXOverlayAssignmentWorkflow.run,
            SpXOverlayAssignmentInput(
                vpc_id=stage_input.vpc_id,
                device=stage_input.device,
                port_names=stage_input.port_names,
                site=stage_input.site,
                namespace_tag=stage_input.namespace_tag,
            ),
            run_timeout=timedelta(minutes=10),
        )

        self.append_child_workflow("assign_spx_overlay", workflow.info().workflow_id)

        # For SpX overlays the overlay, VRF, and L3 VXLAN all share the same
        # name (e.g. SpXTenant60004), so we can surface all three from the VRF result.
        overlay_name = result.vrf.vrf_name
        vxlan_name = result.vrf.vrf_name

        vrf_line = f"VRF: {result.vrf.vrf_name}" if result.vrf_assigned else "VRF already assigned"
        display = (
            f"Overlay: {overlay_name}\n"
            f"L3 VXLAN: {vxlan_name}\n"
            f"{vrf_line}\n"
            f"Ports assigned ({len(result.assigned_ports)}): {', '.join(result.assigned_ports)}"
        )
        return self.AssignSpXOverlayStageOutput(
            assigned_ports=result.assigned_ports,
            vrf_assigned=result.vrf_assigned,
            vrf=result.vrf,
            overlay_name=overlay_name,
            vxlan_name=vxlan_name,
            display=display,
        )

    class RenderStageInput(StageInput):
        """Render Stage Input."""

        device: NetworkDeviceData

    class RenderStageOutput(StageOutput):
        """Render Stage Output."""

        config_id: str | None = None

    @stage_executor("render_tenant_config")
    async def render_stage(self, stage_input: RenderStageInput) -> RenderStageOutput:
        """Render tenant configuration."""
        result = await workflow.execute_activity(
            execute_render,
            ExecuteRenderInput(
                device_id=stage_input.device.id,
                workflow_id=workflow.info().workflow_id,
            ),
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )

        # Get commit_id for tenant.yaml from the updated_files list
        tenant_config_file = stage_input.device.tenant_config_file
        config_id = result.get_commit(tenant_config_file)

        display_message = "Rendered tenant configuration"
        if config_id:
            display_message += f" (config ID: {config_id})"

        return self.RenderStageOutput(
            config_id=config_id,
            display=display_message,
        )

    class WaitForRenderStageInput(StageInput):
        """Wait For Render Stage Input."""

        device: NetworkDeviceData
        config_id: str | None

    class WaitForRenderStageOutput(StageOutput):
        """Wait For Render Stage Output."""

        config_id: str | None = None

    @stage_executor("wait_for_render")
    async def wait_for_render_stage(
        self, stage_input: WaitForRenderStageInput
    ) -> WaitForRenderStageOutput:
        """Wait for tenant render to be updated with expected changes."""
        result = await workflow.execute_activity(
            wait_for_tenant_render,
            WaitForTenantRenderInput(
                device=stage_input.device,
                config_id=stage_input.config_id,
            ),
            start_to_close_timeout=timedelta(minutes=15),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )

        display_message = "Tenant render available"
        if result.config_id:
            display_message += f" (config ID: {result.config_id})"

        return self.WaitForRenderStageOutput(
            config_id=result.config_id,
            display=display_message,
        )

    class DeployStageInput(StageInput):
        """Deploy Stage Input."""

        device: NetworkDeviceData

    class DeployStageOutput(StageOutput):
        """Deploy Stage Output."""

        device_id: str

    @stage_executor("deploy")
    async def deploy_stage(self, stage_input: DeployStageInput) -> DeployStageOutput:
        """Deploy tenant configuration to device."""
        await workflow.execute_child_workflow(
            TenantDeployWorkflow.run,
            TenantDeployInput(device=stage_input.device),
            run_timeout=timedelta(minutes=10),
        )

        self.append_child_workflow("deploy", workflow.info().workflow_id)

        return self.DeployStageOutput(
            device_id=stage_input.device.id,
            display=f"Deployed tenant configuration to device {stage_input.device.id}",
        )

    @run_nv_config_manager_workflow
    async def run(  # type: ignore[override, ty:invalid-method-override]  # pyright: ignore
        self, workflow_input: SpXOverlayTenantChangeInput
    ) -> SpXOverlayTenantChangeWorkflowOutput:
        """Execute the VPC Tenant Change workflow."""
        self.set_input(workflow_input)

        device_output = await self.get_device_stage(
            self.GetDeviceStageInput(device_id=workflow_input.device_id)
        )
        DeviceMixin.attach_device_search_attributes(device_output.device)
        assign_output = await self.assign_spx_overlay_stage(
            self.AssignSpXOverlayStageInput(
                vpc_id=workflow_input.vpc_id,
                device=device_output.device,
                port_names=workflow_input.port_names,
                site=workflow_input.site,
                namespace_tag=workflow_input.namespace_tag,
            )
        )

        if not assign_output.assigned_ports and not assign_output.vrf_assigned:
            self.set_stage_state("render", StateEnum.UNREACHABLE)
            self.set_stage_state("wait_for_render", StateEnum.UNREACHABLE)
            self.set_stage_state("deploy", StateEnum.UNREACHABLE)
            assigned_ports = []
            vrf_assigned = False
            vrf = None
            device_deployed = None
        else:
            render_output = await self.render_stage(
                self.RenderStageInput(
                    device=device_output.device,
                )
            )

            await self.wait_for_render_stage(
                self.WaitForRenderStageInput(
                    device=device_output.device,
                    config_id=render_output.config_id,
                )
            )

            deploy_output = await self.deploy_stage(
                self.DeployStageInput(device=device_output.device)
            )
            device_deployed = deploy_output.device_id
            assigned_ports = assign_output.assigned_ports
            vrf_assigned = assign_output.vrf_assigned
            vrf = assign_output.vrf

        await self.archive_results()
        return SpXOverlayTenantChangeWorkflowOutput(
            assigned_ports=assigned_ports,
            vrf_assigned=vrf_assigned,
            vrf=vrf,
            device_deployed=device_deployed,
        )
