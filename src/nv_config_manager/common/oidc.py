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
"""
OIDC PKCE authentication handler for CLI and programmatic use.

This module provides a reusable OIDC authentication class that implements the
Authorization Code flow with PKCE (Proof Key for Code Exchange). It is designed
to be used by CLIs, integration tests, and any other client that needs to
authenticate against an OIDC-protected API.

Usage (CLI):
    from nv_config_manager.common.oidc import OIDCAuth

    auth = OIDCAuth(issuer_url="https://login.microsoftonline.com/<tenant>/v2.0",
                    client_id="<client-id>")
    token = auth.get_access_token()
    # Use token in Authorization: Bearer header

Usage (integration tests):
    auth = OIDCAuth.discover_from_gateway("https://workflow.qa.kiwi.example.com/v1/workflow")
    token = auth.get_access_token()

Discovery (auto-detect issuer/client_id from gateway redirect):
    issuer, client_id = OIDCAuth.discover_oidc_config("https://workflow.example.com/v1/workflow")
"""

import base64
import hashlib
import json
import secrets
import webbrowser
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from threading import Thread
from typing import Any
from urllib.parse import parse_qs, urlencode, urlparse

import requests

from nv_config_manager.common.log import LogCategory, get_logger

logger = get_logger(__name__, category=LogCategory.AUTH)


def decode_jwt_claims(token: str) -> dict[str, Any] | None:
    """Decode JWT payload claims without verifying the signature.

    Useful for debugging and inspecting tokens. Returns None if the
    token cannot be decoded.

    Args:
        token: A JWT string (header.payload.signature).

    Returns:
        Decoded claims dict, or None if decoding fails.
    """
    parts = token.split(".")
    if len(parts) != 3:
        return None
    try:
        payload_b64 = parts[1]
        # Add padding if needed
        padding = 4 - len(payload_b64) % 4
        if padding != 4:
            payload_b64 += "=" * padding
        decoded = base64.urlsafe_b64decode(payload_b64)
        return json.loads(decoded)  # type: ignore[no-any-return]
    except Exception:
        return None


