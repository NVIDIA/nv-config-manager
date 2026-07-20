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
"""Test Reprovision Workflow."""

import asyncio
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from temporalio import activity
from temporalio.client import Client, WorkflowFailureError, WorkflowHandle
from temporalio.common import RetryPolicy
from temporalio.exceptions import ApplicationError
from temporalio.worker import Worker

from nv_config_manager.temporal.common.mixins.device import NetworkDeviceData
from nv_config_manager.temporal.ngc.activities.backup import (
    PersistConfigBackupInput,
    RecordBackupConfigManagerPluginInput,
)
from nv_config_manager.temporal.ngc.activities.deploy import DiffActivityInput
from nv_config_manager.temporal.ngc.activities.nats import PublishNatsInput
from nv_config_manager.temporal.ngc.activities.nautobot import (
    GetNetworkDeviceInput,
    GetNetworkDeviceOutput,
)
from nv_config_manager.temporal.ngc.activities.os import (
    ExecuteZTPInput,
    ExecuteZTPOutput,
    PollZTPStatusInput,
    PollZTPStatusOutput,
)
from nv_config_manager.temporal.ngc.workflows.backup import BackupWorkflow
from nv_config_manager.temporal.ngc.workflows.reprovision import (
    ReprovisionInput,
    ReprovisionWorkflow,
)

# Test-specific retry policy and timeout
TEST_RETRY_POLICY = RetryPolicy(maximum_attempts=1)
TEST_TIMEOUT = timedelta(seconds=10)


@activity.defn(name="get_network_device")
async def mock_get_network_device(
    activity_input: GetNetworkDeviceInput,
) -> GetNetworkDeviceOutput:
    return GetNetworkDeviceOutput(
        device=NetworkDeviceData(
            id=activity_input.device_id,
            name="mock_device",
            role="mock_role",
            platform="cumulus-linux",
            site="SITEA",
            device_type="sn4200",
            primary_ip4="10.0.0.1",
            primary_ip6=None,
        )
    )


@activity.defn(name="execute_ztp")
def mock_execute_ztp(
    activity_input: ExecuteZTPInput,
) -> ExecuteZTPOutput:
    return ExecuteZTPOutput(start_time=datetime.now().isoformat())


@activity.defn(name="poll_ztp_status")
def mock_poll_ztp_status(
    activity_input: PollZTPStatusInput,
) -> PollZTPStatusOutput:
    return PollZTPStatusOutput(success=True)


@activity.defn(name="poll_ztp_status")
def mock_poll_ztp_status_failure(
    activity_input: PollZTPStatusInput,
) -> PollZTPStatusOutput:
    return PollZTPStatusOutput(success=False)


# Backup workflow activity mocks
@activity.defn(name="load_running_configuration")
def mock_load_running_configuration(
    device_data: NetworkDeviceData,
) -> str:
    return "mock running config"


@activity.defn(name="load_intended_configuration")
async def mock_load_intended_configuration(
    device_data: NetworkDeviceData,
) -> tuple[str, str, str]:
    """Mock load intended configuration activity."""
    return (
        "mock intended config",
        "mock_intended_commit_id",
        "https://gitlab.example.com/example-user/intended-network-configs/-/blob/mock_intended_commit_id/SITEA/MOCK_DEVICE/startup.yaml",
    )


@activity.defn(name="perform_candidate_diff")
def mock_perform_candidate_diff(activity_input: DiffActivityInput) -> str:
    """Mock perform candidate diff activity."""
    return ""


@activity.defn(name="persist_config_backup")
async def mock_persist_config_backup(
    activity_input: PersistConfigBackupInput,
) -> str:
    return "mock_commit_id"


@activity.defn(name="record_backup_config_manager_plugin")
async def mock_record_backup_config_manager_plugin(
    activity_input: RecordBackupConfigManagerPluginInput,
) -> tuple[bool, str]:
    markdown = """
[Configuration Backup](https://gitlab.example.com/example-user/deployed-network-configs/-/blob/main/SITEA/MOCK_DEVICE/startup.yaml)
[Latest Commit](https://gitlab.example.com/example-user/deployed-network-configs/-/commit/mock_commit_id)
"""
    return True, f"Persisted new backup configuration:\n{markdown}"


