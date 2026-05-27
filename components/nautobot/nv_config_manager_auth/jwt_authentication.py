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
"""Multi-provider JWT authentication for Nautobot's REST API.

Handles all JWT-based authentication through a single DRF class:

- **Browser users** -- OIDC JWT from the ``NVConfigManagerAccessToken`` cookie,
  validated against the OIDC provider's JWKS.  Individual Django users
  are created from JWT claims.
- **Internal services** -- SPIFFE JWT-SVID in ``Authorization: Bearer``,
  validated via PyJWT + JWKS.  Uses a shared service user.
- **External services** -- Third-party / other JWTs in ``Authorization:
  Bearer``, validated via ``PyJWT`` + JWKS URI.  Uses a shared service
  user.
- **API tokens** -- ``Authorization: Token`` falls through to Nautobot's
  built-in ``TokenAuthentication``.

Configuration (environment variables on the Nautobot pod)::

    # SPIFFE (optional)
    SPIFFE_JWKS_URI         = https://spire-server.spire:8443/keys
    SPIFFE_AUDIENCES        = spiffe://trust-domain

    # JWT providers -- JSON array (includes OIDC + service issuers)
    NV_CONFIG_MANAGER_JWT_PROVIDERS = [
        {
            "name": "oidc",
            "issuer": "https://login.microsoftonline.com/{tenant}/v2.0",
            "audiences": ["api://{client-id}"],
            "user_provider": true
        },
        {
            "name": "external-svc",
            "issuer": "https://idp.example.com",
            "audiences": ["nautobot"],
            "jwks_uri": "https://idp.example.com/.well-known/jwks.json",
            "claim_user": "sub"
        }
    ]

    # Cookie name for browser JWT (default: NVConfigManagerAccessToken)
    NV_CONFIG_MANAGER_JWT_COOKIE          = NVConfigManagerAccessToken
    # Shared Nautobot user for service-authenticated requests
    NV_CONFIG_MANAGER_SERVICE_USER         = nv-config-manager-service
    # Comma-separated group/role names that grant Django superuser status.
    # Membership is reconciled against the JWT's groups claim on every
    # login, so a user removed from a privileged group in the IdP loses
    # superuser access on their next login.  When unset (default) the
    # feature is disabled and no user's privileges are touched.
    NV_CONFIG_MANAGER_SUPERUSER_GROUPS     = nautobot-admins,nv-config-manager-admins

Provider flags:

    ``user_provider``  (bool, default ``false``)
        When ``true``, the provider represents human users (OIDC).
        Successful validation creates/updates an individual Django user
        from the JWT claims instead of mapping to the shared service user.
"""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import jwt as pyjwt
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.request import Request

log = logging.getLogger(__name__)

User = get_user_model()

_JWT_ALGORITHMS = ["RS256", "RS384", "RS512", "ES256", "ES384", "ES512", "PS256"]


# ── Provider config ──────────────────────────────────────────────────────


@dataclass(frozen=True)
class JwtProviderConfig:
    """One JWT issuer that we trust."""

    name: str
    issuer: str
    audiences: list[str]
    jwks_uri: str
    claim_user: str = "preferred_username"
    claim_email: str = "email"
    claim_groups: str = "roles"
    user_provider: bool = False


def _derive_jwks_uri(issuer: str) -> str:
    """Auto-derive the JWKS URI from an issuer URL."""
    base = issuer.rstrip("/")
    if "login.microsoftonline.com" in base:
        return f"{base}/discovery/v2.0/keys"
    return f"{base}/.well-known/jwks.json"


def _load_jwt_providers() -> list[JwtProviderConfig]:
    raw = os.getenv("NV_CONFIG_MANAGER_JWT_PROVIDERS", "")
    if not raw:
        return []
    try:
        items = json.loads(raw)
    except json.JSONDecodeError:
        log.error("NV_CONFIG_MANAGER_JWT_PROVIDERS is not valid JSON; ignoring")
        return []
    providers: list[JwtProviderConfig] = []
    for item in items:
        issuer = item.get("issuer", "")
        if not issuer:
            continue
        audiences = item.get("audiences", [])
        jwks_uri = item.get("jwks_uri", "") or _derive_jwks_uri(issuer)
        providers.append(
            JwtProviderConfig(
                name=item.get("name", issuer),
                issuer=issuer,
                audiences=audiences,
                jwks_uri=jwks_uri,
                claim_user=item.get("claim_user", "preferred_username"),
                claim_email=item.get("claim_email", "email"),
                claim_groups=item.get("claim_groups", "roles"),
                user_provider=bool(item.get("user_provider", False)),
            )
        )
    return providers


# ── JWKS client cache ─────────────────────────────────────────────────────

_jwks_clients: dict[str, pyjwt.PyJWKClient] = {}
_jwks_lock = threading.Lock()


