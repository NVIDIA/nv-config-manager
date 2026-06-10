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
"""CLI helpers for remote NVIDIA Config Manager MCP endpoints."""

from __future__ import annotations

import shlex
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import click
import requests
import urllib3

from nv_config_manager.common.oidc import AuthDiscovery, OIDCAuth

DEFAULT_DOMAIN = "config-manager.example.com"
DEFAULT_TOKEN_ENV_VAR = "NVCM_MCP_BEARER_TOKEN"
DEFAULT_TIMEOUT_SECONDS = 10
AUTH_MODE_AUTO = "auto"
AUTH_MODE_SSO = "sso"
AUTH_MODE_NONE = "none"


@dataclass(frozen=True)
class ResolvedMCPConnection:
    """Resolved MCP endpoint and authentication requirements."""

    endpoint_url: str
    discovery_url: str
    auth_required: bool
    discovered_oidc: tuple[str, str] | None = None
    discovered_scopes: tuple[str, ...] = ()


def _normalize_url(url: str) -> str:
    """Return a URL without a trailing slash."""
    return url.rstrip("/")


def _normalize_auth_discovery_url(url: str) -> str:
    """Return an HTTPS auth discovery URL without a trailing slash."""
    normalized_url = _normalize_url(url)
    parsed = urlparse(normalized_url)
    if parsed.scheme.lower() != "https":
        raise click.ClickException(f"Refusing non-HTTPS auth discovery URL: {normalized_url}")
    if not parsed.netloc:
        raise click.ClickException(f"Invalid auth discovery URL: {normalized_url}")
    return normalized_url


def _resolve_base_hostname(
    hostname: str | None,
    environment: str | None,
    domain: str,
) -> str:
    """Resolve a deployment base hostname from explicit or environment-based input."""
    if hostname:
        return hostname.removeprefix("https://").removeprefix("http://").strip("/")
    if environment:
        return f"{environment}.{domain}"
    raise click.ClickException("Either --hostname, --environment, or --mcp-url is required.")


def _resolve_mcp_endpoint(
    hostname: str | None,
    environment: str | None,
    domain: str,
    mcp_url: str | None,
    auth_mode: str = AUTH_MODE_SSO,
) -> str:
    """Resolve the remote Streamable HTTP MCP endpoint."""
    if mcp_url:
        return _normalize_url(mcp_url)

    base_hostname = _resolve_base_hostname(hostname, environment, domain)
    if auth_mode == AUTH_MODE_NONE:
        return f"https://mcp.{base_hostname}/mcp"
    return f"https://svc-mcp.{base_hostname}/mcp"


def _replace_svc_mcp_host(mcp_url: str) -> str:
    """Convert a svc-mcp endpoint URL into its OIDC-enabled mcp hostname."""
    parsed = urlparse(mcp_url)
    if not parsed.scheme or not parsed.netloc:
        return _normalize_url(mcp_url)

    netloc = parsed.netloc
    if netloc.startswith("svc-mcp."):
        netloc = netloc.removeprefix("svc-")

    return _normalize_url(parsed._replace(netloc=netloc, query="", fragment="").geturl())


def _resolve_auth_discovery_endpoint(
    hostname: str | None,
    environment: str | None,
    domain: str,
    mcp_url: str | None,
    discovery_url: str | None,
) -> str:
    """Resolve the URL used to discover public auth settings."""
    if discovery_url:
        return _normalize_auth_discovery_url(discovery_url)

    if hostname or environment:
        base_hostname = _resolve_base_hostname(hostname, environment, domain)
        return _normalize_auth_discovery_url(f"https://{base_hostname}/auth/discovery")

    if mcp_url:
        return _auth_discovery_url_from_mcp_url(mcp_url)

    raise click.ClickException("Either --hostname, --environment, or --mcp-url is required.")


def _auth_discovery_url_from_mcp_url(mcp_url: str) -> str:
    """Derive the base-host /auth/discovery URL from an MCP endpoint URL."""
    parsed = urlparse(mcp_url)
    if not parsed.scheme or not parsed.netloc:
        return _normalize_auth_discovery_url(mcp_url)

    netloc = parsed.netloc
    for prefix in ("svc-mcp.", "mcp."):
        if netloc.startswith(prefix):
            netloc = netloc.removeprefix(prefix)
            break

    discovery_url = parsed._replace(
        netloc=netloc,
        path="/auth/discovery",
        params="",
        query="",
        fragment="",
    ).geturl()
    return _normalize_auth_discovery_url(discovery_url)


