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
"""Translate service INI configuration into workflow package runtime state."""

from __future__ import annotations

from configparser import ConfigParser
from typing import TYPE_CHECKING

from nv_config_manager.common.config import nats_archive_config
from nv_config_manager_workflows.runtime import configure_runtime

if TYPE_CHECKING:
    from redis.asyncio import Redis


def configure_workflow_runtime(config: ConfigParser, *, lock_redis: Redis | None) -> None:
    """Configure every workflow runtime resource from service-owned settings."""
    if config.has_section("nats"):
        nats_stream, nats_subject = nats_archive_config(config)
    else:
        nats_stream, nats_subject = None, None
    slack_token = config.get("slack", "bot_token", fallback=None)
    slack_channel = config.get("slack", "channel_name", fallback=None)
    ui_base_url = config.get("temporal", "ui_url", fallback=None)

    configure_runtime(
        lock_redis=lock_redis,
        nats_stream=nats_stream,
        nats_subject=nats_subject,
        slack_token=slack_token,
        slack_channel=slack_channel,
        ui_base_url=ui_base_url,
    )


__all__ = ["configure_workflow_runtime"]
