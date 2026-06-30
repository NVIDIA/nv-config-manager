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

from nv_config_manager.mcp.workflows import (
    DEFAULT_SITE_LEVEL_DEVICE_STATUS,
    SITE_LEVEL_DEVICE_FILTER_PROMPT,
    discover_mcp_workflows,
    normalize_workflow_parameters,
)
from nv_config_manager.temporal.common.mixins.metadata import WorkflowMetadataMixin
from nv_config_manager.temporal.hello_world.workflows import (
    REGISTERED_WORKFLOWS as HELLO_WORLD_WORKFLOWS,
)
from nv_config_manager.temporal.ngc.workflows import REGISTERED_WORKFLOWS as NGC_WORKFLOWS


def test_only_safe_diagnostic_workflows_are_mcp_enabled() -> None:
    workflows = discover_mcp_workflows()
    tool_names = {workflow.tool_name for workflow in workflows}

    assert {
        "run_backup",
        "run_port_lldp_info",
        "run_connected_host_metadata",
        "run_device_cable_validation",
        "run_site_cable_validation",
        "run_cumulus_hardware_validation",
        "run_infiniband_cable_validation",
        "run_infiniband_get_unhealthy_ports",
    }.issubset(tool_names)
    assert "run_deploy" not in tool_names
    assert "run_reprovision" not in tool_names
    assert "run_switch_os_upgrade" not in tool_names
    assert "run_device_password_rotation" not in tool_names
    assert "run_vpc_creation" not in tool_names


def test_registered_workflow_models_describe_every_input_field() -> None:
    missing_descriptions: dict[str, list[str]] = {}
    for workflow in NGC_WORKFLOWS + HELLO_WORLD_WORKFLOWS:
        if not issubclass(workflow, WorkflowMetadataMixin):
            continue
        input_class = workflow.get_workflow_input_class()
        if input_class is None:
            continue
        missing_descriptions[workflow.__name__] = [
            field_name
            for field_name, field_info in input_class.model_fields.items()
            if not field_info.description
        ]

    assert not {tool: fields for tool, fields in missing_descriptions.items() if fields}


def test_workflow_parameter_normalization_fills_existing_nullable_bookkeeping() -> None:
    workflow = next(item for item in discover_mcp_workflows() if item.tool_name == "run_backup")

    normalized = normalize_workflow_parameters(workflow, {"device_id": "device-1"})

    assert normalized["device_id"] == "device-1"
    assert normalized["trigger"] == "API"
    assert normalized["user"] is None
    assert normalized["user_domain"] is None
    assert normalized["workflow_id"] is None
    assert normalized["intended_config_commit_id"] is None


def test_workflow_input_schema_matches_normalized_mcp_parameters() -> None:
    workflow = next(item for item in discover_mcp_workflows() if item.tool_name == "run_backup")

    schema = workflow.input_schema

    assert schema["required"] == ["device_id"]
    assert schema["properties"]["trigger"]["default"] == "API"
    assert schema["properties"]["trigger"]["description"]
    assert schema["properties"]["user"]["default"] is None
    assert schema["properties"]["device_id"]["description"]


def test_site_level_filter_workflows_include_mcp_targeting_prompt() -> None:
    workflows = {workflow.tool_name: workflow for workflow in discover_mcp_workflows()}

    for tool_name in ("run_site_cable_validation", "run_cumulus_hardware_validation"):
        assert workflows[tool_name].tool_prompt == SITE_LEVEL_DEVICE_FILTER_PROMPT
        assert "does not accept a single `device_id`" in workflows[tool_name].tool_description
        assert (
            "`status` defaults to `Active` and `Provisioned`"
            in workflows[tool_name].tool_description
        )
        assert "nv_config_manager_device_status: true" in workflows[tool_name].tool_description
        assert "how many managed devices match" in workflows[tool_name].tool_description

    assert workflows["run_backup"].tool_prompt is None
    assert SITE_LEVEL_DEVICE_FILTER_PROMPT not in workflows["run_backup"].tool_description


def test_site_level_filter_workflows_default_reachable_statuses() -> None:
    workflows = {workflow.tool_name: workflow for workflow in discover_mcp_workflows()}

    for tool_name in ("run_site_cable_validation", "run_cumulus_hardware_validation"):
        normalized = normalize_workflow_parameters(workflows[tool_name], {"site": "PDX01"})
        assert normalized["site"] == "PDX01"
        assert normalized["status"] == DEFAULT_SITE_LEVEL_DEVICE_STATUS

    backup_normalized = normalize_workflow_parameters(
        workflows["run_backup"], {"device_id": "device-1"}
    )
    assert "status" not in backup_normalized
