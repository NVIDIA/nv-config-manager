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
from typing import Any, cast
from unittest.mock import AsyncMock, patch

import pytest
from pydantic import ValidationError
from temporalio import activity, workflow
from temporalio.exceptions import ApplicationError
from temporalio.worker import Worker

from nv_config_manager.temporal.common.mixins.device import InterfaceData, NetworkDeviceData
from nv_config_manager.temporal.ngc.activities.deploy import (
    WaitForTenantRenderInput,
    WaitForTenantRenderOutput,
)
from nv_config_manager.temporal.ngc.activities.nats import publish_nats
from nv_config_manager.temporal.ngc.activities.nautobot import (
    AssignVrfToDeviceInput,
    AssignVrfToInterfaceInput,
    CheckRecordedConfigDriftInput,
    DeviceVrfInfo,
    GetDeviceInterfacesInput,
    GetDeviceInterfacesOutput,
    GetDeviceVrfsInput,
    GetDeviceVrfsOutput,
    GetNetworkDeviceInput,
    GetNetworkDeviceOutput,
    QueryVRFByVPCInput,
    ReconcileSpXOverlayAssignmentsInput,
    ReconcileSpXOverlayAssignmentsOutput,
    Vrf,
)
from nv_config_manager.temporal.ngc.activities.render import (
    ExecuteRenderInput,
    ExecuteRenderOutput,
)
from nv_config_manager.temporal.ngc.workflows.deploy import TenantDeployInput
from nv_config_manager.temporal.ngc.workflows.spx_overlay import (
    SpXOverlayAssignmentInput,
    SpXOverlayAssignmentWorkflow,
    SpXOverlayTenantChangeInput,
    SpXOverlayTenantChangeWorkflow,
)


def make_test_vrf(namespace: str) -> dict[str, Any]:
    return {
        "id": namespace,
        "name": "SpXTenant60004",
        "rd": "*:60004",
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
    "reconcile_calls": 0,
    "recorded_config_drift": False,
}


