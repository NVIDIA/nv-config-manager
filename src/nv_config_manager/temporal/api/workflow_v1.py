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
"""V1 Workflow API Endpoints."""

from __future__ import annotations

import asyncio
import base64
import os
import re
from datetime import datetime
from typing import Any, cast
from uuid import uuid4

import brotli
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, computed_field
from temporalio.client import (
    Client,
    WorkflowExecutionDescription,
    WorkflowExecutionStatus,
    WorkflowHandle,
    WorkflowQueryFailedError,
)
from temporalio.common import SearchAttributes
from temporalio.service import RPCError, RPCStatusCode

from nv_config_manager.common.config import load_config
from nv_config_manager.common.log import LogCategory, get_logger
from nv_config_manager.temporal.api.dynamic_endpoints import (
    register_dynamic_endpoints,
    set_start_workflow_function,
)
from nv_config_manager.temporal.client.redis import RedisClient
from nv_config_manager.temporal.common.mixins.base import BaseMixin
from nv_config_manager.temporal.common.mixins.stage import (
    ReviewSignalInput,
    Stage,
    StageMixin,
    StateEnum,
)
from nv_config_manager.temporal.common.rbac_config import RBACConfig
from nv_config_manager.temporal.converter import get_data_converter
from nv_config_manager.temporal.hello_world.workflows import (
    REGISTERED_WORKFLOWS as HELLO_WORLD_REGISTERED_WORKFLOWS,
)
from nv_config_manager.temporal.ngc.workflows import (
    REGISTERED_WORKFLOWS as NGC_REGISTERED_WORKFLOWS,
)

logger = get_logger(__name__, category=LogCategory.TEMPORAL_API)

router = APIRouter(prefix="/workflow", tags=["workflow"])

_VISIBILITY_SAFE_VALUE = re.compile(r"^[\w.@:/ -]+$")


def _sanitize_visibility_value(value: str, param_name: str) -> str:
    """Validate a value is safe to embed in a Temporal Visibility query literal.

    Raises HTTPException(400) if the value contains characters that could
    allow query injection (single quotes, parentheses, SQL operators, etc.).
    """
    if not _VISIBILITY_SAFE_VALUE.match(value):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid characters in query parameter '{param_name}'",
        )
    return value


class WorkflowListResponse(BaseModel):
    """Workflow List Response Model."""

    workflows: list[WorkflowSummaryResponse]
    next_page_token: str | None


class WorkflowResponse(BaseModel):
    """Workflow Response Model."""

    id: str

    @computed_field
    def href(self) -> str:
        """Calculate URL to Temporal UI Workflow View."""
        ui_server = os.getenv("TEMPORAL_UI", "http://localhost:8080")
        return f"{ui_server}/namespaces/default/workflows/{self.id}"