def _resolve_configured_auth_discovery_endpoint(
    hostname: str | None,
    environment: str | None,
    domain: str,
    mcp_url: str | None,
    discovery_url: str | None,
) -> str:
    """Resolve an explicitly configured discovery URL without deriving it from MCP URLs."""
    if discovery_url or hostname or environment:
        return _resolve_auth_discovery_endpoint(
            hostname=hostname,
            environment=environment,
            domain=domain,
            mcp_url=mcp_url,
            discovery_url=discovery_url,
        )
    return ""


def _resolve_redirect_discovery_endpoint(
    hostname: str | None,
    environment: str | None,
    domain: str,
    mcp_url: str | None,
) -> str:
    """Resolve the legacy OIDC redirect discovery URL."""
    if hostname or environment:
        base_hostname = _resolve_base_hostname(hostname, environment, domain)
        return f"https://mcp.{base_hostname}/mcp"

    if mcp_url:
        return _replace_svc_mcp_host(mcp_url)

    raise click.ClickException("Either --hostname, --environment, or --mcp-url is required.")


def _discovered_oidc_tuple(discovery: AuthDiscovery) -> tuple[str, str] | None:
    """Return issuer/client tuple when auth discovery includes OIDC settings."""
    if not discovery.issuer_url or not discovery.client_id:
        return None
    return (discovery.issuer_url, discovery.client_id)


def _discover_auth_config(
    auth_discovery_url: str,
    redirect_discovery_url: str,
    insecure: bool,
) -> tuple[AuthDiscovery | None, tuple[str, str] | None]:
    """Discover auth settings, falling back to legacy OIDC redirect parsing."""
    try:
        discovery = OIDCAuth.discover_auth_config(auth_discovery_url, verify=not insecure)
    except RuntimeError as e:
        raise click.ClickException(f"OIDC auto-discovery failed: {e}") from e
    if discovery is not None:
        return discovery, _discovered_oidc_tuple(discovery)

    try:
        return None, OIDCAuth.discover_oidc_config(
            redirect_discovery_url,
            verify=not insecure,
        )
    except RuntimeError as e:
        raise click.ClickException(f"OIDC auto-discovery failed: {e}") from e


def _enforce_secure_endpoint(endpoint_url: str, auth_required: bool) -> None:
    """Refuse bearer-token use over plaintext MCP endpoints."""
    if not auth_required:
        return
    parsed = urlparse(endpoint_url)
    if parsed.scheme.lower() != "https":
        raise click.ClickException(
            f"Refusing non-HTTPS MCP endpoint for bearer auth: {endpoint_url}"
        )


def _resolve_connection(
    hostname: str | None,
    environment: str | None,
    domain: str,
    mcp_url: str | None,
    discovery_url: str | None,
    auth_mode: str,
    insecure: bool,
) -> ResolvedMCPConnection:
    """Resolve endpoint and auth requirements for an MCP-capable client."""
    if auth_mode == AUTH_MODE_NONE:
        resolved_discovery_url = _resolve_configured_auth_discovery_endpoint(
            hostname=hostname,
            environment=environment,
            domain=domain,
            mcp_url=mcp_url,
            discovery_url=discovery_url,
        )
        connection = ResolvedMCPConnection(
            endpoint_url=_resolve_mcp_endpoint(
                hostname=hostname,
                environment=environment,
                domain=domain,
                mcp_url=mcp_url,
                auth_mode=AUTH_MODE_NONE,
            ),
            discovery_url=resolved_discovery_url,
            auth_required=False,
        )
        _enforce_secure_endpoint(connection.endpoint_url, connection.auth_required)
        return connection

    if auth_mode == AUTH_MODE_SSO:
        resolved_discovery_url = _resolve_configured_auth_discovery_endpoint(
            hostname=hostname,
            environment=environment,
            domain=domain,
            mcp_url=mcp_url,
            discovery_url=discovery_url,
        )
        connection = ResolvedMCPConnection(
            endpoint_url=_resolve_mcp_endpoint(
                hostname=hostname,
                environment=environment,
                domain=domain,
                mcp_url=mcp_url,
                auth_mode=AUTH_MODE_SSO,
            ),
            discovery_url=resolved_discovery_url,
            auth_required=True,
        )
        _enforce_secure_endpoint(connection.endpoint_url, connection.auth_required)
        return connection

    resolved_discovery_url = _resolve_auth_discovery_endpoint(
        hostname=hostname,
        environment=environment,
        domain=domain,
        mcp_url=mcp_url,
        discovery_url=discovery_url,
    )
    redirect_discovery_url = _resolve_redirect_discovery_endpoint(
        hostname=hostname,
        environment=environment,
        domain=domain,
        mcp_url=mcp_url,
    )
    auth_discovery, discovered = _discover_auth_config(
        resolved_discovery_url,
        redirect_discovery_url,
        insecure,
    )
    if auth_discovery is not None:
        auth_required = auth_discovery.auth_required
        service_endpoint = auth_discovery.services.get("mcp")
        resolved_auth_mode = AUTH_MODE_SSO if auth_required else AUTH_MODE_NONE
        connection = ResolvedMCPConnection(
            endpoint_url=(_normalize_url(service_endpoint) if service_endpoint else None)
            or _resolve_mcp_endpoint(
                hostname=hostname,
                environment=environment,
                domain=domain,
                mcp_url=mcp_url,
                auth_mode=resolved_auth_mode,
            ),
            discovery_url=resolved_discovery_url,
            auth_required=auth_required,
            discovered_oidc=discovered,
            discovered_scopes=auth_discovery.scopes,
        )
        _enforce_secure_endpoint(connection.endpoint_url, connection.auth_required)
        return connection

    resolved_auth_mode = AUTH_MODE_SSO if discovered else AUTH_MODE_NONE
    connection = ResolvedMCPConnection(
        endpoint_url=_resolve_mcp_endpoint(
            hostname=hostname,
            environment=environment,
            domain=domain,
            mcp_url=mcp_url,
            auth_mode=resolved_auth_mode,
        ),
        discovery_url=resolved_discovery_url,
        auth_required=discovered is not None,
        discovered_oidc=discovered,
    )
    _enforce_secure_endpoint(connection.endpoint_url, connection.auth_required)
    return connection


