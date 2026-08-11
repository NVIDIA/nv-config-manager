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
"""Registration invariants for opt-in Backbone sandbox workflows."""

from unittest.mock import patch

from nv_config_manager.temporal.bb_sandbox.activities import REGISTERED_ACTIVITIES
from nv_config_manager.temporal.bb_sandbox.workflows import (
    REGISTERED_WORKFLOWS,
    BBDrainInterfaceWorkflow,
    BBInternalBackboneBringupWorkflow,
    _jira_diff,
    _markdown_diff,
)


def test_sandbox_workflow_registration() -> None:
    """Both demonstrations are available to the opt-in registry."""
    assert REGISTERED_WORKFLOWS == [
        BBDrainInterfaceWorkflow,
        BBInternalBackboneBringupWorkflow,
    ]


def test_drain_stages_update_source_of_truth_before_review() -> None:
    """The drain review is based on a render produced after the Nautobot mutation."""
    with patch("temporalio.workflow.time", return_value=0):
        workflow = BBDrainInterfaceWorkflow()

    assert [stage.name for stage in workflow.stages()] == [
        "resolve_intent",
        "update_nautobot_intent",
        "render_intended_configuration",
        "review_configuration_diff",
        "apply_configuration",
        "validate_applied_configuration",
        "record_audit",
    ]


def test_bringup_deployments_and_validations_have_separate_stage_history() -> None:
    """Each approved push remains distinct from its downstream health validation."""
    with patch("temporalio.workflow.time", return_value=0):
        workflow = BBInternalBackboneBringupWorkflow()

    assert [stage.name for stage in workflow.stages()] == [
        "resolve_circuit",
        "write_physical_intent",
        "physical_router_a",
        "physical_router_z",
        "validate_neighbors",
        "write_addressing_intent",
        "addressing_router_a",
        "addressing_router_z",
        "validate_rtt",
        "write_routing_intent",
        "routing_router_a",
        "routing_router_z",
        "validate_routing",
        "record_jira_audit",
    ]


def test_sandbox_activities_are_explicitly_registered() -> None:
    """All real and mock activity boundaries are worker-visible."""
    assert {activity.__name__ for activity in REGISTERED_ACTIVITIES} == {
        "resolve_drain_intent",
        "set_interface_status",
        "resolve_internal_backbone_intent",
        "enable_backbone_interfaces",
        "apply_backbone_addressing",
        "activate_backbone_routing",
        "apply_drain_candidate",
        "build_mock_candidate_diff",
        "mock_apply_candidate",
        "mock_validate_neighbor",
        "mock_validate_applied_intent",
        "mock_ping_rtt",
        "mock_validate_routing",
        "perform_drain_candidate_diff",
        "load_render_revision_diff",
    }


def test_diff_formatters_preserve_multiline_candidate_output() -> None:
    """Workflow Markdown and Jira wiki markup keep Junos diffs preformatted."""
    diff = "[edit protocols isis interface ae102.0]\n- metric 10;\n+ metric 1000000;"

    assert _markdown_diff(diff) == f"```diff\n{diff}\n```"
    assert _jira_diff(diff) == f"{{noformat}}\n{diff}\n{{noformat}}"
