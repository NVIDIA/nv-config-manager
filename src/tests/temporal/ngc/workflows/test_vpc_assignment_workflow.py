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
"""VPC Assignment Workflow Tests."""

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Any
from unittest.mock import patch

import pytest
from temporalio import activity
from temporalio.worker import Worker

from nv_config_manager.temporal.common.mixins.device import InterfaceData, NetworkDeviceData
from nv_config_manager.temporal.ngc.activities.nautobot import (
    AssignVrfToDeviceInput,
    AssignVrfToInterfaceInput,
    DeviceVrfInfo,
    GetDeviceInterfacesInput,
    GetDeviceInterfacesOutput,
    GetDeviceVrfsInput,
    GetDeviceVrfsOutput,
    GetNetworkDeviceInput,
    GetNetworkDeviceOutput,
    QueryVRFByVPCInput,
    Vrf,
)
from nv_config_manager.temporal.ngc.workflows.vpc import (
    VpcAssignmentInput,
    VpcAssignmentWorkflow,
)


def make_test_vrf(namespace: str) -> dict[str, Any]:
    return {
        "id": namespace,
        "name": "SpXTenant60004",
        "rd": "*:60004",
        "cf_forge_vpc_id": "mock_vpc_id",
        "namespace": {"name": namespace, "location": {"name": "mock_site"}},
        "interfaces": [],
    }


@activity.defn(name="get_network_device")
async def mock_get_network_device(
    activity_input: GetNetworkDeviceInput,
) -> GetNetworkDeviceOutput:
    """Mock activity for getting network device."""
    return GetNetworkDeviceOutput(
        device=NetworkDeviceData(
            id=activity_input.device_id,
            name="mock_device",
            role="switch",
            site="mock_site",
            device_type="mock_type",
            rack="mock_rack",
            position=1,
            primary_ip4="10.0.0.1",
            primary_ip6=None,
            platform="cumulus-linux",
            render_enabled=True,
            deploy_enabled=True,
            backup_enabled=True,
            ztp_enabled=False,
        )
    )


_mock_state = {
    "vrf_exists": True,
    "interfaces_with_vrf": [],
    "newer_commit_allowed": True,
}


@activity.defn(name="get_vrfs_by_vpc_id")
async def mock_get_vrfs_by_vpc_id(
    _activity_input: QueryVRFByVPCInput,
) -> list[Vrf] | None:
    """Mock activity for getting VRFs by VPC ID."""
    if not _mock_state["vrf_exists"]:
        return []
    return [Vrf.from_nautobot_graphql(make_test_vrf("mock_namespace1"))]


@activity.defn(name="get_device_vrfs")
async def mock_get_device_vrfs(
    activity_input: GetDeviceVrfsInput,
) -> GetDeviceVrfsOutput:
    """Mock activity for getting device VRFs."""
    if activity_input.device_id == "mock_device_id_with_vrf":
        return GetDeviceVrfsOutput(
            vrfs=[DeviceVrfInfo(vrf_id="mock_namespace1", vrf_name="SpXTenant60004")]
        )
    return GetDeviceVrfsOutput(vrfs=[])


@activity.defn(name="assign_vrf_to_device")
async def mock_assign_vrf_to_device(
    _activity_input: AssignVrfToDeviceInput,
) -> None:
    """Mock activity for assigning VRF to device."""


@activity.defn(name="get_device_interfaces")
async def mock_get_device_interfaces(
    activity_input: GetDeviceInterfacesInput,
) -> GetDeviceInterfacesOutput:
    """Mock activity for getting device interfaces."""
    from typing import cast

    from temporalio.exceptions import ApplicationError

    interfaces_with_vrf = cast(list[str], _mock_state.get("interfaces_with_vrf", []))

    all_interfaces = [
        InterfaceData(
            id="interface1_id",
            name="swp1",
            host="mock_device",
            mac_address="00:00:00:00:00:01",
            vrf_id="mock_namespace1" if "swp1" in interfaces_with_vrf else None,
        ),
        InterfaceData(
            id="interface2_id",
            name="swp2",
            host="mock_device",
            mac_address="00:00:00:00:00:02",
            vrf_id="mock_namespace1" if "swp2" in interfaces_with_vrf else None,
        ),
    ]

    if activity_input.interface_names:
        filtered = [intf for intf in all_interfaces if intf.name in activity_input.interface_names]

        found_names = {intf.name for intf in filtered}
        missing = set(activity_input.interface_names) - found_names
        if missing:
            raise ApplicationError(
                f"Interfaces not found on device {activity_input.device_id}: "
                f"{', '.join(sorted(missing))}"
            )

        return GetDeviceInterfacesOutput(interfaces=filtered)

    return GetDeviceInterfacesOutput(interfaces=all_interfaces)


