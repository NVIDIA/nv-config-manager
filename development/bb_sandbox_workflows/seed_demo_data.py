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
"""Seed idempotent Nautobot fixtures for the Backbone sandbox workflows."""

import argparse
import os
from typing import Any

import requests
import urllib3


class NautobotSeeder:
    """Minimal Nautobot REST client for local demo fixture creation."""

    def __init__(self, url: str, token: str, *, verify: bool) -> None:
        self.api_url = f"{url.rstrip('/')}/api"
        self.verify = verify
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Accept": "application/json",
                "Authorization": f"Token {token}",
                "Content-Type": "application/json",
            }
        )

    def request(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call a Nautobot API endpoint and return its JSON response."""
        response = self.session.request(
            method,
            f"{self.api_url}{endpoint}",
            params=params,
            json=payload,
            timeout=60,
            verify=self.verify,
        )
        response.raise_for_status()
        return response.json()

    def find_one(self, endpoint: str, **lookup: Any) -> dict[str, Any] | None:
        """Return a unique object matching the supplied API filters."""
        response = self.request("GET", endpoint, params=lookup)
        results = response.get("results", [])
        if len(results) > 1:
            raise RuntimeError(f"Multiple {endpoint} objects matched {lookup}")
        return results[0] if results else None

    def ensure(
        self,
        endpoint: str,
        lookup: dict[str, Any],
        payload: dict[str, Any],
    ) -> tuple[str, dict[str, Any]]:
        """Create a fixture or restore its declared demo attributes."""
        current = self.find_one(endpoint, **lookup)
        if current is None:
            return "created", self.request("POST", endpoint, payload=payload)
        return "updated", self.request("PATCH", f"{endpoint}{current['id']}/", payload=payload)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--url",
        default=os.getenv("NAUTOBOT_URL", "https://nautobot.config-manager.local"),
    )
    parser.add_argument("--token", default=os.getenv("NAUTOBOT_TOKEN"))
    parser.add_argument(
        "--render-url",
        default=os.getenv("RENDER_URL", "https://render.config-manager.local"),
    )
    parser.add_argument(
        "--skip-baseline-renders",
        action="store_true",
        help="Do not create initial Active-state Config Store revisions",
    )
    parser.add_argument(
        "--insecure",
        action="store_true",
        help="Disable TLS certificate verification for the local Kind gateway",
    )
    args = parser.parse_args()
    if not args.token:
        parser.error("provide --token or set NAUTOBOT_TOKEN")
    return args


def required_object(client: NautobotSeeder, endpoint: str, **lookup: Any) -> dict[str, Any]:
    """Resolve a required bootstrap object or fail with useful context."""
    obj = client.find_one(endpoint, **lookup)
    if obj is None:
        raise RuntimeError(f"Required Nautobot object does not exist: {endpoint} {lookup}")
    return obj


def main() -> None:
    """Create allocation pools and unprovisioned demo circuits."""
    args = parse_args()
    if args.insecure:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    client = NautobotSeeder(args.url, args.token, verify=not args.insecure)

    active = required_object(client, "/extras/statuses/", name="Active")
    planned = required_object(client, "/extras/statuses/", name="Planned")
    namespace = required_object(client, "/ipam/namespaces/", name="Global")
    role = required_object(client, "/extras/roles/", name="BB-P2P")
    backbone_role = required_object(client, "/extras/roles/", name="Backbone Router")

    fixtures: list[tuple[str, str, str]] = []
    for prefix in ("198.18.0.0/24", "2001:db8:bb::/120"):
        action, obj = client.ensure(
            "/ipam/prefixes/",
            {"prefix": prefix, "namespace": namespace["id"]},
            {
                "prefix": prefix,
                "namespace": namespace["id"],
                "status": active["id"],
                "role": role["id"],
                "type": "container",
                "description": "BB sandbox point-to-point allocation pool",
            },
        )
        fixtures.append((action, "prefix", obj["prefix"]))

    _, provider = client.ensure(
        "/circuits/providers/",
        {"name": "BB Sandbox Demo"},
        {
            "name": "BB Sandbox Demo",
            "comments": "Local-only provider for Backbone workflow demonstrations",
        },
    )
    _, circuit_type = client.ensure(
        "/circuits/circuit-types/",
        {"name": "Internal Backbone Demo"},
        {
            "name": "Internal Backbone Demo",
            "description": "Unprovisioned internal Backbone test circuit",
        },
    )
    for sequence in range(1, 4):
        cid = f"BB-DEMO-UNPROVISIONED-{sequence:03d}"
        action, obj = client.ensure(
            "/circuits/circuits/",
            {"cid": cid, "provider": provider["id"]},
            {
                "cid": cid,
                "provider": provider["id"],
                "circuit_type": circuit_type["id"],
                "status": planned["id"],
                "description": "Available for the internal Backbone bringup demo",
                "comments": "No terminations are assigned; choose both endpoints in the workflow form.",
            },
        )
        fixtures.append((action, "circuit", obj["cid"]))

    for action, kind, name in fixtures:
        print(f"{action:7} {kind:7} {name}")

    if not args.skip_baseline_renders:
        devices = client.request(
            "GET",
            "/dcim/devices/",
            params={"role": backbone_role["id"], "limit": 100},
        ).get("results", [])
        for device in devices:
            response = client.session.post(
                f"{args.render_url.rstrip('/')}/v1/render/{device['id']}/render",
                json={"commit_message": "BB sandbox initial Active-state render"},
                timeout=300,
                verify=client.verify,
            )
            response.raise_for_status()
            print(f"rendered device  {device['name']}")


if __name__ == "__main__":
    main()