class WorkflowSummaryResponse(WorkflowResponse):
    """Workflow Summary Response for use in List API."""

    workflow_type: str
    workflow_input: Any
    started_by: str
    start_time: datetime
    close_time: datetime | None
    status: str
    pending_approval: bool
    search_attributes: SearchAttributes

    _NON_TERMINAL_STATES = {
        StateEnum.IN_PROGRESS,
        StateEnum.PENDING_APPROVAL,
        StateEnum.APPROVED,
        StateEnum.REJECTED,
    }

    @staticmethod
    def _should_cache(query: str, data: Any) -> bool:
        """Return False for compressed_stages when any stage is still non-terminal."""
        if query != "compressed_stages" or data is None:
            return True
        try:
            stages = StageMixin.decompress_stages(data)
            return not any(s.state in WorkflowSummaryResponse._NON_TERMINAL_STATES for s in stages)
        except Exception:
            return False

    @staticmethod
    async def _execute_queries(
        handle: WorkflowHandle,
        description: WorkflowExecutionDescription,
        queries: list[str],
    ) -> dict[str, Any]:
        use_cache = description.status not in [
            WorkflowExecutionStatus.RUNNING,
            WorkflowExecutionStatus.CONTINUED_AS_NEW,
        ]
        cache = RedisClient.from_config(load_config())
        results = {}

        for query in queries:
            try:
                if use_cache:
                    data = await cache.get_cached_query(handle.id, query)
                    if data is not None:
                        results[query] = data
                        continue

                data = await handle.query(query)

                if WorkflowSummaryResponse._should_cache(query, data):
                    await cache.cache_query(handle.id, query, data)

                results[query] = data
            except WorkflowQueryFailedError:
                logger.exception(
                    "Workflow %s of type %s has not implemented the %s query.",
                    handle.id,
                    description.workflow_type,
                    query,
                )
                results[query] = None
        return results

    @staticmethod
    async def from_handle(handle: WorkflowHandle) -> WorkflowSummaryResponse:
        """Generate a summary response from a WorkflowHandle object."""
        try:
            description: WorkflowExecutionDescription = await handle.describe()
        except RPCError as e:
            # If workflow doesn't exist, user is not authorized to access it
            if e.status == RPCStatusCode.NOT_FOUND:
                raise HTTPException(
                    status_code=404, detail=f"Workflow with ID '{handle.id}' not found"
                ) from e
            else:
                raise
        try:
            query_results = await WorkflowSummaryResponse._execute_queries(
                handle, description, ["pending_approval", "input"]
            )
            workflow_input = query_results.get("input")
            pending_approval = bool(query_results.get("pending_approval"))
        except RPCError:
            # Should not occur in prod, but there was a point in time in
            # test in which signal functions would throw Exceptions when
            # unexpected input was supplied. Temporal does not like this
            # and the workflow ends up wedged.
            logger.exception(
                "Workflow %s of type %s is in a bad state and cannot accept queries.",
                handle.id,
                description.workflow_type,
            )
            pending_approval = False
            workflow_input = None

        try:
            user = cast(str, description.search_attributes["User"][0])
        except (KeyError, IndexError):
            user = "unknown"

        return WorkflowSummaryResponse(
            id=handle.id,
            started_by=user,
            workflow_input=workflow_input,
            status=description.status.name if description.status else "UNKNOWN",
            start_time=description.start_time,
            close_time=description.close_time,
            workflow_type=description.workflow_type,
            pending_approval=pending_approval,
            search_attributes=description.search_attributes,
        )

    @staticmethod
    async def from_handle_with_semaphore(
        handle: WorkflowHandle, semaphore: asyncio.Semaphore
    ) -> WorkflowSummaryResponse:
        """Generate a summary response from a WorkflowHandle object."""
        async with semaphore:
            return await WorkflowSummaryResponse.from_handle(handle)


class WorkflowDetailResponse(WorkflowSummaryResponse):
    """Workflow Detail Response."""

    stages: list[Stage]
    result: Any

    @staticmethod
    async def from_handle(handle: WorkflowHandle) -> WorkflowDetailResponse:
        """Generate a detailed response from a WorkflowHandle object."""
        try:
            description: WorkflowExecutionDescription = await handle.describe()
        except RPCError as e:
            # If workflow doesn't exist, user is not authorized to access it
            if e.status == RPCStatusCode.NOT_FOUND:
                raise HTTPException(
                    status_code=404, detail=f"Workflow with ID '{handle.id}' not found"
                ) from e
            else:
                raise
        # Not every workflow is guaranteed to implement every query
        try:
            query_results = await WorkflowSummaryResponse._execute_queries(
                handle, description, ["pending_approval", "input", "compressed_stages"]
            )
            workflow_input = query_results.get("input")
            pending_approval = bool(query_results.get("pending_approval"))

            # Decompress and parse stages
            compressed_stages = query_results.get("compressed_stages")
            stages = []
            if compressed_stages is not None:
                stages = StageMixin.decompress_stages(compressed_stages)

        except RPCError:
            # Should not occur in prod, but there was a point in time in
            # test in which signal functions would throw Exceptions when
            # unexpected input was supplied. Temporal does not like this
            # and the workflow ends up wedged.
            logger.exception(
                "Workflow %s of type %s is in a bad state and cannot accept queries.",
                handle.id,
                description.workflow_type,
            )
            pending_approval = False
            workflow_input = None
            stages = []

        result = None
        if description.status == WorkflowExecutionStatus.COMPLETED:
            cache = RedisClient.from_config(load_config())
            result = await cache.get_cached_result(handle.id)
            if result is None:
                result = await handle.result()
                await cache.cache_result(handle.id, result)

        try:
            user = cast(str, description.search_attributes["User"][0])
        except (KeyError, IndexError):
            user = "unknown"

        return WorkflowDetailResponse(
            id=handle.id,
            started_by=user,
            workflow_input=workflow_input,
            status=description.status.name if description.status else "UNKNOWN",
            start_time=description.start_time,
            close_time=description.close_time,
            workflow_type=description.workflow_type,
            pending_approval=pending_approval,
            stages=stages,
            result=result,
            search_attributes=description.search_attributes,
        )


