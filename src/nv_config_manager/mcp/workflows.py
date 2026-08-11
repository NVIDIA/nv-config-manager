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

SITE_LEVEL_DEVICE_FILTER_FIELDS = frozenset(
    {"site", "roles", "status", "tenant", "device_type_ids"}
)
DEFAULT_SITE_LEVEL_DEVICE_STATUS = ["Active", "Provisioned"]
SITE_LEVEL_DEVICE_FILTER_PROMPT = (
    "Site-level device filter guidance: this workflow targets every device matching "
    "`site`, `status`, and optional `roles`, `tenant`, and `device_type_ids`; it does "
    "not accept a single `device_id`. `status` defaults to `Active` and `Provisioned` "
    "when the user does not provide one. If the user asks for one named device, first "
    "resolve that device with `get_device_id`, `search_devices`, or `query_nautobot`. "
    "Build the narrowest supported filter from the resolved Nautobot device: `site` "
    "from the device location/site ID, `status` from the device status name if the "
    "user did not provide status, `roles` as a one-item list containing the role name "
    "when available, `tenant` from the tenant name when available, and "
    "`device_type_ids` as a one-item list containing the device type ID when "
    "available. Before starting the workflow, run `query_nautobot` with those same "
    "filters against `devices(location:, status:, role:, tenant:, device_type:, "
    "nv_config_manager_device_status: true)`, then tell the user how many managed "
    "devices match, identify the requested device, and list any other matched devices "
    "that will also be included. If no filter can match only the requested device, say "
    "that this is a site-level workflow and get explicit confirmation before starting "
    "it."
)


@dataclass(frozen=True)
class MCPWorkflow:
    """Workflow metadata used to expose a safe MCP workflow starter."""

    tool_name: str
    workflow_name: str
    description: str
    endpoint: str
    input_class: type[BaseModel]
    tool_prompt: str | None = None

    @property
    def input_schema(self) -> dict[str, Any]:
        """Return the normalized JSON schema accepted by the MCP workflow tool."""
        schema = self.input_class.model_json_schema()
        required = schema.get("required", [])
        for field_name, field_info in self.input_class.model_fields.items():
            property_schema = schema.get("properties", {}).get(field_name)
            if field_name == "trigger":
                required = [name for name in required if name != field_name]
                if isinstance(property_schema, dict):
                    property_schema["default"] = "API"
            elif allows_none(field_info.annotation):
                required = [name for name in required if name != field_name]
                if isinstance(property_schema, dict):
                    property_schema["default"] = None

        if required:
            schema["required"] = required
        else:
            schema.pop("required", None)
        return schema

    @property
    def tool_description(self) -> str:
        """Return the full MCP tool description shown to agent clients."""
        if not self.tool_prompt:
            return self.description
        return f"{self.description}\n\n{self.tool_prompt}"


def discover_mcp_workflows() -> list[MCPWorkflow]:
    """Discover workflows explicitly enabled for MCP."""
    workflows: list[MCPWorkflow] = []
    for workflow_class in NGC_WORKFLOWS + HELLO_WORLD_WORKFLOWS:
        if not issubclass(workflow_class, WorkflowMetadataMixin):
            continue
        metadata_workflow = cast(type[WorkflowMetadataMixin], workflow_class)
        if metadata_workflow.get_workflow_api_endpoint() is None:
            continue
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
                tool_prompt=_tool_prompt_for_input_class(input_class),
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

    if _tool_prompt_for_input_class(workflow.input_class) and "status" not in normalized:
        normalized["status"] = DEFAULT_SITE_LEVEL_DEVICE_STATUS.copy()

    for field_name, field_info in fields.items():
        if field_name in normalized:
            continue
        if allows_none(field_info.annotation):
            normalized[field_name] = None

    return normalized


def _tool_name_from_endpoint(endpoint: str) -> str:
    slug = endpoint.strip("/").split("/")[-1]
    return f"run_{slug.replace('-', '_')}"


def _tool_prompt_for_input_class(input_class: type[BaseModel]) -> str | None:
    field_names = set(input_class.model_fields)
    if SITE_LEVEL_DEVICE_FILTER_FIELDS.issubset(field_names):
        return SITE_LEVEL_DEVICE_FILTER_PROMPT
    return None


def allows_none(annotation: Any) -> bool:
    if annotation is None or annotation is type(None):
        return True
    return type(None) in get_args(annotation)
