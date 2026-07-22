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

from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI, Request, Response
from fastapi.testclient import TestClient

from nv_config_manager.temporal.api.audit import (
    install_workflow_audit_logging,
    log_workflow_action,
)


def test_log_workflow_action_emits_consistent_structured_fields(mocker):
    """Audit logs contain actor, timestamp, roles, source, and target."""
    audit_logger = mocker.patch("nv_config_manager.temporal.api.audit.logger")
    request = MagicMock()
    request.state.user = "operator@example.com"
    request.state.roles = {"nvcm-network", "all"}
    request.state.auth_source = "jwt"

    log_workflow_action(
        request,
        action="terminate",
        outcome="success",
        workflow_id="workflow-1",
        workflow_type="DeployWorkflow",
        stage_name="apply_configuration",
    )

    audit_logger.info.assert_called_once()
    fields = audit_logger.info.call_args.kwargs["extra"]
    assert fields["event_type"] == "workflow_action"
    assert fields["action"] == "terminate"
    assert fields["outcome"] == "success"
    assert fields["actor"] == "operator@example.com"
    assert fields["roles"] == ["all", "nvcm-network"]
    assert fields["source"] == "jwt"
    assert fields["workflow_id"] == "workflow-1"
    assert fields["workflow_type"] == "DeployWorkflow"
    assert fields["stage_name"] == "apply_configuration"
    assert fields["timestamp"].endswith("+00:00")


def _audit_test_app() -> FastAPI:
    app = FastAPI()
    install_workflow_audit_logging(app)

    @app.middleware("http")
    async def set_identity(request: Request, call_next):
        request.state.user = "operator@example.com"
        request.state.roles = {"nvcm-network"}
        request.state.auth_source = "jwt"
        return await call_next(request)

    @app.post("/v1/workflow/ngc/{workflow_name}")
    async def start(request: Request, workflow_name: str, denied: bool = False):
        request.state.audit_workflow_type = f"{workflow_name.title()}Workflow"
        if denied:
            return Response(status_code=403)
        request.state.audit_workflow_id = "workflow-1"
        return {"id": "workflow-1"}

    @app.post("/v1/workflow/{workflow_id}/{action}")
    @app.post("/v1/workflow/{workflow_id}/{action}/{stage_name}")
    async def lifecycle(workflow_id: str, action: str, stage_name: str | None = None):
        return {"id": workflow_id, "action": action, "stage_name": stage_name}

    return app


@pytest.mark.parametrize(
    ("path", "action", "stage_name"),
    [
        ("/v1/workflow/workflow-1/approve/prompt", "approve", "prompt"),
        ("/v1/workflow/workflow-1/reject/prompt", "reject", "prompt"),
        ("/v1/workflow/workflow-1/retry/apply", "retry", "apply"),
        ("/v1/workflow/workflow-1/terminate", "terminate", None),
    ],
)
def test_audit_middleware_logs_lifecycle_action(mocker, path, action, stage_name):
    """Lifecycle routes are logged with their workflow target and outcome."""
    audit_logger = mocker.patch("nv_config_manager.temporal.api.audit.logger")

    response = TestClient(_audit_test_app()).post(path)

    assert response.status_code == 200
    fields = audit_logger.info.call_args.kwargs["extra"]
    assert fields["action"] == action
    assert fields["outcome"] == "success"
    assert fields["workflow_id"] == "workflow-1"
    assert fields["stage_name"] == stage_name
    assert fields["target"] == path


@pytest.mark.parametrize(
    "action",
    ["deploy", "reprovision", "device_password_rotation", "site_password_rotation"],
)
def test_audit_middleware_logs_workflow_start_and_denial(mocker, action):
    """Dynamic workflow starts include workflow type and HTTP denial outcome."""
    audit_logger = mocker.patch("nv_config_manager.temporal.api.audit.logger")
    client = TestClient(_audit_test_app())

    success = client.post(f"/v1/workflow/ngc/{action}")
    success_fields = audit_logger.info.call_args.kwargs["extra"]
    denied = client.post(f"/v1/workflow/ngc/{action}?denied=true")
    denied_fields = audit_logger.info.call_args.kwargs["extra"]

    assert success.status_code == 200
    assert success_fields["action"] == action
    assert success_fields["outcome"] == "success"
    assert success_fields["workflow_id"] == "workflow-1"
    assert success_fields["target"] == f"ngc/{action}"

    assert denied.status_code == 403
    assert denied_fields["action"] == action
    assert denied_fields["outcome"] == "denied"
    assert denied_fields["workflow_id"] is None
    assert denied_fields["detail"] == "HTTP 403"
