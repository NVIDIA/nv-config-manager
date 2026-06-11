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

from nv_config_manager.mcp.workflows import discover_mcp_workflows, normalize_workflow_parameters


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


def test_workflow_parameter_normalization_fills_existing_nullable_bookkeeping() -> None:
    workflow = next(item for item in discover_mcp_workflows() if item.tool_name == "run_backup")

    normalized = normalize_workflow_parameters(workflow, {"device_id": "device-1"})

    assert normalized["device_id"] == "device-1"
    assert normalized["trigger"] == "API"
    assert normalized["user"] is None
    assert normalized["user_domain"] is None
    assert normalized["workflow_id"] is None
    assert normalized["intended_config_commit_id"] is None
