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
"""AIR Simulation Workflow Definitions."""

import asyncio
import urllib.parse
from datetime import timedelta
from typing import Any

from py_markdown_table.markdown_table import markdown_table
from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError

from nv_config_manager.temporal.common.decorators.workflow import run_nv_config_manager_workflow
from nv_config_manager.temporal.common.mixins.archive import ArchiveMixin
from nv_config_manager.temporal.common.mixins.metadata import WorkflowMetadataMixin
from nv_config_manager.temporal.common.mixins.stage import (
    StageInput,
    StageMixin,
    StageOutput,
    stage_executor,
)

with workflow.unsafe.imports_passed_through():
    from nv_config_manager.temporal.ngc.activities.air import (
        AirDevice,
        ConfigTestInput,
        CreateSimulationInput,
        CreateSimulationNodeServicesInput,
        DeleteSimulationInput,
        MinimalTopologyInput,
        PrepareSimulationNodesInput,
        StartSimulationInput,
        WaitForSimulationNodeInput,
        create_simulation,
        create_simulation_node_services,
        delete_simulation,
        generate_air_topology_for_location,
        generate_minimal_topology_for_site,
        prepare_simulation_nodes,
        start_simulation,
        validate_configuration_against_air_device,
        wait_for_simulation_node,
    )
    from nv_config_manager.temporal.ngc.activities.deploy import (
        load_intended_configuration,
    )
    from nv_config_manager.temporal.ngc.activities.nautobot import (
        GetNetworkDevicesInput,
        get_network_devices,
    )

DEFAULT_ACTIVITY_RETRY_POLICY = RetryPolicy(maximum_attempts=3)
DEFAULT_ACTIVITY_TIMEOUT = timedelta(minutes=5)


async def _setup_simulation(name: str, topology: dict[str, Any]) -> tuple[str, list[AirDevice]]:
    """Create a new AIR simulation."""
    create_sim_result = await workflow.execute_activity(
        create_simulation,
        CreateSimulationInput(
            simulation_name=name,
            topology=topology,
        ),
        retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        start_to_close_timeout=DEFAULT_ACTIVITY_TIMEOUT,
    )

    # Prepare simulation nodes
    await workflow.execute_activity(
        prepare_simulation_nodes,
        PrepareSimulationNodesInput(simulation_id=create_sim_result.simulation_id),
        retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        start_to_close_timeout=DEFAULT_ACTIVITY_TIMEOUT,
    )

    # Start the simulation
    await workflow.execute_activity(
        start_simulation,
        StartSimulationInput(simulation_id=create_sim_result.simulation_id),
        retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        start_to_close_timeout=DEFAULT_ACTIVITY_TIMEOUT,
    )

    # Create node services and get device info
    services_result = await workflow.execute_activity(
        create_simulation_node_services,
        CreateSimulationNodeServicesInput(simulation_id=create_sim_result.simulation_id),
        retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        start_to_close_timeout=DEFAULT_ACTIVITY_TIMEOUT,
    )

    # Wait for all nodes to be ready in parallel
    await asyncio.gather(
        *[
            workflow.execute_activity(
                wait_for_simulation_node,
                WaitForSimulationNodeInput(node=device),
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
                start_to_close_timeout=DEFAULT_ACTIVITY_TIMEOUT,
            )
            for device in services_result.devices
        ]
    )

    return create_sim_result.simulation_id, services_result.devices


class AIRCreateSimulationInput(BaseModel):
    """AIR Workflow Input Definition."""

    name: str
    topology: dict[str, Any]
    user: str


