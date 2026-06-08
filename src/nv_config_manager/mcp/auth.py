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
"""Request-scoped auth handling for the MCP server."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from starlette.types import ASGIApp, Receive, Scope, Send

AUTHORIZATION_HEADER = "authorization"
AUTH_CONTEXT_HEADERS = {
    "x-auth-request-email": "X-Auth-Request-Email",
    "x-auth-request-user": "X-Auth-Request-User",
    "x-auth-request-preferred-username": "X-Auth-Request-Preferred-Username",
    "x-auth-request-name": "X-Auth-Request-Name",
    "x-auth-request-groups": "X-Auth-Request-Groups",
    "x-auth-request-subject": "X-Auth-Request-Subject",
}


class MissingBearerTokenError(Exception):
    """Raised when an MCP tool requires the caller's bearer token."""


@dataclass(frozen=True)
class RequestAuth:
    """Authentication material extracted from the inbound MCP HTTP request."""

    authorization: str | None
    identity_headers: dict[str, str]

    @classmethod
    def from_asgi_headers(cls, headers: list[tuple[bytes, bytes]]) -> RequestAuth:
        """Build auth context from ASGI headers."""
        decoded_headers = {
            key.decode("latin-1").lower(): value.decode("latin-1") for key, value in headers
        }
        identity_headers = {
            canonical_name: decoded_headers[header_name]
            for header_name, canonical_name in AUTH_CONTEXT_HEADERS.items()
            if decoded_headers.get(header_name)
        }
        return cls(
            authorization=decoded_headers.get(AUTHORIZATION_HEADER),
            identity_headers=identity_headers,
        )

    @property
    def bearer_authorization(self) -> str | None:
        """Return the inbound Bearer authorization header, if one is present."""
        if self.authorization and self.authorization.lower().startswith("bearer "):
            return self.authorization
        return None


_REQUEST_AUTH: ContextVar[RequestAuth | None] = ContextVar("mcp_request_auth", default=None)


class RequestAuthMiddleware:
    """Capture inbound HTTP auth headers for downstream service calls."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> Any:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        auth = RequestAuth.from_asgi_headers(scope.get("headers", []))
        token = _REQUEST_AUTH.set(auth)
        try:
            return await self.app(scope, receive, send)
        finally:
            _REQUEST_AUTH.reset(token)


def current_request_auth() -> RequestAuth | None:
    """Return auth context for the current MCP request."""
    return _REQUEST_AUTH.get()


def downstream_auth_headers() -> dict[str, str]:
    """Return headers for downstream NVIDIA Config Manager APIs.

    MCP tools must act with the caller's authority. Do not fall back to service
    identity or gateway-derived identity headers here; Nautobot is handled
    separately because some environments intentionally use a read-only token.
    """
    auth = current_request_auth()
    if auth:
        bearer = auth.bearer_authorization
        if bearer:
            return {"Authorization": bearer}

    raise MissingBearerTokenError("MCP request must include an Authorization: Bearer token.")


def user_bearer_authorization() -> str | None:
    """Return the inbound user Bearer authorization header, if available."""
    auth = current_request_auth()
    if not auth:
        return None
    return auth.bearer_authorization