async def get_client() -> Client:
    """Create a temporal client."""
    temporal_server = os.getenv("TEMPORAL_ADDRESS", "localhost:7233")
    return await Client.connect(
        temporal_server,
        namespace="default",
        data_converter=get_data_converter(),
    )


def get_user_info(request: Request) -> tuple[str, set[str]]:
    """Extract the user data from request data."""
    return request.state.user, request.state.roles


async def start_workflow(
    request: Request,
    workflow_class: type[BaseMixin],
    body: BaseModel,
    search_attributes: dict[str, Any] | None = None,
) -> str:
    """Start a workflow with the given input."""

    user, roles = get_user_info(request)

    # Check if the user is authorized to execute the workflow
    rbac_config = RBACConfig()
    workflow_roles = rbac_config.get_workflow_roles(workflow_class.__name__)

    if workflow_roles:
        # Use the roles from the config
        execute_roles = workflow_roles["execute_roles"]
        read_roles = workflow_roles["read_roles"]

        # Check if the user is authorized
        if not (execute_roles.intersection(roles) or "all" in execute_roles):
            logger.error(
                "User %s with roles %s is not authorized to execute workflow %s",
                user,
                roles,
                workflow_class.__name__,
            )
            raise HTTPException(status_code=403, detail="Not authorized to execute this workflow")
    else:
        # No RBAC config for this workflow, deny access
        logger.error(
            "No RBAC configuration found for workflow %s",
            workflow_class.__name__,
        )
        raise HTTPException(status_code=403, detail="No RBAC configuration found for this workflow")

    # Prepare search attributes
    if search_attributes is None:
        search_attributes = {}
    search_attributes["User"] = [user]
    search_attributes["ReadRoles"] = sorted(read_roles)
    search_attributes["ExecuteRoles"] = sorted(execute_roles)

    client = await get_client()
    handle: WorkflowHandle = await client.start_workflow(
        workflow_class.run,
        body,
        id=str(uuid4()),
        task_queue="default-task-queue",
        search_attributes=search_attributes,
    )
    return handle.id


async def is_authorized(request: Request, handle: WorkflowHandle, action: str) -> bool:
    """Check if the user is authorized to perform the action on the workflow."""
    user, roles = get_user_info(request)
    rbac_config = RBACConfig()
    # Admin roles are always permitted
    # This is to handle workflows that predate any RBAC setup
    if roles.intersection(rbac_config.get_admin_roles()):
        return True

    try:
        description: WorkflowExecutionDescription = await handle.describe()
    except RPCError as e:
        # If workflow doesn't exist, user is not authorized to access it
        if e.status == RPCStatusCode.NOT_FOUND:
            raise HTTPException(
                status_code=404, detail=f"Workflow with ID '{handle.id}' not found"
            ) from e
        else:
            # Re-raise if it's a different type of error
            raise

    # convert roles to string set for comparison
    attr = "ExecuteRoles" if action == "execute" else "ReadRoles"
    permitted_roles = description.search_attributes.get(attr, [])
    if not permitted_roles:
        logger.error(
            "Workflow %s of type %s does not have %s search attributes",
            handle.id,
            description.workflow_type,
            attr,
        )
        return False
    if not roles.intersection(permitted_roles):
        logger.error(
            "User %s with roles %s does not have permission to %s workflow %s of type %s",
            user,
            roles,
            action,
            handle.id,
            description.workflow_type,
        )
        return False
    return True


