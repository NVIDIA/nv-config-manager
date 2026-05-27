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
"""NB NATS nv_config_manager.* Event Handlers."""

from typing import Any

from nv_config_manager.render.events.util import (
    build_commit_message,
    extract_user,
    queue_render,
)


async def configmanagerdevicestatus(data: dict[str, Any]) -> None:
    """nv_config_manager.configmanagerdevicestatus event handler."""
    if data["event"] == "delete":
        return
    device_uuid = data["record"]["id"]
    await queue_render(
        device_uuid=device_uuid,
        commit_message=build_commit_message(data),
        user=extract_user(data),
        timestamp=data["@timestamp"],
    )
