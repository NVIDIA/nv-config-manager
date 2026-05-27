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
"""Nautobot GraphQL Client."""

from __future__ import annotations

import pathlib
from typing import Any

import requests
from requests.adapters import HTTPAdapter, Retry

QUERY_PATH = f"{pathlib.Path(__file__).parent.resolve()}/graphql"


class QueryException(Exception):
    """GraphQL Query Exception."""


class NautobotClient:
    """Nautbot GraphQL Client."""

    def __init__(self, nautobot_url: str, nautobot_token: str) -> None:
        """Initialize nautbot client."""
        # Configure retry strategy
        retry_strategy = Retry(
            total=1,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)

        self.session = requests.Session()
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        self.session.headers.update({"Authorization": f"Token {nautobot_token}"})
        if nautobot_url and nautobot_url.endswith("/"):
            nautobot_url = nautobot_url[:-1]
        self.nautobot_url = nautobot_url
        self.graphql_endpoint = f"{nautobot_url}/api/graphql/"

    def graphql_query(
        self, query: str, variables: dict[str, Any] | None, timeout: int = 60
    ) -> dict[str, Any]:
        """Execute a graphql query."""
        payload = {"query": query, "variables": variables or {}}
        rsp = self.session.post(self.graphql_endpoint, json=payload, timeout=timeout)
        rsp.raise_for_status()
        return rsp.json()

    def device_id_from_hostname(self, hostname: str) -> str:
        """Return the device ID for a given device hostname."""
        with open(f"{QUERY_PATH}/query_device_id_by_hostname.graphql", encoding="utf-8") as f:
            query = f.read()
        rsp = self.graphql_query(query=query, variables={"hostname": hostname})
        try:
            if len(rsp["data"]["devices"]) > 1:
                matching_names = [device["name"] for device in rsp["data"]["devices"]]
                raise QueryException(
                    f"Multiple names matched the given hostname query: {matching_names}"
                )
            return rsp["data"]["devices"][0]["id"]
        except (KeyError, IndexError) as exc:
            raise QueryException(f"Failed to find device ID for {hostname}.") from exc

    def load_device_data(
        self, device_id: str | None = None, hostname: str | None = None
    ) -> dict[str, Any]:
        """Load data for the device from nautobot."""
        if not (device_id or hostname):
            raise QueryException("Must supply either a hostname or device ID.")

        if not device_id:
            # Lookup ID from hostname
            device_id = self.device_id_from_hostname(hostname)

        query_file = "query_config_data_by_device_id_v2.graphql"

        with open(f"{QUERY_PATH}/{query_file}", encoding="utf-8") as f:
            query = f.read()
        return self.graphql_query(
            query=query,
            variables={"id": device_id, "id_str": device_id},
        )

    def load_location_data(self, location_name: str) -> dict[str, Any]:
        """Load location data from nautobot."""
        with open(f"{QUERY_PATH}/query_location_data.graphql", encoding="utf-8") as f:
            query = f.read()
        return self.graphql_query(query=query, variables={"location": location_name})