def _resolve_healthcheck_url(mcp_endpoint: str) -> str:
    """Resolve the healthcheck URL for a remote MCP endpoint."""
    parsed = urlparse(mcp_endpoint)
    if not parsed.scheme or not parsed.netloc:
        raise click.ClickException(f"Invalid MCP endpoint URL: {mcp_endpoint}")
    return parsed._replace(path="/healthcheck", params="", query="", fragment="").geturl()


def _build_auth(
    issuer: str | None,
    client_id: str | None,
    connection: ResolvedMCPConnection,
    insecure: bool,
) -> OIDCAuth:
    """Build an OIDC auth helper from explicit settings or gateway discovery."""
    discovered_issuer, discovered_client_id = (
        connection.discovered_oidc if connection.discovered_oidc else (None, None)
    )
    resolved_issuer = issuer or discovered_issuer
    resolved_client_id = client_id or discovered_client_id

    if not resolved_issuer or not resolved_client_id:
        raise click.ClickException(
            "OIDC configuration was not discovered from the MCP gateway. "
            "Provide --issuer and --client-id explicitly, or use a gateway that "
            "supports auth discovery."
        )

    return OIDCAuth(
        issuer_url=resolved_issuer,
        client_id=resolved_client_id,
        scopes=list(connection.discovered_scopes) or None,
        verify=not insecure,
    )


def _target_options(function: Any) -> Any:
    """Apply common target resolution options."""
    options = [
        click.option(
            "--hostname",
            "-H",
            default=None,
            envvar="NV_CONFIG_MANAGER_HOSTNAME",
            help="Deployment base hostname, for example config-manager.example.com.",
        ),
        click.option(
            "--environment",
            "-e",
            default=None,
            help="Environment name. Combined with --domain to form <environment>.<domain>.",
        ),
        click.option(
            "--domain",
            "-d",
            default=DEFAULT_DOMAIN,
            show_default=True,
            help="Base domain used with --environment.",
        ),
        click.option(
            "--mcp-url",
            default=None,
            envvar="NV_CONFIG_MANAGER_MCP_URL",
            help="Explicit remote MCP endpoint URL. Overrides hostname resolution.",
        ),
    ]
    for option in reversed(options):
        function = option(function)
    return function