@workflow.defn
class AIRCreateSimulationWorkflow(WorkflowMetadataMixin, StageMixin, ArchiveMixin):
    """AIR network simulation creation workflow for testing and validation."""

    # Workflow metadata
    workflow_description = "Create AIR network simulation from topology for configuration testing"
    workflow_input_class = AIRCreateSimulationInput
    workflow_api_endpoint = "/ngc/air_create_simulation"
    workflow_namespace = "ngc"

    def __init__(self) -> None:
        """Initialize workflow."""
        StageMixin.__init__(self)
        self.define_stage(
            name="setup_simulation",
            description="Create and populate a new AIR simulation.",
            requires_approval=False,
            depends_on=[],
        )

    class SetupSimulationStageInput(StageInput):
        """Setup Simulation Stage Input."""

        topology: dict[str, Any]
        name: str
        user: str

    class SetupSimulationStageOutput(StageOutput):
        """Setup Simulation Stage Output."""

        simulation_id: str
        devices: list[AirDevice]

    @stage_executor("setup_simulation")
    async def setup_simulation(
        self, stage_input: SetupSimulationStageInput
    ) -> SetupSimulationStageOutput:
        """Create and populate a new AIR simulation."""
        simulation_name = f"{stage_input.name} ({stage_input.user})"
        simulation_id, devices = await _setup_simulation(simulation_name, stage_input.topology)

        return AIRCreateSimulationWorkflow.SetupSimulationStageOutput(
            simulation_id=simulation_id,
            devices=devices,
            display=f"Created simulation with ID: {simulation_id}",
        )

    @run_nv_config_manager_workflow
    async def run(self, workflow_input: AIRCreateSimulationInput) -> str:  # type: ignore[override, ty:invalid-method-override]
        """Execute AIR simulation workflow."""
        self.set_input(workflow_input)

        setup_output = await self.setup_simulation(
            AIRCreateSimulationWorkflow.SetupSimulationStageInput(
                name=workflow_input.name,
                topology=workflow_input.topology,
                user=workflow_input.user,
            )
        )

        await self.archive_results()
        return setup_output.simulation_id


class AIRCreateBlueprintSimulationInput(BaseModel):
    """AIR Workflow Input Definition."""

    blueprint_name: str
    user: str | None
    user_domain: str | None


@workflow.defn
class AIRCreateBlueprintSimulationWorkflow(WorkflowMetadataMixin, StageMixin, ArchiveMixin):
    """AIR blueprint simulation creation workflow for standardized network testing."""

    # Workflow metadata
    workflow_description = (
        "Create AIR simulation from blueprint template for standardized network testing"
    )
    workflow_input_class = AIRCreateBlueprintSimulationInput
    workflow_api_endpoint = "/ngc/air_create_blueprint_simulation"
    workflow_namespace = "ngc"

    def __init__(self) -> None:
        """Initialize workflow."""
        StageMixin.__init__(self)
        self.define_stage(
            name="create_cerebro_location",
            description="Create Cerebro location from blueprint.",
            requires_approval=False,
            depends_on=[],
        )
        self.define_stage(
            name="setup_simulation",
            description="Create and populate a new AIR simulation.",
            requires_approval=False,
            depends_on=["create_cerebro_location"],
        )
        self.define_stage(
            name="configure_devices",
            description="Configure devices in the simulation.",
            requires_approval=False,
            depends_on=["setup_simulation"],
        )

    class CreateCerebroLocationStageInput(StageInput):
        """Create Cerebro Location Stage Input."""

        blueprint_name: str

    class CreateCerebroLocationStageOutput(StageOutput):
        """Create Cerebro Location Stage Output."""

        location_id: str

    @stage_executor("create_cerebro_location")
    async def create_cerebro_location(
        self, stage_input: CreateCerebroLocationStageInput
    ) -> CreateCerebroLocationStageOutput:
        """Create Cerebro location from blueprint."""
        # TODO: Implement activity call to create location
        location_id = "placeholder"
        return AIRCreateBlueprintSimulationWorkflow.CreateCerebroLocationStageOutput(
            location_id=location_id,
            display=f"Created location with ID: {location_id}",
        )

    class SetupSimulationStageInput(StageInput):
        """Setup Simulation Stage Input."""

        user: str | None
        user_domain: str | None
        location_id: str

    class SetupSimulationStageOutput(StageOutput):
        """Setup Simulation Stage Output."""

        simulation_id: str

    @stage_executor("setup_simulation")
    async def setup_simulation(
        self, stage_input: SetupSimulationStageInput
    ) -> SetupSimulationStageOutput:
        """Create and populate a new AIR simulation."""
        topology = await workflow.execute_activity(
            generate_air_topology_for_location,
            stage_input.location_id,
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            start_to_close_timeout=DEFAULT_ACTIVITY_TIMEOUT,
        )

        simulation_name = f"{stage_input.user}-{stage_input.location_id}"

        simulation_id, _ = await _setup_simulation(simulation_name, topology)

        return AIRCreateBlueprintSimulationWorkflow.SetupSimulationStageOutput(
            simulation_id=simulation_id,
            display=f"Created simulation with ID: {simulation_id}",
        )

    class ConfigureDevicesStageInput(StageInput):
        """Configure Devices Stage Input."""

        location_id: str

    class ConfigureDevicesStageOutput(StageOutput):
        """Configure Devices Stage Output."""

        configured_devices: list[str]

    @stage_executor("configure_devices")
    async def configure_devices(
        self, stage_input: ConfigureDevicesStageInput
    ) -> ConfigureDevicesStageOutput:
        """Configure devices in the simulation."""
        # TODO: Implement activity call to configure devices
        configured_devices = ["device1", "device2"]
        return AIRCreateBlueprintSimulationWorkflow.ConfigureDevicesStageOutput(
            configured_devices=configured_devices,
            display=f"Configured devices: {', '.join(configured_devices)}",
        )

    @run_nv_config_manager_workflow
    async def run(self, workflow_input: AIRCreateBlueprintSimulationInput) -> list[str]:  # type: ignore[override, ty:invalid-method-override]
        """Execute AIR simulation workflow."""
        if not workflow_input.user:
            raise ApplicationError("Missing user for workflow attribution.")
        self.set_input(workflow_input)

        create_location_output = await self.create_cerebro_location(
            AIRCreateBlueprintSimulationWorkflow.CreateCerebroLocationStageInput(
                blueprint_name=workflow_input.blueprint_name,
            )
        )

        await self.setup_simulation(
            AIRCreateBlueprintSimulationWorkflow.SetupSimulationStageInput(
                user=workflow_input.user,
                user_domain=workflow_input.user_domain,
                location_id=create_location_output.location_id,
            )
        )

        configure_output = await self.configure_devices(
            AIRCreateBlueprintSimulationWorkflow.ConfigureDevicesStageInput(
                location_id=create_location_output.location_id,
            )
        )

        await self.archive_results()

        return configure_output.configured_devices


