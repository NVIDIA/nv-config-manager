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
"""Decorators for workflow methods."""

from collections.abc import Callable
from functools import wraps
from typing import Any, TypeVar, cast

from temporalio import workflow
from temporalio.exceptions import ApplicationError, TemporalError

F = TypeVar("F", bound=Callable[..., Any])


class WorkflowRuntimeFailure(ApplicationError):
    """Failures raised during workflow execution."""


def run_nv_config_manager_workflow[F: Callable[..., Any]](func: F) -> F:
    """Decorator for the workflow run method.

    Override of the temporalio.workflow.run decorator to raise
    uncaught exceptions as WorkflowRuntimeFailure which will cause
    workflow to enter a failed state rather than to suspend.
    """

    @workflow.run
    @wraps(func)
    async def _run(*args: object) -> Any:
        try:
            return await func(*args)
        except Exception as error:
            non_retryable = False
            if isinstance(error, ApplicationError):
                non_retryable = error.non_retryable
            elif not isinstance(error, TemporalError):
                # Unexpected exceptions likely indicate a bug in the workflow code
                non_retryable = True
            raise WorkflowRuntimeFailure(
                f"Workflow failed: {error}",
                non_retryable=non_retryable,
            ) from error

    return cast(F, _run)
