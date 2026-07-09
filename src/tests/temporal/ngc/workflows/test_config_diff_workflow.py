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
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from typing import Any
from unittest.mock import patch

import pytest
from temporalio import activity
from temporalio.client import Client, WorkflowHandle
from temporalio.worker import Worker

from nv_config_manager.temporal.common.mixins.device import NetworkDeviceData, Platform
from nv_config_manager.temporal.ngc.activities.deploy import perform_candidate_diff
from nv_config_manager.temporal.ngc.activities.nats import publish_nats
from nv_config_manager.temporal.ngc.activities.nautobot import (
    GetNetworkDeviceInput,
    GetNetworkDeviceOutput,
)
from nv_config_manager.temporal.ngc.workflows.config_diff import (
    ConfigDiffInput,
    ConfigDiffWorkflow,
)


@activity.defn(name="get_network_device")
async def mock_get_network_device(
    activity_input: GetNetworkDeviceInput,
) -> GetNetworkDeviceOutput:
    return GetNetworkDeviceOutput(
        device=NetworkDeviceData(
            id=activity_input.device_id,
            name="mock_device",
            role="mock_role",
            platform=Platform.CUMULUS_LINUX,
            device_type="sn4000",
            site="SITEA",
            primary_ip4="10.0.0.1",
            primary_ip6=None,
            render_enabled=False,
            deploy_enabled=False,
            backup_enabled=False,
            ztp_enabled=False,
            config_context=None,
        )
    )


@activity.defn(name="load_intended_configuration")
async def mock_load_intended_configuration(
    _device_data: NetworkDeviceData,
) -> tuple[str, str, str]:
    return (
        "mock intended config",
        "mock_commit_id",
        "https://config-manager.example.com/device/mock_device_uuid/startup.yaml?file_type=intended&commit=mock_commit_id",
    )


def _worker(client: Client, task_queue_name: str) -> Worker:
    return Worker(
        client,
        task_queue=task_queue_name,
        workflows=[ConfigDiffWorkflow],
        activities=[
            mock_get_network_device,
            mock_load_intended_configuration,
            perform_candidate_diff,
            publish_nats,
        ],
        activity_executor=ThreadPoolExecutor(5),
    )


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.client.device.CumulusConnection")
@patch("nv_config_manager.temporal.ngc.activities.nats.NatsProducer", autospec=True)
@patch("nv_config_manager.temporal.common.mixins.stage.workflow.time", return_value=float(0))
async def test_execute_workflow_reports_diff(
    _time: Any,
    _mock_nats_client: Any,
    mock_cumulus_connection: Any,
    env: Any,
) -> None:
    """The workflow returns the live diff and never applies it."""
    task_queue_name = str(uuid.uuid4())
    async with _worker(env.client, task_queue_name):
        mock_cumulus_connection.return_value.perform_candidate_diff.return_value = "mock_diff"

        handle: WorkflowHandle = await env.client.start_workflow(
            ConfigDiffWorkflow.run,
            ConfigDiffInput(device_id="mock_device_uuid"),
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
            run_timeout=timedelta(minutes=5),
        )

        result = await handle.result()
        assert result == "mock_diff"

        stages = await handle.query("stages")
        # Read-only: only load + diff stages exist -- no apply, no backup.
        assert [stage["name"] for stage in stages] == [
            "load_intended_configuration",
            "perform_configuration_diff",
        ]
        assert all(stage["state"] == "COMPLETE" for stage in stages)
        assert all(stage["requires_approval"] is False for stage in stages)

        diff_stage = next(s for s in stages if s["name"] == "perform_configuration_diff")
        assert diff_stage["output"]["diff"] == "mock_diff"
        assert diff_stage["output"]["has_diff"] is True
        assert diff_stage["output"]["display"] == "Configuration Diff\n```\nmock_diff\n```"

        # The device configuration must never be modified by this workflow.
        mock_cumulus_connection.return_value.commit_candidate_config.assert_not_called()


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.client.device.CumulusConnection")
@patch("nv_config_manager.temporal.ngc.activities.nats.NatsProducer", autospec=True)
@patch("nv_config_manager.temporal.common.mixins.stage.workflow.time", return_value=float(0))
async def test_execute_workflow_no_diff(
    _time: Any,
    _mock_nats_client: Any,
    mock_cumulus_connection: Any,
    env: Any,
) -> None:
    """An empty diff reports no drift and returns an empty string."""
    task_queue_name = str(uuid.uuid4())
    async with _worker(env.client, task_queue_name):
        mock_cumulus_connection.return_value.perform_candidate_diff.return_value = ""

        handle: WorkflowHandle = await env.client.start_workflow(
            ConfigDiffWorkflow.run,
            ConfigDiffInput(device_id="mock_device_uuid"),
            id=str(uuid.uuid4()),
            task_queue=task_queue_name,
            run_timeout=timedelta(minutes=5),
        )

        result = await handle.result()
        assert result == ""

        stages = await handle.query("stages")
        diff_stage = next(s for s in stages if s["name"] == "perform_configuration_diff")
        assert diff_stage["output"]["has_diff"] is False
        assert diff_stage["output"]["diff"] == ""
        assert "No diff" in diff_stage["output"]["display"]
        mock_cumulus_connection.return_value.commit_candidate_config.assert_not_called()
