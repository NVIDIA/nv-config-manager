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
# pylint:disable=too-many-branches
"""Workflow Stage Mixin."""

from __future__ import annotations

import base64
import functools
import gzip
import json
import traceback
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, TypeVar, cast

from py_markdown_table.markdown_table import markdown_table
from pydantic import BaseModel, computed_field, field_serializer, field_validator
from temporalio import workflow
from temporalio.exceptions import (
    ActivityError,
    ApplicationError,
    ChildWorkflowError,
    RetryState,
    TemporalError,
)

from nv_config_manager.common.log import LogCategory, get_logger
from nv_config_manager.temporal.common.mixins.base import BaseMixin
from nv_config_manager.temporal.common.search_attributes import (
    FAILED_STAGE_SEARCH_ATTRIBUTE,
    PENDING_APPROVAL_SEARCH_ATTRIBUTE,
)

F = TypeVar("F", bound=Callable[..., Any])
STAGE_STATE_SEARCH_ATTRIBUTES_PATCH = "stage-state-search-attributes-v1"


def stage_executor(stage_name: str) -> Callable[[F], F]:
    """Stage decorator."""

    def stage_decorator(func: F) -> F:
        @functools.wraps(func)
        async def wrap_stage(
            self: StageMixin, stage_input: StageInput | None = None
        ) -> StageOutput:
            self.set_stage_state(stage_name, StateEnum.IN_PROGRESS)
            current_stage = self.get_stage_by_name(stage_name)
            while True:
                try:
                    result: StageOutput
                    if stage_input:
                        self.set_stage_input(stage_name, stage_input)
                        result = await func(self, stage_input)
                    else:
                        result = await func(self)
                    self.set_stage_output(stage_name, result)
                    self.set_stage_state(stage_name, StateEnum.COMPLETE)
                    return result
                except StageStateFailure as exc:
                    raise exc
                except Exception as exc:  # pylint:disable=broad-exception-caught
                    self.set_stage_state(stage_name, StateEnum.FAILED)
                    current_stage.traceback = traceback.format_exc()

                    if not current_stage.retryable:
                        raise StageRuntimeFailure(
                            f"Stage {stage_name} has failed and is non-retryable: {{exc}}",
                            non_retryable=True,
                        ) from exc

                    if isinstance(exc, ApplicationError):
                        if exc.non_retryable:
                            raise StageRuntimeFailure(
                                f"Stage {stage_name} has failed and cannot be retried: {exc.cause}",
                                non_retryable=True,
                            ) from exc
                    elif isinstance(exc, ActivityError):
                        if exc.retry_state == RetryState.NON_RETRYABLE_FAILURE and not isinstance(
                            exc.cause, TimeoutError
                        ):
                            raise StageRuntimeFailure(
                                f"Activity {exc.activity_type}:{exc.activity_id} in "
                                f"{stage_name} has failed and cannot be retried: "
                                f"{exc.cause}",
                                non_retryable=True,
                            ) from exc
                    elif isinstance(exc, ChildWorkflowError):
                        if exc.retry_state == RetryState.NON_RETRYABLE_FAILURE and not isinstance(
                            exc.cause, TimeoutError
                        ):
                            raise StageRuntimeFailure(
                                f"Child workflow {exc.workflow_type}:{exc.workflow_id} "
                                f"in {stage_name} has failed and cannot be retried: "
                                f"{exc.cause}",
                                non_retryable=True,
                            ) from exc
                    elif not isinstance(exc, TemporalError):
                        # Unexpected exceptions likely indicate a bug in the stage code
                        raise StageRuntimeFailure(
                            f"Unexpected exception during stage runtime: {exc}",
                            non_retryable=True,
                        ) from exc
                    # Wait for retry signal that transitions back to in-progress
                    await workflow.wait_condition(
                        lambda: current_stage.state == StateEnum.IN_PROGRESS
                    )
                    current_stage.retry_count += 1

        return cast(F, wrap_stage)

    return stage_decorator


