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
"""Tests for translating service configuration into workflow runtime state."""

from configparser import ConfigParser
from typing import cast

from pytest_mock import MockerFixture
from redis.asyncio import Redis

from nv_config_manager.temporal import runtime as service_runtime


def test_configure_workflow_runtime_translates_service_settings(mocker: MockerFixture) -> None:
    config = ConfigParser()
    config.read_dict(
        {
            "nats": {
                "archive_stream": "archive",
                "archive_subject": "workflow.result",
            },
            "slack": {"bot_token": "token", "channel_name": "channel"},
            "temporal": {"ui_url": "https://config-manager.example"},
        }
    )
    configure_runtime = mocker.patch.object(service_runtime, "configure_runtime")
    backend = cast(Redis, mocker.Mock(spec=Redis))

    service_runtime.configure_workflow_runtime(config, lock_redis=backend)

    configure_runtime.assert_called_once_with(
        lock_redis=backend,
        nats_stream="archive",
        nats_subject="workflow.result",
        slack_token="token",
        slack_channel="channel",
        ui_base_url="https://config-manager.example",
    )


def test_configure_workflow_runtime_accepts_missing_optional_sections(
    mocker: MockerFixture,
) -> None:
    configure_runtime = mocker.patch.object(service_runtime, "configure_runtime")

    service_runtime.configure_workflow_runtime(ConfigParser(), lock_redis=None)

    configure_runtime.assert_called_once_with(
        lock_redis=None,
        nats_stream=None,
        nats_subject=None,
        slack_token=None,
        slack_channel=None,
        ui_base_url=None,
    )
