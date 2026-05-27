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
import urllib.parse
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from unittest.mock import patch

import pytest
from temporalio import activity
from temporalio.client import WorkflowHandle
from temporalio.common import RetryPolicy
from temporalio.worker import Worker

from nv_config_manager.temporal.common.mixins.device import NetworkDeviceData
from nv_config_manager.temporal.ngc.activities.air import (
    AirDevice,
    ConfigTestInput,
    ConfigTestOutput,
    CreateSimulationInput,
    CreateSimulationNodeServicesInput,
    CreateSimulationNodeServicesOutput,
    CreateSimulationOutput,
    DeleteSimulationInput,
    MinimalTopologyInput,
    MinimalTopologyOutput,
    PrepareSimulationNodesInput,
    StartSimulationInput,
    WaitForSimulationNodeInput,
)
from nv_config_manager.temporal.ngc.activities.nats import PublishNatsInput
from nv_config_manager.temporal.ngc.activities.nautobot import (
    GetNetworkDevicesInput,
    GetNetworkDevicesOutput,
)
from nv_config_manager.temporal.ngc.workflows.air import (
    AIRCreateBlueprintSimulationInput,
    AIRCreateBlueprintSimulationWorkflow,
    AIRCreateSimulationInput,
    AIRCreateSimulationWorkflow,
    AIRDeleteInput,
    AIRDeleteSimulationWorkflow,
    AIRValidateSiteInput,
    AIRValidateSiteWorkflow,
)

# Test-specific retry policy and timeout
TEST_RETRY_POLICY = RetryPolicy(maximum_attempts=1)
TEST_TIMEOUT = timedelta(seconds=10)


@activity.defn(name="generate_air_topology_for_location")
async def mock_generate_air_topology_for_location(location_id: str) -> dict:
    """Mock topology generation activity."""
    # Updated to a more realistic topology structure
    return {
        "oob": False,
        "nodes": {
            f"{location_id}_leaf1": {
                "memory": 2048,
                "os": "cumulus-vx-5.10.0",
                "cpu": 1,
                "type": "switch",  # Adding type as it's common in AIR
            },
            f"{location_id}_spine1": {
                "memory": 4096,
                "os": "cumulus-vx-5.11.0",
                "cpu": 2,
                "type": "switch",  # Adding type
            },
            f"{location_id}_server1": {
                "memory": 8192,
                "os": "ubuntu-20.04",
                "cpu": 4,
                "type": "server",  # Adding type
            },
        },
        "links": [
            [
                {"node": f"{location_id}_leaf1", "interface": "swp1s1"},
                {"node": f"{location_id}_spine1", "interface": "swp1s1"},
            ],
            [
                {"node": f"{location_id}_leaf1", "interface": "swp2s1"},
                {"node": f"{location_id}_server1", "interface": "eth0"},
            ],
            [{"node": f"{location_id}_spine1", "interface": "swp2s1"}, "unconnected"],
            [{"node": f"{location_id}_server1", "interface": "eth1"}, "unconnected"],
        ],
    }


@activity.defn(name="create_simulation")
async def mock_create_simulation(
    input: CreateSimulationInput,
) -> CreateSimulationOutput:
    """Mock simulation creation activity."""
    return CreateSimulationOutput(simulation_id="mock_simulation_id")


@activity.defn(name="prepare_simulation_nodes")
async def mock_prepare_simulation_nodes(input: PrepareSimulationNodesInput) -> None:
    """Mock node preparation activity."""
    pass


@activity.defn(name="start_simulation")
async def mock_start_simulation(input: StartSimulationInput) -> None:
    """Mock simulation start activity."""
    pass


@activity.defn(name="create_simulation_node_services")
async def mock_create_simulation_node_services(
    input: CreateSimulationNodeServicesInput,
) -> CreateSimulationNodeServicesOutput:
    """Mock node services creation activity."""
    return CreateSimulationNodeServicesOutput(
        devices=[
            AirDevice(
                id="node1",
                name="node1",
                worker_ip="10.0.0.1",
                api_port=8765,
            ),
            AirDevice(
                id="node2",
                name="node2",
                worker_ip="10.0.0.2",
                api_port=8765,
            ),
        ]
    )


