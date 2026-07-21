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
"""Network Device Reprovision Workflow Definition."""

from datetime import timedelta

from pydantic import BaseModel, Field
from temporalio import workflow
from temporalio.common import RetryPolicy
from temporalio.exceptions import ActivityError, ApplicationError

from nv_config_manager.temporal.common.decorators.workflow import run_nv_config_manager_workflow
from nv_config_manager.temporal.common.mixins.metadata import WorkflowMetadataMixin
from nv_config_manager.temporal.common.mixins.stage import (
    StageInput,
    StageMixin,
    StageOutput,
    stage_executor,
)

with workflow.unsafe.imports_passed_through():
    from nv_config_manager.temporal.common.mixins.archive import ArchiveMixin
    from nv_config_manager.temporal.common.mixins.device import DeviceMixin
    from nv_config_manager.temporal.ngc.activities.config import (
        build_workflow_url,
        get_ui_base_url,
    )
    from nv_config_manager.temporal.ngc.activities.deploy import (
        DiffActivityInput,
        load_intended_configuration,
        perform_candidate_diff,
    )
    from nv_config_manager.temporal.ngc.activities.nautobot import (
        GetNetworkDeviceInput,
        get_network_device,
    )
    from nv_config_manager.temporal.ngc.activities.os import (
        ExecuteZTPInput,
        PollZTPStatusInput,
        execute_ztp,
        poll_ztp_status,
    )
    from nv_config_manager.temporal.ngc.workflows.backup import (
        BackupInput,
        BackupWorkflow,
        TriggerEnum,
    )

DEFAULT_ACTIVITY_RETRY_POLICY = RetryPolicy(
    maximum_attempts=3,
    non_retryable_error_types=["ConfigSyntaxException", "FirmwareUpgradeException"],
)
VALIDATE_INTENDED_CONFIG_PATCH_ID = "reprovision-validate-intended-config-v1"


class ReprovisionInput(BaseModel):
    """Reprovision Workflow Input Definition."""

    device_id: str = Field(description="Identifier of the network device to reprovision.")