def _auth_options(function: Any) -> Any:
    """Apply common authentication options."""
    options = [
        click.option(
            "--auth-mode",
            type=click.Choice([AUTH_MODE_AUTO, AUTH_MODE_SSO, AUTH_MODE_NONE]),
            default=AUTH_MODE_AUTO,
            show_default=True,
            help=(
                "Authentication mode. auto discovers SSO from the MCP gateway; "
                "sso uses svc-mcp with a bearer token; none uses mcp without auth."
            ),
        ),
        click.option(
            "--discovery-url",
            default=None,
            envvar="NV_CONFIG_MANAGER_MCP_DISCOVERY_URL",
            help="Explicit URL used for auth discovery. Defaults to https://<base>/auth/discovery.",
        ),
        click.option(
            "--issuer",
            default=None,
            envvar="NV_CONFIG_MANAGER_OIDC_ISSUER",
            help="OIDC issuer URL. Auto-discovered from the gateway when omitted.",
        ),
        click.option(
            "--client-id",
            default=None,
            envvar="NV_CONFIG_MANAGER_OIDC_CLIENT_ID",
            help="OIDC client ID. Overrides the gateway-discovered client ID when provided.",
        ),
        click.option(
            "--insecure",
            "-k",
            is_flag=True,
            help="Disable TLS certificate verification for discovery and checks.",
        ),
    ]
    for option in reversed(options):
        function = option(function)
    return function


def _resolve_auth(
    hostname: str | None,
    environment: str | None,
    domain: str,
    mcp_url: str | None,
    discovery_url: str | None,
    auth_mode: str,
    issuer: str | None,
    client_id: str | None,
    insecure: bool,
) -> tuple[ResolvedMCPConnection, OIDCAuth | None]:
    """Resolve an auth helper for the selected MCP endpoint."""
    requested_auth_mode = auth_mode
    if issuer and client_id:
        auth_mode = AUTH_MODE_SSO
    elif issuer or client_id or auth_mode == AUTH_MODE_SSO:
        auth_mode = AUTH_MODE_AUTO

    connection = _resolve_connection(
        hostname=hostname,
        environment=environment,
        domain=domain,
        mcp_url=mcp_url,
        discovery_url=discovery_url,
        auth_mode=auth_mode,
        insecure=insecure,
    )
    if not connection.auth_required:
        if issuer or client_id or requested_auth_mode == AUTH_MODE_SSO:
            raise click.ClickException(
                "OIDC configuration was not discovered from the MCP gateway. "
                "Provide --issuer and --client-id explicitly."
            )
        return connection, None

    return connection, _build_auth(
        issuer=issuer,
        client_id=client_id,
        connection=connection,
        insecure=insecure,
    )


@click.group()
@click.version_option(version="1.0.0")
def main() -> None:
    """Authenticate and configure clients for remote NVIDIA Config Manager MCP."""


@main.command()
@_target_options
@_auth_options
@click.option("--force", is_flag=True, help="Force a new login even if a token is cached.")
def login(
    hostname: str | None,
    environment: str | None,
    domain: str,
    mcp_url: str | None,
    auth_mode: str,
    discovery_url: str | None,
    issuer: str | None,
    client_id: str | None,
    insecure: bool,
    force: bool,
) -> None:
    """Authenticate with OIDC and cache a user bearer token."""
    if insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    _connection, auth = _resolve_auth(
        hostname=hostname,
        environment=environment,
        domain=domain,
        mcp_url=mcp_url,
        discovery_url=discovery_url,
        auth_mode=auth_mode,
        issuer=issuer,
        client_id=client_id,
        insecure=insecure,
    )
    if auth is None:
        click.echo("SSO is not enabled for this MCP endpoint; no login is required.")
        return

    auth.get_access_token(force_refresh=force)
    click.echo("Authentication successful.")


@main.command()
@_target_options
@_auth_options
@click.option(
    "--force-auth-refresh",
    is_flag=True,
    help="Force a new login before printing the token.",
)
def token(
    hostname: str | None,
    environment: str | None,
    domain: str,
    mcp_url: str | None,
    auth_mode: str,
    discovery_url: str | None,
    issuer: str | None,
    client_id: str | None,
    insecure: bool,
    force_auth_refresh: bool,
) -> None:
    """Print a valid user bearer token."""
    if insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    _connection, auth = _resolve_auth(
        hostname=hostname,
        environment=environment,
        domain=domain,
        mcp_url=mcp_url,
        discovery_url=discovery_url,
        auth_mode=auth_mode,
        issuer=issuer,
        client_id=client_id,
        insecure=insecure,
    )
    if auth is None:
        click.echo(
            "SSO is not enabled for this MCP endpoint; no bearer token is required.", err=True
        )
        return

    click.echo(auth.get_access_token(force_refresh=force_auth_refresh))


