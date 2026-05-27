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
"""RBAC Configuration Loader."""

import os

import yaml


class RBACConfig:
    """RBAC Configuration loader."""

    _instance = None
    _config: dict[str, dict[str, set[str]]] = {}
    _config_path = "/etc/rbac/rbac.yaml"
    _admin_roles: set[str] = set()

    def __new__(cls) -> "RBACConfig":
        """Singleton pattern."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load_config()
        return cls._instance

    def _load_config(self) -> None:
        """Load RBAC configuration from file."""
        if not os.path.exists(self._config_path):
            return

        with open(self._config_path, encoding="utf-8") as f:
            config = yaml.safe_load(f)

        for admin_role in config.get("admin_roles", []):
            self._admin_roles.add(admin_role)

        for workflow in config.get("workflows", []):
            name = workflow.get("name")
            if not name:
                continue

            # Store roles as strings directly
            read_roles = set(workflow.get("read_roles", []))
            execute_roles = set(workflow.get("execute_roles", []))

            self._config[name] = {
                "read_roles": read_roles,
                "execute_roles": execute_roles,
            }

    def get_workflow_roles(self, workflow_name: str) -> dict[str, set[str]] | None:
        """Get roles for a workflow."""
        return self._config.get(workflow_name)

    def get_all_workflows(self) -> dict[str, dict[str, set[str]]]:
        """Get all workflow configurations."""
        return self._config

    def get_admin_roles(self) -> set[str]:
        """Get all admin roles."""
        return self._admin_roles
