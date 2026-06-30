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
"""OAuth compatibility proxy for providers that reject RFC 8707 resource parameters."""

from __future__ import annotations

import base64
import json
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlparse

import aiohttp
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from nv_config_manager.mcp.settings import MCPOAuthSettings

_DCR_MCP_CLI_CALLBACK_PATH = re.compile(r"/callback/[A-Za-z0-9_-]+")


async def proxy_authorization_request(
    request: Request,
    settings: MCPOAuthSettings,
) -> Response:
    """Redirect an authorization request upstream without its resource parameter."""
    if request.query_params.getlist("client_id") != [settings.client_id]:
        return JSONResponse({"error": "invalid_client"}, status_code=400)

    redirect_uris = request.query_params.getlist("redirect_uri")
    states = request.query_params.getlist("state")
    if (
        len(redirect_uris) != 1
        or len(states) != 1
        or not _is_dcr_mcp_cli_loopback_uri(redirect_uris[0])
    ):
        return JSONResponse({"error": "invalid_request"}, status_code=400)

    upstream_params = tuple(
        (key, value)
        for key, value in request.query_params.multi_items()
        if key not in {"resource", "redirect_uri", "state"}
    ) + (
        ("redirect_uri", settings.callback_proxy_url),
        ("state", _encode_relay_state(redirect_uris[0], states[0])),
    )
    upstream_url = _merge_query_params(settings.authorization_endpoint, upstream_params)
    return RedirectResponse(upstream_url, status_code=302)


async def proxy_authorization_callback(request: Request) -> Response:
    """Relay an upstream authorization response to an MCP CLI loopback callback."""
    states = request.query_params.getlist("state")
    if len(states) != 1:
        return JSONResponse({"error": "invalid_request"}, status_code=400)

    relay_state = _decode_relay_state(states[0])
    if relay_state is None:
        return JSONResponse({"error": "invalid_request"}, status_code=400)

    callback_uri, client_state = relay_state
    callback_params = tuple(
        (key, value) for key, value in request.query_params.multi_items() if key != "state"
    ) + (("state", client_state),)
    callback_url = _merge_query_params(callback_uri, callback_params)
    return RedirectResponse(callback_url, status_code=302)


async def proxy_token_request(
    request: Request,
    settings: MCPOAuthSettings,
) -> Response:
    """Forward a token request upstream without its resource parameter."""
    try:
        params = parse_qsl((await request.body()).decode("utf-8"), keep_blank_values=True)
    except UnicodeDecodeError:
        return JSONResponse({"error": "invalid_request"}, status_code=400)

    if [value for key, value in params if key == "client_id"] != [settings.client_id]:
        return JSONResponse({"error": "invalid_client"}, status_code=400)

    redirect_uris = [value for key, value in params if key == "redirect_uri"]
    if redirect_uris and (
        len(redirect_uris) != 1 or not _is_dcr_mcp_cli_loopback_uri(redirect_uris[0])
    ):
        return JSONResponse({"error": "invalid_request"}, status_code=400)

    upstream_body = urlencode(
        [
            (
                key,
                settings.callback_proxy_url if key == "redirect_uri" else value,
            )
            for key, value in params
            if key != "resource"
        ],
        doseq=True,
    )
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as client:
            async with client.post(
                settings.token_endpoint,
                data=upstream_body,
                headers={
                    "Accept": request.headers.get("accept", "application/json"),
                    "Content-Type": "application/x-www-form-urlencoded",
                },
            ) as upstream_response:
                response_content = await upstream_response.read()
                response_status = upstream_response.status
                response_headers = {
                    key: value
                    for key in ("content-type", "cache-control", "pragma")
                    if (value := upstream_response.headers.get(key))
                }
    except (aiohttp.ClientError, TimeoutError):
        return JSONResponse({"error": "temporarily_unavailable"}, status_code=502)

    return Response(
        content=response_content,
        status_code=response_status,
        headers=response_headers,
    )


def _merge_query_params(url: str, params: tuple[tuple[str, str], ...]) -> str:
    parsed = urlparse(url)
    query = urlencode(
        [*parse_qsl(parsed.query, keep_blank_values=True), *params],
        doseq=True,
    )
    return parsed._replace(query=query).geturl()


def _is_dcr_mcp_cli_loopback_uri(value: str) -> bool:
    parsed = urlparse(value)
    try:
        port = parsed.port
    except ValueError:
        return False
    return (
        parsed.scheme == "http"
        and parsed.hostname == "127.0.0.1"
        and port is not None
        and parsed.netloc == f"127.0.0.1:{port}"
        and _DCR_MCP_CLI_CALLBACK_PATH.fullmatch(parsed.path) is not None
        and not parsed.params
        and not parsed.query
        and not parsed.fragment
    )


def _encode_relay_state(callback_uri: str, client_state: str) -> str:
    payload = json.dumps(
        {"redirect_uri": callback_uri, "state": client_state},
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_relay_state(value: str) -> tuple[str, str] | None:
    try:
        payload: Any = json.loads(
            base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)).decode("utf-8")
        )
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    callback_uri = payload.get("redirect_uri")
    client_state = payload.get("state")
    if (
        not isinstance(callback_uri, str)
        or not isinstance(client_state, str)
        or not _is_dcr_mcp_cli_loopback_uri(callback_uri)
    ):
        return None
    return callback_uri, client_state