@main.command()
@_target_options
@_auth_options
def endpoint(
    hostname: str | None,
    environment: str | None,
    domain: str,
    mcp_url: str | None,
    auth_mode: str,
    discovery_url: str | None,
    issuer: str | None,
    client_id: str | None,
    insecure: bool,
) -> None:
    """Print the remote MCP endpoint URL."""
    if insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    if issuer or client_id:
        auth_mode = AUTH_MODE_SSO
    connection = _resolve_connection(
        hostname=hostname,
        environment=environment,
        domain=domain,
        mcp_url=mcp_url,
        discovery_url=discovery_url,
        auth_mode=auth_mode,
        insecure=insecure,
    )
    click.echo(connection.endpoint_url)


@main.command(name="config")
@_target_options
@_auth_options
@click.option(
    "--token-env-var",
    default=DEFAULT_TOKEN_ENV_VAR,
    show_default=True,
    help="Environment variable name that will hold the bearer token.",
)
def config_command(
    hostname: str | None,
    environment: str | None,
    domain: str,
    mcp_url: str | None,
    auth_mode: str,
    discovery_url: str | None,
    issuer: str | None,
    client_id: str | None,
    insecure: bool,
    token_env_var: str,
) -> None:
    """Print generic Streamable HTTP MCP connection details."""
    if insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    if issuer or client_id:
        auth_mode = AUTH_MODE_SSO
    connection = _resolve_connection(
        hostname=hostname,
        environment=environment,
        domain=domain,
        mcp_url=mcp_url,
        discovery_url=discovery_url,
        auth_mode=auth_mode,
        insecure=insecure,
    )
    click.echo("MCP transport: Streamable HTTP")
    click.echo(f"MCP endpoint: {connection.endpoint_url}")
    if not connection.auth_required:
        click.echo("Authentication: none")
        click.echo("No Authorization header is required.")
        return

    click.echo("Authentication: bearer token")
    click.echo(f"Bearer token environment variable: {token_env_var}")
    click.echo("Required HTTP header:")
    click.echo(f"  Authorization: Bearer ${{{token_env_var}}}")
    click.echo("Token command:")
    token_command = [
        "nvcm-mcp-cli",
        "token",
        "--auth-mode",
        "sso",
        "--mcp-url",
        connection.endpoint_url,
    ]
    if insecure:
        token_command.append("--insecure")
    if discovery_url:
        token_command.extend(["--discovery-url", connection.discovery_url])
    if issuer:
        token_command.extend(["--issuer", issuer])
    if client_id:
        token_command.extend(["--client-id", client_id])
    token_command_text = " ".join(shlex.quote(part) for part in token_command)
    click.echo(f'  export {token_env_var}="$({token_command_text})"')


@main.command()
@_target_options
@_auth_options
@click.option(
    "--force-auth-refresh",
    is_flag=True,
    help="Force a new login before checking the endpoint.",
)
def check(
    hostname: str | None,
    environment: str | None,
    domain: str,
    mcp_url: str | None,
    auth_mode: str,
    discovery_url: str | None,
    issuer: str | None,
    client_id: str | None,
    insecure: bool,
    force_auth_refresh: bool,
) -> None:
    """Validate token availability and remote MCP service health."""
    if insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    connection, auth = _resolve_auth(
        hostname=hostname,
        environment=environment,
        domain=domain,
        mcp_url=mcp_url,
        discovery_url=discovery_url,
        auth_mode=auth_mode,
        issuer=issuer,
        client_id=client_id,
        insecure=insecure,
    )
    headers: dict[str, str] = {}
    if auth is not None:
        access_token = auth.get_access_token(force_refresh=force_auth_refresh)
        headers["Authorization"] = f"Bearer {access_token}"

    healthcheck_url = _resolve_healthcheck_url(connection.endpoint_url)

    try:
        response = requests.get(
            healthcheck_url,
            headers=headers,
            timeout=DEFAULT_TIMEOUT_SECONDS,
            allow_redirects=False,
            verify=not insecure,
        )
        if response.status_code in (301, 302, 303, 307, 308):
            raise click.ClickException(
                "The MCP healthcheck redirected instead of accepting the request. "
                "Verify the MCP endpoint and authentication mode."
            )
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise click.ClickException(f"Remote MCP healthcheck failed: {e}") from e

    if connection.auth_required:
        click.echo(f"Token available for endpoint: {connection.endpoint_url}")
    else:
        click.echo(f"No bearer token required for endpoint: {connection.endpoint_url}")
    click.echo(f"Healthcheck passed: {healthcheck_url}")
