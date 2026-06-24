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
"""Configuration for the NVIDIA Config Manager MCP server."""

from __future__ import annotations

import os
from configparser import ConfigParser
from dataclasses import dataclass
from urllib.parse import urlparse

from nv_config_manager.common.config import load_config, parse_verify_param

NAUTOBOT_AUTH_MODES = {"auto", "jwt", "token"}
MCP_AUTH_CONFIG_ENV_VAR = "NV_CONFIG_MANAGER_MCP_AUTH_INI"
DEFAULT_MCP_AUTH_CONFIG_PATH = "/etc/nv-config-manager/mcp-auth.ini"
PROTECTED_RESOURCE_METADATA_PATH = "/.well-known/oauth-protected-resource"
AUTHORIZATION_SERVER_METADATA_PATH = "/.well-known/oauth-authorization-server"


@dataclass(frozen=True)
class MCPSettings:
    """Resolved MCP service configuration."""

    workflow_api_url: str
    workflow_ui_url: str
    config_store_api_url: str
    dhcp_api_url: str
    nautobot_url: str
    nautobot_read_only_token: str
    nautobot_verify: bool | str
    nautobot_auth_mode: str
    nautobot_token_fallback_enabled: bool
    max_response_bytes: int

    @classmethod
    def from_config(cls, config: ConfigParser | None = None) -> MCPSettings:
        """Resolve MCP settings from nv-config-manager.ini."""
        config = config or load_config()
        use_internal = _get_bool(config, "mcp", "use_internal_endpoints", True)
        configured_auth_mode = _get_value(config, "mcp", "nautobot_auth_mode", "auto").lower()
        if configured_auth_mode not in NAUTOBOT_AUTH_MODES:
            raise ValueError(
                f"mcp.nautobot_auth_mode must be one of: {', '.join(sorted(NAUTOBOT_AUTH_MODES))}"
            )

        return cls(
            workflow_api_url=_service_url(config, "temporal", use_internal),
            workflow_ui_url=_workflow_ui_url(config),
            config_store_api_url=_service_url(config, "config_store.client", use_internal),
            dhcp_api_url=_service_url(config, "dhcp", use_internal),
            nautobot_url=_get_required(config, "nautobot", "server"),
            nautobot_read_only_token=_get_value(config, "mcp", "nautobot_read_only_token", ""),
            nautobot_verify=_verify_value(config, "nautobot"),
            nautobot_auth_mode=_resolve_nautobot_auth_mode(
                configured_auth_mode, _get_required(config, "nautobot", "server")
            ),
            nautobot_token_fallback_enabled=_get_bool(
                config, "mcp", "nautobot_token_fallback_enabled", False
            ),
            max_response_bytes=_get_int(config, "mcp", "max_response_bytes", 100_000),
        )


@dataclass(frozen=True)
class MCPOAuthSettings:
    """Public OAuth metadata advertised for remote MCP clients."""

    enabled: bool
    resource_url: str = ""
    issuer_url: str = ""
    client_id: str = ""
    scopes: tuple[str, ...] = ()
    authorization_endpoint: str = ""
    token_endpoint: str = ""
    jwks_uri: str = ""

    @classmethod
    def from_config(cls, config: ConfigParser | None = None) -> MCPOAuthSettings:
        """Resolve MCP OAuth discovery metadata from mcp-auth.ini."""
        if config is None:
            config = load_mcp_auth_config()
        enabled = _get_bool(config, "mcp.oauth", "enabled", False)
        if not enabled:
            return cls(enabled=False)

        settings = cls(
            enabled=True,
            resource_url=_normalized_required_url(config, "resource_url"),
            issuer_url=_normalized_required_url(config, "issuer_url"),
            client_id=_get_required(config, "mcp.oauth", "client_id").strip(),
            scopes=_parse_scopes(_get_value(config, "mcp.oauth", "scopes", "")),
            authorization_endpoint=_normalized_required_url(config, "authorization_endpoint"),
            token_endpoint=_normalized_required_url(config, "token_endpoint"),
            jwks_uri=_normalize_url(_get_value(config, "mcp.oauth", "jwks_uri", "")),
        )
        if not settings.client_id:
            raise ValueError("Missing required MCP OAuth config value [mcp.oauth] client_id")
        return settings

    @property
    def resource_metadata_url(self) -> str:
        """Return the RFC 9728 protected resource metadata URL for this MCP resource."""
        if not self.enabled or not self.resource_url:
            return ""
        parsed = urlparse(self.resource_url)
        resource_path = parsed.path.rstrip("/")
        return (
            f"{parsed.scheme}://{parsed.netloc}/.well-known/oauth-protected-resource{resource_path}"
        )

    @property
    def authorization_server_url(self) -> str:
        """Return the MCP-origin authorization metadata bridge URL."""
        if not self.enabled or not self.resource_url:
            return ""
        parsed = urlparse(self.resource_url)
        return f"{parsed.scheme}://{parsed.netloc}"

    @property
    def well_known_paths(self) -> frozenset[str]:
        """Return unauthenticated well-known metadata paths served by MCP."""
        paths = {
            PROTECTED_RESOURCE_METADATA_PATH,
            AUTHORIZATION_SERVER_METADATA_PATH,
        }
        if self.enabled and self.resource_metadata_url:
            metadata_path = urlparse(self.resource_metadata_url).path.rstrip("/") or "/"
            paths.add(metadata_path)
        return frozenset(paths)


