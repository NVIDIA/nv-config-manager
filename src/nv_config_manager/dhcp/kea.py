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
"""Local KEA Client for managing DHCP Configuration testing and reloads."""

from __future__ import annotations

from configparser import ConfigParser
from enum import IntEnum
from typing import Any, Literal

import aiohttp

from nv_config_manager.common.config import load_config


class IpVersion(IntEnum):
    """Supported DHCP address families."""

    V4 = 4
    V6 = 6


class KeaException(Exception):
    """KEA Exception Class."""


class KeaClient:
    """Async KEA REST Client."""

    @staticmethod
    def from_config(config: ConfigParser | None = None, attached: bool = False) -> KeaClient:
        """Create a KEA client from the configured server and port."""
        if config is None:
            config = load_config()
        if attached:
            host = "localhost"
        else:
            host = config["dhcp.kea"]["server"]
        return KeaClient(host=host, port=int(config["dhcp.kea"]["port"]))

    def __init__(self, host: str | None = None, port: int = 8000) -> None:
        """Initialize a KEA REST Client."""
        self.url = f"http://{host}:{port}/"
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create the aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            connector = aiohttp.TCPConnector()
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                connector=connector,
            )
        return self._session

    async def close(self) -> None:
        """Close the client session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self) -> KeaClient:
        """Async context manager entry."""
        return self

    async def __aexit__(
        self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: object
    ) -> None:
        """Async context manager exit."""
        await self.close()

    async def status(self) -> Any:
        """Return the status of the KEA server."""
        data = {"command": "status-get"}
        session = await self._get_session()
        try:
            async with session.post(self.url, json=data) as rsp:
                rsp.raise_for_status()
                return await rsp.json()
        except TimeoutError as exc:
            raise TimeoutError(
                "KEA Request timed out, are you running within a KEA Docker Container?"
            ) from exc

    async def test_config(
        self, configuration: dict[str, Any], version: int = 4
    ) -> tuple[bool, str | None]:
        """Test if a proposed configuration is valid."""
        data = {
            "command": "config-test",
            "service": [f"dhcp{version}"],
            "arguments": configuration,
        }
        session = await self._get_session()
        try:
            async with session.post(self.url, json=data) as rsp:
                result = await rsp.json()
                if result[0]["result"] != 0:
                    return False, result[0]["text"]
                return True, None
        except TimeoutError as exc:
            raise TimeoutError(
                "KEA Request timed out, are you running within a KEA Docker Container?"
            ) from exc

    async def set_config(self, configuration: dict[str, Any], version: int = 4) -> None:
        """Set the KEA DHCP Configuration."""
        session = await self._get_session()
        try:
            # Set configuration in memory
            data = {
                "command": "config-set",
                "service": [f"dhcp{version}"],
                "arguments": configuration,
            }
            async with session.post(self.url, json=data) as rsp:
                result = await rsp.json()
                if result[0]["result"] != 0:
                    raise KeaException(f"Failed to set configuration: {result[0]['text']}")

            # Persist configuration to disk
            data = {
                "command": "config-write",
                "service": [f"dhcp{version}"],
                "arguments": {"filename": "/etc/kea/kea-dhcp4.conf"},
            }
            async with session.post(self.url, json=data) as rsp:
                result = await rsp.json()
                if result[0]["result"] != 0:
                    raise KeaException(
                        f"Failed to persist updated configuration to disk: {result[0]['text']}"
                    )

        except TimeoutError as exc:
            raise TimeoutError(
                "KEA Request timed out, are you running within a KEA Docker Container?"
            ) from exc

    async def get_config(self, version: int = 4) -> list[dict[str, Any]]:
        """Return the running KEA DHCP Configuration."""
        session = await self._get_session()
        try:
            data = {
                "command": "config-get",
                "service": [f"dhcp{version}"],
            }
            async with session.post(self.url, json=data) as rsp:
                result: list[dict[str, Any]] = await rsp.json()
                return result

        except TimeoutError as exc:
            raise TimeoutError(
                "KEA Request timed out, are you running within a KEA Docker Container?"
            ) from exc

    async def _lease_command(
        self,
        operation: Literal["get", "del"],
        ip_address: str,
        version: IpVersion,
    ) -> list[dict[str, Any]]:
        """Run a lease command against the selected KEA service."""
        arguments: dict[str, Any] = {"ip-address": ip_address}
        if version == IpVersion.V6 and operation == "get":
            arguments["type"] = "IA_NA"
        data = {
            "command": f"lease{version}-{operation}",
            "service": [f"dhcp{version}"],
            "arguments": arguments,
        }
        session = await self._get_session()
        try:
            async with session.post(self.url, json=data) as rsp:
                rsp.raise_for_status()
                result: list[dict[str, Any]] = await rsp.json()
                return result
        except TimeoutError as exc:
            raise TimeoutError(
                "KEA Request timed out, are you running within a KEA Docker Container?"
            ) from exc

    async def get_lease(
        self,
        ip_address: str,
        version: IpVersion = IpVersion.V4,
    ) -> list[dict[str, Any]]:
        """Return one lease from the selected KEA service."""
        return await self._lease_command("get", ip_address, version)

    async def delete_lease(
        self,
        ip_address: str,
        version: IpVersion = IpVersion.V4,
    ) -> list[dict[str, Any]]:
        """Delete one lease from the selected KEA service."""
        return await self._lease_command("del", ip_address, version)

    async def get_lease_page(
        self,
        limit: int = 100,
        version: IpVersion = IpVersion.V4,
        from_address: str = "start",
    ) -> list[dict[str, Any]]:
        """Return a page of leases from the selected KEA service."""
        data = {
            "command": f"lease{version}-get-page",
            "service": [f"dhcp{version}"],
            "arguments": {"from": from_address, "limit": limit},
        }
        session = await self._get_session()
        try:
            async with session.post(self.url, json=data) as rsp:
                rsp.raise_for_status()
                result: list[dict[str, Any]] = await rsp.json()
                return result
        except TimeoutError as exc:
            raise TimeoutError(
                "KEA Request timed out, are you running within a KEA Docker Container?"
            ) from exc

    async def get_statistics(self, version: int = 4) -> list[dict[str, Any]]:
        """Return all statistics recorded by the KEA DHCP service."""
        data = {
            "command": "statistic-get-all",
            "service": [f"dhcp{version}"],
            "arguments": {},
        }
        session = await self._get_session()
        try:
            async with session.post(self.url, json=data) as rsp:
                rsp.raise_for_status()
                result: list[dict[str, Any]] = await rsp.json()
                return result
        except TimeoutError as exc:
            raise TimeoutError(
                "KEA Request timed out, are you running within a KEA Docker Container?"
            ) from exc
