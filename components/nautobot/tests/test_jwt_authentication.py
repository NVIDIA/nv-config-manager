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
"""Tests for nv_config_manager_auth.jwt_authentication module."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_module():
    """Import jwt_authentication after Django stubs are in place."""
    import nv_config_manager_auth.jwt_authentication as mod

    return mod


# ---------------------------------------------------------------------------
# _derive_jwks_uri
# ---------------------------------------------------------------------------


class TestDeriveJwksUri:
    def test_azure_ad_issuer(self):
        mod = _import_module()
        uri = mod._derive_jwks_uri("https://login.microsoftonline.com/tenant-id/v2.0")
        assert uri == "https://login.microsoftonline.com/tenant-id/v2.0/discovery/v2.0/keys"

    def test_generic_issuer(self):
        mod = _import_module()
        uri = mod._derive_jwks_uri("https://auth.example.com")
        assert uri == "https://auth.example.com/.well-known/jwks.json"

    def test_trailing_slash_stripped(self):
        mod = _import_module()
        uri = mod._derive_jwks_uri("https://auth.example.com/")
        assert uri == "https://auth.example.com/.well-known/jwks.json"


# ---------------------------------------------------------------------------
# _load_jwt_providers
# ---------------------------------------------------------------------------


class TestLoadJwtProviders:
    def test_empty_env(self, monkeypatch):
        monkeypatch.delenv("NV_CONFIG_MANAGER_JWT_PROVIDERS", raising=False)
        mod = _import_module()
        assert mod._load_jwt_providers() == []

    def test_invalid_json(self, monkeypatch):
        monkeypatch.setenv("NV_CONFIG_MANAGER_JWT_PROVIDERS", "not-json")
        mod = _import_module()
        assert mod._load_jwt_providers() == []

    def test_valid_single_provider(self, monkeypatch):
        providers_json = json.dumps(
            [
                {
                    "name": "oidc",
                    "issuer": "https://login.microsoftonline.com/tenant/v2.0",
                    "audiences": ["api://client-id"],
                    "user_provider": True,
                }
            ]
        )
        monkeypatch.setenv("NV_CONFIG_MANAGER_JWT_PROVIDERS", providers_json)
        mod = _import_module()
        providers = mod._load_jwt_providers()

        assert len(providers) == 1
        p = providers[0]
        assert p.name == "oidc"
        assert p.issuer == "https://login.microsoftonline.com/tenant/v2.0"
        assert p.audiences == ["api://client-id"]
        assert p.user_provider is True
        assert "discovery/v2.0/keys" in p.jwks_uri

    def test_multiple_providers(self, monkeypatch):
        providers_json = json.dumps(
            [
                {"name": "a", "issuer": "https://a.example.com", "audiences": []},
                {"name": "b", "issuer": "https://b.example.com", "audiences": ["aud"]},
            ]
        )
        monkeypatch.setenv("NV_CONFIG_MANAGER_JWT_PROVIDERS", providers_json)
        mod = _import_module()
        providers = mod._load_jwt_providers()
        assert len(providers) == 2
        assert providers[0].name == "a"
        assert providers[1].name == "b"

    def test_skips_entries_without_issuer(self, monkeypatch):
        providers_json = json.dumps(
            [
                {"name": "no-issuer", "audiences": ["x"]},
                {"name": "has-issuer", "issuer": "https://ok.com", "audiences": ["x"]},
            ]
        )
        monkeypatch.setenv("NV_CONFIG_MANAGER_JWT_PROVIDERS", providers_json)
        mod = _import_module()
        providers = mod._load_jwt_providers()
        assert len(providers) == 1
        assert providers[0].name == "has-issuer"

    def test_explicit_jwks_uri_used(self, monkeypatch):
        providers_json = json.dumps(
            [
                {
                    "name": "custom",
                    "issuer": "https://custom.com",
                    "audiences": [],
                    "jwks_uri": "https://custom.com/keys",
                }
            ]
        )
        monkeypatch.setenv("NV_CONFIG_MANAGER_JWT_PROVIDERS", providers_json)
        mod = _import_module()
        providers = mod._load_jwt_providers()
        assert providers[0].jwks_uri == "https://custom.com/keys"

    def test_default_claim_fields(self, monkeypatch):
        providers_json = json.dumps([{"name": "min", "issuer": "https://min.com", "audiences": []}])
        monkeypatch.setenv("NV_CONFIG_MANAGER_JWT_PROVIDERS", providers_json)
        mod = _import_module()
        p = mod._load_jwt_providers()[0]
        assert p.claim_user == "preferred_username"
        assert p.claim_email == "email"
        assert p.claim_groups == "roles"
        assert p.user_provider is False


# ---------------------------------------------------------------------------
# _spiffe_id_to_workload_name
# ---------------------------------------------------------------------------


class TestSpiffeIdToWorkloadName:
    def test_normal_spiffe_id(self):
        mod = _import_module()
        result = mod._spiffe_id_to_workload_name("spiffe://domain/ns/prod/sa/render")
        assert result == "ns-prod-sa-render"

    def test_short_path(self):
        mod = _import_module()
        result = mod._spiffe_id_to_workload_name("spiffe://domain/workload")
        assert result == "workload"

    def test_too_short_returns_original(self):
        mod = _import_module()
        result = mod._spiffe_id_to_workload_name("no-slashes")
        assert result == "no-slashes"


# ---------------------------------------------------------------------------
# _strip_email_domain
# ---------------------------------------------------------------------------


class TestStripEmailDomain:
    def test_with_domain(self):
        mod = _import_module()
        assert mod._strip_email_domain("user@nvidia.com") == "user"

    def test_without_domain(self):
        mod = _import_module()
        assert mod._strip_email_domain("username") == "username"

    def test_empty(self):
        mod = _import_module()
        assert mod._strip_email_domain("") == ""


# ---------------------------------------------------------------------------
# _extract_token
# ---------------------------------------------------------------------------


class TestExtractToken:
    def test_bearer_header(self):
        mod = _import_module()
        request = MagicMock()
        request.META = {"HTTP_AUTHORIZATION": "Bearer my-jwt-token"}
        request.COOKIES = {}
        assert mod._extract_token(request) == "my-jwt-token"

    def test_bearer_case_insensitive(self):
        mod = _import_module()
        request = MagicMock()
        request.META = {"HTTP_AUTHORIZATION": "bearer my-jwt-token"}
        request.COOKIES = {}
        assert mod._extract_token(request) == "my-jwt-token"

    def test_token_prefix_returns_none(self):
        mod = _import_module()
        request = MagicMock()
        request.META = {"HTTP_AUTHORIZATION": "Token abc123"}
        request.COOKIES = {}
        assert mod._extract_token(request) is None

    def test_cookie_fallback(self, monkeypatch):
        monkeypatch.setenv("NV_CONFIG_MANAGER_JWT_COOKIE", "NVConfigManagerAccessToken")
        mod = _import_module()
        request = MagicMock()
        request.META = {}
        request.COOKIES = {"NVConfigManagerAccessToken": "cookie-jwt"}
        assert mod._extract_token(request) == "cookie-jwt"

    def test_no_token_anywhere(self, monkeypatch):
        monkeypatch.setenv("NV_CONFIG_MANAGER_JWT_COOKIE", "NVConfigManagerAccessToken")
        mod = _import_module()
        request = MagicMock()
        request.META = {}
        request.COOKIES = {}
        assert mod._extract_token(request) is None

    def test_custom_cookie_name(self, monkeypatch):
        monkeypatch.setenv("NV_CONFIG_MANAGER_JWT_COOKIE", "MyCustomCookie")
        mod = _import_module()
        request = MagicMock()
        request.META = {}
        request.COOKIES = {"MyCustomCookie": "custom-jwt"}
        assert mod._extract_token(request) == "custom-jwt"

    def test_empty_bearer_token(self):
        mod = _import_module()
        request = MagicMock()
        request.META = {"HTTP_AUTHORIZATION": "Bearer   "}
        request.COOKIES = {}
        assert mod._extract_token(request) is None


# ---------------------------------------------------------------------------
# _get_superuser_groups
# ---------------------------------------------------------------------------


class TestGetSuperuserGroups:
    def test_unset_returns_empty(self, monkeypatch):
        monkeypatch.delenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", raising=False)
        mod = _import_module()
        assert mod._get_superuser_groups() == set()

    def test_empty_string_returns_empty(self, monkeypatch):
        monkeypatch.setenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", "")
        mod = _import_module()
        assert mod._get_superuser_groups() == set()

    def test_parses_comma_separated(self, monkeypatch):
        monkeypatch.setenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", "nautobot-admins,nv-config-manager-admins")
        mod = _import_module()
        assert mod._get_superuser_groups() == {"nautobot-admins", "nv-config-manager-admins"}

    def test_strips_whitespace_and_blanks(self, monkeypatch):
        monkeypatch.setenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", "  a , , b  ,c")
        mod = _import_module()
        assert mod._get_superuser_groups() == {"a", "b", "c"}


# ---------------------------------------------------------------------------
# _extract_groups
# ---------------------------------------------------------------------------


class TestExtractGroups:
    def test_list_claim(self):
        mod = _import_module()
        assert mod._extract_groups({"roles": ["a", "b"]}, "roles") == {"a", "b"}

    def test_string_claim(self):
        mod = _import_module()
        assert mod._extract_groups({"roles": "a, b ,c"}, "roles") == {"a", "b", "c"}

    def test_missing_claim(self):
        mod = _import_module()
        assert mod._extract_groups({}, "roles") == set()

    def test_filters_falsy_list_entries(self):
        mod = _import_module()
        assert mod._extract_groups({"roles": ["a", "", None, "b"]}, "roles") == {"a", "b"}

    def test_unsupported_claim_type(self):
        mod = _import_module()
        assert mod._extract_groups({"roles": {"nested": "dict"}}, "roles") == set()

    def test_uses_configured_claim_name(self):
        mod = _import_module()
        claims = {"groups": ["g1"], "roles": ["r1"]}
        assert mod._extract_groups(claims, "groups") == {"g1"}
        assert mod._extract_groups(claims, "roles") == {"r1"}


# ---------------------------------------------------------------------------
# _sync_superuser_status
# ---------------------------------------------------------------------------


class TestSyncSuperuserStatus:
    def _make_user(self, *, is_superuser=False, is_staff=False):
        user = MagicMock()
        user.username = "jdoe"
        user.is_superuser = is_superuser
        user.is_staff = is_staff
        return user

    def test_no_op_when_env_unset(self, monkeypatch):
        monkeypatch.delenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", raising=False)
        mod = _import_module()
        user = self._make_user(is_superuser=True, is_staff=True)

        mod._sync_superuser_status(user, {"any-group"})

        user.save.assert_not_called()
        assert user.is_superuser is True
        assert user.is_staff is True

    def test_promotes_when_group_matches(self, monkeypatch):
        monkeypatch.setenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", "nautobot-admins,nv-config-manager-admins")
        mod = _import_module()
        user = self._make_user(is_superuser=False, is_staff=False)

        mod._sync_superuser_status(user, {"nautobot-admins", "other"})

        assert user.is_superuser is True
        assert user.is_staff is True
        user.save.assert_called_once_with(update_fields=["is_superuser", "is_staff"])

    def test_demotes_when_no_group_matches(self, monkeypatch):
        monkeypatch.setenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", "nautobot-admins")
        mod = _import_module()
        user = self._make_user(is_superuser=True, is_staff=True)

        mod._sync_superuser_status(user, {"some-other-group"})

        assert user.is_superuser is False
        assert user.is_staff is False
        user.save.assert_called_once_with(update_fields=["is_superuser", "is_staff"])

    def test_demotes_when_user_has_no_groups(self, monkeypatch):
        monkeypatch.setenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", "nautobot-admins")
        mod = _import_module()
        user = self._make_user(is_superuser=True, is_staff=True)

        mod._sync_superuser_status(user, set())

        assert user.is_superuser is False
        assert user.is_staff is False
        user.save.assert_called_once()

    def test_idempotent_when_already_superuser(self, monkeypatch):
        monkeypatch.setenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", "nautobot-admins")
        mod = _import_module()
        user = self._make_user(is_superuser=True, is_staff=True)

        mod._sync_superuser_status(user, {"nautobot-admins"})

        user.save.assert_not_called()

    def test_idempotent_when_already_non_superuser(self, monkeypatch):
        monkeypatch.setenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", "nautobot-admins")
        mod = _import_module()
        user = self._make_user(is_superuser=False, is_staff=False)

        mod._sync_superuser_status(user, {"some-other-group"})

        user.save.assert_not_called()

    def test_repairs_partial_state(self, monkeypatch):
        monkeypatch.setenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", "nautobot-admins")
        mod = _import_module()
        user = self._make_user(is_superuser=True, is_staff=False)

        mod._sync_superuser_status(user, {"nautobot-admins"})

        assert user.is_staff is True
        user.save.assert_called_once_with(update_fields=["is_staff"])


# ---------------------------------------------------------------------------
# _get_or_create_service_user
# ---------------------------------------------------------------------------


class TestGetOrCreateServiceUser:
    def test_creates_user_with_defaults(self, monkeypatch, mock_service_user):
        monkeypatch.setenv("NV_CONFIG_MANAGER_SERVICE_USER", "nv-config-manager-service")
        mod = _import_module()
        mod.User.objects.get_or_create.return_value = (mock_service_user, True)

        user = mod._get_or_create_service_user()

        mod.User.objects.get_or_create.assert_called_once_with(
            username="nv-config-manager-service",
            defaults={"is_active": True, "is_superuser": True},
        )
        assert user == mock_service_user

    def test_returns_existing_user(self, monkeypatch, mock_service_user):
        monkeypatch.setenv("NV_CONFIG_MANAGER_SERVICE_USER", "nv-config-manager-service")
        mod = _import_module()
        mod.User.objects.get_or_create.return_value = (mock_service_user, False)

        user = mod._get_or_create_service_user()
        assert user == mock_service_user


# ---------------------------------------------------------------------------
# _get_or_create_user_from_claims
# ---------------------------------------------------------------------------


class TestGetOrCreateUserFromClaims:
    def test_creates_user_from_email(self, mock_user):
        mod = _import_module()
        mod.User.objects.get_or_create.return_value = (mock_user, True)

        provider = mod.JwtProviderConfig(
            name="oidc",
            issuer="https://issuer.com",
            audiences=["aud"],
            jwks_uri="https://issuer.com/jwks",
            user_provider=True,
        )
        claims = {
            "preferred_username": "jdoe@nvidia.com",
            "email": "jdoe@nvidia.com",
        }

        user = mod._get_or_create_user_from_claims(claims, provider)
        assert user == mock_user
        mod.User.objects.get_or_create.assert_called_once()
        call_kwargs = mod.User.objects.get_or_create.call_args
        assert call_kwargs[1]["username"] == "jdoe"

    def test_updates_email_on_existing_user(self, mock_user):
        mod = _import_module()
        mock_user.email = "old@nvidia.com"
        mod.User.objects.get_or_create.return_value = (mock_user, False)

        provider = mod.JwtProviderConfig(
            name="oidc",
            issuer="https://issuer.com",
            audiences=["aud"],
            jwks_uri="https://issuer.com/jwks",
            user_provider=True,
        )
        claims = {
            "preferred_username": "jdoe@nvidia.com",
            "email": "new@nvidia.com",
        }

        user = mod._get_or_create_user_from_claims(claims, provider)
        assert user.email == "new@nvidia.com"
        user.save.assert_called_once_with(update_fields=["email"])

    def test_fallback_to_unknown_username(self):
        mod = _import_module()
        mock_u = MagicMock()
        mod.User.objects.get_or_create.return_value = (mock_u, True)

        provider = mod.JwtProviderConfig(
            name="oidc",
            issuer="https://issuer.com",
            audiences=["aud"],
            jwks_uri="https://issuer.com/jwks",
        )
        claims = {}

        mod._get_or_create_user_from_claims(claims, provider)
        call_kwargs = mod.User.objects.get_or_create.call_args
        assert call_kwargs[1]["username"] == "unknown"

    def test_groups_claim_promotes_to_superuser(self, monkeypatch, mock_user):
        monkeypatch.setenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", "nautobot-admins")
        mock_user.is_superuser = False
        mock_user.is_staff = False

        mod = _import_module()
        mod.User.objects.get_or_create.return_value = (mock_user, True)

        provider = mod.JwtProviderConfig(
            name="oidc",
            issuer="https://issuer.com",
            audiences=["aud"],
            jwks_uri="https://issuer.com/jwks",
            user_provider=True,
        )
        claims = {
            "preferred_username": "jdoe@nvidia.com",
            "email": "jdoe@nvidia.com",
            "roles": ["nautobot-admins", "other-team"],
        }

        user = mod._get_or_create_user_from_claims(claims, provider)
        assert user is mock_user
        assert user.is_superuser is True
        assert user.is_staff is True
        user.save.assert_called_with(update_fields=["is_superuser", "is_staff"])

    def test_missing_groups_claim_demotes_existing_superuser(self, monkeypatch, mock_user):
        monkeypatch.setenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", "nautobot-admins")
        mock_user.is_superuser = True
        mock_user.is_staff = True
        mock_user.email = "jdoe@nvidia.com"

        mod = _import_module()
        mod.User.objects.get_or_create.return_value = (mock_user, False)

        provider = mod.JwtProviderConfig(
            name="oidc",
            issuer="https://issuer.com",
            audiences=["aud"],
            jwks_uri="https://issuer.com/jwks",
            user_provider=True,
        )
        claims = {
            "preferred_username": "jdoe@nvidia.com",
            "email": "jdoe@nvidia.com",
        }

        mod._get_or_create_user_from_claims(claims, provider)
        assert mock_user.is_superuser is False
        assert mock_user.is_staff is False

    def test_honors_per_provider_claim_groups(self, monkeypatch, mock_user):
        monkeypatch.setenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", "nv-config-manager-admins")
        mock_user.is_superuser = False
        mock_user.is_staff = False

        mod = _import_module()
        mod.User.objects.get_or_create.return_value = (mock_user, True)

        provider = mod.JwtProviderConfig(
            name="keycloak",
            issuer="https://kc.example.com",
            audiences=["aud"],
            jwks_uri="https://kc.example.com/jwks",
            claim_groups="groups",
            user_provider=True,
        )
        claims = {
            "preferred_username": "jdoe",
            "email": "jdoe@nvidia.com",
            "groups": ["nv-config-manager-admins"],
            "roles": [],
        }

        mod._get_or_create_user_from_claims(claims, provider)
        assert mock_user.is_superuser is True


# ---------------------------------------------------------------------------
# _get_spiffe_audiences
# ---------------------------------------------------------------------------


class TestGetSpiffeAudiences:
    def test_parses_comma_separated(self, monkeypatch):
        monkeypatch.setenv("SPIFFE_AUDIENCES", "aud1, aud2, aud3")
        mod = _import_module()
        assert mod._get_spiffe_audiences() == ["aud1", "aud2", "aud3"]

    def test_empty(self, monkeypatch):
        monkeypatch.delenv("SPIFFE_AUDIENCES", raising=False)
        mod = _import_module()
        assert mod._get_spiffe_audiences() == []


# ---------------------------------------------------------------------------
# _get_jwks_client (caching)
# ---------------------------------------------------------------------------


class TestGetJwksClient:
    def test_caches_client(self):
        mod = _import_module()
        mod._jwks_clients.clear()

        with patch.object(mod.pyjwt, "PyJWKClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            c1 = mod._get_jwks_client("https://example.com/jwks")
            c2 = mod._get_jwks_client("https://example.com/jwks")
            assert c1 is c2
            mock_cls.assert_called_once()

        mod._jwks_clients.clear()


# ---------------------------------------------------------------------------
# _try_spiffe
# ---------------------------------------------------------------------------


class TestTrySpiffe:
    def test_returns_none_when_no_jwks_uri(self, monkeypatch):
        mod = _import_module()
        monkeypatch.setattr(mod, "_get_spiffe_jwks_uri", lambda: "")
        assert mod._try_spiffe("some-token") is None

    def test_returns_none_when_no_audiences(self, monkeypatch):
        mod = _import_module()
        monkeypatch.setattr(mod, "_get_spiffe_jwks_uri", lambda: "/var/run/secrets/spiffe/bundle.json")
        monkeypatch.setattr(mod, "_get_spiffe_audiences", lambda: [])
        assert mod._try_spiffe("some-token") is None

    def test_returns_none_on_validation_failure(self, monkeypatch, mock_service_user):
        mod = _import_module()
        monkeypatch.setattr(mod, "_get_spiffe_jwks_uri", lambda: "https://spire:8443/keys")
        monkeypatch.setattr(mod, "_get_spiffe_audiences", lambda: ["aud"])
        monkeypatch.setattr(mod, "_get_signing_key_from_jwks", MagicMock(side_effect=Exception("bad token")))
        assert mod._try_spiffe("bad-token") is None

    def test_returns_none_when_no_sub_claim(self, monkeypatch, mock_service_user):
        mod = _import_module()
        mock_key = MagicMock()
        monkeypatch.setattr(mod, "_get_spiffe_jwks_uri", lambda: "https://spire:8443/keys")
        monkeypatch.setattr(mod, "_get_spiffe_audiences", lambda: ["spiffe://domain"])
        monkeypatch.setattr(mod, "_get_signing_key_from_jwks", lambda uri, t: mock_key)
        monkeypatch.setattr(mod.pyjwt, "decode", MagicMock(return_value={}))
        assert mod._try_spiffe("token-without-sub") is None

    def test_success_returns_service_user(self, monkeypatch, mock_service_user):
        mod = _import_module()
        mock_key = MagicMock()
        decoded = {"sub": "spiffe://domain/ns/prod/sa/render", "aud": "spiffe://domain"}

        monkeypatch.setattr(mod, "_get_spiffe_jwks_uri", lambda: "https://spire:8443/keys")
        monkeypatch.setattr(mod, "_get_spiffe_audiences", lambda: ["spiffe://domain"])
        monkeypatch.setattr(mod, "_get_signing_key_from_jwks", lambda uri, t: mock_key)
        monkeypatch.setattr(mod.pyjwt, "decode", MagicMock(return_value=decoded))
        monkeypatch.setattr(mod, "_get_or_create_service_user", lambda: mock_service_user)

        result = mod._try_spiffe("good-token")
        assert result is not None
        user, spiffe_id = result
        assert user == mock_service_user
        assert spiffe_id == "spiffe://domain/ns/prod/sa/render"


# ---------------------------------------------------------------------------
# _try_jwt_provider
# ---------------------------------------------------------------------------


class TestTryJwtProvider:
    def _make_provider(self, mod, user_provider=False, audiences=None):
        return mod.JwtProviderConfig(
            name="test-provider",
            issuer="https://issuer.com",
            audiences=audiences if audiences is not None else ["aud"],
            jwks_uri="https://issuer.com/jwks",
            user_provider=user_provider,
        )

    def test_returns_none_on_jwt_error(self, monkeypatch):
        mod = _import_module()
        import jwt as pyjwt

        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.side_effect = pyjwt.exceptions.PyJWTError("bad")
        monkeypatch.setattr(mod, "_get_jwks_client", lambda uri: mock_client)

        provider = self._make_provider(mod)
        assert mod._try_jwt_provider("bad-token", provider) is None

    def test_service_provider_returns_service_user(self, monkeypatch, mock_service_user):
        mod = _import_module()

        mock_client = MagicMock()
        mock_key = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value = mock_key

        decoded = {"email": "svc@nvidia.com", "preferred_username": "svc"}
        monkeypatch.setattr(mod, "_get_jwks_client", lambda uri: mock_client)
        monkeypatch.setattr(mod.pyjwt, "decode", MagicMock(return_value=decoded))
        monkeypatch.setattr(mod, "_get_or_create_service_user", lambda: mock_service_user)

        provider = self._make_provider(mod, user_provider=False)
        result = mod._try_jwt_provider("token", provider)
        assert result is not None
        user, info = result
        assert user == mock_service_user
        assert "test-provider:" in info

    def test_user_provider_returns_individual_user(self, monkeypatch, mock_user):
        mod = _import_module()

        mock_client = MagicMock()
        mock_key = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value = mock_key

        decoded = {"email": "jdoe@nvidia.com", "preferred_username": "jdoe@nvidia.com"}
        monkeypatch.setattr(mod, "_get_jwks_client", lambda uri: mock_client)
        monkeypatch.setattr(mod.pyjwt, "decode", MagicMock(return_value=decoded))
        monkeypatch.setattr(mod, "_get_or_create_user_from_claims", lambda c, p: mock_user)

        provider = self._make_provider(mod, user_provider=True)
        result = mod._try_jwt_provider("token", provider)
        assert result is not None
        user, info = result
        assert user == mock_user
        assert "test-provider:" in info

    def test_no_audiences_disables_aud_verification(self, monkeypatch, mock_service_user):
        mod = _import_module()

        mock_client = MagicMock()
        mock_key = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value = mock_key

        decoded = {"email": "svc@nvidia.com"}
        monkeypatch.setattr(mod, "_get_jwks_client", lambda uri: mock_client)

        mock_decode = MagicMock(return_value=decoded)
        monkeypatch.setattr(mod.pyjwt, "decode", mock_decode)
        monkeypatch.setattr(mod, "_get_or_create_service_user", lambda: mock_service_user)

        provider = self._make_provider(mod, audiences=[])
        mod._try_jwt_provider("token", provider)

        call_kwargs = mock_decode.call_args[1]
        assert call_kwargs["audience"] is None


# ---------------------------------------------------------------------------
# NVConfigManagerJWTAuthentication.authenticate
# ---------------------------------------------------------------------------


class TestNVConfigManagerJWTAuthentication:
    def test_returns_none_when_no_token(self, monkeypatch):
        mod = _import_module()
        monkeypatch.setattr(mod, "_extract_token", lambda r: None)

        auth = mod.NVConfigManagerJWTAuthentication()
        assert auth.authenticate(MagicMock()) is None

    def test_tries_spiffe_first(self, monkeypatch, mock_service_user):
        mod = _import_module()
        monkeypatch.setattr(mod, "_extract_token", lambda r: "token")
        monkeypatch.setattr(mod, "_try_spiffe", lambda t: (mock_service_user, "spiffe://id"))

        auth = mod.NVConfigManagerJWTAuthentication()
        result = auth.authenticate(MagicMock())
        assert result == (mock_service_user, "spiffe://id")

    def test_falls_through_to_jwt_providers(self, monkeypatch, mock_user):
        mod = _import_module()
        provider = mod.JwtProviderConfig(
            name="oidc",
            issuer="https://issuer.com",
            audiences=["aud"],
            jwks_uri="https://issuer.com/jwks",
            user_provider=True,
        )
        monkeypatch.setattr(mod, "_extract_token", lambda r: "token")
        monkeypatch.setattr(mod, "_try_spiffe", lambda t: None)
        monkeypatch.setattr(mod, "_get_providers", lambda: [provider])
        monkeypatch.setattr(
            mod,
            "_try_jwt_provider",
            lambda t, p: (mock_user, "oidc:jdoe"),
        )

        auth = mod.NVConfigManagerJWTAuthentication()
        result = auth.authenticate(MagicMock())
        assert result == (mock_user, "oidc:jdoe")

    def test_returns_none_when_no_provider_matches(self, monkeypatch):
        mod = _import_module()
        monkeypatch.setattr(mod, "_extract_token", lambda r: "token")
        monkeypatch.setattr(mod, "_try_spiffe", lambda t: None)
        monkeypatch.setattr(mod, "_get_providers", lambda: [])

        auth = mod.NVConfigManagerJWTAuthentication()
        assert auth.authenticate(MagicMock()) is None

    def test_authenticate_header(self):
        mod = _import_module()
        auth = mod.NVConfigManagerJWTAuthentication()
        assert auth.authenticate_header(MagicMock()) == "Bearer"
