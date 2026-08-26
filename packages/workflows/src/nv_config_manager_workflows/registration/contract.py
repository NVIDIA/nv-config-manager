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
"""The attribute contract the registry reads from workflows and activities.

Every registered workflow must inherit
:class:`nv_config_manager_workflows.stage.StageMixin` and
:class:`nv_config_manager_workflows.metadata.WorkflowMetadataMixin`. This module
centralizes how registration and its consumers read the optional declarations
provided by the metadata mixin.

The attributes this module reads from a workflow class (each one optional):

======================================  =========================================
``workflow_name``                       human-readable name, unique across plugins
``workflow_description``                one-line description
``workflow_input_class``                Pydantic model accepted as workflow input
``workflow_api_enabled``                expose for direct invocation through the API
``workflow_api_endpoint``               API path, unique across plugins
``workflow_mcp_enabled``                expose as an MCP tool
``workflow_required_activities``        activity functions the workflow executes
``get_workflow_cli_name()``             CLI command name, unique across plugins
``get_workflow_required_activities()``  overrides the attribute above
======================================  =========================================

These accessors are the same ones the worker, API, CLI and MCP consumers read,
so they live here rather than beside the checks in ``validation``.

Temporal identity — the workflow type and the activity name — comes from the SDK's
own definition readers rather than from the attributes ``@workflow.defn`` and
``@activity.defn`` attach. Reading those attributes by name would make an SDK
rename silent: every class would read as undecorated, and the name accessors
would fall back to the Python name, leaving the duplicate checks in ``validation``
comparing keys Temporal never sees. Importing the definitions turns that same
rename into an import error at startup.
"""

from collections.abc import Callable, Sequence
from typing import Any

from temporalio.activity import _Definition as ActivityDefinition
from temporalio.workflow import _Definition as WorkflowDefinition

from nv_config_manager_workflows.registration.errors import WorkflowRegistrationError

METADATA_ATTRIBUTES = (
    "workflow_name",
    "workflow_description",
    "workflow_input_class",
    "workflow_api_endpoint",
)


def workflow_class_name(workflow: type) -> str:
    """Return the Python class name, which RBAC and the API catalog key on."""
    return workflow.__name__


def workflow_declared_name(workflow: type) -> str | None:
    """Return the human-readable workflow name, or ``None`` when undeclared."""
    return getattr(workflow, "workflow_name", None)


def workflow_type_name(workflow: type) -> str | None:
    """Return the Temporal workflow type, or ``None`` when the class declares none."""
    definition = _workflow_definition(workflow)
    return definition.name if definition is not None else None


def workflow_has_definition(workflow: type) -> bool:
    """Return whether the class carries its own ``@workflow.defn``."""
    return _workflow_definition(workflow) is not None


def workflow_is_dynamic(workflow: type) -> bool:
    """Return whether the class is declared as Temporal's catch-all workflow."""
    definition = _workflow_definition(workflow)
    return definition is not None and definition.name is None


def activity_name(activity: Callable[..., Any]) -> str | None:
    """Return the Temporal activity name, or ``None`` when the callable declares none.

    ``None`` is both the undecorated and the dynamic case, as for
    :func:`workflow_type_name`.
    """
    definition = _activity_definition(activity)
    return definition.name if definition is not None else None


def activity_has_definition(activity: Callable[..., Any]) -> bool:
    """Return whether the callable carries an ``@activity.defn``."""
    return _activity_definition(activity) is not None


def activity_is_dynamic(activity: Callable[..., Any]) -> bool:
    """Return whether the callable is declared as Temporal's catch-all activity."""
    definition = _activity_definition(activity)
    return definition is not None and definition.name is None


def workflow_api_endpoint(workflow: type) -> str | None:
    """Return the API path the workflow is served under, if any."""
    return getattr(workflow, "workflow_api_endpoint", None)


def workflow_api_enabled(workflow: type) -> bool:
    """Return whether the workflow opts in to direct invocation through the API."""
    return bool(getattr(workflow, "workflow_api_enabled", False))


