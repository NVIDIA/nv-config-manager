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
"""Structured audit logging for Workflow API actions."""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Literal

from fastapi import FastAPI, Request, Response

from nv_config_manager.common.log import LogCategory, escape_log_newlines, get_logger

logger = get_logger(__name__, category=LogCategory.TEMPORAL_AUDIT)

AuditOutcome = Literal["success", "denied", "failure"]

_WORKFLOW_ACTION_PATH = re.compile(
    r"^/v1/workflow/(?P<workflow_id>[^/]+)/"
    r"(?P<action>approve|reject|retry|terminate)"
    r"(?:/(?P<stage_name>[^/]+))?/?$"
)


def request_auth_source(request: Request) -> str:
    """Return the trusted authentication source populated by auth middleware."""
    source = getattr(request.state, "auth_source", "unknown")
    return source if isinstance(source, str) else "unknown"


def log_workflow_action(
    request: Request,
    *,
    action: str,
    outcome: AuditOutcome,
    workflow_id: str | None = None,
    workflow_type: str | None = None,
    stage_name: str | None = None,
    target: str | None = None,
    detail: str | None = None,
) -> None:
    """Emit a consistent structured audit event for a Workflow API action."""
    actor = getattr(request.state, "user", "unknown")
    if not isinstance(actor, str):
        actor = "unknown"

    request_roles: object = getattr(request.state, "roles", set())
    roles = (
        sorted(str(role) for role in request_roles)
        if isinstance(request_roles, (set, frozenset, list, tuple))
        else []
    )

    logger.info(
        "Workflow action %s finished with outcome %s",
        action,
        outcome,
        extra={
            "event_type": "workflow_action",
            "action": action,
            "outcome": outcome,
            "actor": escape_log_newlines(actor),
            "roles": [escape_log_newlines(role) for role in roles],
            "source": escape_log_newlines(request_auth_source(request)),
            "timestamp": datetime.now(UTC).isoformat(),
            "workflow_id": escape_log_newlines(workflow_id) if workflow_id else None,
            "workflow_type": escape_log_newlines(workflow_type) if workflow_type else None,
            "stage_name": escape_log_newlines(stage_name) if stage_name else None,
            "target": escape_log_newlines(target) if target else None,
            "detail": escape_log_newlines(detail) if detail else None,
        },
    )


def _workflow_action_target(request: Request) -> tuple[str, str | None, str | None, str] | None:
    """Parse a Workflow API POST into action, workflow ID, stage, and target."""
    if request.method != "POST":
        return None

    path = request.url.path
    prefix = "/v1/workflow/"
    if not path.startswith(prefix):
        return None

    lifecycle_match = _WORKFLOW_ACTION_PATH.fullmatch(path)
    if lifecycle_match:
        return (
            lifecycle_match.group("action"),
            lifecycle_match.group("workflow_id"),
            lifecycle_match.group("stage_name"),
            path,
        )

    target = path.removeprefix(prefix).rstrip("/")
    return target.rsplit("/", maxsplit=1)[-1], None, None, target


def _audit_outcome(status_code: int) -> AuditOutcome:
    """Map an HTTP response status to a stable audit outcome."""
    if 200 <= status_code < 300:
        return "success"
    if status_code in (401, 403):
        return "denied"
    return "failure"


def install_workflow_audit_logging(app: FastAPI) -> None:
    """Install centralized structured logging for Workflow API actions."""

    @app.middleware("http")
    async def audit_workflow_actions(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Log the normalized result of each Workflow API POST action."""
        action_target = _workflow_action_target(request)
        if action_target is None:
            return await call_next(request)

        action, path_workflow_id, stage_name, target = action_target
        try:
            response = await call_next(request)
        except Exception as exc:
            log_workflow_action(
                request,
                action=action,
                outcome="failure",
                workflow_id=path_workflow_id,
                workflow_type=getattr(request.state, "audit_workflow_type", None),
                stage_name=stage_name,
                target=target,
                detail=type(exc).__name__,
            )
            raise

        outcome = _audit_outcome(response.status_code)
        log_workflow_action(
            request,
            action=action,
            outcome=outcome,
            workflow_id=(path_workflow_id or getattr(request.state, "audit_workflow_id", None)),
            workflow_type=getattr(request.state, "audit_workflow_type", None),
            stage_name=stage_name,
            target=target,
            detail=f"HTTP {response.status_code}" if outcome != "success" else None,
        )
        return response