def _get_jwks_client(jwks_uri: str) -> pyjwt.PyJWKClient:
    client = _jwks_clients.get(jwks_uri)
    if client is not None:
        return client
    with _jwks_lock:
        client = _jwks_clients.get(jwks_uri)
        if client is not None:
            return client
        client = pyjwt.PyJWKClient(jwks_uri, cache_jwk_set=True, lifespan=600)
        _jwks_clients[jwks_uri] = client
        return client


def _get_spiffe_jwks_uri() -> str:
    return os.getenv("SPIFFE_JWKS_URI", "")


def _get_spiffe_audiences() -> list[str]:
    raw = os.getenv("SPIFFE_AUDIENCES", "")
    return [a.strip() for a in raw.split(",") if a.strip()]


def _get_signing_key_from_jwks(jwks_uri: str, token: str) -> pyjwt.PyJWK:
    """Get the signing key for *token* from an HTTP JWKS endpoint or local file.

    File-based JWKS (from spiffe-helper ``jwt_bundle_file_name``) is
    re-read on each call so key rotations are picked up immediately.
    """
    if jwks_uri.startswith(("http://", "https://")):
        return _get_jwks_client(jwks_uri).get_signing_key_from_jwt(token)

    bundle_path = Path(jwks_uri)
    jwks_data = json.loads(bundle_path.read_text())
    jwk_set = pyjwt.PyJWKSet.from_dict(jwks_data)
    header = pyjwt.get_unverified_header(token)
    kid = header.get("kid")
    for key in jwk_set.keys:
        if kid and key.key_id == kid:
            return key
    if jwk_set.keys:
        return jwk_set.keys[0]
    raise pyjwt.exceptions.PyJWKClientError("No matching key in JWKS bundle")


# ── Helpers ───────────────────────────────────────────────────────────────


def _spiffe_id_to_workload_name(spiffe_id: str) -> str:
    """``spiffe://domain/ns/prod/sa/render``  →  ``ns-prod-sa-render``"""
    try:
        path = spiffe_id.split("/", 3)[3]
    except (IndexError, AttributeError):
        return spiffe_id
    return path.replace("/", "-") if path else spiffe_id


def _strip_email_domain(email: str) -> str:
    if "@" in email:
        return email.split("@", 1)[0]
    return email


def _get_superuser_groups() -> set[str]:
    """Return the set of group/role names that grant Nautobot superuser status."""
    raw = os.getenv("NV_CONFIG_MANAGER_SUPERUSER_GROUPS", "")
    return {g.strip() for g in raw.split(",") if g.strip()}


def _extract_groups(claims: dict[str, Any], claim: str) -> set[str]:
    """Read a groups/roles claim from a JWT, supporting list and comma-string forms."""
    val = claims.get(claim)
    if isinstance(val, list):
        return {str(g) for g in val if g}
    if isinstance(val, str) and val:
        return {g.strip() for g in val.split(",") if g.strip()}
    return set()


def _sync_superuser_status(user: Any, user_groups: set[str]) -> None:
    """Reconcile Django ``is_superuser``/``is_staff`` against ``NV_CONFIG_MANAGER_SUPERUSER_GROUPS``.

    Called on every JWT login so privilege changes in the IdP propagate
    without manual intervention.  No-op when the env var is unset, which
    leaves any pre-existing superusers (e.g. the bootstrap ``admin`` user
    created by the migration init container) untouched.
    """
    superuser_groups = _get_superuser_groups()
    if not superuser_groups:
        return

    matched = user_groups & superuser_groups
    should_be_superuser = bool(matched)

    fields: list[str] = []
    if user.is_superuser != should_be_superuser:
        user.is_superuser = should_be_superuser
        fields.append("is_superuser")
    if user.is_staff != should_be_superuser:
        user.is_staff = should_be_superuser
        fields.append("is_staff")

    if fields:
        user.save(update_fields=fields)
        if should_be_superuser:
            log.info(
                "Promoted %r to superuser (matched groups: %s)",
                user.username,
                sorted(matched),
            )
        else:
            log.info(
                "Demoted %r from superuser (no matching groups in %s)",
                user.username,
                sorted(superuser_groups),
            )


def _get_or_create_service_user() -> Any:
    service_username = os.getenv("NV_CONFIG_MANAGER_SERVICE_USER", "nv-config-manager-service")
    user, created = User.objects.get_or_create(
        username=service_username,
        defaults={
            "is_active": True,
            "is_superuser": True,
        },
    )
    if created:
        log.info("Created Nautobot service user %r", service_username)
    return user


def _get_or_create_user_from_claims(
    claims: dict[str, Any],
    provider: JwtProviderConfig,
) -> Any:
    """Create or update a Django user from JWT claims (for human users)."""
    email = claims.get(provider.claim_email, "")
    user_claim = claims.get(provider.claim_user, "")
    username = _strip_email_domain(user_claim or email)
    if not username:
        username = _strip_email_domain(email) if email else "unknown"

    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "is_active": True,
        },
    )
    if created:
        log.info("Created user %r from %s JWT", username, provider.name)
    elif email and user.email != email:
        user.email = email
        user.save(update_fields=["email"])

    user_groups = _extract_groups(claims, provider.claim_groups)
    _sync_superuser_status(user, user_groups)

    return user


