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

Workflows are read through this contract rather than through an ``isinstance``
check, so it works for any class that declares the attributes — the workflow
metadata mixin, a plugin's own base class, or a test double. The accessors bind
to the real mixin unchanged once it moves into this package.

Contract read from a workflow class (every attribute optional):

===============================  =========================================
``workflow_name``                human-readable name, unique across plugins
``workflow_description``         one-line description
``workflow_input_class``         Pydantic model accepted as workflow input
``workflow_api_endpoint``        API path, unique across plugins
``workflow_mcp_enabled``         expose as an MCP tool
``workflow_required_activities`` activity functions the workflow executes
``get_workflow_cli_name()``      CLI command name, unique across plugins
``has_complete_metadata()``      overrides the attribute-derived answer
===============================  =========================================

These accessors are the same ones the worker, API, CLI and MCP consumers read,
so they live here rather than beside the checks in ``validation``.

Temporal identity is read from the definitions the ``@workflow.defn`` and
``@activity.defn`` decorators attach, so this module needs no ``temporalio``
import.
"""

from collections.abc import Callable, Iterable
from typing import Any

from nv_config_manager_workflows.registration.errors import WorkflowRegistrationError

TEMPORAL_WORKFLOW_DEFINITION_ATTRIBUTE = "__temporal_workflow_definition"
TEMPORAL_ACTIVITY_DEFINITION_ATTRIBUTE = "__temporal_activity_definition"

_UNDECLARED = object()

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


def workflow_type_name(workflow: type) -> str:
    """Return the Temporal workflow type, falling back to the class name."""
    name = getattr(_workflow_definition(workflow), "name", None)
    if isinstance(name, str) and name:
        return name
    return workflow.__name__


def workflow_has_definition(workflow: type) -> bool:
    """Return whether the class carries its own usable ``@workflow.defn``."""
    return _is_usable_definition(_workflow_definition(workflow))


def workflow_is_dynamic(workflow: type) -> bool:
    """Return whether the class is declared as Temporal's catch-all workflow."""
    return _is_dynamic_definition(_workflow_definition(workflow))


def activity_name(activity: Callable[..., Any]) -> str:
    """Return the Temporal activity name, falling back to the callable's name."""
    name = getattr(_activity_definition(activity), "name", None)
    if isinstance(name, str) and name:
        return name
    return getattr(activity, "__name__", repr(activity))


def activity_has_definition(activity: Callable[..., Any]) -> bool:
    """Return whether the callable carries a usable ``@activity.defn``."""
    return _is_usable_definition(_activity_definition(activity))


def activity_is_dynamic(activity: Callable[..., Any]) -> bool:
    """Return whether the callable is declared as Temporal's catch-all activity."""
    return _is_dynamic_definition(_activity_definition(activity))


def workflow_api_endpoint(workflow: type) -> str | None:
    """Return the API path the workflow is served under, if any."""
    return getattr(workflow, "workflow_api_endpoint", None)


def normalized_api_endpoint(workflow: type) -> str | None:
    """Return the API path in the form used to compare two workflows.

    A trailing slash does not make a second route, so ``/ngc/backup`` and
    ``/ngc/backup/`` are the same endpoint for conflict purposes even though the
    router is handed the declared spelling.
    """
    endpoint = workflow_api_endpoint(workflow)
    if not isinstance(endpoint, str):
        return None
    return endpoint.rstrip("/") or "/"


def workflow_cli_name(workflow: type) -> str | None:
    """Return the CLI command name for the workflow, or ``None`` if it has none.

    Raises:
        WorkflowRegistrationError: The workflow declares the accessor but does
            not return a usable name; a silently dropped CLI command is the
            failure mode the registry exists to replace.
    """
    if not _has_contract_accessor(workflow, "get_workflow_cli_name"):
        return None
    name = declared_cli_name(workflow)
    if not isinstance(name, str) or not name.strip():
        raise WorkflowRegistrationError(
            f'Workflow "{workflow.__name__}" returns CLI name {name!r} from '
            f"get_workflow_cli_name(), which is not a non-empty string"
        )
    return name


