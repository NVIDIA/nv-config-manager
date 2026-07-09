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
"""Tests for nv_config_manager_auth.middleware."""

from __future__ import annotations

from unittest.mock import MagicMock, patch


def _import_module():
    import nv_config_manager_auth.middleware as mod

    return mod


class _RedirectResponse(dict):
    status_code = 302


class TestJWTCookieMiddleware:
    def test_init_reads_cookie_env(self, monkeypatch):
        monkeypatch.setenv("NV_CONFIG_MANAGER_JWT_COOKIE", "MyCookie")
        mod = _import_module()
        mw = mod.JWTCookieMiddleware(get_response=MagicMock())
        assert mw._cookie_name == "MyCookie"

    def test_init_default_cookie_name(self, monkeypatch):
        monkeypatch.delenv("NV_CONFIG_MANAGER_JWT_COOKIE", raising=False)
        mod = _import_module()
        mw = mod.JWTCookieMiddleware(get_response=MagicMock())
        assert mw._cookie_name == "NVConfigManagerAccessToken"

    def test_skips_authenticated_user(self, monkeypatch):
        mod = _import_module()
        get_response = MagicMock(return_value="response")
        mw = mod.JWTCookieMiddleware(get_response=get_response)

        request = MagicMock()
        request.user.is_authenticated = True
        request.COOKIES = {"NVConfigManagerAccessToken": "token"}

        result = mw(request)
        assert result == "response"
        get_response.assert_called_once_with(request)

    def test_skips_when_no_cookie(self, monkeypatch):
        monkeypatch.setenv("NV_CONFIG_MANAGER_JWT_COOKIE", "NVConfigManagerAccessToken")
        mod = _import_module()
        get_response = MagicMock(return_value="response")
        mw = mod.JWTCookieMiddleware(get_response=get_response)

        request = MagicMock()
        request.user.is_authenticated = False
        request.COOKIES = {}
        request.META = {}

        with patch("nv_config_manager_auth.middleware._get_providers") as mock_gp:
            result = mw(request)
            mock_gp.assert_not_called()

        assert result == "response"

    def test_logs_in_user_from_proxy_bearer_token(self, monkeypatch):
        monkeypatch.setenv("NV_CONFIG_MANAGER_JWT_COOKIE", "NVConfigManagerAccessToken")
        mod = _import_module()

        import nv_config_manager_auth.jwt_authentication as jwt_mod

        provider = jwt_mod.JwtProviderConfig(
            name="oidc",
            issuer="https://issuer.com",
            audiences=["aud"],
            jwks_uri="https://issuer.com/jwks",
            user_provider=True,
        )
        mock_user = MagicMock(username="jdoe")
        request = MagicMock()
        request.user.is_authenticated = False
        request.COOKIES = {}
        request.META = {"HTTP_AUTHORIZATION": "Bearer proxy-id-token"}
        mw = mod.JWTCookieMiddleware(get_response=MagicMock(return_value="response"))

        with (
            patch("nv_config_manager_auth.middleware._get_providers", return_value=[provider]),
            patch(
                "nv_config_manager_auth.middleware._try_jwt_provider",
                return_value=(mock_user, "oidc:jdoe"),
            ) as mock_try,
            patch("nv_config_manager_auth.middleware.login") as mock_login,
        ):
            result = mw(request)

        mock_try.assert_called_once_with("proxy-id-token", provider)
        mock_login.assert_called_once_with(
            request,
            mock_user,
            backend="nautobot.core.authentication.ObjectPermissionBackend",
        )
        assert result == "response"

    def test_logs_in_user_on_valid_jwt(self, monkeypatch):
        monkeypatch.setenv("NV_CONFIG_MANAGER_JWT_COOKIE", "NVConfigManagerAccessToken")
        mod = _import_module()

        mock_user = MagicMock()
        mock_user.username = "jdoe"

        import nv_config_manager_auth.jwt_authentication as jwt_mod

        provider = jwt_mod.JwtProviderConfig(
            name="oidc",
            issuer="https://issuer.com",
            audiences=["aud"],
            jwks_uri="https://issuer.com/jwks",
            user_provider=True,
        )

        get_response = MagicMock(return_value="response")
        mw = mod.JWTCookieMiddleware(get_response=get_response)

        request = MagicMock()
        request.user.is_authenticated = False
        request.COOKIES = {"NVConfigManagerAccessToken": "valid-jwt"}

        with (
            patch("nv_config_manager_auth.middleware._get_providers", return_value=[provider]),
            patch(
                "nv_config_manager_auth.middleware._try_jwt_provider",
                return_value=(mock_user, "oidc:jdoe"),
            ),
            patch("nv_config_manager_auth.middleware.login") as mock_login,
        ):
            result = mw(request)

        mock_login.assert_called_once_with(
            request,
            mock_user,
            backend="nautobot.core.authentication.ObjectPermissionBackend",
        )
        assert result == "response"

    def test_skips_non_user_providers(self, monkeypatch):
        monkeypatch.setenv("NV_CONFIG_MANAGER_JWT_COOKIE", "NVConfigManagerAccessToken")
        mod = _import_module()

        import nv_config_manager_auth.jwt_authentication as jwt_mod

        service_provider = jwt_mod.JwtProviderConfig(
            name="external-svc",
            issuer="https://external-idp.example.com",
            audiences=["aud"],
            jwks_uri="https://external-idp.example.com/jwks",
            user_provider=False,
        )

        get_response = MagicMock(return_value="response")
        mw = mod.JWTCookieMiddleware(get_response=get_response)

        request = MagicMock()
        request.user.is_authenticated = False
        request.COOKIES = {"NVConfigManagerAccessToken": "some-jwt"}

        with (
            patch(
                "nv_config_manager_auth.middleware._get_providers",
                return_value=[service_provider],
            ),
            patch("nv_config_manager_auth.middleware._try_jwt_provider") as mock_try,
            patch("nv_config_manager_auth.middleware.login") as mock_login,
        ):
            result = mw(request)

        mock_try.assert_not_called()
        mock_login.assert_not_called()
        assert result == "response"

    def test_no_login_when_provider_rejects(self, monkeypatch):
        monkeypatch.setenv("NV_CONFIG_MANAGER_JWT_COOKIE", "NVConfigManagerAccessToken")
        mod = _import_module()

        import nv_config_manager_auth.jwt_authentication as jwt_mod

        provider = jwt_mod.JwtProviderConfig(
            name="oidc",
            issuer="https://issuer.com",
            audiences=["aud"],
            jwks_uri="https://issuer.com/jwks",
            user_provider=True,
        )

        get_response = MagicMock(return_value="response")
        mw = mod.JWTCookieMiddleware(get_response=get_response)

        request = MagicMock()
        request.user.is_authenticated = False
        request.COOKIES = {"NVConfigManagerAccessToken": "bad-jwt"}

        with (
            patch("nv_config_manager_auth.middleware._get_providers", return_value=[provider]),
            patch("nv_config_manager_auth.middleware._try_jwt_provider", return_value=None),
            patch("nv_config_manager_auth.middleware.login") as mock_login,
        ):
            result = mw(request)

        mock_login.assert_not_called()
        assert result == "response"


