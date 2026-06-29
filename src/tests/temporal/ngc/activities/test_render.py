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
"""Test Render Activities."""

from unittest.mock import AsyncMock, patch

import pytest
from aioresponses import aioresponses

from nv_config_manager.common.client.render import (
    FileCommit,
    RenderClient,
    RenderClientException,
)
from nv_config_manager.temporal.ngc.activities.render import (
    ExecuteRenderInput,
    ExecuteRenderOutput,
    execute_render,
)


@pytest.mark.asyncio
async def test_execute_render_success() -> None:
    """Test execute_render activity when render succeeds."""
    base_url = "https://render.test.config-manager.example.com"
    mock_client = RenderClient(base_url=base_url)
    mock_config_client = AsyncMock()
    mock_config_client.__aenter__.return_value = mock_config_client
    mock_config_client.list_device_configs.return_value = [
        {"filename": "tenant.yaml", "version": 5},
        {"filename": "startup.yaml", "version": 6},
    ]

    with (
        patch(
            "nv_config_manager.temporal.ngc.activities.render.render_client",
            return_value=mock_client,
        ),
        patch(
            "nv_config_manager.temporal.ngc.activities.render.config_store_client",
            return_value=mock_config_client,
        ),
    ):
        with aioresponses() as m:
            m.post(
                f"{base_url}/v1/render/test-device-id/render",
                payload={
                    "updated_files": [
                        {"filename": "tenant.yaml", "commit": "5"},
                        {"filename": "startup.yaml", "commit": "6"},
                    ]
                },
                status=201,
            )

            activity_input = ExecuteRenderInput(
                device_id="test-device-id",
                workflow_id="test-workflow-id",
            )

            result = await execute_render(activity_input)

    assert isinstance(result, ExecuteRenderOutput)
    assert result.updated_files == [
        FileCommit(filename="tenant.yaml", commit="5"),
        FileCommit(filename="startup.yaml", commit="6"),
    ]
    assert result.snapshot_files == [
        FileCommit(filename="tenant.yaml", commit="5"),
        FileCommit(filename="startup.yaml", commit="6"),
    ]
    assert result.get_commit("tenant.yaml") == "5"
    assert result.get_commit("startup.yaml") == "6"
    assert result.get_commit("nonexistent.yaml") is None


@pytest.mark.asyncio
async def test_execute_render_empty_result() -> None:
    """Test execute_render activity when no files are changed."""
    base_url = "https://render.test.config-manager.example.com"
    mock_client = RenderClient(base_url=base_url)
    mock_config_client = AsyncMock()
    mock_config_client.__aenter__.return_value = mock_config_client
    mock_config_client.list_device_configs.return_value = [
        {"filename": "tenant.yaml", "version": 7},
        {"filename": "startup.yaml", "version": 11},
    ]

    with (
        patch(
            "nv_config_manager.temporal.ngc.activities.render.render_client",
            return_value=mock_client,
        ),
        patch(
            "nv_config_manager.temporal.ngc.activities.render.config_store_client",
            return_value=mock_config_client,
        ),
    ):
        with aioresponses() as m:
            m.post(
                f"{base_url}/v1/render/test-device-id/render",
                payload={"updated_files": []},
                status=200,
            )

            activity_input = ExecuteRenderInput(
                device_id="test-device-id",
                workflow_id="test-workflow-id",
            )

            result = await execute_render(activity_input)

    assert isinstance(result, ExecuteRenderOutput)
    assert result.updated_files == []
    assert result.snapshot_files == [
        FileCommit(filename="tenant.yaml", commit="7"),
        FileCommit(filename="startup.yaml", commit="11"),
    ]
    assert result.get_commit("tenant.yaml") == "7"
    assert result.get_commit("startup.yaml") == "11"


@pytest.mark.asyncio
async def test_execute_render_http_error() -> None:
    """Test execute_render activity when HTTP request fails."""
    base_url = "https://render.test.config-manager.example.com"
    mock_client = RenderClient(base_url=base_url)

    with patch(
        "nv_config_manager.temporal.ngc.activities.render.render_client",
        return_value=mock_client,
    ):
        with aioresponses() as m:
            m.post(
                f"{base_url}/v1/render/test-device-id/render",
                status=500,
                body="Internal Server Error",
            )

            activity_input = ExecuteRenderInput(
                device_id="test-device-id",
                workflow_id="test-workflow-id",
            )

            with pytest.raises(RenderClientException) as exc_info:
                await execute_render(activity_input)

            assert "Failed to render device" in str(exc_info.value)