@activity.defn(name="publish_nats")
async def mock_publish_nats(activity_input: PublishNatsInput) -> None:
    """Mock publish nats activity."""
    return None


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.common.mixins.stage.workflow.time", return_value=float(0))
@patch(
    "nv_config_manager.temporal.ngc.workflows.reprovision.DEFAULT_ACTIVITY_RETRY_POLICY",
    return_value=TEST_RETRY_POLICY,
)
@patch("nv_config_manager.temporal.ngc.workflows.reprovision.timedelta", return_value=TEST_TIMEOUT)
async def test_reprovision_workflow(
    mock_timedelta,
    mock_retry_policy,
    mock_time,
    env,
):
    """Test reprovision workflow."""
    task_queue_name = str(uuid.uuid4())
    client: Client = env.client
    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[ReprovisionWorkflow, BackupWorkflow],
        activities=[
            mock_get_network_device,
            mock_execute_ztp,
            mock_poll_ztp_status,
            # Backup workflow activities
            mock_load_running_configuration,
            mock_load_intended_configuration,
            mock_perform_candidate_diff,
            mock_persist_config_backup,
            mock_record_backup_config_manager_plugin,
            mock_publish_nats,
        ],
        activity_executor=ThreadPoolExecutor(5),
    ):
        # Execute workflow
        workflow_input = ReprovisionInput(device_id="test-device")
        workflow_id = str(uuid.uuid4())
        handle: WorkflowHandle = await env.client.start_workflow(
            ReprovisionWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue=task_queue_name,
            run_timeout=timedelta(minutes=1),
        )

        # Wait for workflow to complete
        result = await handle.result()
        assert result is True

        # Now query stages after workflow is complete
        stages = await handle.query("stages")
        assert len(stages) == 2  # execute_ztp and perform_backup stages

        # Verify execute_ztp stage
        execute_ztp_stage = next(s for s in stages if s["name"] == "execute_ztp")
        assert execute_ztp_stage["state"] == "COMPLETE"
        assert execute_ztp_stage["output"]["display"] == "ZTP completed successfully"

        # Verify perform_backup stage
        backup_stage = next(s for s in stages if s["name"] == "perform_backup")
        assert backup_stage["state"] == "COMPLETE"
        assert len(backup_stage["child_workflows"]) == 1

        # Verify backup workflow was executed
        backup_workflow_id = backup_stage["child_workflows"][0]
        backup_handle = client.get_workflow_handle(backup_workflow_id)
        backup_result = await backup_handle.result()
        assert backup_result is True


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.common.mixins.stage.workflow.time", return_value=float(0))
@patch(
    "nv_config_manager.temporal.ngc.workflows.reprovision.DEFAULT_ACTIVITY_RETRY_POLICY",
    new=TEST_RETRY_POLICY,
)
@patch("nv_config_manager.temporal.ngc.workflows.reprovision.timedelta", return_value=TEST_TIMEOUT)
async def test_reprovision_validates_intended_config_before_factory_reset(
    mock_timedelta,
    mock_time,
    env,
):
    """An invalid intended config must fail before factory reset is requested."""
    factory_reset_calls: list[ExecuteZTPInput] = []

    @activity.defn(name="perform_candidate_diff")
    def mock_invalid_candidate_diff(_activity_input: DiffActivityInput) -> str:
        raise ApplicationError("Invalid intended configuration", non_retryable=True)

    @activity.defn(name="execute_ztp")
    def mock_counting_execute_ztp(activity_input: ExecuteZTPInput) -> ExecuteZTPOutput:
        factory_reset_calls.append(activity_input)
        return ExecuteZTPOutput(start_time=datetime.now().isoformat())

    task_queue_name = str(uuid.uuid4())
    async with Worker(
        env.client,
        task_queue=task_queue_name,
        workflows=[ReprovisionWorkflow],
        activities=[
            mock_get_network_device,
            mock_load_intended_configuration,
            mock_invalid_candidate_diff,
            mock_counting_execute_ztp,
            mock_poll_ztp_status,
        ],
        activity_executor=ThreadPoolExecutor(5),
    ):
        handle: WorkflowHandle = await env.client.start_workflow(
            ReprovisionWorkflow.run,
            ReprovisionInput(device_id="test-device"),
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
            run_timeout=timedelta(minutes=1),
        )

        with pytest.raises(WorkflowFailureError):
            await handle.result()

        stages = await handle.query("stages")
        execute_ztp_stage = next(stage for stage in stages if stage["name"] == "execute_ztp")
        backup_stage = next(stage for stage in stages if stage["name"] == "perform_backup")
        assert execute_ztp_stage["state"] == "FAILED"
        assert "Invalid intended configuration" in execute_ztp_stage["traceback"]
        assert backup_stage["state"] == "NOT_STARTED"
        assert factory_reset_calls == []


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.common.mixins.stage.workflow.time", return_value=float(0))
@patch(
    "nv_config_manager.temporal.ngc.workflows.reprovision.DEFAULT_ACTIVITY_RETRY_POLICY",
    return_value=TEST_RETRY_POLICY,
)
@patch("nv_config_manager.temporal.ngc.workflows.reprovision.timedelta", return_value=TEST_TIMEOUT)
async def test_reprovision_workflow_ztp_failure(
    mock_timedelta,
    mock_retry_policy,
    mock_time,
    env,
):
    """Test reprovision workflow with ZTP failure."""

    # Override mock_poll_ztp_status to return False
    @activity.defn(name="poll_ztp_status")
    async def mock_poll_ztp_status_failure(
        activity_input: PollZTPStatusInput,
    ) -> PollZTPStatusOutput:
        return PollZTPStatusOutput(success=False)

    task_queue_name = str(uuid.uuid4())
    client: Client = env.client
    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[ReprovisionWorkflow, BackupWorkflow],
        activities=[
            mock_get_network_device,
            mock_execute_ztp,
            mock_poll_ztp_status_failure,
            # Backup workflow activities
            mock_load_running_configuration,
            mock_load_intended_configuration,
            mock_perform_candidate_diff,
            mock_persist_config_backup,
            mock_record_backup_config_manager_plugin,
            mock_publish_nats,
        ],
        activity_executor=ThreadPoolExecutor(5),
    ):
        # Execute workflow and expect failure
        workflow_input = ReprovisionInput(device_id="test-device")
        workflow_id = str(uuid.uuid4())
        handle: WorkflowHandle = await env.client.start_workflow(
            ReprovisionWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue=task_queue_name,
            run_timeout=timedelta(minutes=2),
        )

        # Wait for the execute_ztp stage to be marked as failed
        stages = await handle.query("stages")
        while stages[0]["state"] != "FAILED":
            await asyncio.sleep(1)
            stages = await handle.query("stages")

        # Verify execute_ztp stage
        execute_ztp_stage = next(s for s in stages if s["name"] == "execute_ztp")
        assert execute_ztp_stage["state"] == "FAILED"
        assert "ZTP failed to complete within 30 minutes" in execute_ztp_stage["traceback"]

        # Verify other stages are defined but UNREACHABLE
        assert len(stages) == 2  # execute_ztp and perform_backup stages
        backup_stage = next(s for s in stages if s["name"] == "perform_backup")
        assert backup_stage["state"] == "NOT_STARTED"


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.common.mixins.stage.workflow.time", return_value=float(0))
@patch(
    "nv_config_manager.temporal.ngc.workflows.reprovision.DEFAULT_ACTIVITY_RETRY_POLICY",
    return_value=TEST_RETRY_POLICY,
)
@patch("nv_config_manager.temporal.ngc.workflows.reprovision.timedelta", return_value=TEST_TIMEOUT)
async def test_reprovision_workflow_ztp_timeout(
    mock_timedelta,
    mock_retry_policy,
    mock_time,
    env,
):
    """Test reprovision workflow with ZTP timeout/failure."""

    task_queue_name = str(uuid.uuid4())
    client: Client = env.client
    async with Worker(
        client,
        task_queue=task_queue_name,
        workflows=[ReprovisionWorkflow, BackupWorkflow],
        activities=[
            mock_get_network_device,
            mock_execute_ztp,
            mock_poll_ztp_status_failure,  # Use failure mock for this test
            # Backup workflow activities
            mock_load_running_configuration,
            mock_load_intended_configuration,
            mock_perform_candidate_diff,
            mock_persist_config_backup,
            mock_record_backup_config_manager_plugin,
            mock_publish_nats,
        ],
        activity_executor=ThreadPoolExecutor(5),
    ):
        # Execute workflow and expect failure
        workflow_input = ReprovisionInput(device_id="test-device")
        workflow_id = str(uuid.uuid4())
        handle: WorkflowHandle = await env.client.start_workflow(
            ReprovisionWorkflow.run,
            workflow_input,
            id=workflow_id,
            task_queue=task_queue_name,
            run_timeout=timedelta(minutes=2),
        )

        # Wait for the execute_ztp stage to be marked as failed
        stages = await handle.query("stages")
        while stages[0]["state"] != "FAILED":
            await asyncio.sleep(1)
            stages = await handle.query("stages")

        # Verify execute_ztp stage
        execute_ztp_stage = next(s for s in stages if s["name"] == "execute_ztp")
        assert execute_ztp_stage["state"] == "FAILED"
        assert (
            "ZTP failed to complete within 30 minutes, check the device logs for details"
            in execute_ztp_stage["traceback"]
        )

        # Verify other stages are defined but UNREACHABLE
        assert len(stages) == 2  # execute_ztp and perform_backup stages
        backup_stage = next(s for s in stages if s["name"] == "perform_backup")
        assert backup_stage["state"] == "NOT_STARTED"
