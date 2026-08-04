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
"""Tests that the archive consumer follows its stream's JetStream API prefix."""

from unittest.mock import AsyncMock, patch

from nv_config_manager.temporal.archive.main import main
from nv_config_manager.temporal.client.nats import NatsConsumer

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