class StageRuntimeFailure(ApplicationError):
    """Exception thrown during stage runtime."""


class StageStateFailure(ApplicationError):
    """Exception thrown for invalid stage states."""

    def __init__(self, message: str) -> None:
        """Init method."""
        super().__init__(message, non_retryable=True)


class ReviewSignalInput(BaseModel):
    """Input for approve/reject signals."""

    stage_name: str
    user: str


class Review(BaseModel):
    """Individual Review."""

    user: str
    time: float

    @field_serializer("time")
    def serialize_time(self, time: float) -> str:
        """Serialize time as isoformat datetime."""
        # Due to an issue with Temporal, we cannot use
        # datetime objects directly in Pydantic models
        return datetime.fromtimestamp(time, tz=UTC).isoformat()

    @field_validator("time", mode="before")
    @classmethod
    def convert_isoformat(cls, raw: str | float | int) -> float:
        """Convert isoformat string to timestamp."""
        if isinstance(raw, (float, int)):
            return float(raw)
        return datetime.fromisoformat(raw).timestamp()


class StateEnum(StrEnum):
    """Enum of states for a Stage."""

    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    COMPLETE = "COMPLETE"
    UNREACHABLE = "UNREACHABLE"
    FAILED = "FAILED"
    REJECTED = "REJECTED"
    APPROVED = "APPROVED"


class HistoryEntry(BaseModel):
    """State Transition History Entry."""

    state: StateEnum
    time: float

    @field_serializer("time")
    def serialize_time(self, time: float) -> str:
        """Serialize time as isoformat datetime."""
        # Due to an issue with Temporal, we cannot use
        # datetime objects directly in Pydantic models
        return datetime.fromtimestamp(time, tz=UTC).isoformat()

    @field_validator("time", mode="before")
    @classmethod
    def convert_isoformat(cls, raw: str | float | int) -> float:
        """Convert isoformat string to timestamp."""
        if isinstance(raw, (float, int)):
            return float(raw)
        return datetime.fromisoformat(raw).timestamp()


class StageInput(BaseModel):
    """Dataclass to represent Stage Input."""


class StageOutput(BaseModel):
    """Dataclass to represent Stage Output."""

    display: str


