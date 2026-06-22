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
"""OAuth metadata advertised by the remote MCP resource server."""

from __future__ import annotations

from typing import Any

from nv_config_manager.mcp.settings import MCPOAuthSettings


def protected_resource_metadata(settings: MCPOAuthSettings) -> dict[str, Any]:
    """Build RFC 9728 protected resource metadata for the MCP endpoint."""
    authorization_servers = _unique_urls([settings.authorization_server_url, settings.issuer_url])
    metadata: dict[str, Any] = {
        "resource": settings.resource_url,
        "authorization_servers": authorization_servers,
        "bearer_methods_supported": ["header"],
        "resource_name": "NVIDIA Config Manager MCP",
    }
    if settings.scopes:
        metadata["scopes_supported"] = list(settings.scopes)
    if settings.jwks_uri:
        metadata["jwks_uri"] = settings.jwks_uri
    return metadata


def _unique_urls(values: list[str]) -> list[str]:
    unique_values: list[str] = []
    for value in values:
        if value and value not in unique_values:
            unique_values.append(value)
    return unique_values


def authorization_server_metadata(settings: MCPOAuthSettings) -> dict[str, Any]:
    """Build OAuth authorization server metadata backed by the configured IdP."""
    metadata: dict[str, Any] = {
        "issuer": settings.issuer_url,
        "authorization_endpoint": settings.authorization_endpoint,
        "token_endpoint": settings.token_endpoint,
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": ["none"],
        "code_challenge_methods_supported": ["S256"],
        "client_id_metadata_document_supported": False,
    }
    if settings.scopes:
        metadata["scopes_supported"] = list(settings.scopes)
    if settings.jwks_uri:
        metadata["jwks_uri"] = settings.jwks_uri
    return metadata
