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

import contextlib
import json
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _import_module():
    """Import jwt_authentication after Django stubs are in place."""
    import nv_config_manager_auth.jwt_authentication as mod  # noqa: PLC0415 -- deferred for stub fixture

    return mod


@pytest.fixture()
def rbac():
    """Import :mod:`nv_config_manager_auth.rbac` once the conftest's Django stubs are live.

    Tests that exercise the RBAC sync paths in ``_get_or_create_user_from_claims``
    need to monkeypatch attributes on the real ``rbac`` module (not a copy),
    so we return the imported module rather than re-importing it inside each
    test.  Same deferred-import pattern as :func:`_import_module` above and
    ``test_rbac.py``'s ``rbac`` fixture; required because the autouse
    ``_django_stubs`` conftest fixture must install its stubs before
    ``nv_config_manager_auth.rbac`` is loaded (it pulls in ``nautobot.users.models``).
    """
    from nv_config_manager_auth import rbac as mod  # noqa: PLC0415 -- deferred for stub fixture

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

    def test_promotes_via_extra_superuser_match_when_env_unset(self, monkeypatch):
        """Group-mapping ``is_superuser: true`` entries promote even with no env var."""
        monkeypatch.delenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", raising=False)
        mod = _import_module()
        user = self._make_user(is_superuser=False, is_staff=False)

        mod._sync_superuser_status(
            user,
            {"admin-team"},
            extra_superuser_match=True,
            extra_superuser_enabled=True,
        )

        assert user.is_superuser is True
        assert user.is_staff is True

    def test_demotes_when_mapping_super_lost_and_env_unset(self, monkeypatch):
        """Regression: user promoted on a previous login via an ``is_superuser:
        true`` mapping entry must be demoted when the IdP no longer hands them
        that group -- even though ``NV_CONFIG_MANAGER_SUPERUSER_GROUPS`` is unset.

        Before the fix, ``_sync_superuser_status`` returned early whenever the
        env var was empty and the per-user match was False, leaving Alice as
        a stale superuser forever.
        """
        monkeypatch.delenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", raising=False)
        mod = _import_module()
        user = self._make_user(is_superuser=True, is_staff=True)

        mod._sync_superuser_status(
            user,
            {"some-non-admin-role"},
            extra_superuser_match=False,
            extra_superuser_enabled=True,
        )

        assert user.is_superuser is False
        assert user.is_staff is False
        user.save.assert_called_once_with(update_fields=["is_superuser", "is_staff"])

    def test_preserves_when_neither_source_configured(self, monkeypatch):
        """Bootstrap-admin protection: no env var AND mapping has no superuser
        entries → existing privileges untouched."""
        monkeypatch.delenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", raising=False)
        mod = _import_module()
        user = self._make_user(is_superuser=True, is_staff=True)

        mod._sync_superuser_status(
            user,
            {"any-group"},
            extra_superuser_match=False,
            extra_superuser_enabled=False,
        )

        user.save.assert_not_called()
        assert user.is_superuser is True
        assert user.is_staff is True

    def test_env_var_alone_still_triggers_reconciliation(self, monkeypatch):
        """When NV_CONFIG_MANAGER_SUPERUSER_GROUPS is set, mapping-side flags are
        immaterial to the early-return guard -- the env-var list alone drives the sync."""
        monkeypatch.setenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", "nautobot-admins")
        mod = _import_module()
        user = self._make_user(is_superuser=True, is_staff=True)

        mod._sync_superuser_status(
            user,
            {"some-other-group"},
            extra_superuser_match=False,
            extra_superuser_enabled=False,
        )

        assert user.is_superuser is False
        assert user.is_staff is False


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


