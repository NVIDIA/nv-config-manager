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
"""Tests for workflow-result routing and the resilience of the publish."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import nats.errors
import pytest

from nv_config_manager.temporal.archive.main import main
from nv_config_manager.temporal.client.nats import NatsConsumer
from nv_config_manager.temporal.common.mixins.archive import ArchiveMixin
from nv_config_manager.temporal.ngc.activities.nats import PublishNatsInput, publish_nats

BASE_NATS_CONFIG = """
[nats]
server = nats://nats.example.local:4222
queue = nv-config-manager
auth_method = none
config_manager_stream = nv-config-manager
archive_stream = nv-config-manager
archive_subject = nv-config-manager.workflow.result
"""

PREFIXED_NATS_CONFIG = BASE_NATS_CONFIG + "config_manager_api_prefix = $JS.CUSTOM.API\n"
NAMED_NATS_CONFIG = BASE_NATS_CONFIG + "archive_consumer_name = externally-managed-archive\n"


def _consumer() -> NatsConsumer:
    return NatsConsumer(
        stream="nv-config-manager",
        subject="nv-config-manager.workflow.result",
        queue_suffix="archive",
        handler=AsyncMock(),
    )


def test_consumer_defaults_to_standard_prefix(custom_ini):
    """An unset prefix leaves the consumer on the JetStream default."""
    custom_ini(BASE_NATS_CONFIG)
    assert _consumer().api_prefix == "$JS.API"


def test_consumer_follows_config_manager_prefix(custom_ini):
    """Archive events are a subject on the config-manager stream, so they share its prefix."""
    custom_ini(PREFIXED_NATS_CONFIG)
    assert _consumer().api_prefix == "$JS.CUSTOM.API"


def test_consumer_uses_fixed_default_name(custom_ini):
    """Archive identity does not inherit the site-specific queue prefix."""
    custom_ini(BASE_NATS_CONFIG.replace("queue = nv-config-manager", "queue = site-42"))
    assert _consumer().full_queue_name == "nv-config-manager-archive"
    assert _consumer().deliver_subject == "nv-config-manager.archive.delivery"


def test_consumer_name_is_configurable(custom_ini):
    """Externally provisioned archive durable names are configurable."""
    custom_ini(NAMED_NATS_CONFIG)
    assert _consumer().full_queue_name == "externally-managed-archive"


def test_archive_main_does_not_override_the_stream_prefix(custom_ini):
    """The entrypoint inherits the stream's prefix instead of supplying its own."""
    custom_ini(PREFIXED_NATS_CONFIG)

    with (
        patch("nv_config_manager.temporal.archive.main.NatsConsumer") as mock_consumer,
        patch("nv_config_manager.temporal.archive.main.configure_logging"),
        patch("nv_config_manager.temporal.archive.main.setup_telemetry"),
        patch("sys.argv", ["archive"]),
    ):
        main()

    kwargs = mock_consumer.call_args.kwargs
    assert kwargs["stream"] == "nv-config-manager"
    assert kwargs["subject"] == "nv-config-manager.workflow.result"
    assert "api_prefix" not in kwargs


@pytest.mark.asyncio
async def test_workflow_result_publish_subject_is_unchanged(custom_ini):
    """Account routing must not rename the workflow-result data subject."""
    custom_ini(PREFIXED_NATS_CONFIG)
    producer = AsyncMock()

    with patch(
        "nv_config_manager.temporal.ngc.activities.nats.NatsProducer",
        return_value=producer,
    ):
        await publish_nats(PublishNatsInput(message='{"workflow_id":"workflow-1"}'))

    producer.publish.assert_awaited_once_with(
        "nv-config-manager.workflow.result",
        '{"workflow_id":"workflow-1"}',
        stream="nv-config-manager",
    )


@pytest.mark.asyncio
async def test_publish_raises_so_temporal_can_retry(custom_ini):
    """The activity must surface broker errors; the mixin decides they are not fatal."""
    custom_ini(BASE_NATS_CONFIG)
    producer = AsyncMock()
    producer.publish.side_effect = nats.errors.NoServersError()

    with (
        patch(
            "nv_config_manager.temporal.ngc.activities.nats.NatsProducer",
            return_value=producer,
        ),
        pytest.raises(nats.errors.NoServersError),
    ):
        await publish_nats(PublishNatsInput(message='{"workflow_id":"workflow-1"}'))


def _workflow_info() -> MagicMock:
    info = MagicMock()
    info.workflow_id = "workflow-1"
    info.workflow_type = "SomeWorkflow"
    info.start_time = datetime(2026, 1, 1, tzinfo=UTC)
    info.search_attributes = {}
    return info


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.common.mixins.archive.workflow.logger")
@patch("nv_config_manager.temporal.common.mixins.archive.workflow.now")
@patch("nv_config_manager.temporal.common.mixins.archive.workflow.info", new=_workflow_info)
@patch("nv_config_manager.temporal.common.mixins.archive.workflow.execute_activity")
async def test_a_failed_publish_does_not_fail_the_workflow(execute_activity, now, logger):
    """The run has already done its work, so a broker outage must not fail it."""
    now.return_value = datetime(2026, 1, 1, tzinfo=UTC)
    execute_activity.side_effect = RuntimeError("nats unreachable")

    await ArchiveMixin().archive_results()

    logger.warning.assert_called_once()


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.common.mixins.archive.workflow.logger")
@patch("nv_config_manager.temporal.common.mixins.archive.workflow.now")
@patch("nv_config_manager.temporal.common.mixins.archive.workflow.info", new=_workflow_info)
@patch("nv_config_manager.temporal.common.mixins.archive.workflow.execute_activity")
async def test_publish_is_retried_before_being_given_up_on(execute_activity, now, logger):
    """Consumers rely on these events, so a transient failure should be retried."""
    now.return_value = datetime(2026, 1, 1, tzinfo=UTC)

    await ArchiveMixin().archive_results()

    assert execute_activity.call_args.kwargs["retry_policy"].maximum_attempts > 1
    logger.warning.assert_not_called()
