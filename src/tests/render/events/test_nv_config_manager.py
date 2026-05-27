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
"""Tests for the nv_config_manager event handlers."""

from unittest.mock import AsyncMock, patch

import pytest

from nv_config_manager.render.events.nv_config_manager import configmanagerdevicestatus


@pytest.mark.asyncio
async def test_configmanagerdevicestatus_delete_event(base_message):
    """Test configmanagerdevicestatus handler with delete event."""
    base_message["event"] = "delete"
    base_message["model"] = "configmanagerdevicestatus"
    base_message["record"]["id"] = "test-device"
    base_message["record"]["name"] = "Test Device"

    with patch(
        "nv_config_manager.render.events.nv_config_manager.queue_render", new_callable=AsyncMock
    ) as mock_queue:
        await configmanagerdevicestatus(base_message)
        mock_queue.assert_not_called()


@pytest.mark.asyncio
async def test_configmanagerdevicestatus_create_event(base_message):
    """Test configmanagerdevicestatus handler with create event."""
    base_message["event"] = "create"
    base_message["model"] = "configmanagerdevicestatus"
    base_message["record"]["id"] = "test-device"
    base_message["record"]["name"] = "Test Device"

    with patch(
        "nv_config_manager.render.events.nv_config_manager.queue_render", new_callable=AsyncMock
    ) as mock_queue:
        await configmanagerdevicestatus(base_message)
        mock_queue.assert_called_once_with(
            device_uuid="test-device",
            commit_message="Triggered from nb configmanagerdevicestatus create on Test Device by testuser at 2024-01-16T21:46:05Z",
            user="testuser",
            timestamp="2024-01-16T21:46:05Z",
        )


@pytest.mark.asyncio
async def test_configmanagerdevicestatus_update_event(base_message):
    """Test configmanagerdevicestatus handler with update event."""
    base_message["event"] = "update"
    base_message["model"] = "configmanagerdevicestatus"
    base_message["record"]["id"] = "test-device"
    base_message["record"]["name"] = "Test Device"

    with patch(
        "nv_config_manager.render.events.nv_config_manager.queue_render", new_callable=AsyncMock
    ) as mock_queue:
        await configmanagerdevicestatus(base_message)
        mock_queue.assert_called_once_with(
            device_uuid="test-device",
            commit_message="Triggered from nb configmanagerdevicestatus update on Test Device by testuser at 2024-01-16T21:46:05Z",
            user="testuser",
            timestamp="2024-01-16T21:46:05Z",
        )