class TestGetOrCreateUserFromClaimsMappingStates:
    """Cover the three orthogonal mapping-gate states that the JWT auth path
    must distinguish (see :func:`nv_config_manager_auth.rbac.mapping_is_configured`):

    * unconfigured -> never touch rbac.sync_groups_and_permissions, and
      treat ``extra_superuser_enabled`` as False so manual is_superuser
      flags set outside SSO are preserved.
    * configured + loaded OK -> rbac.sync_groups_and_permissions runs with
      the loaded mapping (possibly empty -> revoke-everyone idiom).
    * configured + load failed -> rbac.sync_groups_and_permissions runs
      with an empty mapping (fail closed; previously-granted access is
      revoked rather than silently preserved behind a parser error), and
      ``extra_superuser_enabled`` stays True so demotion runs.
    """

    def _make_provider(self, mod):
        return mod.JwtProviderConfig(
            name="oidc",
            issuer="https://issuer.com",
            audiences=["aud"],
            jwks_uri="https://issuer.com/jwks",
            user_provider=True,
        )

    def _claims(self):
        return {
            "preferred_username": "alice@nvidia.com",
            "email": "alice@nvidia.com",
            "roles": ["noc"],
        }

    def test_unconfigured_skips_rbac_sync_and_does_not_force_reconciliation(self, monkeypatch, mock_user, rbac):
        """No env var, no file: rbac.sync_groups_and_permissions must NOT
        run (would otherwise touch the DB), and _sync_superuser_status must
        see ``extra_superuser_enabled=False`` so manual superuser state is
        preserved when NV_CONFIG_MANAGER_SUPERUSER_GROUPS is unset."""
        monkeypatch.delenv("NV_CONFIG_MANAGER_GROUP_MAPPING_PATH", raising=False)
        monkeypatch.delenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", raising=False)
        mod = _import_module()

        monkeypatch.setattr(rbac, "mapping_is_configured", MagicMock(return_value=False))
        sync_mock = MagicMock()
        monkeypatch.setattr(rbac, "sync_groups_and_permissions", sync_mock)
        load_mock = MagicMock()
        monkeypatch.setattr(rbac, "load_group_mapping", load_mock)
        sync_super_mock = MagicMock()
        monkeypatch.setattr(mod, "_sync_superuser_status", sync_super_mock)

        mod.User.objects.get_or_create.return_value = (mock_user, False)
        mod._get_or_create_user_from_claims(self._claims(), self._make_provider(mod))

        sync_mock.assert_not_called()
        load_mock.assert_not_called()
        assert sync_super_mock.call_args.kwargs["extra_superuser_enabled"] is False

    def test_configured_and_empty_runs_sync_and_forces_reconciliation(self, monkeypatch, mock_user, rbac):
        """``groupMapping: []`` is the explicit revoke-everyone idiom.
        Sync must run (with empty mapping) so pass 3 prunes previously-
        managed memberships/perms, AND ``extra_superuser_enabled`` must be
        True so any stale superuser is demoted on this login."""
        monkeypatch.delenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", raising=False)
        mod = _import_module()

        monkeypatch.setattr(rbac, "mapping_is_configured", MagicMock(return_value=True))
        monkeypatch.setattr(rbac, "load_group_mapping", MagicMock(return_value={}))
        sync_mock = MagicMock()
        monkeypatch.setattr(rbac, "sync_groups_and_permissions", sync_mock)
        sync_super_mock = MagicMock()
        monkeypatch.setattr(mod, "_sync_superuser_status", sync_super_mock)

        mod.User.objects.get_or_create.return_value = (mock_user, False)
        mod._get_or_create_user_from_claims(self._claims(), self._make_provider(mod))

        # Sync ran even with empty mapping.
        sync_mock.assert_called_once()
        assert sync_mock.call_args.kwargs["mapping"] == {}
        # _sync_superuser_status saw the configuration intent.
        kwargs = sync_super_mock.call_args.kwargs
        assert kwargs["extra_superuser_enabled"] is True
        assert kwargs["extra_superuser_match"] is False  # empty mapping -> no match

    def test_configured_and_load_failed_fails_closed(self, monkeypatch, mock_user, caplog, rbac):
        """Corrupt mapping must not silently preserve previously-granted
        access.  The caller catches GroupMappingError, logs it, and treats
        the mapping as empty -- so the same revoke/demote paths run as
        for an explicitly-empty mapping."""
        monkeypatch.delenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", raising=False)
        mod = _import_module()

        monkeypatch.setattr(rbac, "mapping_is_configured", MagicMock(return_value=True))
        monkeypatch.setattr(
            rbac,
            "load_group_mapping",
            MagicMock(side_effect=rbac.GroupMappingParseError("syntax error at line 3")),
        )
        sync_mock = MagicMock()
        monkeypatch.setattr(rbac, "sync_groups_and_permissions", sync_mock)
        sync_super_mock = MagicMock()
        monkeypatch.setattr(mod, "_sync_superuser_status", sync_super_mock)

        mod.User.objects.get_or_create.return_value = (mock_user, False)
        with caplog.at_level("ERROR", logger="nv_config_manager_auth.jwt_authentication"):
            mod._get_or_create_user_from_claims(self._claims(), self._make_provider(mod))

        # Loud log so the operator notices.
        assert any("failed to load group mapping" in r.message for r in caplog.records)
        # Sync still runs (with empty mapping) -> revoke pass executes.
        sync_mock.assert_called_once()
        assert sync_mock.call_args.kwargs["mapping"] == {}
        # Demotion path is armed.
        assert sync_super_mock.call_args.kwargs["extra_superuser_enabled"] is True

    def test_configured_with_loaded_entries_passes_mapping_through(self, monkeypatch, mock_user, rbac):
        """The happy path: loaded mapping reaches sync_groups_and_permissions
        intact, and is_superuser_per_mapping decides the match flag."""
        monkeypatch.delenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", raising=False)
        mod = _import_module()

        mapping = {"admins": {"name": "admins", "is_superuser": True}}
        monkeypatch.setattr(rbac, "mapping_is_configured", MagicMock(return_value=True))
        monkeypatch.setattr(rbac, "load_group_mapping", MagicMock(return_value=mapping))
        sync_mock = MagicMock()
        monkeypatch.setattr(rbac, "sync_groups_and_permissions", sync_mock)
        sync_super_mock = MagicMock()
        monkeypatch.setattr(mod, "_sync_superuser_status", sync_super_mock)

        claims = self._claims() | {"roles": ["admins"]}
        mod.User.objects.get_or_create.return_value = (mock_user, False)
        mod._get_or_create_user_from_claims(claims, self._make_provider(mod))

        sync_mock.assert_called_once()
        assert sync_mock.call_args.kwargs["mapping"] is mapping
        kwargs = sync_super_mock.call_args.kwargs
        assert kwargs["extra_superuser_enabled"] is True
        assert kwargs["extra_superuser_match"] is True  # "admins" matched is_superuser

    def test_sync_runs_inside_web_request_context_bound_to_user(self, monkeypatch, mock_user, rbac):
        """Regression: the revoke/prune paths call ``ObjectPermission.delete()``,
        which fires Nautobot's change-logging signal and needs an acting user.

        The sync runs during ``authenticate()`` before a user is bound to the
        request, so it must be wrapped in ``web_request_context(user)`` -- else
        deletes crash with ``AttributeError: 'NoneType' object has no attribute
        'pk'`` and (being ``@transaction.atomic``) roll the whole sync back.
        This asserts the reconciliation happens *inside* that context, bound to
        the authenticating user.
        """
        monkeypatch.delenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", raising=False)
        mod = _import_module()

        events: list[tuple[str, object]] = []

        @contextlib.contextmanager
        def tracking_ctx(user, **_kwargs):
            events.append(("enter", user))
            try:
                yield
            finally:
                events.append(("exit", user))

        monkeypatch.setattr(
            sys.modules["nautobot.extras.context_managers"],
            "web_request_context",
            tracking_ctx,
        )
        monkeypatch.setattr(rbac, "mapping_is_configured", MagicMock(return_value=True))
        monkeypatch.setattr(rbac, "load_group_mapping", MagicMock(return_value={}))
        monkeypatch.setattr(
            rbac,
            "sync_groups_and_permissions",
            MagicMock(side_effect=lambda *a, **k: events.append(("sync", None))),
        )
        monkeypatch.setattr(
            mod,
            "_sync_superuser_status",
            MagicMock(side_effect=lambda *a, **k: events.append(("superuser", None))),
        )

        mod.User.objects.get_or_create.return_value = (mock_user, False)
        mod._get_or_create_user_from_claims(self._claims(), self._make_provider(mod))

        # Context opened with the authenticating user, both sync passes ran
        # inside it, and it closed cleanly.
        assert events[0] == ("enter", mock_user)
        assert events[-1] == ("exit", mock_user)
        assert ("sync", None) in events
        assert ("superuser", None) in events
        assert events.index(("sync", None)) < events.index(("exit", mock_user))


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

    def test_serializes_cold_keyset_fetches(self):
        mod = _import_module()
        mod._jwks_signing_key_locks.clear()

        class ColdCacheClient:
            def __init__(self):
                self.cached = False
                self.fetches = 0
                self.lock = Lock()

            def get_signing_key_from_jwt(self, token):
                if not self.cached:
                    with self.lock:
                        self.fetches += 1
                    time.sleep(0.01)
                    self.cached = True
                return MagicMock()

        client = ColdCacheClient()
        with patch.object(mod, "_get_jwks_client", return_value=client):
            with ThreadPoolExecutor(max_workers=8) as executor:
                list(
                    executor.map(
                        lambda _: mod._get_signing_key_from_jwks("https://idp.example.com/jwks", "token"),
                        range(8),
                    )
                )

        assert client.fetches == 1
        mod._jwks_signing_key_locks.clear()

        with patch.object(mod.pyjwt, "PyJWKClient") as mock_cls:
            mock_cls.return_value = MagicMock()
            c1 = mod._get_jwks_client("https://example.com/jwks")
            c2 = mod._get_jwks_client("https://example.com/jwks")
            assert c1 is c2
            mock_cls.assert_called_once_with(
                "https://example.com/jwks",
                cache_jwk_set=True,
                lifespan=mod.JWKS_KEYSET_CACHE_LIFESPAN_SECONDS,
            )

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
        monkeypatch.setattr(mod, "_unverified_jwt_issuer", lambda t: provider.issuer)
        monkeypatch.setattr(
            mod,
            "_try_jwt_provider",
            lambda t, p: (mock_user, "oidc:jdoe"),
        )

        auth = mod.NVConfigManagerJWTAuthentication()
        result = auth.authenticate(MagicMock())
        assert result == (mock_user, "oidc:jdoe")

    def test_tries_only_provider_matching_unverified_issuer(self, monkeypatch, mock_user):
        mod = _import_module()
        other = mod.JwtProviderConfig(
            name="other",
            issuer="https://other.example.com",
            audiences=["aud"],
            jwks_uri="https://other.example.com/jwks",
        )
        starfleet = mod.JwtProviderConfig(
            name="starfleet",
            issuer="https://starfleet.example.com",
            audiences=["aud"],
            jwks_uri="https://starfleet.example.com/jwks",
        )
        attempted: list[str] = []

        def try_provider(token, provider):
            attempted.append(provider.name)
            if provider is starfleet:
                return (mock_user, "starfleet:operator")
            return None

        monkeypatch.setattr(mod, "_extract_token", lambda r: "token")
        monkeypatch.setattr(mod, "_try_spiffe", lambda t: None)
        monkeypatch.setattr(mod, "_get_providers", lambda: [other, starfleet])
        monkeypatch.setattr(mod, "_unverified_jwt_issuer", lambda t: starfleet.issuer)
        monkeypatch.setattr(mod, "_try_jwt_provider", try_provider)

        result = mod.NVConfigManagerJWTAuthentication().authenticate(MagicMock())

        assert result == (mock_user, "starfleet:operator")
        assert attempted == ["starfleet"]

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
