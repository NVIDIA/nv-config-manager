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
"""Tests for dynamic workflow endpoint generation."""

from unittest.mock import MagicMock

import pytest
from pydantic import BaseModel

from nv_config_manager.temporal.api import dynamic_endpoints
from nv_config_manager.temporal.api.dynamic_endpoints import create_workflow_endpoint
from nv_config_manager.temporal.common.mixins.metadata import WorkflowMetadataMixin


class _Input(BaseModel):
    host: str


class _CanonWorkflow(WorkflowMetadataMixin):
    workflow_name = "Canon"
    workflow_description = "Canonicalizing workflow"
    workflow_input_class = _Input
    workflow_api_endpoint = "/x"

    @classmethod
    async def canonicalize_input(cls, body: BaseModel) -> BaseModel:
        body.host = "canonical"  # type: ignore[attr-defined]
        return body


@pytest.mark.asyncio
async def test_default_canonicalize_input_is_noop():
    body = _Input(host="ufm01")
    assert await WorkflowMetadataMixin.canonicalize_input(body) is body
    assert body.host == "ufm01"


@pytest.mark.asyncio
async def test_endpoint_canonicalizes_input_before_start(mocker):
    """The generated endpoint runs canonicalize_input before starting the run."""
    captured: dict[str, BaseModel] = {}

    async def _fake_start(request, workflow_class, body):
        captured["body"] = body
        return "wid-1"

    mocker.patch.object(dynamic_endpoints, "start_workflow", new=_fake_start)

    endpoint = create_workflow_endpoint(_CanonWorkflow, _Input, "/x")
    request = MagicMock()
    request.state.user = "user@nvidia.com"

    response = await endpoint(_Input(host="ufm01"), request)

    assert response.id == "wid-1"
    assert captured["body"].host == "canonical"