class Stage(BaseModel):
    """Workflow Stage Model."""

    _VALID_TRANSITIONS = {  # pylint: disable=invalid-name
        StateEnum.NOT_STARTED: [
            StateEnum.IN_PROGRESS,
            StateEnum.UNREACHABLE,
        ],
        StateEnum.IN_PROGRESS: [
            StateEnum.PENDING_APPROVAL,
            StateEnum.COMPLETE,
            StateEnum.FAILED,
        ],
        StateEnum.PENDING_APPROVAL: [StateEnum.APPROVED, StateEnum.REJECTED],
        StateEnum.APPROVED: [StateEnum.COMPLETE, StateEnum.FAILED],
        StateEnum.REJECTED: [StateEnum.COMPLETE, StateEnum.FAILED],
        StateEnum.FAILED: [StateEnum.IN_PROGRESS],
    }

    name: str
    description: str
    requires_approval: bool
    state: StateEnum
    input: Any = None
    output: Any = None
    depends_on: list[str]
    approvers: list[Review] = []
    rejecters: list[Review] = []
    approval_threshold: int = 0
    state_history: list[HistoryEntry] = []
    retryable: bool
    retry_count: int = 0
    traceback: str | None
    child_workflows: list[str] = []

    @computed_field
    def execution_time(self) -> float | None:
        """Calculate the time spent executing the stage."""
        if self.state not in (StateEnum.COMPLETE, StateEnum.FAILED):
            return None
        # Find latest history entry where state is IN_PROGRESS
        start_entry: HistoryEntry = next(
            entry for entry in reversed(self.state_history) if entry.state == StateEnum.IN_PROGRESS
        )
        start = start_entry.time
        end_entry: HistoryEntry = next(
            entry for entry in reversed(self.state_history) if entry.state == self.state
        )
        end = end_entry.time
        return end - start

    def approve(self, reviewer: str) -> None:
        """Approve the stage."""
        if not self.state == StateEnum.PENDING_APPROVAL:
            raise StageStateFailure(f"Stage {self.name} is not pending approval.")
        self.approvers.append(Review(user=reviewer, time=workflow.time()))
        if len(self.approvers) >= self.approval_threshold:
            self.transition(StateEnum.APPROVED)

    def reject(self, reviewer: str) -> None:
        """Reject the stage."""
        if not self.state == StateEnum.PENDING_APPROVAL:
            raise StageStateFailure(f"Stage {self.name} is not pending approval.")
        self.rejecters.append(Review(user=reviewer, time=workflow.time()))
        self.transition(StateEnum.REJECTED)

    def transition(self, new_state: StateEnum) -> None:
        """Transition the state."""
        if new_state not in self._VALID_TRANSITIONS.get(self.state, []):
            raise StageStateFailure(f"Invalid transition from {self.state} to {new_state}.")
        if (
            new_state == StateEnum.COMPLETE
            and self.requires_approval
            and self.state not in [StateEnum.APPROVED, StateEnum.REJECTED]
        ):
            raise StageStateFailure(
                "A stage that requires approval must be reviewed before completion."
            )

        if self.state == StateEnum.FAILED and new_state == StateEnum.IN_PROGRESS:
            # Clear the previous traceback
            self.traceback = None

        self.state_history.append(HistoryEntry(state=new_state, time=workflow.time()))
        self.state = new_state