@activity.defn(name="assign_vrf_to_interface")
async def mock_assign_vrf_to_interface(
    _activity_input: AssignVrfToInterfaceInput,
) -> None:
    """Mock activity for assigning VRF to interface."""


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.ngc.activities.nats.NatsProducer", autospec=True)
@patch("nv_config_manager.temporal.common.mixins.stage.workflow.time", return_value=float(0))
async def test_vpc_assignment_workflow_vrf_not_assigned(_mock_time, _mock_nats_client, env):
    """Test VPC assignment when VRF is not already assigned to device."""
    from nv_config_manager.temporal.ngc.activities.nats import publish_nats

    _mock_state["vrf_exists"] = True
    _mock_state["interfaces_with_vrf"] = []

    task_queue_name = str(uuid.uuid4())
    async with Worker(
        env.client,
        task_queue=task_queue_name,
        workflows=[VpcAssignmentWorkflow],
        activities=[
            mock_get_network_device,
            mock_get_vrfs_by_vpc_id,
            mock_get_device_vrfs,
            mock_assign_vrf_to_device,
            mock_get_device_interfaces,
            mock_assign_vrf_to_interface,
            publish_nats,
        ],
        activity_executor=ThreadPoolExecutor(1),
    ):
        workflow_input = VpcAssignmentInput(
            vpc_id="mock_vpc_id",
            device="mock_device_id",
            port_names=["swp1", "swp2"],
            site="mock_site",
        )
        workflow_id = str(uuid.uuid4())

        handle = await env.client.start_workflow(
            VpcAssignmentWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue=task_queue_name,
            run_timeout=timedelta(seconds=30),
        )

        result = await handle.result()
        assert result.vrf_assigned is True
        assert result.vrf.vrf_id == "mock_namespace1"
        assert result.vrf.vrf_name == "SpXTenant60004"
        assert set(result.assigned_ports) == {"swp1", "swp2"}


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.ngc.activities.nats.NatsProducer", autospec=True)
@patch("nv_config_manager.temporal.common.mixins.stage.workflow.time", return_value=float(0))
async def test_vpc_assignment_workflow_vrf_already_assigned(_mock_time, _mock_nats_client, env):
    """Test VPC assignment when VRF is already assigned to device."""
    from nv_config_manager.temporal.ngc.activities.nats import publish_nats

    _mock_state["vrf_exists"] = True
    _mock_state["interfaces_with_vrf"] = ["swp1"]

    task_queue_name = str(uuid.uuid4())
    async with Worker(
        env.client,
        task_queue=task_queue_name,
        workflows=[VpcAssignmentWorkflow],
        activities=[
            mock_get_network_device,
            mock_get_vrfs_by_vpc_id,
            mock_get_device_vrfs,
            mock_assign_vrf_to_device,
            mock_get_device_interfaces,
            mock_assign_vrf_to_interface,
            publish_nats,
        ],
        activity_executor=ThreadPoolExecutor(1),
    ):
        workflow_input = VpcAssignmentInput(
            vpc_id="mock_vpc_id",
            device="mock_device_id_with_vrf",
            port_names=["swp1", "swp2"],
            site="mock_site",
        )
        workflow_id = str(uuid.uuid4())

        handle = await env.client.start_workflow(
            VpcAssignmentWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue=task_queue_name,
            run_timeout=timedelta(seconds=30),
        )

        result = await handle.result()
        assert result.vrf_assigned is False
        assert result.vrf.vrf_id == "mock_namespace1"
        assert result.vrf.vrf_name == "SpXTenant60004"
        assert set(result.assigned_ports) == {"swp2"}


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.ngc.activities.nats.NatsProducer", autospec=True)
@patch("nv_config_manager.temporal.common.mixins.stage.workflow.time", return_value=float(0))
async def test_vpc_assignment_workflow_vrf_not_found(_mock_time, _mock_nats_client, env):
    """Test VPC assignment when VRF doesn't exist in Nautobot."""
    from nv_config_manager.temporal.ngc.activities.nats import publish_nats

    _mock_state["vrf_exists"] = False
    _mock_state["interfaces_with_vrf"] = []

    task_queue_name = str(uuid.uuid4())
    async with Worker(
        env.client,
        task_queue=task_queue_name,
        workflows=[VpcAssignmentWorkflow],
        activities=[
            mock_get_network_device,
            mock_get_vrfs_by_vpc_id,
            mock_get_device_vrfs,
            mock_assign_vrf_to_device,
            mock_get_device_interfaces,
            mock_assign_vrf_to_interface,
            publish_nats,
        ],
        activity_executor=ThreadPoolExecutor(1),
    ):
        workflow_input = VpcAssignmentInput(
            vpc_id="mock_vpc_id",
            device="mock_device_id",
            port_names=["swp1", "swp2"],
            site="mock_site",
        )
        workflow_id = str(uuid.uuid4())

        handle = await env.client.start_workflow(
            VpcAssignmentWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue=task_queue_name,
        )
        stages = await handle.query("stages")
        get_device_vrf_stage = next((s for s in stages if s["name"] == "get_device_and_vrf"), None)
        while get_device_vrf_stage["state"] != "FAILED":
            await asyncio.sleep(0.1)
            stages = await handle.query("stages")
            get_device_vrf_stage = next(
                (s for s in stages if s["name"] == "get_device_and_vrf"), None
            )

        assert get_device_vrf_stage is not None
        assert get_device_vrf_stage["state"] == "FAILED"

        if get_device_vrf_stage.get("traceback"):
            assert "No VRF found for VPC ID mock_vpc_id" in get_device_vrf_stage["traceback"]


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.ngc.activities.nats.NatsProducer", autospec=True)
@patch("nv_config_manager.temporal.common.mixins.stage.workflow.time", return_value=float(0))
async def test_vpc_assignment_workflow_interface_not_found(_mock_time, _mock_nats_client, env):
    """Test VPC assignment when one of the interfaces doesn't exist on device."""
    from nv_config_manager.temporal.ngc.activities.nats import publish_nats

    _mock_state["vrf_exists"] = True
    _mock_state["interfaces_with_vrf"] = []

    task_queue_name = str(uuid.uuid4())
    async with Worker(
        env.client,
        task_queue=task_queue_name,
        workflows=[VpcAssignmentWorkflow],
        activities=[
            mock_get_network_device,
            mock_get_vrfs_by_vpc_id,
            mock_get_device_vrfs,
            mock_assign_vrf_to_device,
            mock_get_device_interfaces,
            mock_assign_vrf_to_interface,
            publish_nats,
        ],
        activity_executor=ThreadPoolExecutor(1),
    ):
        workflow_input = VpcAssignmentInput(
            vpc_id="mock_vpc_id",
            device="mock_device_id",
            port_names=["swp1", "swp99"],
            site="mock_site",
        )
        workflow_id = str(uuid.uuid4())

        handle = await env.client.start_workflow(
            VpcAssignmentWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue=task_queue_name,
            run_timeout=timedelta(seconds=5),
        )

        with pytest.raises(Exception) as exc_info:
            await handle.result()

        error_msg = (
            str(exc_info.value.cause) if hasattr(exc_info.value, "cause") else str(exc_info.value)
        )
        assert (
            "Workflow timed out" in error_msg
            or "timed out" in error_msg.lower()
            or "Interfaces not found" in error_msg
            or ("Stage" in error_msg and "failed" in error_msg.lower())
        )

        stages = await handle.query("stages")

        assign_ports_stage = next((s for s in stages if s["name"] == "assign_vrf_to_ports"), None)
        assert assign_ports_stage is not None
        assert assign_ports_stage["state"] == "FAILED"

        if assign_ports_stage.get("traceback"):
            assert "Interfaces not found on device" in assign_ports_stage["traceback"]
            assert "swp99" in assign_ports_stage["traceback"]
