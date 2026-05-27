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
"""Start backup workflows for managed devices returned by the workflow parameter API."""

import argparse
import json
import sys
from typing import Any

import requests
import urllib3

REDIRECT_STATUSES = {301, 302, 303, 307, 308}


def workflow_url(hostname: str) -> str:
    """Return the workflow service URL from a hostname or full URL."""
    hostname = hostname.rstrip("/")
    if hostname.startswith(("http://", "https://")):
        return hostname
    return f"https://{hostname}"


def request_json(
    session: requests.Session,
    method: str,
    url: str,
    *,
    verify_tls: bool,
    **kwargs: Any,
) -> Any:
    """Make an HTTP request and return JSON with useful errors."""
    response = session.request(
        method,
        url,
        timeout=30,
        allow_redirects=False,
        verify=verify_tls,
        **kwargs,
    )
    if response.status_code in REDIRECT_STATUSES:
        location = response.headers.get("Location", "")
        raise RuntimeError(
            f"{method} {url} redirected to {location[:160]}; expected the unauthenticated API."
        )

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = response.text[:1000]
        try:
            detail = json.dumps(response.json(), indent=2)
        except ValueError:
            pass
        raise RuntimeError(
            f"{method} {url} failed with HTTP {response.status_code}: {detail}"
        ) from exc

    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError(f"{method} {url} returned non-JSON: {response.text[:1000]}") from exc


def resolve_site_id(session: requests.Session, base_url: str, site: str, verify_tls: bool) -> str:
    """Resolve a site name to the ID expected by the device parameter API."""
    locations = request_json(
        session,
        "GET",
        f"{base_url}/v1/parameter/location",
        verify_tls=verify_tls,
        params=[("location_type", "Site"), ("location_type", "Module")],
    )
    if not isinstance(locations, list):
        raise RuntimeError(f"Unexpected location response: {locations!r}")

    matches = [
        location
        for location in locations
        if isinstance(location, dict)
        and (str(location.get("id")) == site or str(location.get("name")) == site)
    ]
    if len(matches) == 1:
        return str(matches[0]["id"])
    if len(matches) > 1:
        names = ", ".join(str(location.get("name")) for location in matches)
        raise RuntimeError(f"Site {site!r} matched multiple locations: {names}")
    return site


def get_devices(
    session: requests.Session,
    base_url: str,
    verify_tls: bool,
    site: str | None,
) -> list[dict[str, Any]]:
    """Return devices from the parameter API."""
    params = None
    if site:
        params = {"site": resolve_site_id(session, base_url, site, verify_tls)}

    devices = request_json(
        session,
        "GET",
        f"{base_url}/v1/parameter/device",
        verify_tls=verify_tls,
        params=params,
    )
    if not isinstance(devices, list):
        raise RuntimeError(f"Unexpected device response: {devices!r}")

    return [
        device
        for device in devices
        if isinstance(device, dict) and device.get("id") and device.get("name")
    ]


def start_backup(
    session: requests.Session,
    base_url: str,
    verify_tls: bool,
    device: dict[str, Any],
) -> dict[str, Any]:
    """Start one backup workflow."""
    payload = {
        "device_id": device["id"],
        "trigger": "API",
        "user": None,
        "user_domain": None,
        "workflow_id": None,
        "intended_config_commit_id": None,
    }
    result = request_json(
        session,
        "POST",
        f"{base_url}/v1/workflow/ngc/backup",
        verify_tls=verify_tls,
        json=payload,
    )
    if not isinstance(result, dict):
        raise RuntimeError(f"Unexpected backup response for {device['name']}: {result!r}")
    return result


def parse_args(argv: list[str]) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Call the backup workflow for each device returned by the parameter API.",
    )
    parser.add_argument(
        "workflow_hostname",
        help="Workflow hostname or URL, for example workflow.config-manager.example.com or http://localhost:9000.",
    )
    parser.add_argument("--site", help="Optional site/location name or ID to filter devices.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List devices without starting backup workflows.",
    )
    parser.add_argument(
        "--verify-tls",
        action="store_true",
        help="Verify TLS certificates. Disabled by default for local/AIR-style setups.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the backup helper."""
    args = parse_args(argv if argv is not None else sys.argv[1:])
    base_url = workflow_url(args.workflow_hostname)
    verify_tls = bool(args.verify_tls)
    if not verify_tls:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    failures = 0
    with requests.Session() as session:
        devices = get_devices(session, base_url, verify_tls, args.site)
        print(f"Found {len(devices)} device(s).")
        for device in devices:
            platform = f" ({device.get('platform')})" if device.get("platform") else ""
            print(f"  - {device['name']}{platform}: {device['id']}")

        if args.dry_run or not devices:
            return 0

        print()
        for device in devices:
            try:
                result = start_backup(session, base_url, verify_tls, device)
            except RuntimeError as exc:
                failures += 1
                print(f"FAIL {device['name']}: {exc}", file=sys.stderr)
                continue

            workflow_id = result.get("id", "<missing workflow id>")
            href = f" {result['href']}" if result.get("href") else ""
            print(f"OK {device['name']}: {workflow_id}{href}")

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
