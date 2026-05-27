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
"""NVIDIA Config Manager Config Store Service API Client (Async)."""

from __future__ import annotations

import re
import ssl
import types
from collections.abc import Callable
from configparser import ConfigParser
from typing import TYPE_CHECKING
from urllib.parse import quote

import aiohttp
from aiohttp_retry import ExponentialRetry, RetryClient
from pydantic import BaseModel

from nv_config_manager.common.client._mixins import _WhoamiViaRetryClientMixin
from nv_config_manager.common.log import LogCategory, get_logger

if TYPE_CHECKING:
    from nv_config_manager.common.config import ConfigStoreType


class ConfigStoreException(Exception):
    """Exception interacting with Config Store."""


class ConfigStoreFileNotFound(ConfigStoreException):
    """Desired file not found in Config Store."""


class ConfigFileMetadata(BaseModel):
    filename: str
    commit: str


class ConfigFile(ConfigFileMetadata):
    content: str
    sha: str | None = None
    created_at: str | None = None


class ConfigStoreClient(_WhoamiViaRetryClientMixin):
    """Async NVIDIA Config Manager Config Store Service Client.

    This client interfaces with the nv-config-manager-config-store-service API using async/await.
    """

    logger = get_logger(__name__, category=LogCategory.CONFIG_STORE)

    def __init__(
        self,
        target: str,
        file_type: str,
        ui_url: str,
        verify: bool | str = True,
        client_certificate: tuple[str, str] | None = None,
        headers: dict[str, str] | Callable[[], dict[str, str]] | None = None,
    ) -> None:
        """Initialize an Async Config Store Client.

        Args:
            target: Base URL of the nv-config-manager-config-store-service
            file_type: File type - "intended" or "backup"
            ui_url: UI base URL for generating user-facing links
            verify: SSL verification - True (default), False (disable), or str (path to CA cert)
            client_certificate: Tuple of (cert_file, key_file) for mTLS
            headers: Static dict or callable returning fresh headers per-request
        """
        if file_type not in ["intended", "backup"]:
            raise ValueError(f"Invalid file_type: {file_type}, must be 'intended' or 'backup'")

        self.base_url = target.rstrip("/")
        self.target = self.base_url
        self.file_type = file_type
        self.config_url = f"{self.base_url}/v1/config"
        self._ui_url = ui_url.rstrip("/")
        self._headers = headers
        self._verify = verify
        self._client_certificate = client_certificate
        self.connector = self._create_connector(verify, client_certificate)
        self.timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.retry_options = ExponentialRetry(
            attempts=5,
            start_timeout=1.0,
            statuses={429, 500, 502, 503, 504},
        )

    @classmethod
    def from_config(
        cls,
        config: ConfigParser,
        file_type: ConfigStoreType | str = "intended",
        section: str = "config_store.client",
    ) -> ConfigStoreClient:
        """Create ConfigStoreClient from INI configuration.

        Args:
            config: ConfigParser with config_store.client section
            file_type: File type - ConfigStoreType enum or "intended"/"backup" string
            section: Config section name

        Returns:
            Configured ConfigStoreClient instance
        """
        from nv_config_manager.common.config import (
            get_internal_auth_headers,
            get_mtls_cert_paths,
            parse_verify_param,
        )

        if hasattr(file_type, "value"):
            file_type_str = str(file_type.value)
        else:
            file_type_str = str(file_type)

        config_section = config[section]
        use_internal = config_section.getboolean("use_internal_endpoint", fallback=False)
        ui_url = config_section["ui_url"]

        if use_internal:
            return cls(
                target=config_section["api_service"],
                file_type=file_type_str,
                ui_url=ui_url,
                verify=False,
                client_certificate=None,
                headers=get_internal_auth_headers,
            )
        else:
            return cls(
                target=config_section["api_url"],
                file_type=file_type_str,
                ui_url=ui_url,
                verify=parse_verify_param(config_section),
                client_certificate=get_mtls_cert_paths(config),
            )

    @staticmethod
    def _sanitize_url(url: str) -> str:
        """Remove duplicate slashes from URL."""
        return re.sub(r"([^:]/)(/)+", r"\1", url)

    @staticmethod
    def _create_connector(
        verify: bool | str = True,
        client_certificate: tuple[str, str] | None = None,
    ) -> aiohttp.TCPConnector:
        ssl_context = ssl.create_default_context()
        if isinstance(verify, str):
            ssl_context.load_verify_locations(verify)
        elif verify is False:
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        if client_certificate:
            ssl_context.load_cert_chain(client_certificate[0], client_certificate[1])

        return aiohttp.TCPConnector(ssl=ssl_context)

    @property
    def ui_target(self) -> str:
        """Return the UI target URL."""
        return self._ui_url

    def file_url(self, device_uuid: str, filename: str, version: str | None = None) -> str:
        """Generate URL to view full file content in the UI."""
        url = f"{self.ui_target}/device/{device_uuid}/{filename}?file_type={self.file_type}"
        if version:
            url += f"&version={version}"
        return self._sanitize_url(url)

    def history_url(self, device_uuid: str, filename: str) -> str:
        """Generate URL to view version history."""
        return self._sanitize_url(
            f"{self.ui_target}/device/{device_uuid}/{filename}/history?file_type={self.file_type}"
        )

    def _resolve_headers(self) -> dict[str, str] | None:
        """Return headers for the current request."""
        if callable(self._headers):
            return self._headers()  # type: ignore[ty:call-top-callable]  # ty can't narrow dict|Callable union
        return self._headers

    def _new_session(self) -> RetryClient:
        """Create a RetryClient that does not close the shared connector."""
        return RetryClient(
            connector=self.connector,
            connector_owner=False,
            timeout=self.timeout,
            retry_options=self.retry_options,
            headers=self._resolve_headers(),
        )

    async def load_file(self, device_uuid: str, filename: str) -> ConfigFile:
        """Load a file from the Config Store."""
        try:
            async with self._new_session() as session:
                async with session.get(
                    f"{self.config_url}/{device_uuid}/{quote(filename, safe='')}",
                    params={"file_type": self.file_type},
                ) as rsp:
                    rsp.raise_for_status()
                    data = await rsp.json()

                    return ConfigFile(
                        content=data["content"],
                        commit=str(data["version"]),
                        filename=filename,
                        sha=data["content_hash"],
                        created_at=data.get("created_at"),
                    )
        except aiohttp.ClientResponseError as e:
            if e.status == 404:
                raise ConfigStoreFileNotFound(
                    f"Did not locate {filename} for device {device_uuid}"
                ) from e
            raise ConfigStoreException(f"Failed to load {filename}: {e.status} {e.message}") from e
        except Exception as e:
            raise ConfigStoreException(f"Failed to load {filename}: {e}") from e

    async def persist_files(
        self,
        device_uuid: str,
        files: dict[str, str],
        commit_message: str,
        user: str,
        user_domain: str,
    ) -> list[ConfigFileMetadata] | None:
        """Persist files to the Config Store using batch API.

        Args:
            device_uuid: Device UUID
            files: Dictionary mapping filenames to content
            commit_message: Commit message for the changes
            user: Username
            user_domain: User's domain (for email construction)

        Returns:
            List of ConfigFileMetadata for created/updated files, or None if nothing changed
        """
        author_email = f"{user}@{user_domain}"

        filtered_items = []
        for filename, content in files.items():
            clean_filename = filename.replace(".j2", "")
            try:
                existing_file = await self.load_file(device_uuid, clean_filename)
                if content == existing_file.content:
                    self.logger.info("No diff for %s/%s", device_uuid, clean_filename)
                    continue
            except ConfigStoreFileNotFound:
                pass

            filtered_items.append(
                {
                    "filename": clean_filename,
                    "content": content,
                    "author": author_email,
                    "commit_message": commit_message,
                    "file_type": self.file_type,
                }
            )

        if not filtered_items:
            return None

        try:
            async with self._new_session() as session:
                async with session.post(
                    f"{self.config_url}/{device_uuid}/batch",
                    json={"files": filtered_items},
                ) as rsp:
                    rsp.raise_for_status()
                    result = await rsp.json()
                    created = result.get("created", [])

                    if not created:
                        return None

                    return [
                        ConfigFileMetadata(
                            commit=str(item["version"]),
                            filename=filtered_items[i]["filename"],
                        )
                        for i, item in enumerate(created)
                    ]
        except aiohttp.ClientResponseError as exc:
            raise ConfigStoreException(
                f"Failed to persist files: {exc.status} {exc.message}"
            ) from exc
        except Exception as exc:
            raise ConfigStoreException(f"Failed to persist files: {exc}") from exc

    async def close(self) -> None:
        """Close the connector."""
        if self.connector and not self.connector.closed:
            await self.connector.close()

    async def __aenter__(self) -> ConfigStoreClient:
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.close()