@activity.defn(name="wait_for_simulation_node")
async def mock_wait_for_simulation_node(input: WaitForSimulationNodeInput) -> None:
    """Mock node wait activity."""
    pass


@activity.defn(name="delete_simulation")
async def mock_delete_simulation(input: DeleteSimulationInput) -> None:
    """Mock simulation deletion activity."""
    pass


@activity.defn(name="get_network_devices")
async def mock_get_network_devices(
    activity_input: GetNetworkDevicesInput,
) -> GetNetworkDevicesOutput:
    """Mock get_network_devices activity. Dynamically sets device name."""

    devices = []
    for device_id in activity_input.device_ids:
        devices.append(
            NetworkDeviceData(
                id=device_id,
                name=device_id,
                role="mock_role",
                platform="cumulus-linux",
                site="SITEA",
                device_type="sn4200",
                primary_ip4="10.0.0.1",
                primary_ip6=None,
            )
        )

    return GetNetworkDevicesOutput(devices=devices)


@activity.defn(name="load_intended_configuration")
async def mock_load_intended_configuration(
    input: NetworkDeviceData,
) -> tuple[str, str, str]:
    """Mock load_intended_configuration activity. Returns dynamic URL."""
    # The input.name here is now the AirDevice name (e.g., "switch1")
    # due to changes in mock_get_network_device
    url = f"https://git.nvidia.com/mock_site/{input.name}/startup.yaml"
    return "mock config for " + input.name, "mock_commit_for_" + input.name, url


@activity.defn(name="validate_configuration_against_air_device")
async def mock_validate_configuration_against_air_device(
    input: ConfigTestInput,
) -> ConfigTestOutput:
    """Mock test_configuration_against_air_device activity."""
    return ConfigTestOutput(error=None)


@activity.defn(name="generate_minimal_topology_for_site")
async def mock_generate_minimal_topology_for_site(
    input: MinimalTopologyInput,
) -> MinimalTopologyOutput:
    """Mock generate_minimal_topology_for_site activity."""
    topology_dict = {
        "oob": True,  # Minimal topology for config testing might use OOB
        "nodes": {
            "node1": {
                "memory": 1024,
                "os": "cumulus-vx-5.9.0",  # Example OS
                "cpu": 1,
                "type": "switch",  # Standard type for AIR nodes
            },
            "node2": {
                "memory": 1024,
                "os": "cumulus-vx-5.9.0",
                "cpu": 1,
                "type": "switch",
            },
        },
        "links": [
            # For minimal config testing, nodes might be largely isolated
            # or have very specific, simple connections if inter-device config is tested.
            # Often, they are tested as standalone.
            [
                {"node": "node1", "interface": "eth0"},
                "unconnected",
            ],  # Management interface
            [{"node": "node1", "interface": "swp1"}, "unconnected"],
            [
                {"node": "node2", "interface": "eth0"},
                "unconnected",
            ],  # Management interface
            [{"node": "node2", "interface": "swp1"}, "unconnected"],
        ],
    }
    # 2 devices mapped to the same node
    node_map_dict = {
        "switch1": "node1",
        "switch2": "node2",
        "switch3": "node2",
    }
    return MinimalTopologyOutput(topology=topology_dict, node_map=node_map_dict)


@activity.defn(
    name="validate_configuration_against_air_device"
)  # Give it a unique name if registered globally
async def mock_validate_config_with_error(input: ConfigTestInput) -> ConfigTestOutput:
    """Mock validate_configuration_against_air_device that returns an error for a specific node."""
    if input.node.name == "node1":
        return ConfigTestOutput(error="Syntax Error! Invalid command found.")
    return ConfigTestOutput(error=None)