def normalized_api_endpoint(workflow: type) -> str | None:
    """Return the API path in the form used to compare two workflows."""
    endpoint = workflow_api_endpoint(workflow)
    if not isinstance(endpoint, str):
        return None
    return endpoint.rstrip("/") or "/"


def workflow_cli_name(workflow: type) -> Any:
    """Read the declared CLI command name without interpreting it.

    ``validation`` rejects a declaration that is not a usable name, so a
    silently dropped CLI command stays impossible.
    """
    return _call_contract_accessor(workflow, "get_workflow_cli_name")


def workflow_mcp_enabled(workflow: type) -> bool:
    """Return whether the workflow opts in to being exposed as an MCP tool."""
    return bool(getattr(workflow, "workflow_mcp_enabled", False))


def workflow_mcp_tool_name(workflow: type) -> str | None:
    """Return the MCP tool name the workflow is exposed under, if any."""
    if not workflow_mcp_enabled(workflow):
        return None
    endpoint = workflow_api_endpoint(workflow)
    if not isinstance(endpoint, str) or not endpoint.strip("/"):
        return None
    return mcp_tool_name_for_endpoint(endpoint)


def mcp_tool_name_for_endpoint(endpoint: str) -> str:
    """Derive the MCP tool name an API endpoint is exposed under."""
    slug = endpoint.strip("/").split("/")[-1]
    return f"run_{slug.replace('-', '_')}"


def workflow_has_complete_metadata(workflow: type) -> bool:
    """Return whether the workflow carries every attribute the API needs."""
    return not missing_metadata_attributes(workflow)


def missing_metadata_attributes(workflow: type) -> tuple[str, ...]:
    """Return the API metadata attributes the workflow leaves unset."""
    return tuple(name for name in METADATA_ATTRIBUTES if getattr(workflow, name, None) is None)


def workflow_required_activity_names(workflow: type) -> tuple[str, ...]:
    """Return the Temporal activity names the workflow declares that it calls."""
    declared = declared_required_activities(workflow)
    if not is_activity_sequence(declared):
        return ()
    resolved = (required_activity_name(entry) for entry in declared)
    return tuple(name for name in resolved if name is not None)


def declared_required_activities(workflow: type) -> Any:
    """Read the required-activity declaration without interpreting it."""
    if _has_contract_accessor(workflow, "get_workflow_required_activities"):
        return _call_contract_accessor(workflow, "get_workflow_required_activities")
    return getattr(workflow, "workflow_required_activities", None)


def required_activity_name(entry: Any) -> str | None:
    """Resolve one required-activity entry to a Temporal activity name.

    A callable carrying no ``@activity.defn`` resolves to ``None`` like any other
    unusable entry, because ``workflow.execute_activity`` would reject it too.
    """
    if callable(entry):
        return activity_name(entry)
    if isinstance(entry, str) and entry.strip():
        return entry
    return None


def is_activity_sequence(declared: Any) -> bool:
    """Return whether a required-activity declaration is a usable sequence."""
    return not isinstance(declared, str) and isinstance(declared, Sequence)


def _workflow_definition(workflow: type) -> WorkflowDefinition | None:
    """Return the Temporal definition ``@workflow.defn`` attached to this class."""
    return WorkflowDefinition.from_class(workflow)


def _activity_definition(activity: Callable[..., Any]) -> ActivityDefinition | None:
    """Return the Temporal definition ``@activity.defn`` attached, if any."""
    return ActivityDefinition.from_callable(activity)


def _has_contract_accessor(workflow: type, accessor: str) -> bool:
    """Return whether the workflow exposes a callable contract accessor."""
    return callable(getattr(workflow, accessor, None))


def _call_contract_accessor(workflow: type, accessor: str) -> Any:
    """Call a plugin-supplied accessor, reporting failures as our own error."""
    method = getattr(workflow, accessor, None)
    if not callable(method):
        return None
    try:
        return method()
    except WorkflowRegistrationError:
        raise
    except Exception as exc:
        raise WorkflowRegistrationError(
            f'Workflow "{workflow.__name__}" failed in {accessor}(): {exc}'
        ) from exc