def declared_cli_name(workflow: type) -> Any:
    """Read the declared CLI name without interpreting it."""
    return _call_contract_accessor(workflow, "get_workflow_cli_name")


def workflow_mcp_enabled(workflow: type) -> bool:
    """Return whether the workflow opts in to being exposed as an MCP tool."""
    return bool(getattr(workflow, "workflow_mcp_enabled", False))


def workflow_mcp_tool_name(workflow: type) -> str | None:
    """Return the MCP tool name the workflow is exposed under, if any.

    The tool name comes from the endpoint's last path segment, so two workflows
    with distinct endpoints — ``/ngc/backup`` and ``/acme/backup`` — still claim
    the same tool.
    """
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
    """Return whether the workflow carries every attribute the API needs.

    Defers to a ``has_complete_metadata()`` classmethod when the workflow
    defines one, so the mixin stays the single source of truth for the answer
    the API, the CLI and MCP all branch on.
    """
    if _has_contract_accessor(workflow, "has_complete_metadata"):
        return bool(_call_contract_accessor(workflow, "has_complete_metadata"))
    return not missing_metadata_attributes(workflow)


def missing_metadata_attributes(workflow: type) -> tuple[str, ...]:
    """Return the API metadata attributes the workflow leaves unset."""
    return tuple(name for name in METADATA_ATTRIBUTES if getattr(workflow, name, None) is None)


def workflow_required_activity_names(workflow: type) -> tuple[str, ...]:
    """Return the Temporal activity names the workflow declares that it calls.

    Entries are the activity functions themselves — the same references passed
    to ``workflow.execute_activity`` — resolved here to their Temporal names.
    Plain names are accepted too, for the string form of that call.
    """
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
    """Resolve one required-activity entry to a Temporal activity name."""
    if callable(entry):
        return activity_name(entry)
    if isinstance(entry, str) and entry.strip():
        return entry
    return None


def is_activity_sequence(declared: Any) -> bool:
    """Return whether a required-activity declaration is a usable sequence."""
    return declared is not None and not isinstance(declared, str) and isinstance(declared, Iterable)


def _is_usable_definition(definition: Any) -> bool:
    """Return whether a Temporal definition is one the registry can read."""
    name = _definition_name(definition)
    if name is _UNDECLARED:
        return False
    return name is None or (isinstance(name, str) and bool(name))


def _is_dynamic_definition(definition: Any) -> bool:
    """Return whether a Temporal definition is the ``dynamic=True`` catch-all."""
    return _definition_name(definition) is None


def _definition_name(definition: Any) -> Any:
    """Return the name a Temporal definition declares, or ``_UNDECLARED``.

    ``None`` is a meaningful value here — it is how Temporal spells a dynamic
    handler — so an absent definition and an absent ``name`` need a value of
    their own to stay distinguishable from it.
    """
    if definition is None:
        return _UNDECLARED
    return getattr(definition, "name", _UNDECLARED)


def _workflow_definition(workflow: type) -> Any:
    """Return the Temporal definition ``@workflow.defn`` attached to this class."""
    return vars(workflow).get(TEMPORAL_WORKFLOW_DEFINITION_ATTRIBUTE)


def _activity_definition(activity: Callable[..., Any]) -> Any:
    """Return the Temporal definition ``@activity.defn`` attached, if any."""
    return getattr(activity, TEMPORAL_ACTIVITY_DEFINITION_ATTRIBUTE, None)


def _has_contract_accessor(workflow: type, accessor: str) -> bool:
    """Return whether the workflow exposes a callable contract accessor."""
    return callable(getattr(workflow, accessor, None))


def _call_contract_accessor(workflow: type, accessor: str) -> Any:
    """Call a plugin-supplied accessor, reporting failures as our own error.

    Plugin code sits on the far side of the registration boundary; a plugin that
    declares one of these as an instance method instead of a classmethod, or
    that raises inside it, must surface as a registration error naming the
    workflow rather than as an unhandled ``TypeError`` from registry internals.
    """
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