class AIRDeleteInput(BaseModel):
    """AIR Delete Workflow Input Definition."""

    simulation_id: str


@workflow.defn
class AIRDeleteSimulationWorkflow(WorkflowMetadataMixin, StageMixin, ArchiveMixin):
    """AIR simulation cleanup workflow for resource management."""

    # Workflow metadata
    workflow_description = "Delete AIR simulation and clean up associated resources"
    workflow_input_class = AIRDeleteInput
    workflow_api_endpoint = "/ngc/air_delete"
    workflow_namespace = "ngc"

    def __init__(self) -> None:
        """Initialize workflow."""
        StageMixin.__init__(self)
        self.define_stage(
            name="delete_simulation",
            description="Delete an AIR simulation.",
            requires_approval=False,
            depends_on=[],
        )

    class DeleteSimulationStageInput(StageInput):
        """Delete Simulation Stage Input."""

        simulation_id: str

    class DeleteSimulationStageOutput(StageOutput):
        """Delete Simulation Stage Output."""

        success: bool

    @stage_executor("delete_simulation")
    async def delete_simulation(
        self, stage_input: DeleteSimulationStageInput
    ) -> DeleteSimulationStageOutput:
        """Delete an AIR simulation."""
        await workflow.execute_activity(
            delete_simulation,
            DeleteSimulationInput(simulation_id=stage_input.simulation_id),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            start_to_close_timeout=DEFAULT_ACTIVITY_TIMEOUT,
        )

        return AIRDeleteSimulationWorkflow.DeleteSimulationStageOutput(
            success=True,
            display=f"Successfully deleted simulation with ID: {stage_input.simulation_id}",
        )

    @run_nv_config_manager_workflow
    async def run(self, workflow_input: AIRDeleteInput) -> bool:  # type: ignore[override, ty:invalid-method-override]
        """Execute AIR simulation delete workflow."""
        self.set_input(workflow_input)

        delete_output = await self.delete_simulation(
            AIRDeleteSimulationWorkflow.DeleteSimulationStageInput(
                simulation_id=workflow_input.simulation_id,
            )
        )

        await self.archive_results()

        return delete_output.success