@activity.defn(name="publish_nats")
async def mock_publish_nats(activity_input: PublishNatsInput) -> None:
    """Mock publish nats activity."""
    return None


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.common.mixins.stage.workflow.time", return_value=float(0))
@patch(
    "nv_config_manager.temporal.ngc.workflows.air.DEFAULT_ACTIVITY_RETRY_POLICY",
    return_value=TEST_RETRY_POLICY,
)
@patch("nv_config_manager.temporal.ngc.workflows.air.timedelta", return_value=TEST_TIMEOUT)
async def test_execute_workflow(mock_time_delta, mock_retry_policy, mock_time, env):
    """Test the AIR workflow execution."""
    task_queue_name = str(uuid.uuid4())
    async with Worker(
        env.client,
        task_queue=task_queue_name,
        workflows=[AIRCreateBlueprintSimulationWorkflow],
        activities=[
            mock_generate_air_topology_for_location,
            mock_create_simulation,
            mock_prepare_simulation_nodes,
            mock_start_simulation,
            mock_create_simulation_node_services,
            mock_wait_for_simulation_node,
            mock_publish_nats,
        ],
        activity_executor=ThreadPoolExecutor(100),
    ):
        input = AIRCreateBlueprintSimulationInput(
            blueprint_name="test_blueprint",
            user="test_user",
            user_domain="nvidia.com",
        )
        workflow_id = str(uuid.uuid4())
        handle: WorkflowHandle = await env.client.start_workflow(
            AIRCreateBlueprintSimulationWorkflow.run,
            input,
            id=workflow_id,
            task_queue=task_queue_name,
            run_timeout=timedelta(minutes=10),
        )

        result = await handle.result()

        assert result == ["device1", "device2"]
        assert await handle.query("stages") == [
            {
                "approval_threshold": 0,
                "approvers": [],
                "child_workflows": [],
                "depends_on": [],
                "description": "Create Cerebro location from blueprint.",
                "execution_time": 0.0,
                "input": {"blueprint_name": "test_blueprint"},
                "name": "create_cerebro_location",
                "output": {
                    "location_id": "placeholder",
                    "display": "Created location with ID: placeholder",
                },
                "rejecters": [],
                "requires_approval": False,
                "retry_count": 0,
                "retryable": True,
                "state": "COMPLETE",
                "state_history": [
                    {"state": "NOT_STARTED", "time": "1970-01-01T00:00:00+00:00"},
                    {"state": "IN_PROGRESS", "time": "1970-01-01T00:00:00+00:00"},
                    {"state": "COMPLETE", "time": "1970-01-01T00:00:00+00:00"},
                ],
                "traceback": None,
            },
            {
                "approval_threshold": 0,
                "approvers": [],
                "child_workflows": [],
                "depends_on": ["create_cerebro_location"],
                "description": "Create and populate a new AIR simulation.",
                "execution_time": 0.0,
                "input": {
                    "user": "test_user",
                    "user_domain": "nvidia.com",
                    "location_id": "placeholder",
                },
                "name": "setup_simulation",
                "output": {
                    "simulation_id": "mock_simulation_id",
                    "display": "Created simulation with ID: mock_simulation_id",
                },
                "rejecters": [],
                "requires_approval": False,
                "retry_count": 0,
                "retryable": True,
                "state": "COMPLETE",
                "state_history": [
                    {"state": "NOT_STARTED", "time": "1970-01-01T00:00:00+00:00"},
                    {"state": "IN_PROGRESS", "time": "1970-01-01T00:00:00+00:00"},
                    {"state": "COMPLETE", "time": "1970-01-01T00:00:00+00:00"},
                ],
                "traceback": None,
            },
            {
                "approval_threshold": 0,
                "approvers": [],
                "child_workflows": [],
                "depends_on": ["setup_simulation"],
                "description": "Configure devices in the simulation.",
                "execution_time": 0.0,
                "input": {"location_id": "placeholder"},
                "name": "configure_devices",
                "output": {
                    "configured_devices": ["device1", "device2"],
                    "display": "Configured devices: device1, device2",
                },
                "rejecters": [],
                "requires_approval": False,
                "retry_count": 0,
                "retryable": True,
                "state": "COMPLETE",
                "state_history": [
                    {"state": "NOT_STARTED", "time": "1970-01-01T00:00:00+00:00"},
                    {"state": "IN_PROGRESS", "time": "1970-01-01T00:00:00+00:00"},
                    {"state": "COMPLETE", "time": "1970-01-01T00:00:00+00:00"},
                ],
                "traceback": None,
            },
        ]


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.common.mixins.stage.workflow.time", return_value=float(0))
@patch(
    "nv_config_manager.temporal.ngc.workflows.air.DEFAULT_ACTIVITY_RETRY_POLICY",
    return_value=TEST_RETRY_POLICY,
)
@patch("nv_config_manager.temporal.ngc.workflows.air.timedelta", return_value=TEST_TIMEOUT)
async def test_air_create_simulation_workflow(mock_time_delta, mock_retry_policy, mock_time, env):
    """Test the AIRCreateSimulationWorkflow execution."""
    task_queue_name = str(uuid.uuid4())
    async with Worker(
        env.client,
        task_queue=task_queue_name,
        workflows=[AIRCreateSimulationWorkflow],
        activities=[
            mock_create_simulation,
            mock_prepare_simulation_nodes,
            mock_start_simulation,
            mock_create_simulation_node_services,
            mock_wait_for_simulation_node,
            mock_publish_nats,
        ],
        activity_executor=ThreadPoolExecutor(100),
    ):
        input_data = AIRCreateSimulationInput(
            name="test_simulation",
            topology={
                "oob": False,
                "nodes": {
                    "node1": {
                        "memory": 2048,
                        "os": "cumulus-vx-5.10.0",
                        "cpu": 1,
                        "type": "switch",
                    },
                },
                "links": [],
            },
            user="test_user",
        )
        workflow_id = str(uuid.uuid4())
        handle: WorkflowHandle = await env.client.start_workflow(
            AIRCreateSimulationWorkflow.run,
            input_data,
            id=workflow_id,
            task_queue=task_queue_name,
            run_timeout=timedelta(minutes=10),
        )

        result = await handle.result()
        assert result == "mock_simulation_id"

        stages = await handle.query("stages")
        assert len(stages) == 1
        assert stages[0]["name"] == "setup_simulation"
        assert stages[0]["state"] == "COMPLETE"
        assert stages[0]["output"]["simulation_id"] == "mock_simulation_id"
        assert len(stages[0]["output"]["devices"]) == 2


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.common.mixins.stage.workflow.time", return_value=float(0))
async def test_air_delete_simulation_workflow(mock_time, env):
    """Test the AIRDeleteSimulationWorkflow execution."""
    task_queue_name = str(uuid.uuid4())
    async with Worker(
        env.client,
        task_queue=task_queue_name,
        workflows=[AIRDeleteSimulationWorkflow],
        activities=[mock_delete_simulation, mock_publish_nats],
        activity_executor=ThreadPoolExecutor(100),
    ):
        input_data = AIRDeleteInput(simulation_id="mock_sim_id_to_delete")
        workflow_id = str(uuid.uuid4())
        handle: WorkflowHandle = await env.client.start_workflow(
            AIRDeleteSimulationWorkflow.run,
            input_data,
            id=workflow_id,
            task_queue=task_queue_name,
            run_timeout=timedelta(minutes=10),
        )

        result = await handle.result()
        assert result is True

        stages = await handle.query("stages")
        assert len(stages) == 1
        assert stages[0]["name"] == "delete_simulation"
        assert stages[0]["state"] == "COMPLETE"
        assert stages[0]["output"]["success"] is True


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.common.mixins.stage.workflow.time", return_value=float(0))
@patch(
    "nv_config_manager.temporal.ngc.workflows.air.DEFAULT_ACTIVITY_RETRY_POLICY",
    return_value=TEST_RETRY_POLICY,
)
@patch("nv_config_manager.temporal.ngc.workflows.air.timedelta", return_value=TEST_TIMEOUT)
async def test_air_validate_site_workflow(mock_time_delta, mock_retry_policy, mock_time, env):
    """Test the AIRValidateSiteWorkflow execution."""
    task_queue_name = str(uuid.uuid4())
    async with Worker(
        env.client,
        task_queue=task_queue_name,
        workflows=[AIRValidateSiteWorkflow],
        activities=[
            mock_generate_minimal_topology_for_site,
            mock_create_simulation,
            mock_prepare_simulation_nodes,
            mock_start_simulation,
            mock_create_simulation_node_services,
            mock_wait_for_simulation_node,
            mock_get_network_devices,
            mock_load_intended_configuration,
            mock_validate_configuration_against_air_device,
            mock_delete_simulation,
            mock_publish_nats,
        ],
        activity_executor=ThreadPoolExecutor(100),
    ):
        input_data = AIRValidateSiteInput(site_name="test_site", user="test_user")
        workflow_id = str(uuid.uuid4())
        handle: WorkflowHandle = await env.client.start_workflow(
            AIRValidateSiteWorkflow.run,
            input_data,
            id=workflow_id,
            task_queue=task_queue_name,
            run_timeout=timedelta(minutes=10),
        )

        result = await handle.result()
        assert result == []

        stages = await handle.query("stages")
        assert len(stages) == 4
        assert stages[0]["name"] == "generate_minimal_topology"
        assert stages[0]["state"] == "COMPLETE"
        assert stages[1]["name"] == "setup_simulation"
        assert stages[1]["state"] == "COMPLETE"
        assert stages[2]["name"] == "configure_devices"
        assert stages[2]["state"] == "COMPLETE"
        assert stages[2]["output"]["failed_devices"] == []
        assert stages[3]["name"] == "delete_simulation"
        assert stages[3]["state"] == "COMPLETE"
        assert stages[3]["output"]["success"] is True


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.common.mixins.stage.workflow.time", return_value=float(0))
@patch(
    "nv_config_manager.temporal.ngc.workflows.air.DEFAULT_ACTIVITY_RETRY_POLICY",
    return_value=TEST_RETRY_POLICY,
)
@patch("nv_config_manager.temporal.ngc.workflows.air.timedelta", return_value=TEST_TIMEOUT)
async def test_air_validate_site_workflow_with_config_error(
    mock_time_delta, mock_retry_policy, mock_time, env
):
    """Test the AIRValidateSiteWorkflow when a device has a configuration error."""
    task_queue_name = str(uuid.uuid4())
    async with Worker(
        env.client,
        task_queue=task_queue_name,
        workflows=[AIRValidateSiteWorkflow],
        activities=[
            mock_generate_minimal_topology_for_site,
            mock_create_simulation,
            mock_prepare_simulation_nodes,
            mock_start_simulation,
            mock_create_simulation_node_services,
            mock_wait_for_simulation_node,
            mock_get_network_devices,
            mock_load_intended_configuration,
            mock_validate_config_with_error,  # Specific mock for this test
            mock_delete_simulation,
            mock_publish_nats,
        ],
        activity_executor=ThreadPoolExecutor(100),
    ):
        input_data = AIRValidateSiteInput(site_name="test_site_error", user="test_user")
        workflow_id = str(uuid.uuid4())
        handle: WorkflowHandle = await env.client.start_workflow(
            AIRValidateSiteWorkflow.run,
            input_data,
            id=workflow_id,
            task_queue=task_queue_name,
            run_timeout=timedelta(minutes=10),
        )

        result = await handle.result()

        expected_failed_device_name = "switch1"
        expected_error_message = "Syntax Error! Invalid command found."
        # URL needs to be constructed carefully based on mock_load_intended_configuration and then URL encoded by the workflow
        raw_url_for_failed_device = (
            f"https://git.nvidia.com/mock_site/{expected_failed_device_name}/startup.yaml"
        )
        encoded_url_for_failed_device = urllib.parse.quote(raw_url_for_failed_device, safe="/:")

        expected_failure = {
            "Device": expected_failed_device_name,
            "Error Message": expected_error_message,
            "Intended Config": f"[startup.yaml]({encoded_url_for_failed_device})",
        }

        assert result == [expected_failure]

        stages = await handle.query("stages")
        assert len(stages) == 4
        assert stages[0]["name"] == "generate_minimal_topology"
        assert stages[0]["state"] == "COMPLETE"
        assert stages[1]["name"] == "setup_simulation"
        assert stages[1]["state"] == "COMPLETE"
        assert stages[2]["name"] == "configure_devices"
        assert stages[2]["state"] == "COMPLETE"
        assert stages[2]["output"]["failed_devices"] == [expected_failure]
        assert stages[3]["name"] == "delete_simulation"
        assert stages[3]["state"] == "COMPLETE"
        assert stages[3]["output"]["success"] is True

        expected_display_table = """
| Device|            Error Message           |                           Intended Config                           |
|-------|------------------------------------|---------------------------------------------------------------------|
|switch1|Syntax Error! Invalid command found.|[startup.yaml](https://git.nvidia.com/mock_site/switch1/startup.yaml)|
"""
        assert stages[2]["output"]["display"].strip() == expected_display_table.strip()
