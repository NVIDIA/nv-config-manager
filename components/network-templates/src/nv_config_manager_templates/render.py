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
"""Template rendering implementation."""

from __future__ import annotations

import logging
import re
import sys
from inspect import getmembers, isfunction
from typing import Any

from jinja2 import (
    ChoiceLoader,
    Environment,
    FileSystemLoader,
    PackageLoader,
    select_autoescape,
)

try:
    from importlib.metadata import entry_points
except ImportError:
    from importlib_metadata import entry_points  # type: ignore

import nv_config_manager_templates.filters.bgp as bgp_filters
import nv_config_manager_templates.filters.device as device_filters
import nv_config_manager_templates.filters.ip as ip_filters
import nv_config_manager_templates.filters.location as location_filters
import nv_config_manager_templates.filters.vault as vault_filters
from nv_config_manager_templates.filters import DeviceNotRenderableError, FilterException
from nv_config_manager_templates.nautobot import NautobotClient

# Modify this constant as new filter modules are implemented
FILTER_MODULES = [
    bgp_filters,
    device_filters,
    ip_filters,
    location_filters,
    vault_filters,
]

logger = logging.getLogger(__name__)


class TemplateLookupException(Exception):
    """Template Lookup Exception."""


class PluginException(Exception):
    """Plugin Exception."""


