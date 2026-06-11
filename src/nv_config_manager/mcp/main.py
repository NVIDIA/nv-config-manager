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
"""NVIDIA Config Manager MCP Streamable HTTP server."""

from __future__ import annotations

import argparse

import uvicorn
from mcp.server.fastmcp import FastMCP
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from nv_config_manager.common.log import configure_logging
from nv_config_manager.mcp.auth import RequestAuthMiddleware, ServiceAuthMiddleware
from nv_config_manager.mcp.settings import MCPSettings
from nv_config_manager.mcp.tools import register_tools

configure_logging(service="mcp")


def create_mcp_server(settings: MCPSettings | None = None) -> FastMCP:
    """Create the FastMCP server and register tools."""
    resolved_settings = settings or MCPSettings.from_config()
    server = FastMCP(
        "nvidia-config-manager-mcp",
        instructions=(
            "Read-only NVIDIA Config Manager operator tools plus explicitly "
            "enabled safe diagnostic workflow starters. When auth is enabled, tools "
            "use the caller's Bearer token for Config Manager APIs. Nautobot auth "
            "mode is configured per environment. Use list_related_mcp_servers to "
            "discover public documentation MCP servers that clients can connect to "
            "directly."
        ),
        host="0.0.0.0",
        json_response=True,
        stateless_http=True,
        streamable_http_path="/mcp",
    )

    @server.custom_route("/healthcheck", methods=["GET"], include_in_schema=False)
    async def healthcheck(request: Request) -> JSONResponse:
        return JSONResponse({"status": "healthy"})

    @server.custom_route("/metrics", methods=["GET"], include_in_schema=False)
    async def metrics(request: Request) -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    register_tools(server, resolved_settings)
    return server


def create_app(settings: MCPSettings | None = None) -> ASGIApp:
    """Create the ASGI application for Streamable HTTP MCP."""
    return ServiceAuthMiddleware(
        RequestAuthMiddleware(create_mcp_server(settings).streamable_http_app())
    )


def main() -> None:
    """CLI entrypoint for the MCP service."""
    parser = argparse.ArgumentParser(description="NVIDIA Config Manager MCP Server")
    parser.add_argument("--port", type=int, default=9000, help="Port to listen on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()

    uvicorn.run(
        create_app(),
        host=args.host,
        port=args.port,
        proxy_headers=True,
        log_config=None,
    )