class StageMixin(BaseMixin):
    """Stage Mixin Class."""

    logger = get_logger(__name__, category=LogCategory.TEMPORAL_WORKFLOW)

    def __init__(self) -> None:
        """Initialize Workflow with Stages."""
        self._stages: list[Stage] = []
        self._input: BaseModel | None = None

    def set_input(self, workflow_input: BaseModel) -> None:
        """Set the workflow input."""
        self._input = workflow_input

    def stage_exists(self, name: str) -> bool:
        """Return true if a stage has been defined with the given name."""
        try:
            next(stage for stage in self._stages if stage.name == name)
            return True
        except StopIteration:
            return False

    def get_stage_by_name(self, name: str) -> Stage:
        """Get workflow stage by name."""
        try:
            return next(stage for stage in self._stages if stage.name == name)
        except StopIteration as exc:
            raise StageStateFailure(f"No stage defined with name {name}.") from exc

    def define_stage(  # pylint: disable=too-many-arguments
        self,
        name: str,
        description: str,
        requires_approval: bool,
        depends_on: list[str],
        approval_threshold: int = 0,
        retryable: bool = True,
    ) -> None:
        """Define a stage."""
        if self.stage_exists(name):
            raise StageStateFailure(f"Stage already defined with name {name}.")

        if requires_approval and approval_threshold < 1:
            raise StageStateFailure("Approval stages must have a threshold >= 1.")

        for depname in depends_on:
            if not self.stage_exists(depname):
                raise StageStateFailure(f"Stage {depname} in depends_on does not exist.")

        stage = Stage(
            name=name,
            description=description,
            requires_approval=requires_approval,
            state=StateEnum.NOT_STARTED,
            output=None,
            depends_on=depends_on,
            approval_threshold=approval_threshold,
            state_history=[HistoryEntry(state=StateEnum.NOT_STARTED, time=workflow.time())],
            retryable=retryable,
            retry_count=0,
            traceback=None,
            child_workflows=[],
        )
        self._stages.append(stage)

    def append_child_workflow(self, name: str, workflow_id: str) -> None:
        """Append a child workflow to the child workflows associated with this stage."""
        stage = self.get_stage_by_name(name)
        stage.child_workflows.append(workflow_id)

    def set_stage_state(
        self, name: str, state: StateEnum, *, cascade_unreachable: bool = True
    ) -> None:
        """Update stage progress."""
        stage = self.get_stage_by_name(name)
        if stage.state == state:
            return
        # Check dependencies
        if state == StateEnum.IN_PROGRESS:
            for dependency in stage.depends_on:
                depstage = self.get_stage_by_name(dependency)
                if depstage.state not in (StateEnum.COMPLETE, StateEnum.UNREACHABLE):
                    raise StageStateFailure(f"Cannot start {name} before {dependency} is complete.")

        stage.transition(state)
        self._upsert_stage_state_search_attributes()

        if state == StateEnum.UNREACHABLE and cascade_unreachable:
            # Set all stages dependent on this stage as unreachable as well
            for dependent_stage in self.stages_by_dependency(stage.name):
                if dependent_stage.state != state:
                    dependent_stage.transition(state)
            self._upsert_stage_state_search_attributes()

    def get_stage_state(self, name: str) -> StateEnum:
        """Get the state of the stage."""
        return self.get_stage_by_name(name).state

    def set_stage_input(self, name: str, stage_input: StageInput) -> None:
        """Set the input for a stage."""
        stage = self.get_stage_by_name(name)
        stage.input = stage_input

    def set_stage_output(self, name: str, output: StageOutput) -> None:
        """Set the output for a stage."""
        stage = self.get_stage_by_name(name)
        stage.output = output

    def stages_by_state(self, state: StateEnum) -> list[Stage]:
        """Return a list of stages by their current state."""
        return [stage for stage in self._stages if stage.state == state]

    def stages_by_dependency(self, dependency: str) -> list[Stage]:
        """Return a list of stages dependent on a given stage."""
        return [stage for stage in self._stages if dependency in stage.depends_on]

    def _upsert_stage_state_search_attributes(self) -> None:
        """Index workflow stage state summary flags."""
        # Keep histories from before stage-state search attributes replayable.
        if not workflow.patched(STAGE_STATE_SEARCH_ATTRIBUTES_PATCH):
            return
        workflow.upsert_search_attributes(
            {
                FAILED_STAGE_SEARCH_ATTRIBUTE: [self.failed_stage()],
                PENDING_APPROVAL_SEARCH_ATTRIBUTE: [self.pending_approval()],
            }
        )

    @staticmethod
    def _format_row_for_markdown_table(row_data: dict[str, Any]) -> dict[str, Any]:
        """Format list-of-strings values as comma-separated for table display."""
        for key, value in list(row_data.items()):
            if isinstance(value, list) and all(isinstance(x, str) for x in value):
                row_data[key] = ", ".join(value) if value else ""
        return row_data

    @staticmethod
    def markdown_table(
        rows: Sequence[BaseModel] | BaseModel, exclude: set[str] | None = None
    ) -> str:
        """Provide a markdown table output."""
        if isinstance(rows, BaseModel):
            row_list: list[BaseModel] = [rows]
        else:
            row_list = list(rows)
        if not row_list:
            return ""

        first_row = row_list[0]
        markdown_fields = getattr(first_row, "markdown_fields", None)

        table_data = []
        for row in row_list:
            row_data = row.model_dump(exclude=exclude, mode="json")
            if markdown_fields:
                row_data = {k: v for k, v in row_data.items() if k in markdown_fields}
            table_data.append(StageMixin._format_row_for_markdown_table(row_data))

        return str(
            markdown_table(table_data).set_params(quote=False, row_sep="markdown").get_markdown()
        )

    @staticmethod
    def markdown_table_dict(rows: Sequence[Any] | Any) -> str:
        """Provide a tabular output for a dict."""
        row_list = list(rows) if isinstance(rows, Sequence) else [rows]
        return (
            str(markdown_table(row_list).set_params(quote=False, row_sep="markdown").get_markdown())
            if row_list
            else ""
        )

    @workflow.query
    def pending_approval(self) -> bool:
        """Return true if the workflow is currently pending approval."""
        return bool(
            next(
                (stage for stage in self._stages if stage.state == StateEnum.PENDING_APPROVAL),
                None,
            )
        )

    @workflow.query
    def failed_stage(self) -> bool:
        """Return true if any workflow stage is currently failed."""
        return bool(
            next(
                (stage for stage in self._stages if stage.state == StateEnum.FAILED),
                None,
            )
        )

    @workflow.query
    def stages(self) -> list[Stage]:
        """Return all defined stages for the workflow."""
        return self._stages

    @staticmethod
    def compress_stages(stages: list[Stage]) -> str:
        """Compress stages into a base64 encoded gzipped JSON string.

        Args:
            stages: List of Stage objects to compress

        Returns:
            str: Base64 encoded gzipped JSON string
        """
        # Convert stages to JSON string.
        # mode="json" coerces bytes fields to lists of ints (Pydantic v2 default)
        # so that json.dumps never encounters a raw bytes object.
        stages_json = json.dumps([stage.model_dump(mode="json") for stage in stages])

        # Compress the JSON string using gzip
        compressed = gzip.compress(stages_json.encode("utf-8"))

        # Encode the compressed data in base64
        return base64.b64encode(compressed).decode("utf-8")

    @staticmethod
    def decompress_stages(compressed_stages: str) -> list[Stage]:
        """Decompress stages from a base64 encoded gzipped JSON string.

        Args:
            compressed_stages: Base64 encoded gzipped JSON string

        Returns:
            list[Stage]: List of decompressed Stage objects
        """
        # Decode base64
        compressed_data = base64.b64decode(compressed_stages)

        # Decompress gzip
        json_str = gzip.decompress(compressed_data).decode("utf-8")

        # Parse JSON and convert to Stage objects
        return [Stage.model_validate(stage_dict) for stage_dict in json.loads(json_str)]

    @workflow.query
    def compressed_stages(self) -> str:
        """Return the stages output in a compressed format.

        Returns:
            str: A compressed JSON string containing the stages data.
            The string is compressed using gzip and encoded in base64 for efficient transmission.
        """
        return self.compress_stages(self._stages)

    @workflow.query
    def input(self) -> BaseModel | None:
        """Return the worfklow input."""
        return self._input

    @workflow.signal
    async def approve(self, review_input: ReviewSignalInput) -> None:
        """Approve signal."""
        if self.stage_exists(review_input.stage_name):
            stage = self.get_stage_by_name(review_input.stage_name)
            stage.approve(review_input.user)
            self._upsert_stage_state_search_attributes()
        else:
            self.logger.error(
                "Received approve signal for non-existent stage: %s",
                review_input.stage_name,
            )

    @workflow.signal
    async def reject(self, review_input: ReviewSignalInput) -> None:
        """Reject signal."""
        if self.stage_exists(review_input.stage_name):
            stage = self.get_stage_by_name(review_input.stage_name)
            stage.reject(review_input.user)
            self._upsert_stage_state_search_attributes()
        else:
            self.logger.error(
                "Received reject signal for non-existent stage: %s",
                review_input.stage_name,
            )

    @workflow.signal
    async def retry(self, stage_name: str) -> None:
        """Reject signal."""
        if not self.stage_exists(stage_name):
            self.logger.error("Received retry signal for non-existent stage: %s", stage_name)
            return
        stage = self.get_stage_by_name(stage_name)
        if not stage.retryable:
            self.logger.warning("Ignoring retry request for non-retryable stage.")
            return
        if stage.state != StateEnum.FAILED:
            self.logger.warning("Ignoring retry request for non-failed stage.")
            return
        # Move the stage back to IN_PROGRESS to trigger rerun of stage function
        self.set_stage_state(stage_name, StateEnum.IN_PROGRESS)
