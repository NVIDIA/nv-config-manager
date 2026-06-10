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
from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest
from pydantic import BaseModel

from nv_config_manager.mcp import tools
from nv_config_manager.mcp.settings import MCPSettings
from nv_config_manager.mcp.workflows import MCPWorkflow


class FakeServer:
    def __init__(self) -> None:
        self.tools: dict[str, Callable[..., Any]] = {}

    def tool(
        self,
        name: str | None = None,
        description: str | None = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(function: Callable[..., Any]) -> Callable[..., Any]:
            self.tools[name or function.__name__] = function
            return function

        return decorator


class WorkflowInput(BaseModel):
    device_id: str


@pytest.fixture
def settings() -> MCPSettings:
    return MCPSettings(
        workflow_api_url="http://workflow:9000",
        workflow_ui_url="https://config-manager.example.test",
        config_store_api_url="http://config-store:9000",
        dhcp_api_url="http://dhcp:9000",
        nautobot_url="http://nautobot",
        nautobot_read_only_token="token",
        nautobot_verify=True,
        nautobot_auth_mode="jwt",
        nautobot_token_fallback_enabled=False,
        max_response_bytes=10_000,
    )


async def test_workflow_starter_promotes_config_manager_ui_href(
    monkeypatch: pytest.MonkeyPatch,
    settings: MCPSettings,
) -> None:
    async def fake_start_workflow(
        settings: MCPSettings,
        endpoint: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "truncated": False,
            "data": {
                "id": "workflow-123",
                "ui_href": "https://config-manager.example.test/workflows/workflow-123",
            },
        }

    monkeypatch.setattr(tools, "start_workflow", fake_start_workflow)
    server = FakeServer()
    workflow = MCPWorkflow(
        tool_name="run_backup",
        workflow_name="BackupWorkflow",
        description="Run a backup.",
        endpoint="/ngc/backup",
        input_class=WorkflowInput,
    )

    tools._register_workflow_starter(server, settings, workflow)
    result = await server.tools["run_backup"]({"device_id": "device-1"})

    assert result["workflow_id"] == "workflow-123"
    assert result["workflow_ui_href"] == (
        "https://config-manager.example.test/workflows/workflow-123"
    )
    assert "workflow_ui_href" in (server.tools["run_backup"].__doc__ or "")


async def test_related_mcp_servers_includes_public_docs(
    monkeypatch: pytest.MonkeyPatch,
    settings: MCPSettings,
) -> None:
    monkeypatch.setattr(tools, "discover_mcp_workflows", lambda: [])
    server = FakeServer()

    tools.register_tools(server, settings)
    result = await server.tools["list_related_mcp_servers"]()

    assert result["servers"] == [
        {
            "name": "nvidia-config-manager-public-docs",
            "url": tools.PUBLIC_DOCS_MCP_SERVER_URL,
            "purpose": (
                "Public NVIDIA Config Manager documentation. Use this server for "
                "product documentation, usage guidance, and conceptual reference."
            ),
            "authentication": "none",
            "notes": (
                "Connect the MCP-capable client directly to this URL; the operational "
                "Config Manager MCP server does not proxy public documentation tools."
            ),
        }
    ]
