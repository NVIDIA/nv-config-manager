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
"""InfiniBand PKey Partition Creation Workflow."""

from datetime import timedelta
from typing import Any

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy

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
    from nv_config_manager.temporal.ngc.activities.ib_nautobot import (
        RecordIBPKeyInNautobotInput,
        RecordIBPKeyInNautobotOutput,
        record_ib_pkey_in_nautobot,
    )
    from nv_config_manager.temporal.ngc.activities.ib_pkey import (
        CreatePKeyInput,
        CreatePKeyOutput,
        ValidatePKeyInput,
        ValidatePKeyOutput,
        VerifyPKeyInput,
        VerifyPKeyOutput,
        create_pkey_on_ufm,
        validate_pkey_available,
        verify_pkey_created,
    )
    from nv_config_manager.temporal.ngc.workflows._ib_pkey_helpers import (
        call_resolve_ib_site_for_host,
    )


DEFAULT_ACTIVITY_RETRY_POLICY = RetryPolicy(
    maximum_attempts=3,
)


class IBPKeyCreationInput(BaseModel):
    """InfiniBand PKey Creation Workflow Input.

    By default, auto-assigns the next available PKey. Pass an explicit
    ``pkey`` value only when a specific partition key is required.

    ``site`` is optional. When omitted, the workflow resolves the device's
    Site-typed Nautobot location from ``host`` and uses that as the UFM
    credential lookup key. Pass ``site`` explicitly to override the
    auto-resolved value (e.g. for API callers that want to skip the
    Nautobot round-trip).
    """

    host: str
    site: str | None = None
    pkey: str | None = None
    ip_over_ib: bool = True
    pkey_min: int = 0x0001
    pkey_max: int = 0x7FFE


class IBPKeyCreationWorkflowOutput(BaseModel):
    """InfiniBand PKey Creation Workflow Output."""

    pkey: str
    auto_assigned: bool
    created: bool
    verified: bool
    pkey_data: dict[str, Any]
    nautobot_pkey_id: str


