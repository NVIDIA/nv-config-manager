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
"""Workflow Metadata Mixin."""

import re

from pydantic import BaseModel

from nv_config_manager.temporal.common.lock import WorkflowLockSpec


class WorkflowMetadataMixin:
    """Mixin to provide metadata for workflows."""

    # Class attributes that should be overridden in workflow classes
    workflow_name: str | None = None
    workflow_description: str | None = None
    workflow_input_class: type[BaseModel] | None = None
    workflow_api_endpoint: str | None = None
    workflow_namespace: str | None = None
    workflow_mcp_enabled: bool = False
    workflow_lock: WorkflowLockSpec | None = None

    @classmethod
    def get_workflow_name(cls) -> str:
        """Get the human-readable workflow name."""
        if cls.workflow_name is None:
            raise ValueError(f"Workflow {cls.__name__} is missing workflow_name metadata")
        return cls.workflow_name

    @classmethod
    def get_workflow_description(cls) -> str:
        """Get the workflow description."""
        if cls.workflow_description:
            return cls.workflow_description

        # Fallback to docstring
        if cls.__doc__:
            return cls.__doc__.strip().split("\n")[0].replace('"""', "").strip()

        return f"Execute {cls.__name__} workflow"

    @classmethod
    def get_workflow_input_class(cls) -> type[BaseModel] | None:
        """Get the workflow input class."""
        return cls.workflow_input_class

    @classmethod
    def get_workflow_api_endpoint(cls) -> str | None:
        """Get the workflow API endpoint."""
        return cls.workflow_api_endpoint

    @classmethod
    def get_workflow_namespace(cls) -> str | None:
        """Get the workflow namespace."""
        return cls.workflow_namespace

    @classmethod
    def get_workflow_cli_name(cls) -> str:
        """Get the CLI command name for this workflow."""
        # Convert CamelCase to kebab-case
        name = cls.__name__
        # Remove 'Workflow' suffix if present
        if name.endswith("Workflow"):
            name = name[:-8]

        # Insert hyphens before uppercase letters (except the first one)
        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1-\2", name)
        # Insert hyphens before uppercase letters that follow lowercase letters or numbers
        return re.sub("([a-z0-9])([A-Z])", r"\1-\2", s1).lower()

    @classmethod
    def get_workflow_mcp_enabled(cls) -> bool:
        """Return whether this workflow can be exposed as an MCP tool."""
        return cls.workflow_mcp_enabled

    @classmethod
    def get_workflow_lock(cls) -> WorkflowLockSpec | None:
        """Return the per-resource lock this workflow serializes on, if any."""
        return cls.workflow_lock

    @classmethod
    def has_complete_metadata(cls) -> bool:
        """Check if the workflow has complete metadata defined."""
        return (
            cls.workflow_name is not None
            and cls.workflow_description is not None
            and cls.workflow_input_class is not None
            and cls.workflow_api_endpoint is not None
        )
