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

from typing import Any

import pytest
from click.testing import CliRunner
from pydantic import BaseModel

from nv_config_manager.temporal import cli as temporal_cli


class NullableWorkflowInput(BaseModel):
    required_nullable: str | None
    optional_nullable: str | None = None
    nonnullable_default: str = "default-value"


class NullableWorkflow:
    """Workflow used to verify CLI request serialization."""


def test_workflow_command_sends_omitted_nullable_fields_as_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured_parameters: dict[str, Any] = {}

    monkeypatch.setattr(
        temporal_cli,
        "_build_auth",
        lambda *_args: (None, "https://workflow.example.com/v1/workflow"),
    )

    def capture_invoke(
        _self: temporal_cli.WorkflowClient,
        _workflow_info: temporal_cli.WorkflowInfo,
        parameters: dict[str, Any],
        **_kwargs: Any,
    ) -> dict[str, Any]:
        captured_parameters.update(parameters)
        return {}

    monkeypatch.setattr(temporal_cli.WorkflowClient, "invoke_workflow", capture_invoke)

    workflow_info = temporal_cli.WorkflowInfo(
        NullableWorkflow,
        NullableWorkflowInput,
        "/nullable",
    )
    command = temporal_cli.create_workflow_command("nullable", workflow_info)

    result = CliRunner().invoke(command, ["--hostname", "config-manager.example.com"])

    assert result.exit_code == 0, result.output
    assert captured_parameters == {
        "required_nullable": None,
        "optional_nullable": None,
        "nonnullable_default": "default-value",
    }