class AIRValidateSiteInput(BaseModel):
    """AIR Validate Site Workflow Input Definition."""

    site_name: str
    user: str


@workflow.defn
class AIRValidateSiteWorkflow(WorkflowMetadataMixin, StageMixin, ArchiveMixin):
    """AIR site validation workflow for network configuration testing."""

    # Workflow metadata
    workflow_description = "Validate site network configuration using AIR simulation environment"
    workflow_input_class = AIRValidateSiteInput
    workflow_api_endpoint = "/ngc/air_validate_site"
    workflow_namespace = "ngc"

    def __init__(self) -> None:
        """Initialize workflow."""
        StageMixin.__init__(self)
        self.define_stage(
            name="generate_minimal_topology",
            description="Generate minimal topology for testing rendered configs.",
            requires_approval=False,
            depends_on=[],
        )
        self.define_stage(
            name="setup_simulation",
            description="Create and populate a new AIR simulation.",
            requires_approval=False,
            depends_on=["generate_minimal_topology"],
        )
        self.define_stage(
            name="configure_devices",
            description="Configure and validate devices in the simulation.",
            requires_approval=False,
            depends_on=["setup_simulation"],
        )
        self.define_stage(
            name="delete_simulation",
            description="Delete the AIR simulation.",
            requires_approval=False,
            depends_on=["configure_devices"],
        )

    class GenerateMinimalTopologyStageInput(StageInput):
        """Generate Minimal Topology Stage Input."""

        site_name: str

    class GenerateMinimalTopologyStageOutput(StageOutput):
        """Generate Minimal Topology Stage Output."""

        topology: dict[str, Any]
        node_map: dict[str, str]  # Maps nv-config-manager device to AIR node

    @stage_executor("generate_minimal_topology")
    async def generate_minimal_topology(
        self, stage_input: GenerateMinimalTopologyStageInput
    ) -> GenerateMinimalTopologyStageOutput:
        """Generate minimal topology for testing rendered configs."""
        output = await workflow.execute_activity(
            generate_minimal_topology_for_site,
            MinimalTopologyInput(site_name=stage_input.site_name),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            start_to_close_timeout=DEFAULT_ACTIVITY_TIMEOUT,
        )

        display = f"Generated minimal topology for {stage_input.site_name}\n\n"
        display += f"Representing {len(output.node_map)} devices with {len(output.topology['nodes'])} nodes"
        return AIRValidateSiteWorkflow.GenerateMinimalTopologyStageOutput(
            topology=output.topology,
            node_map=output.node_map,
            display=display,
        )

    class SetupSimulationStageInput(StageInput):
        """Setup Simulation Stage Input."""

        topology: dict[str, Any]
        site_name: str
        user: str

    class SetupSimulationStageOutput(StageOutput):
        """Setup Simulation Stage Output."""

        simulation_id: str
        devices: dict[str, AirDevice]

    @stage_executor("setup_simulation")
    async def setup_simulation(
        self, stage_input: SetupSimulationStageInput
    ) -> SetupSimulationStageOutput:
        """Create and populate a new AIR simulation."""
        simulation_name = f"{stage_input.site_name} Validation ({stage_input.user})"

        simulation_id, devices = await _setup_simulation(simulation_name, stage_input.topology)

        return AIRValidateSiteWorkflow.SetupSimulationStageOutput(
            simulation_id=simulation_id,
            devices={device.name: device for device in devices},
            display=f"Created validation simulation with ID: {simulation_id}",
        )

    class ConfigureDevicesStageInput(StageInput):
        """Configure Devices Stage Input."""

        device_to_node_map: dict[str, str]
        node_map: dict[str, AirDevice]

    class ConfigureDevicesStageOutput(StageOutput):
        """Configure Devices Stage Output."""

        failed_devices: list[dict[str, str]]  # Maps device name to error message

    @stage_executor("configure_devices")
    async def configure_devices(
        self, stage_input: ConfigureDevicesStageInput
    ) -> ConfigureDevicesStageOutput:
        """Configure and validate devices in the simulation."""
        failed_devices = []

        # This is a very long running stage, update the display to show progress
        # after each device, final output will be replaced with the result
        stage_progress_display = (
            f"In Progress:0/{len(stage_input.device_to_node_map)} devices configured..."
        )
        stage = self.get_stage_by_name("configure_devices")
        stage.output = AIRValidateSiteWorkflow.ConfigureDevicesStageOutput(
            failed_devices=[],
            display=stage_progress_display,
        )

        network_device_results = await workflow.execute_activity(
            get_network_devices,
            GetNetworkDevicesInput(device_ids=list(stage_input.device_to_node_map.keys())),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            start_to_close_timeout=DEFAULT_ACTIVITY_TIMEOUT,
        )

        device_map = {device.id: device for device in network_device_results.devices}

        for i, (device_id, air_node_name) in enumerate(stage_input.device_to_node_map.items()):
            network_device = device_map[device_id]

            # Load intended configuration
            content, commit, url = await workflow.execute_activity(
                load_intended_configuration,
                network_device,
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
                start_to_close_timeout=DEFAULT_ACTIVITY_TIMEOUT,
            )

            # Diff configuration
            air_node = stage_input.node_map[air_node_name]
            test_result = await workflow.execute_activity(
                validate_configuration_against_air_device,
                ConfigTestInput(node=air_node, config=content),
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
                start_to_close_timeout=DEFAULT_ACTIVITY_TIMEOUT,
            )
            if test_result.error:
                encoded_url = urllib.parse.quote(url, safe="/:")
                failed_devices.append(
                    {
                        "Device": network_device.name,
                        "Error Message": test_result.error,
                        "Intended Config": f"[startup.yaml]({encoded_url})",
                    }
                )
            stage_progress_display = (
                f"In Progress: {i + 1}/{len(stage_input.device_to_node_map)} devices configured..."
            )
            stage.output = AIRValidateSiteWorkflow.ConfigureDevicesStageOutput(
                failed_devices=failed_devices,
                display=stage_progress_display,
            )

        if failed_devices:
            display = (
                markdown_table(failed_devices)
                .set_params(quote=False, row_sep="markdown")
                .get_markdown()
            )
        else:
            display = "All devices configured successfully."

        return AIRValidateSiteWorkflow.ConfigureDevicesStageOutput(
            failed_devices=failed_devices,
            display=display,
        )

    class DeleteSimulationStageInput(StageInput):
        """Delete Simulation Stage Input."""

        simulation_id: str

    class DeleteSimulationStageOutput(StageOutput):
        """Delete Simulation Stage Output."""

        success: bool

    @stage_executor("delete_simulation")
    async def delete_simulation(
        self, stage_input: DeleteSimulationStageInput
    ) -> DeleteSimulationStageOutput:
        """Delete an AIR simulation."""
        await workflow.execute_activity(
            delete_simulation,
            DeleteSimulationInput(simulation_id=stage_input.simulation_id),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            start_to_close_timeout=DEFAULT_ACTIVITY_TIMEOUT,
        )

        return AIRValidateSiteWorkflow.DeleteSimulationStageOutput(
            success=True,
            display=f"Successfully deleted simulation with ID: {stage_input.simulation_id}",
        )

    @run_nv_config_manager_workflow
    async def run(self, workflow_input: AIRValidateSiteInput) -> list[dict[str, str]]:  # type: ignore[override, ty:invalid-method-override]
        """Execute AIR test rendered configs workflow."""
        self.set_input(workflow_input)

        topology_output = await self.generate_minimal_topology(
            AIRValidateSiteWorkflow.GenerateMinimalTopologyStageInput(
                site_name=workflow_input.site_name,
            )
        )

        setup_output = await self.setup_simulation(
            AIRValidateSiteWorkflow.SetupSimulationStageInput(
                topology=topology_output.topology,
                site_name=workflow_input.site_name,
                user=workflow_input.user,
            )
        )

        configure_output = await self.configure_devices(
            AIRValidateSiteWorkflow.ConfigureDevicesStageInput(
                node_map=setup_output.devices,
                device_to_node_map=topology_output.node_map,
            )
        )

        await self.delete_simulation(
            AIRValidateSiteWorkflow.DeleteSimulationStageInput(
                simulation_id=setup_output.simulation_id,
            )
        )

        await self.archive_results()

        return configure_output.failed_devices
