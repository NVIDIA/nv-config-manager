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
"""Tests for the NVDataflow client."""

import pytest
from aioresponses import aioresponses

from nv_config_manager.common.client.nvdataflow import NVDataflowClient, NVDataflowException


def test_nvdataflow_client_requires_configured_async_endpoint() -> None:
    """Async posting must not fall back to hardcoded endpoint URLs."""
    with pytest.raises(NVDataflowException, match="async_endpoint"):
        NVDataflowClient(project="test-project")


def test_nvdataflow_client_requires_configured_sync_endpoint() -> None:
    """Sync posting must not fall back to hardcoded endpoint URLs."""
    with pytest.raises(NVDataflowException, match="sync_endpoint"):
        NVDataflowClient(project="test-project", sync=True)


@pytest.mark.asyncio
async def test_nvdataflow_client_posts_to_configured_async_endpoint() -> None:
    """The project placeholder in the configured async endpoint is expanded."""
    endpoint = "https://nvdataflow.example.invalid/dataflow/test-project/posting"

    with aioresponses() as mocked:
        mocked.post(endpoint, status=201)

        async with NVDataflowClient(
            project="test-project",
            async_endpoint="https://nvdataflow.example.invalid/dataflow/{project}/posting",
        ) as client:
            assert client.endpoint == endpoint
            assert await client.post({"key": "value"}) == 201


def test_nvdataflow_client_uses_configured_sync_endpoint() -> None:
    """The sync endpoint template is selected when sync posting is enabled."""
    client = NVDataflowClient(
        project="test-project",
        sync=True,
        async_endpoint="https://nvdataflow.example.invalid/dataflow/{project}/posting",
        sync_endpoint="https://nvdataflow.example.invalid/dataflow-sync/{project}/posting",
    )

    assert client.endpoint == (
        "https://nvdataflow.example.invalid/dataflow-sync/test-project/posting"
    )
