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
"""Tests that the archive consumer honours the archive JetStream API prefix."""

from unittest.mock import AsyncMock, patch

from nv_config_manager.temporal.client.nats import NatsConsumer

ARCHIVE_NATS_CONFIG = """
[nats]
server = nats://nats.example.local:4222
queue = nv-config-manager
auth_method = none
config_manager_stream = nv-config-manager
config_manager_api_prefix = $JS.API
archive_stream = nv-config-manager
archive_subject = nv-config-manager.workflow.result
archive_api_prefix = $JS.CEREBRO.API
"""


def _consumer(**kwargs) -> NatsConsumer:
    return NatsConsumer(
        stream="nv-config-manager",
        subject="nv-config-manager.workflow.result",
        queue_suffix="archive",
        handler=AsyncMock(),
        **kwargs,
    )


def test_consumer_defaults_to_config_manager_prefix(custom_ini):
    """Without an explicit prefix the consumer stays on the local account."""
    custom_ini(ARCHIVE_NATS_CONFIG)
    assert _consumer().api_prefix == "$JS.API"


def test_consumer_accepts_explicit_prefix(custom_ini):
    """An explicit prefix overrides the config-manager account default."""
    custom_ini(ARCHIVE_NATS_CONFIG)
    assert _consumer(api_prefix="$JS.CEREBRO.API").api_prefix == "$JS.CEREBRO.API"


def test_archive_main_wires_archive_api_prefix(custom_ini):
    """The archive entrypoint passes the archive-specific prefix to its consumer."""
    custom_ini(ARCHIVE_NATS_CONFIG)

    with (
        patch("nv_config_manager.temporal.archive.main.NatsConsumer") as mock_consumer,
        patch("nv_config_manager.temporal.archive.main.configure_logging"),
        patch("nv_config_manager.temporal.archive.main.setup_telemetry"),
        patch("sys.argv", ["archive"]),
    ):
        from nv_config_manager.temporal.archive.main import main

        main()

    assert mock_consumer.call_args.kwargs["api_prefix"] == "$JS.CEREBRO.API"
