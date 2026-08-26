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
"""How the stage decorator reacts to a stage body that returns or raises."""

import pytest
from temporalio import workflow
from temporalio.exceptions import ApplicationError

from nv_config_manager_workflows.stage import (
    StageMixin,
    StageOutput,
    StageRuntimeFailure,
    StageStateFailure,
    StateEnum,
    stage_executor,
)


class Workflow(StageMixin):
    """A one-stage workflow whose stage body the test supplies."""

    def __init__(self, body, *, retryable=True):
        super().__init__()
        self._body = body
        self.attempts = 0
        self.define_stage(
            name="render",
            description="Render",
            requires_approval=False,
            depends_on=[],
            retryable=retryable,
        )

    @stage_executor("render")
    async def render(self):
        """Run the supplied stage body."""
        self.attempts += 1
        return await self._body(self)


async def succeeds(_workflow):
    return StageOutput(display="rendered")


def failing(error):
    """Build a stage body that always raises ``error``."""

    async def body(_workflow):
        raise error

    return body


def failing_once(error):
    """Build a stage body that raises once and then succeeds."""

    async def body(state):
        if state.attempts == 1:
            raise error
        return StageOutput(display="rendered")

    return body


class TestSuccess:
    async def test_a_completed_stage_records_its_output(self, clock, legacy_history):
        state = Workflow(succeeds)

        result = await state.render()

        assert result == StageOutput(display="rendered")
        assert state.get_stage_state("render") == StateEnum.COMPLETE
        assert state.get_stage_by_name("render").output == StageOutput(display="rendered")


class TestFailure:
    async def test_a_state_failure_propagates_untouched(self, clock, legacy_history):
        """An invalid transition is a bug in the workflow, not a retryable stage failure."""
        state = Workflow(failing(StageStateFailure("bad transition")))

        with pytest.raises(StageStateFailure, match="bad transition"):
            await state.render()

        assert state.get_stage_state("render") == StateEnum.IN_PROGRESS

    async def test_a_failed_stage_records_the_traceback(self, clock, legacy_history):
        state = Workflow(failing(RuntimeError("boom")), retryable=False)

        with pytest.raises(StageRuntimeFailure):
            await state.render()

        assert state.get_stage_state("render") == StateEnum.FAILED
        assert "RuntimeError: boom" in state.get_stage_by_name("render").traceback

    async def test_a_non_retryable_stage_fails_the_workflow(self, clock, legacy_history):
        state = Workflow(failing(RuntimeError("boom")), retryable=False)

        with pytest.raises(StageRuntimeFailure, match="is non-retryable") as failure:
            await state.render()

        assert failure.value.non_retryable is True

    async def test_terminate_on_failure_fails_the_workflow(self, clock, legacy_history):
        state = Workflow(failing(RuntimeError("boom")))
        state.set_terminate_on_failure(True)

        with pytest.raises(StageRuntimeFailure, match="is non-retryable"):
            await state.render()

    async def test_a_non_retryable_application_error_is_not_awaited_for_retry(
        self, clock, legacy_history
    ):
        state = Workflow(failing(ApplicationError("no route to host", non_retryable=True)))

        with pytest.raises(StageRuntimeFailure, match="cannot be retried"):
            await state.render()

    async def test_an_unexpected_exception_is_not_awaited_for_retry(self, clock, legacy_history):
        """A plain exception signals a bug in the stage body, which a retry will not fix."""
        state = Workflow(failing(ValueError("off by one")))

        with pytest.raises(StageRuntimeFailure, match="Unexpected exception"):
            await state.render()


class TestRetry:
    async def test_a_retryable_failure_waits_for_the_retry_signal(
        self, clock, legacy_history, monkeypatch
    ):
        """A retryable stage parks until a signal returns it to IN_PROGRESS."""
        state = Workflow(failing_once(ApplicationError("transient")))

        async def retry_signal(_condition):
            state.set_stage_state("render", StateEnum.IN_PROGRESS)

        monkeypatch.setattr(workflow, "wait_condition", retry_signal)

        result = await state.render()

        assert result == StageOutput(display="rendered")
        assert state.get_stage_state("render") == StateEnum.COMPLETE
        assert state.get_stage_by_name("render").retry_count == 1
        assert state.attempts == 2
