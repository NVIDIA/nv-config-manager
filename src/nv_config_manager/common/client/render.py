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
"""Render Service Client."""

from __future__ import annotations

import ssl
from collections.abc import Callable
from configparser import ConfigParser
from typing import Any

from aiohttp import ClientTimeout, TCPConnector
from aiohttp_retry import ExponentialRetry
from pydantic import BaseModel

from nv_config_manager.common.client._mixins import _WhoamiViaRetryClientMixin
from nv_config_manager.common.log import LogCategory, get_logger

logger = get_logger(__name__, category=LogCategory.RENDER)


class FileCommit(BaseModel):
    """A rendered file and the config store commit it produced."""

    filename: str
    commit: str


class RenderClientException(Exception):
    """Exception raised for errors in the Render client."""


class RenderClient(_WhoamiViaRetryClientMixin):
    """Async client for interacting with the render service."""

    def __init__(
        self,
        base_url: str,
        client_certificate: tuple[str, str] | None = None,
        headers: dict[str, str] | Callable[[], dict[str, str]] | None = None,
    ) -> None:
        """Initialize the render client.

        Args:
            base_url: Base URL of the render service
            client_certificate: Tuple of (cert_file, key_file) for mTLS, or None for internal endpoints
            headers: Static dict or callable returning fresh headers per-request
        """
        self.base_url = base_url.rstrip("/")
        self._headers = headers

        if client_certificate:
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.load_cert_chain(client_certificate[0], client_certificate[1])
            ssl_ctx.minimum_version = ssl.TLSVersion.TLSv1_3
            self.connector = TCPConnector(ssl=ssl_ctx)
        else:
            self.connector = TCPConnector()

        self.timeout = ClientTimeout(total=30)
        self.retry_options = ExponentialRetry(
            attempts=5,
            start_timeout=1.0,
            max_timeout=10.0,
            factor=2.0,
            statuses={409, 500, 502, 503, 504},
        )

    @classmethod
    def from_config(
        cls,
        config: ConfigParser,
        section: str = "render",
    ) -> RenderClient:
        """Create RenderClient from INI configuration.

        Args:
            config: ConfigParser with render section
            section: Config section name

        Returns:
            Configured RenderClient instance
        """
        from nv_config_manager.common.config import get_internal_auth_headers, get_mtls_cert_paths

        render_config = config[section]
        use_internal = render_config.getboolean("use_internal_endpoint", fallback=False)

        if use_internal:
            return cls(
                base_url=render_config["api_service"],
                client_certificate=None,
                headers=get_internal_auth_headers,
            )
        else:
            return cls(
                base_url=render_config["api_url"],
                client_certificate=get_mtls_cert_paths(config),
            )

    async def execute_render(self, device_id: str, workflow_id: str) -> list[FileCommit]:
        """Execute a fresh render for a device.

        Args:
            device_id: The device ID to render
            workflow_id: The workflow ID triggering this render

        Returns:
            List of FileCommit objects for files that changed

        Raises:
            RenderClientException: If the render request fails
        """
        logger.info("Rendering device=%s, workflow=%s", device_id, workflow_id)
        url = f"{self.base_url}/v1/render/{device_id}/render"
        payload = {"commit_message": f"Render triggered by workflow {workflow_id}"}

        try:
            async with self._new_session() as session:
                async with session.post(url, json=payload) as response:
                    response.raise_for_status()
                    data: dict[str, Any] = await response.json()
                    raw_commits = data.get("updated_files", [])
                    return [FileCommit(**fc) for fc in raw_commits]
        except Exception as exc:
            logger.exception("Failed to render device %s: %s", device_id, str(exc))
            raise RenderClientException(f"Failed to render device: {exc}") from exc
