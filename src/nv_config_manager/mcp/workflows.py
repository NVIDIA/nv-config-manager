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
"""Workflow metadata helpers for MCP tool registration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast, get_args

from pydantic import BaseModel

from nv_config_manager.temporal.common.mixins.metadata import WorkflowMetadataMixin
from nv_config_manager.temporal.hello_world.workflows import (
    REGISTERED_WORKFLOWS as HELLO_WORLD_WORKFLOWS,
)
from nv_config_manager.temporal.ngc.workflows import REGISTERED_WORKFLOWS as NGC_WORKFLOWS


@dataclass(frozen=True)
class MCPWorkflow:
    """Workflow metadata used to expose a safe MCP workflow starter."""

    tool_name: str
    workflow_name: str
    description: str
    endpoint: str
    input_class: type[BaseModel]

    @property
    def input_schema(self) -> dict[str, Any]:
        """Return the Pydantic JSON schema for the workflow input model."""
        return self.input_class.model_json_schema()


def discover_mcp_workflows() -> list[MCPWorkflow]:
    """Discover workflows explicitly enabled for MCP."""
    workflows: list[MCPWorkflow] = []
    for workflow_class in NGC_WORKFLOWS + HELLO_WORLD_WORKFLOWS:
        if not issubclass(workflow_class, WorkflowMetadataMixin):
            continue
        metadata_workflow = cast(type[WorkflowMetadataMixin], workflow_class)
        if not metadata_workflow.has_complete_metadata():
            continue
        if not metadata_workflow.get_workflow_mcp_enabled():
            continue

        endpoint = metadata_workflow.get_workflow_api_endpoint()
        input_class = metadata_workflow.get_workflow_input_class()
        if not endpoint or not input_class:
            continue

        workflow_name = workflow_class.__name__
        workflows.append(
            MCPWorkflow(
                tool_name=_tool_name_from_endpoint(endpoint),
                workflow_name=workflow_name,
                description=metadata_workflow.get_workflow_description(),
                endpoint=endpoint,
                input_class=input_class,
            )
        )
    return sorted(workflows, key=lambda workflow: workflow.tool_name)


def normalize_workflow_parameters(
    workflow: MCPWorkflow, parameters: dict[str, Any] | None
) -> dict[str, Any]:
    """Fill neutral API defaults for existing workflow input models."""
    normalized = dict(parameters or {})
    fields = workflow.input_class.model_fields

    if "trigger" in fields and "trigger" not in normalized:
        normalized["trigger"] = "API"

    for field_name, field_info in fields.items():
        if field_name in normalized:
            continue
        if _allows_none(field_info.annotation):
            normalized[field_name] = None

    return normalized


def _tool_name_from_endpoint(endpoint: str) -> str:
    slug = endpoint.strip("/").split("/")[-1]
    return f"run_{slug.replace('-', '_')}"


def _allows_none(annotation: Any) -> bool:
    if annotation is None or annotation is type(None):
        return True
    return type(None) in get_args(annotation)