def load_mcp_auth_config() -> ConfigParser:
    """Load public MCP OAuth metadata from a dedicated ConfigMap-backed INI."""
    config = ConfigParser(interpolation=None, delimiters=("=",))
    config_path = os.getenv(MCP_AUTH_CONFIG_ENV_VAR, DEFAULT_MCP_AUTH_CONFIG_PATH)
    config.read(config_path)
    return config


def _get_value(config: ConfigParser, section: str, key: str, fallback: str) -> str:
    if not config.has_section(section):
        return fallback
    return config[section].get(key, fallback=fallback)


def _get_required(config: ConfigParser, section: str, key: str) -> str:
    if not config.has_section(section) or key not in config[section]:
        raise ValueError(f"Missing required config value [{section}] {key}")
    return config[section][key]


def _get_bool(config: ConfigParser, section: str, key: str, fallback: bool) -> bool:
    if not config.has_section(section):
        return fallback
    return config[section].getboolean(key, fallback=fallback)


def _get_int(config: ConfigParser, section: str, key: str, fallback: int) -> int:
    if not config.has_section(section):
        return fallback
    return config[section].getint(key, fallback=fallback)


def _service_url(config: ConfigParser, section: str, use_internal: bool) -> str:
    key = "api_service" if use_internal else "api_url"
    return _get_required(config, section, key).rstrip("/")


def _workflow_ui_url(config: ConfigParser) -> str:
    configured = _get_value(config, "temporal", "ui_url", "").strip()
    if configured:
        return configured.rstrip("/")

    api_url = _get_value(config, "temporal", "api_url", "").strip()
    parsed = urlparse(api_url)
    if not parsed.scheme or not parsed.netloc:
        return api_url.rstrip("/")

    hostname = parsed.netloc
    if hostname.startswith("workflow."):
        hostname = hostname.removeprefix("workflow.")
    return f"{parsed.scheme}://{hostname}"


def _verify_value(config: ConfigParser, section: str) -> bool | str:
    if not config.has_section(section):
        return True
    return parse_verify_param(config[section])


def _resolve_nautobot_auth_mode(configured_auth_mode: str, nautobot_url: str) -> str:
    if configured_auth_mode != "auto":
        return configured_auth_mode
    if _looks_like_local_nautobot(nautobot_url):
        return "jwt"
    return "token"


def _looks_like_local_nautobot(nautobot_url: str) -> bool:
    parsed = urlparse(nautobot_url)
    hostname = parsed.hostname or nautobot_url
    return (
        hostname == "nautobot"
        or hostname.endswith("-nautobot")
        or hostname.endswith(".svc")
        or ".svc." in hostname
        or hostname.endswith(".svc.cluster.local")
    )


def _normalize_url(value: str) -> str:
    return value.strip().rstrip("/")


def _normalized_required_url(config: ConfigParser, key: str) -> str:
    value = _normalize_url(_get_required(config, "mcp.oauth", key))
    if not value:
        raise ValueError(f"Missing required MCP OAuth config value [mcp.oauth] {key}")
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid MCP OAuth URL value [mcp.oauth] {key}: {value}")
    return value


def _parse_scopes(value: str) -> tuple[str, ...]:
    return tuple(scope for scope in value.replace(",", " ").split() if scope)