@activity.defn(name="get_vrfs_by_overlay_id")
async def mock_get_vrfs_by_overlay_id(
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
        InterfaceData(
            id="interface3_id",
            name="swp3",
            host="mock_device",
            mac_address="00:00:00:00:00:03",
            vrf_id="mock_namespace1" if "swp3" in interfaces_with_vrf else None,
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


@activity.defn(name="reconcile_spx_overlay_assignments")
async def mock_reconcile_spx_overlay_assignments(
    activity_input: ReconcileSpXOverlayAssignmentsInput,
) -> ReconcileSpXOverlayAssignmentsOutput:
    """Mock reconciliation of overlay-plugin assignments."""
    _mock_state["reconcile_calls"] = int(_mock_state["reconcile_calls"]) + 1
    return ReconcileSpXOverlayAssignmentsOutput(
        created=1 + len(activity_input.interface_ids),
        removed=0,
    )


@activity.defn(name="check_recorded_config_drift")
async def mock_check_recorded_config_drift(
    _activity_input: CheckRecordedConfigDriftInput,
) -> bool:
    """Mock pending deployment check."""
    return bool(_mock_state["recorded_config_drift"])


@activity.defn(name="execute_render")
async def mock_execute_render(_activity_input: ExecuteRenderInput) -> ExecuteRenderOutput:
    """Model the forced render losing a race with the Nautobot render consumer."""
    return ExecuteRenderOutput(
        updated_files=[],
        snapshot_files=[
            {"filename": "tenant.yaml", "commit": "7"},
            {"filename": "startup.yaml", "commit": "11"},
        ],
    )


@activity.defn(name="wait_for_tenant_render")
async def mock_wait_for_tenant_render(
    activity_input: WaitForTenantRenderInput,
) -> WaitForTenantRenderOutput:
    """Return the tenant version immediately."""
    return WaitForTenantRenderOutput(config_id=activity_input.config_id)


@pytest.mark.parametrize(
    "commit_ids",
    [
        {"tenant_config_commit_id": "7"},
        {"intended_config_commit_id": "11"},
    ],
)
@pytest.mark.asyncio
async def test_spx_deploy_stage_rejects_partial_render_commit_pair(commit_ids):
    device_output = await mock_get_network_device(GetNetworkDeviceInput(device_id="device-1"))
    with patch(
        "nv_config_manager.temporal.common.mixins.stage.workflow.time",
        return_value=float(0),
    ):
        workflow_instance = SpXOverlayTenantChangeWorkflow()
    stage_input = workflow_instance.DeployStageInput(
        device=device_output.device,
        **commit_ids,
    )

    with pytest.raises(ApplicationError, match="must both be supplied or both be omitted"):
        await SpXOverlayTenantChangeWorkflow.deploy_stage.__wrapped__(
            workflow_instance,
            stage_input,
        )


@pytest.mark.asyncio
async def test_spx_deploy_stage_normalizes_child_workflow_errors():
    """Convert tenant deploy child failures to the workflow's ApplicationError shape."""
    device_output = await mock_get_network_device(GetNetworkDeviceInput(device_id="device-1"))
    with patch(
        "nv_config_manager.temporal.common.mixins.stage.workflow.time",
        return_value=float(0),
    ):
        workflow_instance = SpXOverlayTenantChangeWorkflow()
    stage_input = workflow_instance.DeployStageInput(device=device_output.device)

    with (
        patch(
            "nv_config_manager.temporal.ngc.workflows.spx_overlay.workflow.start_child_workflow",
            new=AsyncMock(side_effect=RuntimeError("tenant deploy failed")),
        ),
        pytest.raises(ApplicationError, match="tenant deploy failed"),
    ):
        await SpXOverlayTenantChangeWorkflow.deploy_stage.__wrapped__(
            workflow_instance,
            stage_input,
        )


@workflow.defn(name="TenantDeployWorkflow", sandboxed=False)
class MockTenantDeployWorkflow:
    """Mock tenant deploy child workflow."""

    @workflow.run
    async def run(self, _workflow_input: TenantDeployInput) -> bool:
        """Mock tenant deploy run."""
        return True


def test_spx_render_stage_output_requires_snapshot_commit_ids():
    """Do not allow the SpX workflow to fall back to an unpinned deploy."""
    with pytest.raises(ValidationError):
        SpXOverlayTenantChangeWorkflow.RenderStageOutput(
            tenant_config_commit_id=None,
            intended_config_commit_id="11",
        )


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.ngc.activities.nats.NatsProducer", autospec=True)
@patch("nv_config_manager.temporal.common.mixins.stage.workflow.time", return_value=float(0))
async def test_spx_overlay_assignment_workflow_vrf_not_assigned(_mock_time, _mock_nats_client, env):
    """Test VPC assignment when VRF is not already assigned to device."""

    _mock_state["vrf_exists"] = True
    _mock_state["interfaces_with_vrf"] = []

    task_queue_name = str(uuid.uuid4())
    async with Worker(
        env.client,
        task_queue=task_queue_name,
        workflows=[SpXOverlayAssignmentWorkflow],
        activities=[
            mock_get_network_device,
            mock_get_vrfs_by_overlay_id,
            mock_get_device_vrfs,
            mock_assign_vrf_to_device,
            mock_get_device_interfaces,
            mock_assign_vrf_to_interface,
            mock_reconcile_spx_overlay_assignments,
            publish_nats,
        ],
        activity_executor=ThreadPoolExecutor(1),
    ):
        workflow_input = SpXOverlayAssignmentInput(
            overlay_id="mock_overlay_id",
            device="mock_device_id",
            port_names=["swp1", "swp2"],
            site="mock_site",
        )
        workflow_id = str(uuid.uuid4())

        handle = await env.client.start_workflow(
            SpXOverlayAssignmentWorkflow.run,
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
async def test_spx_overlay_assignment_workflow_vrf_already_assigned(
    _mock_time, _mock_nats_client, env
):
    """Test VPC assignment when VRF is already assigned to device."""

    _mock_state["vrf_exists"] = True
    _mock_state["interfaces_with_vrf"] = ["swp1"]

    task_queue_name = str(uuid.uuid4())
    async with Worker(
        env.client,
        task_queue=task_queue_name,
        workflows=[SpXOverlayAssignmentWorkflow],
        activities=[
            mock_get_network_device,
            mock_get_vrfs_by_overlay_id,
            mock_get_device_vrfs,
            mock_assign_vrf_to_device,
            mock_get_device_interfaces,
            mock_assign_vrf_to_interface,
            mock_reconcile_spx_overlay_assignments,
            publish_nats,
        ],
        activity_executor=ThreadPoolExecutor(1),
    ):
        workflow_input = SpXOverlayAssignmentInput(
            overlay_id="mock_overlay_id",
            device="mock_device_id_with_vrf",
            port_names=["swp1", "swp2"],
            site="mock_site",
        )
        workflow_id = str(uuid.uuid4())

        handle = await env.client.start_workflow(
            SpXOverlayAssignmentWorkflow.run,
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
async def test_spx_overlay_tenant_change_is_noop_when_already_assigned(
    _mock_time, _mock_nats_client, env
):
    """A repeated tenant change completes without rendering or deploying again."""

    _mock_state["vrf_exists"] = True
    _mock_state["interfaces_with_vrf"] = ["swp1", "swp2"]
    _mock_state["reconcile_calls"] = 0
    _mock_state["recorded_config_drift"] = False

    task_queue_name = str(uuid.uuid4())
    async with Worker(
        env.client,
        task_queue=task_queue_name,
        workflows=[SpXOverlayAssignmentWorkflow, SpXOverlayTenantChangeWorkflow],
        activities=[
            mock_get_network_device,
            mock_get_vrfs_by_overlay_id,
            mock_get_device_vrfs,
            mock_assign_vrf_to_device,
            mock_get_device_interfaces,
            mock_assign_vrf_to_interface,
            mock_reconcile_spx_overlay_assignments,
            mock_check_recorded_config_drift,
            publish_nats,
        ],
        activity_executor=ThreadPoolExecutor(1),
    ):
        handle = await env.client.start_workflow(
            SpXOverlayTenantChangeWorkflow.run,
            SpXOverlayTenantChangeInput(
                overlay_id="mock_overlay_id",
                device_id="mock_device_id_with_vrf",
                port_names=["swp1", "swp2"],
                site="mock_site",
            ),
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
            run_timeout=timedelta(seconds=30),
        )

        result = await handle.result()

        assert result.assigned_ports == []
        assert result.vrf_assigned is False
        assert result.vrf is None
        assert result.device_deployed is None
        assert _mock_state["reconcile_calls"] == 1

        stages = {stage["name"]: stage for stage in await handle.query("stages")}
        assert stages["render_tenant_config"]["state"] == "UNREACHABLE"
        assert stages["wait_for_render"]["state"] == "UNREACHABLE"
        assert stages["deploy"]["state"] == "UNREACHABLE"


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.ngc.activities.nats.NatsProducer", autospec=True)
@patch("nv_config_manager.temporal.common.mixins.stage.workflow.time", return_value=float(0))
async def test_spx_overlay_tenant_change_uses_current_versions_after_render_race(
    _mock_time, _mock_nats_client, env
):
    """Use versions committed by the Nautobot consumer before the forced render."""

    _mock_state["vrf_exists"] = True
    _mock_state["interfaces_with_vrf"] = ["swp1", "swp2"]
    _mock_state["reconcile_calls"] = 0

    task_queue_name = str(uuid.uuid4())
    async with Worker(
        env.client,
        task_queue=task_queue_name,
        workflows=[
            SpXOverlayAssignmentWorkflow,
            SpXOverlayTenantChangeWorkflow,
            MockTenantDeployWorkflow,
        ],
        activities=[
            mock_get_network_device,
            mock_get_vrfs_by_overlay_id,
            mock_get_device_vrfs,
            mock_assign_vrf_to_device,
            mock_get_device_interfaces,
            mock_assign_vrf_to_interface,
            mock_reconcile_spx_overlay_assignments,
            mock_execute_render,
            mock_wait_for_tenant_render,
            publish_nats,
        ],
        activity_executor=ThreadPoolExecutor(1),
    ):
        handle = await env.client.start_workflow(
            SpXOverlayTenantChangeWorkflow.run,
            SpXOverlayTenantChangeInput(
                overlay_id="mock_overlay_id",
                device_id="mock_device_id_with_vrf",
                port_names=["swp1", "swp2", "swp3"],
                site="mock_site",
            ),
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
            run_timeout=timedelta(seconds=30),
        )

        result = await handle.result()

        assert result.assigned_ports == ["swp3"]
        assert result.device_deployed == "mock_device_id_with_vrf"

        stages = {stage["name"]: stage for stage in await handle.query("stages")}
        assert stages["render_tenant_config"]["state"] == "COMPLETE"
        assert stages["render_tenant_config"]["output"]["tenant_config_commit_id"] == "7"
        assert stages["render_tenant_config"]["output"]["intended_config_commit_id"] == "11"
        assert (
            stages["wait_for_render"]["input"]["config_id"]
            == stages["render_tenant_config"]["output"]["tenant_config_commit_id"]
        )
        assert stages["deploy"]["state"] == "COMPLETE"
        assert stages["deploy"]["input"]["tenant_config_commit_id"] == "7"
        assert stages["deploy"]["input"]["intended_config_commit_id"] == "11"
        assignment_children = stages["assign_spx_overlay"]["child_workflows"]
        deploy_children = stages["deploy"]["child_workflows"]
        assert len(assignment_children) == 1
        assert len(deploy_children) == 1
        assert assignment_children == [f"{handle.id}-assign-spx-overlay"]
        assert handle.id not in assignment_children
        assert handle.id not in deploy_children
        assert assignment_children != deploy_children


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.ngc.activities.nats.NatsProducer", autospec=True)
@patch("nv_config_manager.temporal.common.mixins.stage.workflow.time", return_value=float(0))
async def test_spx_overlay_tenant_change_retries_deploy_when_already_assigned_but_pending(
    _mock_time, _mock_nats_client, env
):
    """A rerun deploys if Nautobot assignment is complete but deployment is still pending."""

    _mock_state["vrf_exists"] = True
    _mock_state["interfaces_with_vrf"] = ["swp1", "swp2"]
    _mock_state["reconcile_calls"] = 0
    _mock_state["recorded_config_drift"] = True

    task_queue_name = str(uuid.uuid4())
    async with Worker(
        env.client,
        task_queue=task_queue_name,
        workflows=[
            SpXOverlayAssignmentWorkflow,
            SpXOverlayTenantChangeWorkflow,
            MockTenantDeployWorkflow,
        ],
        activities=[
            mock_get_network_device,
            mock_get_vrfs_by_overlay_id,
            mock_get_device_vrfs,
            mock_assign_vrf_to_device,
            mock_get_device_interfaces,
            mock_assign_vrf_to_interface,
            mock_reconcile_spx_overlay_assignments,
            mock_check_recorded_config_drift,
            publish_nats,
        ],
        activity_executor=ThreadPoolExecutor(1),
    ):
        handle = await env.client.start_workflow(
            SpXOverlayTenantChangeWorkflow.run,
            SpXOverlayTenantChangeInput(
                overlay_id="mock_overlay_id",
                device_id="mock_device_id_with_vrf",
                port_names=["swp1", "swp2"],
                site="mock_site",
            ),
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
            run_timeout=timedelta(seconds=30),
        )

        result = await handle.result()

        assert result.assigned_ports == []
        assert result.vrf_assigned is False
        assert result.device_deployed == "mock_device_id_with_vrf"

        stages = {stage["name"]: stage for stage in await handle.query("stages")}
        assert stages["determine_deployment_action"]["state"] == "COMPLETE"
        assert stages["render_tenant_config"]["state"] == "UNREACHABLE"
        assert stages["wait_for_render"]["state"] == "UNREACHABLE"
        assert stages["deploy"]["state"] == "COMPLETE"
        assert stages["deploy"]["input"]["tenant_config_commit_id"] is None
        assert stages["deploy"]["input"]["intended_config_commit_id"] is None


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.ngc.activities.nats.NatsProducer", autospec=True)
@patch("nv_config_manager.temporal.common.mixins.stage.workflow.time", return_value=float(0))
async def test_spx_overlay_assignment_workflow_vrf_not_found(_mock_time, _mock_nats_client, env):
    """Test VPC assignment when VRF doesn't exist in Nautobot."""

    _mock_state["vrf_exists"] = False
    _mock_state["interfaces_with_vrf"] = []

    task_queue_name = str(uuid.uuid4())
    async with Worker(
        env.client,
        task_queue=task_queue_name,
        workflows=[SpXOverlayAssignmentWorkflow],
        activities=[
            mock_get_network_device,
            mock_get_vrfs_by_overlay_id,
            mock_get_device_vrfs,
            mock_assign_vrf_to_device,
            mock_get_device_interfaces,
            mock_assign_vrf_to_interface,
            mock_reconcile_spx_overlay_assignments,
            publish_nats,
        ],
        activity_executor=ThreadPoolExecutor(1),
    ):
        workflow_input = SpXOverlayAssignmentInput(
            overlay_id="mock_overlay_id",
            device="mock_device_id",
            port_names=["swp1", "swp2"],
            site="mock_site",
        )
        workflow_id = str(uuid.uuid4())

        handle = await env.client.start_workflow(
            SpXOverlayAssignmentWorkflow.run,
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
            assert (
                "No VRF found for Overlay ID mock_overlay_id" in get_device_vrf_stage["traceback"]
            )


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.ngc.activities.nats.NatsProducer", autospec=True)
@patch("nv_config_manager.temporal.common.mixins.stage.workflow.time", return_value=float(0))
async def test_spx_overlay_assignment_workflow_interface_not_found(
    _mock_time, _mock_nats_client, env
):
    """Test VPC assignment when one of the interfaces doesn't exist on device."""

    _mock_state["vrf_exists"] = True
    _mock_state["interfaces_with_vrf"] = []

    task_queue_name = str(uuid.uuid4())
    async with Worker(
        env.client,
        task_queue=task_queue_name,
        workflows=[SpXOverlayAssignmentWorkflow],
        activities=[
            mock_get_network_device,
            mock_get_vrfs_by_overlay_id,
            mock_get_device_vrfs,
            mock_assign_vrf_to_device,
            mock_get_device_interfaces,
            mock_assign_vrf_to_interface,
            mock_reconcile_spx_overlay_assignments,
            publish_nats,
        ],
        activity_executor=ThreadPoolExecutor(1),
    ):
        workflow_input = SpXOverlayAssignmentInput(
            overlay_id="mock_overlay_id",
            device="mock_device_id",
            port_names=["swp1", "swp99"],
            site="mock_site",
        )
        workflow_id = str(uuid.uuid4())

        handle = await env.client.start_workflow(
            SpXOverlayAssignmentWorkflow.run,
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
