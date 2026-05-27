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
"""Django middleware for JWT cookie authentication.

Authenticates Nautobot web UI sessions using the JWT cookie set by the
Envoy Gateway OIDC flow.  This is the Django-side counterpart to
:class:`~nv_config_manager_auth.jwt_authentication.NVConfigManagerJWTAuthentication` (which
handles DRF API requests).

When a user visits the Nautobot UI with a valid JWT cookie but no
active Django session, this middleware validates the JWT, creates or
looks up the Django user, and logs them in -- giving them a seamless
SSO experience without needing ``RemoteUserBackend``.
"""

from __future__ import annotations

import logging
import os
from typing import Any

from django.contrib.auth import login
from django.http import HttpRequest, HttpResponse

log = logging.getLogger(__name__)


class JWTCookieMiddleware:
    """Authenticate Django sessions from the gateway's JWT cookie.

    Processing order:

    1. Skip if user is already authenticated (session or prior middleware).
    2. Read the JWT from the configured cookie (``NV_CONFIG_MANAGER_JWT_COOKIE``).
    3. Validate against each configured ``user_provider`` JWT provider.
    4. On success, log the user into Django's session framework.

    Must be placed **after** ``SessionMiddleware`` and
    ``AuthenticationMiddleware`` in ``MIDDLEWARE``.
    """

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response
        self._cookie_name = os.getenv("NV_CONFIG_MANAGER_JWT_COOKIE", "NVConfigManagerAccessToken")

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if not request.user.is_authenticated:
            self._try_jwt_login(request)
        return self.get_response(request)

    def _try_jwt_login(self, request: HttpRequest) -> None:
        token = request.COOKIES.get(self._cookie_name)
        if not token:
            return

        from nv_config_manager_auth.jwt_authentication import (
            _get_providers,
            _try_jwt_provider,
        )

        for provider in _get_providers():
            if not provider.user_provider:
                continue
            result = _try_jwt_provider(token, provider)
            if result is not None:
                user, _info = result
                login(request, user, backend="nautobot.core.authentication.ObjectPermissionBackend")
                log.debug("JWT cookie login: %s via %s", user.username, provider.name)
                return