class TestLogoutRedirectMiddleware:
    def test_rewrites_logout_redirect(self, monkeypatch):
        monkeypatch.setenv(
            "NAUTOBOT_LOGOUT_REDIRECT_URL",
            "https://config-manager.local/auth/logout",
        )
        mod = _import_module()

        response = _RedirectResponse(Location="/")
        get_response = MagicMock(return_value=response)
        request = MagicMock()
        request.path_info = "/logout/"

        mw = mod.LogoutRedirectMiddleware(get_response=get_response)
        result = mw(request)

        assert result["Location"] == "https://config-manager.local/auth/logout"

    def test_leaves_other_paths_unchanged(self, monkeypatch):
        monkeypatch.setenv(
            "NAUTOBOT_LOGOUT_REDIRECT_URL",
            "https://config-manager.local/auth/logout",
        )
        mod = _import_module()

        response = _RedirectResponse(Location="/")
        get_response = MagicMock(return_value=response)
        request = MagicMock()
        request.path_info = "/"

        mw = mod.LogoutRedirectMiddleware(get_response=get_response)
        result = mw(request)

        assert result["Location"] == "/"

    def test_leaves_logout_unchanged_without_redirect_env(self, monkeypatch):
        monkeypatch.delenv("NAUTOBOT_LOGOUT_REDIRECT_URL", raising=False)
        mod = _import_module()

        response = _RedirectResponse(Location="/")
        get_response = MagicMock(return_value=response)
        request = MagicMock()
        request.path_info = "/logout/"

        mw = mod.LogoutRedirectMiddleware(get_response=get_response)
        result = mw(request)

        assert result["Location"] == "/"

    def test_leaves_non_redirect_logout_response_unchanged(self, monkeypatch):
        monkeypatch.setenv(
            "NAUTOBOT_LOGOUT_REDIRECT_URL",
            "https://config-manager.local/auth/logout",
        )
        mod = _import_module()

        response = _RedirectResponse(Location="/")
        response.status_code = 200
        get_response = MagicMock(return_value=response)
        request = MagicMock()
        request.path_info = "/logout/"

        mw = mod.LogoutRedirectMiddleware(get_response=get_response)
        result = mw(request)

        assert result["Location"] == "/"