class OIDCAuth:
    """OIDC PKCE authentication handler.

    Implements the Authorization Code flow with PKCE for public/native clients.
    Handles the full flow: browser-based authorization, local callback server,
    token exchange, and token caching.

    This class is intentionally free of CLI framework dependencies (e.g. click)
    so it can be imported and used in integration tests, other CLIs, or any
    Python code that needs OIDC authentication.
    """

    def __init__(
        self,
        issuer_url: str,
        client_id: str,
        redirect_port: int = 8765,
        scopes: list[str] | None = None,
        token_file: Path | None = None,
    ) -> None:
        """Initialize OIDC auth handler.

        Args:
            issuer_url: OIDC issuer URL (e.g., https://login.microsoftonline.com/<tenant>/v2.0)
            client_id: OIDC application (client) ID.
            redirect_port: Local port for OAuth callback (default: 8765).
            scopes: OAuth scopes to request. Defaults to api://<client_id>/.default + openid + profile.
            token_file: Path for cached token storage. Defaults to ~/.nv-config-manager/token.json.
        """
        self.issuer_url = issuer_url.rstrip("/")
        self.client_id = client_id
        self.redirect_port = redirect_port
        # Request app-specific scope to get a token for THIS app (not Microsoft Graph).
        # Without api://<client_id>/.default, Azure AD issues a Graph token (aud=00000003-...).
        self.scopes = scopes or [f"api://{client_id}/.default", "openid", "profile"]
        self.redirect_uri = f"http://localhost:{redirect_port}/callback"

        # Token storage
        self.token_file = token_file or (Path.home() / ".nv-config-manager" / "token.json")
        self.token_file.parent.mkdir(parents=True, exist_ok=True)

    # ── PKCE ──────────────────────────────────────────────────────────────

    @staticmethod
    def generate_pkce_pair() -> tuple[str, str]:
        """Generate PKCE code verifier and challenge.

        Returns:
            Tuple of (code_verifier, code_challenge).
        """
        code_verifier = (
            base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("utf-8").rstrip("=")
        )
        challenge_bytes = hashlib.sha256(code_verifier.encode("utf-8")).digest()
        code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode("utf-8").rstrip("=")
        return code_verifier, code_challenge

    # ── Endpoint resolution ───────────────────────────────────────────────

    def _get_token_endpoint(self) -> str:
        """Get token endpoint URL.

        Handles issuer as .../v2.0 or .../oauth2/v2.0 (from redirect discovery).
        """
        if "microsoftonline.com" in self.issuer_url:
            if "/oauth2/v2.0" in self.issuer_url:
                return f"{self.issuer_url.rstrip('/')}/token"
            base = self.issuer_url.replace("/v2.0", "").rstrip("/")
            return f"{base}/oauth2/v2.0/token"
        return f"{self.issuer_url}/token"

    def _get_auth_endpoint(self) -> str:
        """Get authorization endpoint URL.

        Handles issuer as .../v2.0 or .../oauth2/v2.0 (from redirect discovery).
        """
        if "microsoftonline.com" in self.issuer_url:
            if "/oauth2/v2.0" in self.issuer_url:
                return f"{self.issuer_url.rstrip('/')}/authorize"
            base = self.issuer_url.replace("/v2.0", "").rstrip("/")
            return f"{base}/oauth2/v2.0/authorize"
        return f"{self.issuer_url}/authorize"

    # ── Authorization URL ─────────────────────────────────────────────────

    def get_auth_url(self, code_challenge: str, state: str) -> str:
        """Build PKCE authorization URL.

        Args:
            code_challenge: PKCE S256 code challenge.
            state: Random state parameter for CSRF protection.

        Returns:
            Full authorization URL to open in the user's browser.
        """
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": self.redirect_uri,
            "response_mode": "query",
            "scope": " ".join(self.scopes),
            "state": state,
            "code_challenge": code_challenge,
            "code_challenge_method": "S256",
        }
        return f"{self._get_auth_endpoint()}?{urlencode(params)}"

    # ── Token exchange ────────────────────────────────────────────────────

    def exchange_code(self, code: str, code_verifier: str) -> dict[str, Any]:
        """Exchange authorization code for access token using PKCE.

        Args:
            code: The authorization code from the callback.
            code_verifier: The original PKCE code verifier.

        Returns:
            Token response dict containing access_token, expires_in, etc.

        Raises:
            requests.exceptions.HTTPError: If the token exchange fails.
        """
        data = {
            "client_id": self.client_id,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier,
        }
        token_endpoint = self._get_token_endpoint()
        try:
            response = requests.post(token_endpoint, data=data, timeout=30)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
        except requests.exceptions.HTTPError as e:
            error_detail = "Unknown error"
            if e.response is not None:
                try:
                    error_data = e.response.json()
                    error_detail = error_data.get(
                        "error_description", error_data.get("error", str(e))
                    )
                except Exception:
                    error_detail = e.response.text or str(e)

            logger.error("Token exchange failed: %s", error_detail)
            if "client_assertion" in error_detail or "client_secret" in error_detail:
                logger.error(
                    "Redirect URI must be registered under 'Mobile and desktop applications'"
                )
                logger.error("Azure Portal → App Registration → Authentication → Add platform")
                logger.error(
                    "Select 'Mobile and desktop applications', add redirect URI: %s",
                    self.redirect_uri,
                )
            else:
                logger.error(
                    "Possible causes: redirect URI not registered (%s), "
                    "public client flows not enabled, or invalid authorization code",
                    self.redirect_uri,
                )
            raise

    # ── Token persistence ─────────────────────────────────────────────────

    def save_token(self, token_data: dict[str, Any]) -> None:
        """Save token data to disk with restrictive permissions.

        Args:
            token_data: Token response dict from the IdP.
        """
        token_data["obtained_at"] = datetime.now(UTC).isoformat()
        with open(self.token_file, "w") as f:
            json.dump(token_data, f, indent=2)
        self.token_file.chmod(0o600)

    def load_token(self) -> dict[str, Any] | None:
        """Load cached token from disk if it exists and hasn't expired.

        Uses a 5-minute buffer before expiry to avoid edge-case failures.

        Returns:
            Token data dict, or None if no valid token is cached.
        """
        if not self.token_file.exists():
            return None

        try:
            with open(self.token_file) as f:
                token_data = json.load(f)

            obtained_at = datetime.fromisoformat(token_data["obtained_at"])
            expires_in = token_data.get("expires_in", 3600)
            expiry_time = obtained_at.timestamp() + expires_in - 300  # 5 min buffer

            if datetime.now(UTC).timestamp() < expiry_time:
                return token_data  # type: ignore[no-any-return]

            logger.info("Cached token has expired")
            return None
        except Exception as e:
            logger.warning("Error loading cached token: %s", e)
            return None

    def clear_token(self) -> None:
        """Remove cached token from disk."""
        if self.token_file.exists():
            self.token_file.unlink()
            logger.info("Cached token cleared")

    # ── High-level access token retrieval ─────────────────────────────────

    def get_access_token(self, force_refresh: bool = False) -> str:
        """Get a valid access token, performing the PKCE browser flow if needed.

        Checks for a cached token first. If none is available (or force_refresh
        is True), opens the user's browser for interactive authentication.

        Args:
            force_refresh: Force new authentication even if a cached token exists.

        Returns:
            A valid JWT access token string.

        Raises:
            RuntimeError: If authentication times out or fails.
        """
        # Try cached token
        if not force_refresh:
            token_data = self.load_token()
            if token_data:
                return str(token_data["access_token"])

        # Perform PKCE flow
        logger.info("Opening browser for OIDC authentication...")
        state = secrets.token_urlsafe(32)
        code_verifier, code_challenge = self.generate_pkce_pair()

        # Callback storage
        callback_data: dict[str, Any] = {}

        class _CallbackHandler(BaseHTTPRequestHandler):
            """Local HTTP handler for the OAuth redirect callback."""

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                pass  # Suppress default request logging

            def do_GET(self) -> None:
                parsed = urlparse(self.path)
                params = parse_qs(parsed.query)

                if "error" in params:
                    error = params["error"][0]
                    error_desc = params.get("error_description", ["Unknown error"])[0]
                    callback_data["error"] = f"{error}: {error_desc}"
                    self._send_response("Authentication failed. You can close this window.", 400)
                    return

                if "state" not in params or params["state"][0] != state:
                    callback_data["error"] = "Invalid state parameter"
                    self._send_response("Invalid state. You can close this window.", 400)
                    return

                if "code" not in params:
                    callback_data["error"] = "No authorization code received"
                    self._send_response(
                        "No authorization code received. You can close this window.", 400
                    )
                    return

                callback_data["code"] = params["code"][0]
                self._send_response("Authentication successful! You can close this window.", 200)

            def _send_response(self, message: str, status: int) -> None:
                self.send_response(status)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                icon = "\u2713" if status == 200 else "\u2717"
                html = (
                    "<html>"
                    "<head><title>NVIDIA Config Manager Authentication</title></head>"
                    '<body style="font-family: sans-serif; text-align: center; padding: 50px;">'
                    f"<h1>{icon} {message}</h1>"
                    "<p>You can now return to the terminal.</p>"
                    "</body></html>"
                )
                self.wfile.write(html.encode())

        server = HTTPServer(("localhost", self.redirect_port), _CallbackHandler)

        def _run_server() -> None:
            server.handle_request()

        server_thread = Thread(target=_run_server, daemon=True)
        server_thread.start()

        auth_url = self.get_auth_url(code_challenge, state)
        webbrowser.open(auth_url)

        logger.info("Waiting for authentication callback on port %d...", self.redirect_port)
        logger.info("If your browser doesn't open automatically, visit:\n  %s", auth_url)

        server_thread.join(timeout=300)  # 5 minute timeout

        if "error" in callback_data:
            raise RuntimeError(f"Authentication failed: {callback_data['error']}")

        if "code" not in callback_data:
            raise RuntimeError("Authentication timed out or failed")

        logger.info("Exchanging authorization code for access token...")
        token_data = self.exchange_code(callback_data["code"], code_verifier)

        self.save_token(token_data)
        logger.info("Authentication successful!")

        return str(token_data["access_token"])

    # ── Token status ──────────────────────────────────────────────────────

    def token_status(self) -> dict[str, Any]:
        """Check the status of the cached token.

        Returns:
            Dict with keys: authenticated (bool), expires_in_seconds (float | None).
        """
        token_data = self.load_token()
        if not token_data:
            return {"authenticated": False, "expires_in_seconds": None}

        obtained_at = datetime.fromisoformat(token_data["obtained_at"])
        expires_in = token_data.get("expires_in", 3600)
        expiry_time = obtained_at.timestamp() + expires_in
        remaining = expiry_time - datetime.now(UTC).timestamp()

        return {
            "authenticated": remaining > 0,
            "expires_in_seconds": max(remaining, 0),
        }

    # ── SSO detection and OIDC discovery from gateway redirect ─────────────

    @staticmethod
    def is_sso_enabled(gateway_url: str, verify: bool = True) -> bool:
        """Probe the gateway to determine whether SSO/OIDC is enabled.

        Makes a lightweight unauthenticated request (to /whoami relative to the
        gateway base). If the gateway returns a redirect (302), SSO is enabled.
        If it returns a non-redirect (e.g. 200, 401, 404), SSO is not enabled
        and callers can skip authentication entirely.

        Args:
            gateway_url: A URL behind the gateway. The /whoami endpoint is
                derived by replacing the path.
                E.g. https://workflow.example.com/v1/workflow -> https://workflow.example.com/whoami
            verify: Whether to verify TLS certificates.

        Returns:
            True if the gateway redirects to an OIDC provider, False otherwise.
        """
        parsed = urlparse(gateway_url)
        whoami_url = f"{parsed.scheme}://{parsed.netloc}/whoami"

        try:
            response = requests.get(
                whoami_url,
                allow_redirects=False,
                timeout=10,
                verify=verify,
            )
            return response.status_code in (302, 303, 307, 308)
        except requests.exceptions.RequestException:
            # Can't reach the gateway at all — caller should handle this later
            return False

    @staticmethod
    def discover_oidc_config(
        gateway_url: str,
        verify: bool = True,
    ) -> tuple[str, str] | None:
        """Discover OIDC issuer and client_id from a gateway's login redirect.

        When a gateway receives an unauthenticated request, it returns a 302
        redirect to the OIDC provider's authorization endpoint. This method
        parses that redirect to extract the issuer URL and client_id.

        Args:
            gateway_url: A URL behind the OIDC-protected gateway
                (e.g., https://workflow.example.com/v1/workflow).
            verify: Whether to verify TLS certificates. Set False for local dev.

        Returns:
            Tuple of (issuer_url, client_id), or None if SSO is not enabled
            (gateway returned a non-redirect response).

        Raises:
            RuntimeError: If the gateway is unreachable or the redirect URL
                cannot be parsed.
        """
        try:
            response = requests.get(
                gateway_url,
                allow_redirects=False,
                timeout=10,
                verify=verify,
            )
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to reach gateway at {gateway_url}: {e}") from e

        if response.status_code not in (302, 303, 307, 308):
            # No redirect → SSO is not enabled on this gateway
            return None

        redirect_url = response.headers.get("Location")
        if not redirect_url:
            raise RuntimeError("Gateway returned a redirect but no Location header.")

        parsed = urlparse(redirect_url)

        # Derive issuer from the redirect path (remove /authorize or Keycloak /auth suffix)
        issuer_path = parsed.path.rstrip("/")
        if issuer_path.endswith("/authorize"):
            issuer_path = issuer_path[:-10]
        elif issuer_path.endswith("/protocol/openid-connect/auth"):
            issuer_path = issuer_path.rsplit("/protocol/openid-connect/auth", 1)[0]

        issuer_url = f"{parsed.scheme}://{parsed.netloc}{issuer_path}"

        query_params = parse_qs(parsed.query)
        client_id = query_params.get("client_id", [None])[0]

        if not client_id:
            raise RuntimeError(f"Could not extract client_id from redirect URL: {redirect_url}")

        return issuer_url, client_id

    @classmethod
    def discover_from_gateway(
        cls,
        gateway_url: str,
        verify: bool = True,
        **kwargs: Any,
    ) -> "OIDCAuth | None":
        """Create an OIDCAuth instance by auto-discovering config from a gateway.

        Convenience factory that calls discover_oidc_config() and constructs
        an OIDCAuth instance with the discovered issuer and client_id.

        Args:
            gateway_url: A URL behind the OIDC-protected gateway.
            verify: Whether to verify TLS certificates.
            **kwargs: Additional keyword arguments passed to OIDCAuth.__init__.

        Returns:
            A configured OIDCAuth instance, or None if SSO is not enabled.
        """
        result = cls.discover_oidc_config(gateway_url, verify=verify)
        if result is None:
            return None
        issuer_url, client_id = result
        return cls(issuer_url=issuer_url, client_id=client_id, **kwargs)