def _extract_token(request: Request) -> str | None:
    """Extract a JWT from the Authorization header or cookie."""
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    if auth_header:
        parts = auth_header.split(" ", 1)
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1].strip()
            if token:
                return token
        # Token prefix → let Nautobot's TokenAuthentication handle it
        return None

    cookie_name = os.getenv("NV_CONFIG_MANAGER_JWT_COOKIE", "NVConfigManagerAccessToken")
    return request.COOKIES.get(cookie_name)


# ── Validation methods ────────────────────────────────────────────────────


def _try_spiffe(token: str) -> tuple[Any, str] | None:
    """Validate *token* as a SPIFFE JWT-SVID via PyJWT + JWKS."""
    jwks_uri = _get_spiffe_jwks_uri()
    if not jwks_uri:
        return None

    audiences = _get_spiffe_audiences()
    if not audiences:
        return None

    try:
        signing_key = _get_signing_key_from_jwks(jwks_uri, token)

        claims = pyjwt.decode(
            token,
            signing_key.key,
            algorithms=_JWT_ALGORITHMS,
            audience=audiences,
            options={"verify_iss": False},
        )

        spiffe_id = claims.get("sub", "")
        if not spiffe_id:
            return None
    except Exception:
        log.debug("SPIFFE JWT-SVID validation failed", exc_info=True)
        return None

    workload_name = _spiffe_id_to_workload_name(spiffe_id)
    log.info("SPIFFE auth: %s (%s)", workload_name, spiffe_id)
    return (_get_or_create_service_user(), spiffe_id)


def _try_jwt_provider(token: str, provider: JwtProviderConfig) -> tuple[Any, str] | None:
    """Validate *token* against a single JWT provider."""
    try:
        jwks_client = _get_jwks_client(provider.jwks_uri)
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        options: dict[str, Any] = {}
        if not provider.audiences:
            options["verify_aud"] = False

        claims = pyjwt.decode(
            token,
            signing_key.key,
            algorithms=_JWT_ALGORITHMS,
            issuer=provider.issuer,
            audience=provider.audiences or None,
            options=options,
        )

        if provider.user_provider:
            user = _get_or_create_user_from_claims(claims, provider)
            log.info("JWT auth via %s: user %s", provider.name, user.username)
            return (user, f"{provider.name}:{user.username}")

        email = claims.get(provider.claim_email, "")
        user_claim = claims.get(provider.claim_user, "")
        identity_label = _strip_email_domain(user_claim or email) or provider.name
        log.info("JWT auth via %s: %s", provider.name, identity_label)
        return (_get_or_create_service_user(), f"{provider.name}:{identity_label}")

    except pyjwt.exceptions.PyJWTError:
        log.debug("JWT validation failed for provider %s", provider.name, exc_info=True)
        return None
    except Exception:
        log.warning("Unexpected error validating JWT with %s", provider.name, exc_info=True)
        return None


# ── Cached provider list ──────────────────────────────────────────────────

_providers: list[JwtProviderConfig] | None = None
_providers_lock = threading.Lock()


def _get_providers() -> list[JwtProviderConfig]:
    global _providers
    if _providers is not None:
        return _providers
    with _providers_lock:
        if _providers is not None:
            return _providers
        _providers = _load_jwt_providers()
        if _providers:
            log.info(
                "Loaded %d JWT provider(s): %s",
                len(_providers),
                [p.name for p in _providers],
            )
        return _providers


# ── DRF Authentication Class ──────────────────────────────────────────────


class NVConfigManagerJWTAuthentication(BaseAuthentication):
    """DRF authentication class supporting SPIFFE + multi-provider JWT.

    Token extraction (in order):

      1. ``Authorization: Bearer <token>`` header
      2. ``NVConfigManagerAccessToken`` cookie (configurable via ``NV_CONFIG_MANAGER_JWT_COOKIE``)

    Validation (in order):

      1. SPIFFE JWT-SVID (via PyJWT + JWKS)
      2. Each configured JWT provider (via PyJWT + JWKS)

    Providers with ``user_provider: true`` create individual Django users
    from JWT claims (for OIDC / browser users).  All other providers map
    to a shared service user.

    Returns ``None`` (fall through to next authenticator) when no token
    is found, the header uses ``Token`` prefix, or no provider accepts
    the token.
    """

    keyword = "Bearer"

    def authenticate(self, request: Request) -> tuple[Any, str] | None:
        token = _extract_token(request)
        if token is None:
            return None

        # 1. Try SPIFFE
        result = _try_spiffe(token)
        if result is not None:
            return result

        # 2. Try each JWT provider
        providers = _get_providers()
        for provider in providers:
            result = _try_jwt_provider(token, provider)
            if result is not None:
                return result

        # No provider matched -- fall through so Nautobot's
        # TokenAuthentication (or session auth) can try instead.
        return None

    def authenticate_header(self, request: Request) -> str:
        return self.keyword
