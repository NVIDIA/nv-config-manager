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
"""Download latest device configs from the NVIDIA Config Manager Config Store API."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import ParseResult, urlparse, urlunparse

import requests
import urllib3

from nv_config_manager.common.oidc import OIDCAuth

REDIRECT_STATUSES = {301, 302, 303, 307, 308}
CONFIG_FILE_TYPES = ("intended", "backup")
DEFAULT_TIMEOUT = 60

RequestParams = Mapping[str, str | int | bool] | Sequence[tuple[str, str | int | bool]] | None


@dataclass(frozen=True)
class TargetURLs:
    """Resolved Config Store URLs."""

    discovery_api_url: str
    browser_api_url: str
    service_api_url: str | None


@dataclass(frozen=True)
class DownloadResult:
    """Summary of one written config file."""

    device_uuid: str
    device_name: str
    file_type: str
    filename: str
    path: Path


class ConfigStoreClient:
    """Small requests-based client for Config Store API reads."""

    def __init__(self, base_url: str, verify_tls: bool, access_token: str | None) -> None:
        self.base_url = base_url.rstrip("/")
        self.verify_tls = verify_tls
        self.session = requests.Session()
        self.headers: dict[str, str] = {}
        if access_token:
            self.headers["Authorization"] = f"Bearer {access_token}"

    def close(self) -> None:
        """Close the underlying requests session."""
        self.session.close()

    def get_json(self, path: str, params: RequestParams = None) -> Any:
        """Run a GET request and return parsed JSON."""
        url = f"{self.base_url}{path}"
        response = self.session.get(
            url,
            headers=self.headers,
            params=params,
            timeout=DEFAULT_TIMEOUT,
            allow_redirects=False,
            verify=self.verify_tls,
        )

        if response.status_code in REDIRECT_STATUSES:
            location = response.headers.get("Location", "")
            raise RuntimeError(
                f"GET {url} redirected to {location[:160]}; the API request was not accepted."
            )

        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(
                f"GET {url} failed with HTTP {response.status_code}: "
                f"{format_response_detail(response)}"
            ) from exc

        try:
            return response.json()
        except ValueError as exc:
            raise RuntimeError(f"GET {url} returned non-JSON: {response.text[:1000]}") from exc


def format_response_detail(response: requests.Response) -> str:
    """Return a useful short error body for an HTTP response."""
    try:
        return json.dumps(response.json(), indent=2)[:1000]
    except ValueError:
        return response.text[:1000]


def with_path(base_url: str, path: str) -> str:
    """Append an API path to a base URL."""
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


def api_base_from_parts(parsed: ParseResult, path: str = "") -> str:
    """Build a base URL from parsed URL parts and a path."""
    clean_path = path.rstrip("/")
    return urlunparse((parsed.scheme, parsed.netloc, clean_path, "", "", ""))


def replace_hostname(parsed: ParseResult, hostname: str) -> str:
    """Return a URL using the same scheme/path with a different hostname."""
    return api_base_from_parts(parsed._replace(netloc=hostname), parsed.path)


def target_from_hostname(hostname: str) -> TargetURLs:
    """Resolve Config Store API URLs from a bare hostname."""
    host = hostname.strip().strip("/")
    if host.startswith("svc-config-store."):
        browser_host = host.removeprefix("svc-")
        return TargetURLs(
            discovery_api_url=f"https://{browser_host}",
            browser_api_url=f"https://{browser_host}",
            service_api_url=f"https://{host}",
        )

    if host.startswith("config-store."):
        return TargetURLs(
            discovery_api_url=f"https://{host}",
            browser_api_url=f"https://{host}",
            service_api_url=f"https://svc-{host}",
        )

    return TargetURLs(
        discovery_api_url=f"https://config-store.{host}",
        browser_api_url=f"https://config-store.{host}",
        service_api_url=f"https://svc-config-store.{host}",
    )


def target_from_url(target: str) -> TargetURLs:
    """Resolve Config Store API URLs from a URL."""
    parsed = urlparse(target)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Expected URL with scheme and hostname, got {target!r}")

    path = parsed.path.rstrip("/")
    host = parsed.hostname or parsed.netloc

    if host.startswith("svc-config-store."):
        browser_host = host.removeprefix("svc-")
        return TargetURLs(
            discovery_api_url=replace_hostname(parsed, browser_host),
            browser_api_url=replace_hostname(parsed, browser_host),
            service_api_url=api_base_from_parts(parsed, path),
        )

    if host.startswith("config-store."):
        service_host = f"svc-{host}"
        return TargetURLs(
            discovery_api_url=api_base_from_parts(parsed, path),
            browser_api_url=api_base_from_parts(parsed, path),
            service_api_url=replace_hostname(parsed, service_host),
        )

    if path in ("", "/configs"):
        return target_from_hostname(host)

    # Treat non-empty, non-UI paths as an explicit API base, for example
    # https://api.config-manager.local/config-store.
    explicit_api_url = api_base_from_parts(parsed, path)
    return TargetURLs(
        discovery_api_url=explicit_api_url,
        browser_api_url=explicit_api_url,
        service_api_url=None,
    )


def resolve_target(target: str) -> TargetURLs:
    """Resolve the target argument into discovery, browser, and svc API URLs."""
    if target.startswith(("http://", "https://")):
        return target_from_url(target)
    return target_from_hostname(target)


def build_oidc_auth(args: argparse.Namespace, discovery_api_url: str) -> OIDCAuth | None:
    """Build an OIDCAuth instance from explicit args or gateway discovery."""
    if args.no_auth:
        return None

    token_file = Path(args.token_file).expanduser() if args.token_file else None
    if args.issuer or args.client_id:
        if not args.issuer or not args.client_id:
            raise RuntimeError("--issuer and --client-id must be provided together.")
        return OIDCAuth(
            issuer_url=args.issuer,
            client_id=args.client_id,
            redirect_port=args.redirect_port,
            token_file=token_file,
        )

    discovery_url = with_path(discovery_api_url, "/v1/admin/stats")
    result = OIDCAuth.discover_oidc_config(discovery_url, verify=not args.insecure)
    if result is None:
        return None

    issuer_url, client_id = result
    print(f"Discovered OIDC issuer: {issuer_url}")
    print(f"Discovered OIDC client ID: {client_id}")
    return OIDCAuth(
        issuer_url=issuer_url,
        client_id=client_id,
        redirect_port=args.redirect_port,
        token_file=token_file,
    )


def fetch_access_token(auth: OIDCAuth | None, force_login: bool) -> str | None:
    """Return a bearer token when OIDC auth is enabled."""
    if auth is None:
        return None
    print("Authenticating with OIDC PKCE...")
    return auth.get_access_token(force_refresh=force_login)


def expect_dict_list(value: Any, context: str) -> list[dict[str, Any]]:
    """Validate that an API response is a list of dict objects."""
    if not isinstance(value, list):
        raise RuntimeError(f"Unexpected {context} response: {value!r}")
    if not all(isinstance(item, dict) for item in value):
        raise RuntimeError(f"Unexpected {context} response entries: {value!r}")
    return value


def list_device_uuids(client: ConfigStoreClient, page_size: int) -> list[str]:
    """Return every device UUID known to the Config Store."""
    uuids: list[str] = []
    seen: set[str] = set()
    offset = 0

    while True:
        response = client.get_json(
            "/v1/admin/devices",
            params={"limit": page_size, "offset": offset},
        )
        rows = expect_dict_list(response, "device list")
        if not rows:
            break

        for row in rows:
            device_uuid = row.get("uuid")
            if not isinstance(device_uuid, str) or not device_uuid:
                raise RuntimeError(f"Unexpected device row: {row!r}")
            if device_uuid not in seen:
                seen.add(device_uuid)
                uuids.append(device_uuid)

        if len(rows) < page_size:
            break
        offset += page_size

    return uuids


def fetch_device_configs(
    client: ConfigStoreClient,
    device_uuid: str,
    file_type: str,
) -> list[dict[str, Any]]:
    """Return latest config files for a device and file type."""
    response = client.get_json(
        f"/v1/config/device/{device_uuid}",
        params={"file_type": file_type},
    )
    return expect_dict_list(response, f"{file_type} configs for {device_uuid}")


def safe_path_component(value: str, fallback: str) -> str:
    """Sanitize one filesystem path component."""
    normalized = re.sub(r"[\\/]+", "_", value.strip())
    normalized = re.sub(r"[^A-Za-z0-9._ -]+", "_", normalized)
    normalized = re.sub(r"\s+", "_", normalized).strip("._- ")
    return normalized or fallback


def safe_config_path(filename: str) -> Path:
    """Return a safe relative path for a config filename."""
    parts: list[str] = []
    pure_path = PurePosixPath(filename.replace("\\", "/"))
    for part in pure_path.parts:
        if part in ("", ".", "/"):
            continue
        if part == "..":
            parts.append("_")
            continue
        parts.append(safe_path_component(part, "file"))
    return Path(*parts) if parts else Path("config.txt")


def device_name_from_configs(device_uuid: str, configs: Sequence[dict[str, Any]]) -> str:
    """Return the enriched device name when available."""
    for config in configs:
        device = config.get("device")
        if isinstance(device, dict):
            name = device.get("name")
            if isinstance(name, str) and name.strip():
                return name
    return device_uuid


def unique_path(path: Path, used_paths: set[Path]) -> Path:
    """Return a unique path for this run without deleting existing files."""
    candidate = path
    counter = 2
    while candidate in used_paths:
        candidate = path.with_name(f"{path.stem}-{counter}{path.suffix}")
        counter += 1
    used_paths.add(candidate)
    return candidate


def write_config_file(
    output_dir: Path,
    config: dict[str, Any],
    device_uuid: str,
    device_name: str,
    file_type: str,
    include_file_type_dir: bool,
    used_paths: set[Path],
) -> DownloadResult:
    """Write a single config file to disk."""
    filename = config.get("filename")
    content = config.get("content")
    if not isinstance(filename, str) or not filename:
        raise RuntimeError(f"Config for {device_uuid} is missing filename: {config!r}")
    if not isinstance(content, str):
        raise RuntimeError(f"Config {filename} for {device_uuid} is missing text content.")

    device_dir = safe_path_component(device_name, device_uuid)
    relative_path = Path(device_dir) / safe_config_path(filename)
    if include_file_type_dir:
        relative_path = Path(file_type) / relative_path

    path = unique_path(output_dir / relative_path, used_paths)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")

    return DownloadResult(
        device_uuid=device_uuid,
        device_name=device_name,
        file_type=file_type,
        filename=filename,
        path=path,
    )


def selected_file_types(file_type: str) -> tuple[str, ...]:
    """Return the file types selected by the CLI option."""
    if file_type == "both":
        return CONFIG_FILE_TYPES
    return (file_type,)


def download_configs(
    client: ConfigStoreClient,
    output_dir: Path,
    file_types: Sequence[str],
    page_size: int,
) -> tuple[list[DownloadResult], list[str], list[str]]:
    """Download configs and return writes, skipped devices, and failures."""
    device_uuids = list_device_uuids(client, page_size)
    print(f"Found {len(device_uuids)} device(s) in Config Store.")

    output_dir.mkdir(parents=True, exist_ok=True)

    results: list[DownloadResult] = []
    skipped: list[str] = []
    failures: list[str] = []
    used_paths: set[Path] = set()
    include_file_type_dir = len(file_types) > 1

    for index, device_uuid in enumerate(device_uuids, start=1):
        written_for_device = 0
        device_label = device_uuid
        try:
            for file_type in file_types:
                configs = fetch_device_configs(client, device_uuid, file_type)
                if not configs:
                    continue

                device_name = device_name_from_configs(device_uuid, configs)
                device_label = device_name
                for config in configs:
                    result = write_config_file(
                        output_dir,
                        config,
                        device_uuid,
                        device_name,
                        file_type,
                        include_file_type_dir,
                        used_paths,
                    )
                    results.append(result)
                    written_for_device += 1
        except RuntimeError as exc:
            failures.append(f"{device_uuid}: {exc}")
            print(f"[{index}/{len(device_uuids)}] FAIL {device_uuid}: {exc}", file=sys.stderr)
            continue

        if written_for_device:
            print(
                f"[{index}/{len(device_uuids)}] wrote {written_for_device} file(s): {device_label}"
            )
        else:
            skipped.append(device_uuid)

    return results, skipped, failures


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Download latest configs from the NVIDIA Config Manager Config Store API into a local directory. "
            "Pass a base hostname such as config-manager.example.com, a config-store hostname, or a full API URL."
        ),
    )
    parser.add_argument(
        "target",
        help=(
            "Base hostname or Config Store API URL. Examples: config-manager.local, "
            "config-store.config-manager.example.com, https://config-store.config-manager.example.com, "
            "http://localhost:9000."
        ),
    )
    parser.add_argument("output_dir", help="Directory to write downloaded config files.")
    parser.add_argument(
        "--file-type",
        choices=("intended", "backup", "both"),
        default="intended",
        help="Config type to download. Default: intended.",
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=1000,
        help="Page size for /v1/admin/devices pagination. Default: 1000.",
    )
    parser.add_argument("--issuer", help="OIDC issuer URL. Requires --client-id.")
    parser.add_argument("--client-id", help="OIDC client ID. Requires --issuer.")
    parser.add_argument(
        "--redirect-port",
        type=int,
        default=8765,
        help="Local callback port for OIDC PKCE login. Default: 8765.",
    )
    parser.add_argument(
        "--token-file",
        help="Path for cached OIDC token JSON. Default: ~/.nv-config-manager/token.json.",
    )
    parser.add_argument(
        "--force-login",
        action="store_true",
        help="Force a fresh OIDC login instead of using a cached token.",
    )
    parser.add_argument(
        "-k",
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification.",
    )
    parser.add_argument(
        "--no-auth",
        action="store_true",
        help="Skip OIDC discovery/login and call the API without Authorization.",
    )
    return parser.parse_args(argv)


def validate_args(args: argparse.Namespace) -> None:
    """Validate parsed CLI arguments."""
    if args.page_size < 1:
        raise RuntimeError("--page-size must be at least 1.")
    if args.redirect_port < 1 or args.redirect_port > 65535:
        raise RuntimeError("--redirect-port must be between 1 and 65535.")


def run(argv: list[str] | None = None) -> int:
    """Run the config download helper."""
    args = parse_args(argv if argv is not None else sys.argv[1:])
    validate_args(args)

    if args.insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    output_dir = Path(args.output_dir).expanduser().resolve()
    targets = resolve_target(args.target)
    auth = build_oidc_auth(args, targets.discovery_api_url)
    access_token = fetch_access_token(auth, args.force_login)
    api_url = (
        targets.service_api_url
        if access_token and targets.service_api_url
        else targets.browser_api_url
    )

    print(f"Using Config Store API: {api_url}")
    if access_token is None:
        print("OIDC auth not enabled for this run.")

    client = ConfigStoreClient(api_url, verify_tls=not args.insecure, access_token=access_token)
    try:
        results, skipped, failures = download_configs(
            client,
            output_dir,
            selected_file_types(args.file_type),
            args.page_size,
        )
    finally:
        client.close()

    print()
    print(f"Wrote {len(results)} config file(s) to {output_dir}")
    if skipped:
        print(f"Skipped {len(skipped)} device(s) with no matching configs.")
    if failures:
        print(f"Failed to process {len(failures)} device(s):", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    try:
        return run(argv)
    except (RuntimeError, ValueError, requests.RequestException) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