async def signal_workflow(request: Request, workflow_id: str, signal_name: str, *args: Any) -> None:
    """Send signal to workflow."""
    client = await get_client()
    handle = client.get_workflow_handle(workflow_id=workflow_id)

    if await is_authorized(request, handle, "execute"):
        await handle.signal(signal_name, *args)
    else:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.get("/")
async def get_workflows(  # pylint: disable=R0913,R0914
    request: Request,
    user: str | None = None,
    workflow_type: str | None = None,
    device_id: str | None = None,
    device_name: str | None = None,
    device_role: str | None = None,
    device_platform: str | None = None,
    site: str | None = None,
    status: str | None = None,
    limit: int = 100,
    next_page_token: str | None = None,
) -> WorkflowListResponse:
    """Return a filtered list of workflows."""
    _, user_roles = get_user_info(request)
    filters = []
    if user:
        filters.append(f"User = '{_sanitize_visibility_value(user, 'user')}'")
    if workflow_type:
        filters.append(
            f"WorkflowType = '{_sanitize_visibility_value(workflow_type, 'workflow_type')}'"
        )
    if device_id:
        filters.append(f"DeviceID = '{_sanitize_visibility_value(device_id, 'device_id')}'")
    if device_name:
        filters.append(f"DeviceName = '{_sanitize_visibility_value(device_name, 'device_name')}'")
    if device_role:
        filters.append(f"DeviceRole = '{_sanitize_visibility_value(device_role, 'device_role')}'")
    if device_platform:
        filters.append(
            f"DevicePlatform = '{_sanitize_visibility_value(device_platform, 'device_platform')}'"
        )
    if site:
        filters.append(f"Site = '{_sanitize_visibility_value(site, 'site')}'")
    if status:
        filters.append(f"ExecutionStatus = '{_sanitize_visibility_value(status, 'status')}'")
    # Add role filters
    # Permit admin roles to view workflows that are missing
    # RBAC search attributes
    admin_roles = RBACConfig().get_admin_roles()
    if not admin_roles.intersection(user_roles):
        role_filters = [f"ReadRoles = '{role}'" for role in sorted(user_roles)]
        role_filter = " or ".join(role_filters)
        filters.append(f"({role_filter})")
    query = " and ".join(filters) if filters else None

    client = await get_client()

    tasks = []
    semaphore = asyncio.Semaphore(10)
    next_page_token = (
        brotli.decompress(base64.urlsafe_b64decode(next_page_token)) if next_page_token else None
    )
    aiter = client.list_workflows(
        query, limit=limit, page_size=limit, next_page_token=next_page_token
    )

    async for workflow in aiter:
        handle = client.get_workflow_handle(workflow.id)
        tasks.append(
            asyncio.create_task(
                WorkflowSummaryResponse.from_handle_with_semaphore(handle, semaphore)
            )
        )

    workflows = await asyncio.gather(*tasks)
    new_token = aiter.next_page_token
    encoded_token = (
        base64.urlsafe_b64encode(brotli.compress(new_token)).decode() if new_token else None
    )

    return WorkflowListResponse(workflows=workflows, next_page_token=encoded_token)


@router.get("/types")
async def get_workflow_types() -> list[str]:
    """Return the list of registered workflow types."""
    return sorted(
        [wf.__name__ for wf in NGC_REGISTERED_WORKFLOWS + HELLO_WORLD_REGISTERED_WORKFLOWS]
    )