@workflow.defn
class ReprovisionWorkflow(WorkflowMetadataMixin, StageMixin, DeviceMixin, ArchiveMixin):
    """Network device reprovisioning workflow with ZTP."""

    # Workflow metadata
    workflow_name = "Reprovision"
    workflow_description = "Reprovision network device using ZTP and perform post-provision backup"
    workflow_input_class = ReprovisionInput
    workflow_api_endpoint = "/ngc/reprovision"
    workflow_namespace = "ngc"

    def __init__(self) -> None:
        """Initialize workflow."""
        StageMixin.__init__(self)
        self.define_stage(
            name="execute_ztp",
            description="Execute ZTP and wait for completion.",
            requires_approval=False,
            depends_on=[],
        )

        self.define_stage(
            name="perform_backup",
            description="Run the backup workflow for the device.",
            requires_approval=False,
            depends_on=["execute_ztp"],
        )

    class ExecuteZTPStageInput(StageInput):
        """Execute ZTP Stage Input."""

        device_id: str

    class ExecuteZTPStageOutput(StageOutput):
        """Execute ZTP Stage Output."""

    @stage_executor("execute_ztp")
    async def execute_ztp_stage(self, stage_input: ExecuteZTPStageInput) -> ExecuteZTPStageOutput:
        """Execute ZTP and wait for completion."""
        # Get device data
        result = await workflow.execute_activity(
            get_network_device,
            GetNetworkDeviceInput(device_id=stage_input.device_id),
            start_to_close_timeout=timedelta(minutes=1),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )
        # Add device search attributes the first time we pull
        # them from nautobot
        DeviceMixin.attach_device_search_attributes(result.device)

        device_data = result.device

        # Validate that the rendered config exists and can be loaded as a candidate
        # before factory reset makes the current configuration unavailable.
        if workflow.patched(VALIDATE_INTENDED_CONFIG_PATCH_ID):
            intended_config, _commit_id, intended_config_url = await workflow.execute_activity(
                load_intended_configuration,
                device_data,
                start_to_close_timeout=timedelta(minutes=1),
                retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
            )
            try:
                await workflow.execute_activity(
                    perform_candidate_diff,
                    DiffActivityInput(device_data=device_data, configuration=intended_config),
                    start_to_close_timeout=timedelta(minutes=1),
                    retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
                )
            except ActivityError as exc:
                config_syntax_error = (
                    isinstance(exc.cause, ApplicationError)
                    and (exc.cause.type or exc.cause.__class__.__name__) == "ConfigSyntaxException"
                )
                if not config_syntax_error:
                    raise

                self.set_stage_output(
                    "execute_ztp",
                    ReprovisionWorkflow.ExecuteZTPStageOutput(
                        display=(
                            "### Invalid intended configuration\n\n"
                            f"The intended configuration for **{device_data.name}** is invalid "
                            "and could not be loaded as a candidate. No factory reset was "
                            "requested.\n\n"
                            "Check the intended configuration "
                            f"[here]({intended_config_url}). Once it is fixed this stage can be "
                            "retried."
                        )
                    ),
                )
                raise ApplicationError(
                    "The intended configuration is invalid. Fix the errors and retry this stage."
                ) from exc

        # Trigger ZTP through factory reset
        ztp_execute_result = await workflow.execute_activity(
            execute_ztp,
            ExecuteZTPInput(device_data=device_data),
            start_to_close_timeout=timedelta(minutes=5),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )

        # Poll ZTP status until success (with integrated reboot verification)
        ztp_status_result = await workflow.execute_activity(
            poll_ztp_status,
            PollZTPStatusInput(
                device_data=device_data,
                ztp_execution_timestamp=ztp_execute_result.start_time,  # Verify reboot happened
            ),
            start_to_close_timeout=timedelta(minutes=35),  # 30 min + 5 min buffer
            heartbeat_timeout=timedelta(minutes=3),  # Detect dead activities within 3 minutes
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )
        if not ztp_status_result.success:
            raise ApplicationError(
                "ZTP failed to complete within 30 minutes, check the device logs for details."
            )

        return ReprovisionWorkflow.ExecuteZTPStageOutput(
            display="ZTP completed successfully",
        )

    class BackupStageInput(StageInput):
        """Backup Stage Input."""

        device_id: str

    class BackupStageOutput(StageOutput):
        """Backup Stage Output."""

    @stage_executor("perform_backup")
    async def perform_backup(self, stage_input: BackupStageInput) -> BackupStageOutput:
        """Perform a configuration backup."""
        ui_base_url = ""
        if workflow.patched(VALIDATE_INTENDED_CONFIG_PATCH_ID):
            try:
                ui_base_url = await workflow.execute_activity(
                    get_ui_base_url,
                    start_to_close_timeout=timedelta(seconds=10),
                    retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
                )
            except ActivityError:
                self.logger.warning(
                    "Unable to retrieve the Temporal UI URL; continuing backup without a link."
                )

        backup_input = BackupInput(
            device_id=stage_input.device_id,
            trigger=TriggerEnum.WORKFLOW,
            user="nv-config-manager-temporal",
            user_domain=None,
            workflow_id=workflow.info().workflow_id,
            intended_config_commit_id="",
        )

        backup_handle = await workflow.start_child_workflow(
            BackupWorkflow.run, backup_input, run_timeout=timedelta(minutes=10)
        )
        self.append_child_workflow("perform_backup", backup_handle.id)
        await workflow.wait_condition(backup_handle.done)

        if ui_base_url:
            backup_workflow_url = build_workflow_url(ui_base_url, backup_handle.id)
            display = (
                f"Configuration backup completed via [backup workflow]({backup_workflow_url})."
            )
        else:
            display = f"Configuration backup completed via workflow {backup_handle.id}."

        return ReprovisionWorkflow.BackupStageOutput(
            display=display,
        )

    @run_nv_config_manager_workflow
    async def run(self, workflow_input: ReprovisionInput) -> bool:  # type: ignore[override, ty:invalid-method-override]
        """Execute reprovision workflow."""
        self.set_input(workflow_input)

        # Execute ZTP
        await self.execute_ztp_stage(
            ReprovisionWorkflow.ExecuteZTPStageInput(device_id=workflow_input.device_id)
        )

        # Perform backup
        await self.perform_backup(
            ReprovisionWorkflow.BackupStageInput(device_id=workflow_input.device_id)
        )

        await self.archive_results()
        return True