class Renderer:
    """Manages querying nautobot, rendering templates, and persisting to gitlab."""

    def __init__(
        self,
        nautobot_url: str,
        nautobot_token: str,
        enable_plugins: bool = True,
    ):
        """Initialize Renderer object.

        Args:
            nautobot_url: URL for Nautobot instance
            nautobot_token: Authentication token for Nautobot
            enable_plugins: Whether to discover and load plugins (default: True)
        """
        # Discover plugins first
        self.plugins = []
        if enable_plugins:
            self.plugins = self._discover_plugins()

        # Set up Jinja2 environment with plugin template paths
        loaders = []

        # Add plugin template paths first (higher priority)
        for plugin in self.plugins:
            for path in plugin.get("template_paths", []):
                loaders.append(FileSystemLoader(str(path)))
                logger.info("Loaded template path from plugin: %s", path)

        # Add base template loader last (fallback)
        loaders.append(PackageLoader("nv_config_manager_templates"))

        # Create environment with ChoiceLoader
        loader = ChoiceLoader(loaders) if loaders else PackageLoader("nv_config_manager_templates")
        self.environment = Environment(
            loader=loader,
            autoescape=select_autoescape(),
            trim_blocks=True,
        )

        # Load filters from base library and plugins
        self._dynamically_load_filters()
        self._load_plugin_filters()

        # Store plugin queries for access
        self.plugin_queries = self._collect_plugin_queries()

        self.nautobot_client = NautobotClient(nautobot_url, nautobot_token)

    def _discover_plugins(self) -> list[dict]:
        """Discover installed template plugins via entry points.

        Returns:
            List of plugin dictionaries with metadata and callable functions
        """
        discovered_plugins = []

        try:
            # Look for plugins registered under 'nv_config_manager_templates.plugins'
            eps = entry_points()

            # Handle different versions of importlib.metadata API
            if hasattr(eps, "select"):
                # Python 3.10+
                plugin_eps = eps.select(group="nv_config_manager_templates.plugins")
            else:
                # Python 3.9
                plugin_eps = eps.get("nv_config_manager_templates.plugins", [])

            for entry_point in plugin_eps:
                try:
                    # Load from entry point (could be function or module)
                    loaded = entry_point.load()

                    # Get the module - entry point might load function directly
                    if callable(loaded) and hasattr(loaded, "__module__"):
                        # Entry point loaded a function, get its module
                        plugin_module = sys.modules[loaded.__module__]
                    else:
                        # Entry point loaded the module directly
                        plugin_module = loaded

                    plugin_info = {
                        "name": entry_point.name,
                        "module": plugin_module,
                        "template_paths": [],
                        "filters": {},
                        "queries": {},
                    }

                    # Get template paths
                    if hasattr(plugin_module, "get_template_paths"):
                        paths = plugin_module.get_template_paths()
                        plugin_info["template_paths"] = (
                            paths if isinstance(paths, list) else [paths]
                        )

                    # Get custom filters
                    if hasattr(plugin_module, "get_custom_filters"):
                        plugin_info["filters"] = plugin_module.get_custom_filters()

                    # Get GraphQL queries
                    if hasattr(plugin_module, "get_graphql_queries"):
                        plugin_info["queries"] = plugin_module.get_graphql_queries()

                    discovered_plugins.append(plugin_info)
                    logger.info(
                        "Loaded plugin: %s with %s template path(s)",
                        entry_point.name,
                        len(plugin_info["template_paths"]),
                    )

                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.warning("Failed to load plugin %s: %s", entry_point.name, exc)

        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("Error discovering plugins: %s", exc)

        return discovered_plugins

    def _dynamically_load_filters(self):
        """Dynamically load all public functions from relevant filter modules."""
        for filter_module in FILTER_MODULES:
            for name, func in getmembers(filter_module, isfunction):
                if name.startswith("_"):
                    continue
                if name in self.environment.filters:
                    raise FilterException(f"Conflicting filter names across modules: {name}")
                self.environment.filters[name] = func

    def _load_plugin_filters(self):
        """Load custom filters from discovered plugins."""
        for plugin in self.plugins:
            for name, func in plugin.get("filters", {}).items():
                if name in self.environment.filters:
                    logger.warning(
                        "Plugin %s filter '%s' conflicts with existing filter, skipping",
                        plugin["name"],
                        name,
                    )
                    continue
                self.environment.filters[name] = func
                logger.info("Loaded filter '%s' from plugin %s", name, plugin["name"])

    def _collect_plugin_queries(self) -> dict[str, str]:
        """Collect all GraphQL queries from plugins.

        Returns:
            Dictionary mapping query names to query strings
        """
        all_queries = {}
        for plugin in self.plugins:
            for name, query in plugin.get("queries", {}).items():
                if name in all_queries:
                    logger.warning(
                        "Plugin %s query '%s' conflicts with existing query, skipping",
                        plugin["name"],
                        name,
                    )
                    continue
                all_queries[name] = query
                logger.info("Registered query '%s' from plugin %s", name, plugin["name"])
        return all_queries

    def _plugin_location_name(self, device_data: dict[str, Any]) -> str | None:
        """Return a plugin-provided location name when a plugin owns that mapping."""
        for plugin in self.plugins:
            resolver = getattr(plugin["module"], "get_location_name", None)
            if not resolver:
                continue
            location = resolver(device_data)
            if location:
                return location
        return None

    def execute_plugin_query(
        self,
        query_name: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a plugin-provided GraphQL query.

        Args:
            query_name: Name of the query (as registered by plugin)
            variables: Variables to pass to the query

        Returns:
            Query response data

        Raises:
            PluginException: If query name not found
        """
        if query_name not in self.plugin_queries:
            available = list(self.plugin_queries.keys())
            raise PluginException(f"Query '{query_name}' not found. Available queries: {available}")

        query = self.plugin_queries[query_name]
        return self.nautobot_client.graphql_query(query, variables)

    @staticmethod
    def _normalize_string(src_string: str):
        return re.sub(r"\s+", "-", src_string).lower()

    def load_data(
        self,
        device_id: str | None = None,
        hostname: str | None = None,
        device_data: dict[str, Any] | None = None,
        location_data: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        """Load all necessary data for rendering.

        Returns:
            Tuple of (device_data, location_data, plugin_data)
        """
        if not device_data:
            device_data = self.nautobot_client.load_device_data(
                device_id=device_id, hostname=hostname
            )

        if not location_data:
            location = self._plugin_location_name(device_data) or device_filters.site_name(
                device_data
            )
            location_data = self.nautobot_client.load_location_data(location)

        # Execute plugin queries if any are registered
        plugin_data = self._execute_plugin_queries(device_id, hostname, device_data)

        return device_data, location_data, plugin_data

    def _execute_plugin_queries(
        self,
        device_id: str | None,
        hostname: str | None,
        device_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute all plugin-provided GraphQL queries.

        Args:
            device_id: Device ID for queries that need it
            hostname: Hostname for queries that need it
            device_data: Device data for queries that need it

        Returns:
            Dictionary mapping query names to their results
        """
        plugin_data = {}

        if not self.plugin_queries:
            return plugin_data

        # Determine device_id if not provided
        if not device_id and hostname:
            device_id = self.nautobot_client.device_id_from_hostname(hostname)
        elif not device_id and device_data:
            device_id = device_data.get("data", {}).get("device", {}).get("id")

        for query_name, query in self.plugin_queries.items():
            try:
                # Execute query with common variables
                variables = {}
                if device_id:
                    variables["id"] = device_id
                if hostname:
                    variables["hostname"] = hostname

                result = self.nautobot_client.graphql_query(query, variables)
                plugin_data[query_name] = result
                logger.info("Executed plugin query '%s'", query_name)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("Failed to execute plugin query '%s': %s", query_name, exc)
                plugin_data[query_name] = None

        return plugin_data

    def render_entrypoints(
        self,
        device_id: str | None = None,
        hostname: str | None = None,
        device_data: dict[str, Any] | None = None,
        location_data: dict[str, Any] | None = None,
    ) -> dict[str, str]:
        """Render all entrypoint files for the given device."""
        # Perform GraphQL query (including plugin queries)
        device_data, location_data, plugin_data = self.load_data(
            device_id, hostname, device_data, location_data
        )

        # Load all Entrypoint templates
        entrypoints = self.list_entrypoints(device_data)

        # Render all Entrypoint templates
        files = {}
        for entrypoint in entrypoints:
            files[entrypoint] = self.render(entrypoint, device_data, location_data, plugin_data)
        return files

    def list_entrypoints(self, device_data: dict[str, Any]) -> list[str]:
        """List all entrypoint templates for the given device."""
        platform = self._normalize_string(device_filters.platform(device_data))
        role = self._normalize_string(device_filters.role(device_data))
        try:
            fwver = device_filters.desired_firmware(device_data)
        except DeviceNotRenderableError as exc:
            # The firmware version is only a path component here, so a device
            # without one matches no entrypoints. Report that as an empty set
            # rather than failing the whole render: a device awaiting firmware
            # assignment is a normal state, not a defect.
            logger.info("No entrypoints for %s/%s: %s", platform, role, exc)
            return []

        path = f"{platform}/{role}/{fwver}/entrypoint/"
        return [
            template for template in self.environment.list_templates() if template.startswith(path)
        ]

    def render(
        self,
        template: str,
        device_data: dict[str, Any],
        location_data: dict[str, Any],
        plugin_data: dict[str, Any] | None = None,
    ):
        """Execute a render of a template given the nautobot GraphQL data.

        Args:
            template: Template path to render
            device_data: Device data from Nautobot
            location_data: Location data from Nautobot
            plugin_data: Optional data from plugin queries
        """
        template_obj = self.environment.get_template(template)

        # Build render context
        context = {
            "device_data": device_data,
            "location_data": location_data,
        }

        # Add plugin data to context if available
        if plugin_data:
            context["plugin_data"] = plugin_data

        output = template_obj.render(**context)
        return re.sub(r"\n+", "\n", output).strip()