@router.get("/{workflow_id}")
async def get_workflow(workflow_id: str, request: Request) -> WorkflowDetailResponse:
    """Get workflow execution details."""
    client = await get_client()
    handle = client.get_workflow_handle(workflow_id=workflow_id)
    if await is_authorized(request, handle, "read"):
        return await WorkflowDetailResponse.from_handle(handle)
    else:
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/{workflow_id}/approve/{stage_name}")
async def approve(workflow_id: str, stage_name: str, request: Request) -> WorkflowResponse:
    """Send the approve signal to a workflow."""
    user, _ = get_user_info(request)
    await signal_workflow(
        request,
        workflow_id,
        "approve",
        ReviewSignalInput(user=user, stage_name=stage_name),
    )
    return WorkflowResponse(id=workflow_id)


@router.post("/{workflow_id}/reject/{stage_name}")
async def reject(workflow_id: str, stage_name: str, request: Request) -> WorkflowResponse:
    """Send the reject signal to a workflow."""
    user, _ = get_user_info(request)
    await signal_workflow(
        request,
        workflow_id,
        "reject",
        ReviewSignalInput(user=user, stage_name=stage_name),
    )
    return WorkflowResponse(id=workflow_id)


@router.post("/{workflow_id}/retry/{stage_name}")
async def retry(workflow_id: str, stage_name: str, request: Request) -> WorkflowResponse:
    """Send the retry signal for the given stage to a workflow."""
    await signal_workflow(request, workflow_id, "retry", stage_name)
    return WorkflowResponse(id=workflow_id)


@router.get("/{workflow_id}/tech-support/{device_name}")
async def download_tech_support(workflow_id: str, device_name: str, request: Request) -> Response:
    """Download a tech-support bundle stored in Redis by the diagnostics workflow."""
    client = await get_client()
    handle = client.get_workflow_handle(workflow_id=workflow_id)
    if not await is_authorized(request, handle, "read"):
        raise HTTPException(status_code=403, detail="Forbidden")

    redis_key = f"tech_support:{workflow_id}:{device_name}"
    cache = RedisClient.from_config(load_config())
    content: bytes | None = await cache.get(redis_key, deserialize=False)
    if content is None:
        raise HTTPException(
            status_code=404,
            detail=f"Tech-support bundle for '{device_name}' not found (key={redis_key}). It may have expired.",
        )
    safe_name = re.sub(r'[\x00-\x1f\x7f"\\]', "", device_name)
    return Response(
        content=content,
        media_type="application/gzip",
        headers={"Content-Disposition": f'attachment; filename="tech-support_{safe_name}.tar.gz"'},
    )


@router.post("/{workflow_id}/terminate")
async def terminate(workflow_id: str, request: Request) -> WorkflowResponse:
    """Terminate a running workflow."""
    client = await get_client()
    handle = client.get_workflow_handle(workflow_id=workflow_id)

    if await is_authorized(request, handle, "execute"):
        try:
            description = await handle.describe()
            if description.status != WorkflowExecutionStatus.RUNNING:
                status_name = description.status.name if description.status else "UNKNOWN"
                raise HTTPException(
                    status_code=400,
                    detail=f"Workflow is not running (status: {status_name})",
                )
        except RPCError as e:
            if e.status == RPCStatusCode.NOT_FOUND:
                raise HTTPException(
                    status_code=404, detail=f"Workflow with ID '{workflow_id}' not found"
                ) from e
            raise
        await handle.terminate()
    else:
        raise HTTPException(status_code=403, detail="Forbidden")

    return WorkflowResponse(id=workflow_id)


# Register dynamic endpoints for workflows with metadata

# Set the start_workflow function to avoid circular imports
set_start_workflow_function(start_workflow)

# Register dynamic endpoints
register_dynamic_endpoints(router)