@workflow.defn
class IBPKeyCreationWorkflow(WorkflowMetadataMixin, StageMixin, ArchiveMixin):
    """Create an InfiniBand PKey partition on UFM for tenant isolation."""

    workflow_name = "InfiniBand PKey Creation"
    workflow_description = "Create an InfiniBand PKey partition on UFM for multi-tenant isolation"
    workflow_input_class = IBPKeyCreationInput
    workflow_api_endpoint = "/ngc/ib_pkey_creation"
    workflow_namespace = "ngc"

    def __init__(self) -> None:
        """Initialize workflow stages."""
        StageMixin.__init__(self)
        self.define_stage(
            name="resolve_context",
            description="Resolve Site from host via Nautobot (skipped when site is provided)",
            requires_approval=False,
            depends_on=[],
        )
        self.define_stage(
            name="validate_pkey",
            description="Validate PKey availability on UFM",
            requires_approval=False,
            depends_on=["resolve_context"],
        )
        self.define_stage(
            name="create_pkey",
            description="Create PKey partition on UFM",
            requires_approval=False,
            depends_on=["validate_pkey"],
        )
        self.define_stage(
            name="verify_pkey",
            description="Verify PKey was propagated by the SM",
            requires_approval=False,
            depends_on=["create_pkey"],
        )
        self.define_stage(
            name="record_nautobot",
            description="Record PKey in Nautobot",
            requires_approval=False,
            depends_on=["verify_pkey"],
        )

    class ResolveContextStageInput(StageInput):
        """Resolve Context Stage Input."""

        host: str
        site_override: str | None

    class ResolveContextStageOutput(StageOutput):
        """Resolve Context Stage Output."""

        effective_site: str | None
        resolved_site: str | None

    @stage_executor("resolve_context")
    async def resolve_context(
        self, stage_input: ResolveContextStageInput
    ) -> ResolveContextStageOutput:
        """Resolve the Site for the host unless the caller supplied one explicitly."""
        if stage_input.site_override:
            return self.ResolveContextStageOutput(
                effective_site=stage_input.site_override,
                resolved_site=None,
                display=f"Using caller-supplied site {stage_input.site_override!r}",
            )

        resolved = await call_resolve_ib_site_for_host(stage_input.host)
        return self.ResolveContextStageOutput(
            effective_site=resolved.location_name,
            resolved_site=resolved.location_name,
            display=f"Resolved site for {stage_input.host} -> {resolved.location_name!r}",
        )

    class ValidatePKeyStageInput(StageInput):
        """Validate PKey Stage Input."""

        host: str
        site: str | None
        pkey: str | None
        pkey_min: int
        pkey_max: int

    class ValidatePKeyStageOutput(StageOutput):
        """Validate PKey Stage Output."""

        pkey: str
        auto_assigned: bool
        existing_pkeys: list[str]

    @stage_executor("validate_pkey")
    async def validate_pkey(self, stage_input: ValidatePKeyStageInput) -> ValidatePKeyStageOutput:
        """Validate that the requested PKey is available on UFM."""
        result: ValidatePKeyOutput = await workflow.execute_activity(
            validate_pkey_available,
            ValidatePKeyInput(
                host=stage_input.host,
                site=stage_input.site,
                pkey=stage_input.pkey,
                pkey_min=stage_input.pkey_min,
                pkey_max=stage_input.pkey_max,
            ),
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )
        return self.ValidatePKeyStageOutput(
            pkey=result.pkey,
            auto_assigned=result.auto_assigned,
            existing_pkeys=result.existing_pkeys,
            display=result.display,
        )

    class CreatePKeyStageInput(StageInput):
        """Create PKey Stage Input."""

        host: str
        site: str | None
        pkey: str
        ip_over_ib: bool

    class CreatePKeyStageOutput(StageOutput):
        """Create PKey Stage Output."""

        pkey: str
        created: bool

    @stage_executor("create_pkey")
    async def create_pkey(self, stage_input: CreatePKeyStageInput) -> CreatePKeyStageOutput:
        """Create the PKey partition on UFM."""
        result: CreatePKeyOutput = await workflow.execute_activity(
            create_pkey_on_ufm,
            CreatePKeyInput(
                host=stage_input.host,
                site=stage_input.site,
                pkey=stage_input.pkey,
                ip_over_ib=stage_input.ip_over_ib,
            ),
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )
        return self.CreatePKeyStageOutput(
            pkey=result.pkey,
            created=result.created,
            display=result.display,
        )

    class VerifyPKeyStageInput(StageInput):
        """Verify PKey Stage Input."""

        host: str
        site: str | None
        pkey: str

    class VerifyPKeyStageOutput(StageOutput):
        """Verify PKey Stage Output."""

        pkey: str
        verified: bool
        pkey_data: dict[str, Any]

    @stage_executor("verify_pkey")
    async def verify_pkey(self, stage_input: VerifyPKeyStageInput) -> VerifyPKeyStageOutput:
        """Verify the PKey was created and propagated by the SM."""
        result: VerifyPKeyOutput = await workflow.execute_activity(
            verify_pkey_created,
            VerifyPKeyInput(
                host=stage_input.host,
                site=stage_input.site,
                pkey=stage_input.pkey,
            ),
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )
        return self.VerifyPKeyStageOutput(
            pkey=result.pkey,
            verified=result.verified,
            pkey_data=result.pkey_data,
            display=result.display,
        )

    class RecordNautobotStageInput(StageInput):
        """Record Nautobot Stage Input."""

        pkey: str

    class RecordNautobotStageOutput(StageOutput):
        """Record Nautobot Stage Output."""

        pkey_id: str
        pkey: str

    @stage_executor("record_nautobot")
    async def record_nautobot(
        self, stage_input: RecordNautobotStageInput
    ) -> RecordNautobotStageOutput:
        """Record the PKey in Nautobot as source of truth."""
        result: RecordIBPKeyInNautobotOutput = await workflow.execute_activity(
            record_ib_pkey_in_nautobot,
            RecordIBPKeyInNautobotInput(pkey=stage_input.pkey),
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )
        return self.RecordNautobotStageOutput(
            pkey_id=result.pkey_id,
            pkey=result.pkey,
            display=result.display,
        )

    @run_nv_config_manager_workflow
    async def run(  # type: ignore[override, ty:invalid-method-override]  # pyright: ignore
        self, workflow_input: IBPKeyCreationInput
    ) -> IBPKeyCreationWorkflowOutput:
        """Execute the IB PKey Creation workflow."""
        self.set_input(workflow_input)

        context_output = await self.resolve_context(
            self.ResolveContextStageInput(
                host=workflow_input.host,
                site_override=workflow_input.site,
            )
        )
        effective_site = context_output.effective_site

        validate_output = await self.validate_pkey(
            self.ValidatePKeyStageInput(
                host=workflow_input.host,
                site=effective_site,
                pkey=workflow_input.pkey,
                pkey_min=workflow_input.pkey_min,
                pkey_max=workflow_input.pkey_max,
            )
        )

        create_output = await self.create_pkey(
            self.CreatePKeyStageInput(
                host=workflow_input.host,
                site=effective_site,
                pkey=validate_output.pkey,
                ip_over_ib=workflow_input.ip_over_ib,
            )
        )

        verify_output = await self.verify_pkey(
            self.VerifyPKeyStageInput(
                host=workflow_input.host,
                site=effective_site,
                pkey=create_output.pkey,
            )
        )

        nautobot_output = await self.record_nautobot(
            self.RecordNautobotStageInput(pkey=verify_output.pkey)
        )

        await self.archive_results()
        return IBPKeyCreationWorkflowOutput(
            pkey=verify_output.pkey,
            auto_assigned=validate_output.auto_assigned,
            created=create_output.created,
            verified=verify_output.verified,
            pkey_data=verify_output.pkey_data,
            nautobot_pkey_id=nautobot_output.pkey_id,
        )
