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
"""Mixin to log workflow results."""

from __future__ import annotations

from datetime import timedelta

from pydantic import BaseModel
from temporalio import workflow
from temporalio.common import RetryPolicy, SearchAttributes

from nv_config_manager.temporal.common.mixins.base import BaseMixin

with workflow.unsafe.imports_passed_through():
    from nv_config_manager.temporal.ngc.activities.nats import PublishNatsInput, publish_nats


class WorkflowResultLog(BaseModel):
    """Workflow Result data."""

    workflow_id: str
    workflow_type: str
    start_time: str
    publish_time: str
    search_attributes: SearchAttributes

    @staticmethod
    def from_workflow_info(info: workflow.Info) -> WorkflowResultLog:
        """Build result from workflow info."""
        return WorkflowResultLog(
            workflow_id=info.workflow_id,
            workflow_type=info.workflow_type,
            start_time=info.start_time.isoformat(),
            publish_time=workflow.now().isoformat(),
            search_attributes=info.search_attributes,
        )


_PUBLISH_RETRY_POLICY = RetryPolicy(maximum_attempts=3)


class ArchiveMixin(BaseMixin):
    """Mixin to publish a workflow result to NATS."""

    async def archive_results(self) -> None:
        """Publish the workflow result; never mask the run's own outcome."""
        try:
            await workflow.execute_activity(
                publish_nats,
                PublishNatsInput(
                    message=WorkflowResultLog.from_workflow_info(workflow.info()).model_dump_json(),
                ),
                schedule_to_close_timeout=timedelta(minutes=1),
                retry_policy=_PUBLISH_RETRY_POLICY,
            )
        except Exception:  # pylint: disable=broad-exception-caught
            # The run has already finished its work by the time results are
            # published, so a broker problem must not turn it into a failure.
            # Consumers treat these events as an optimisation over polling.
            workflow.logger.warning(
                "Failed to publish the result for %s; consumers will not see this run",
                workflow.info().workflow_id,
            )
