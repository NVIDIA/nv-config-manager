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
"""NVDataflow client.

This module provides a lightweight replacement for the nvdataflow package,
implementing only the `post` functionality needed by the nv-config-manager temporal archive.

Endpoint URL templates are intentionally supplied by deployment configuration
instead of this OSS client module.
"""

from __future__ import annotations

import asyncio
import json
import types
from typing import Any, Self

import aiohttp
from aiohttp import ClientTimeout

from nv_config_manager.common.log import LogCategory, get_logger

logger = get_logger(__name__, category=LogCategory.TEMPORAL_ACTIVITY)

# Default configuration values (matching original nvdataflow)
PAYLOAD_MAX_MB = 10  # Maximum payload size in megabytes
RETRY_ATTEMPT_MAX = 3
RETRY_INTERVAL_SECONDS = 5
RETRY_INTERVAL_INCREASE_SECONDS = 5
REQUEST_TIMEOUT_SECONDS = 30


class NVDataflowException(Exception):
    """Exception raised for NVDataflow errors."""


class NVDataflowClient:
    """Async NVDataflow Client.

    A drop-in replacement for nvdataflow that uses aiohttp instead of the
    requests library with elasticsearch dependencies.

    Usage:
        async with NVDataflowClient(
            project="my-project",
            async_endpoint="https://nvdataflow.example.invalid/dataflow/{project}/posting",
        ) as client:
            await client.post(data={"key": "value"})
    """

    def __init__(
        self,
        project: str,
        sync: bool = False,
        payload_max: int = PAYLOAD_MAX_MB,
        retry_attempt_max: int = RETRY_ATTEMPT_MAX,
        retry_interval: int = RETRY_INTERVAL_SECONDS,
        retry_interval_increase: int = RETRY_INTERVAL_INCREASE_SECONDS,
        endpoint: str | None = None,
        async_endpoint: str | None = None,
        sync_endpoint: str | None = None,
        timeout: int = REQUEST_TIMEOUT_SECONDS,
    ) -> None:
        """Initialize the NVDataflow client.

        Args:
            project: The NVDataflow project name to post to.
            sync: If True, use synchronous posting endpoint. Defaults to False (async).
            payload_max: Maximum payload chunk size in megabytes. Defaults to 10.
            retry_attempt_max: Maximum number of retry attempts on 500 errors. Defaults to 3.
            retry_interval: Initial wait time between retries in seconds. Defaults to 5.
            retry_interval_increase: Additional wait time added per retry. Defaults to 5.
            endpoint: Endpoint URL template for the selected posting mode. Takes
                precedence over async_endpoint/sync_endpoint.
            async_endpoint: Endpoint URL template for asynchronous posting.
            sync_endpoint: Endpoint URL template for synchronous posting.
            timeout: Request timeout in seconds. Defaults to 30.
        """
        self.project = project
        self.sync = sync
        self.payload_max = payload_max
        self.retry_attempt_max = retry_attempt_max
        self.retry_interval = retry_interval
        self.retry_interval_increase = retry_interval_increase
        self.timeout = timeout
        self._session: aiohttp.ClientSession | None = None

        endpoint_template = endpoint or (sync_endpoint if sync else async_endpoint)
        if not endpoint_template:
            endpoint_key = "sync_endpoint" if sync else "async_endpoint"
            raise NVDataflowException(
                "NVDataflow endpoint URL must be configured. "
                f"Set {endpoint_key} in [temporal.nvdataflow]."
            )
        self.endpoint = endpoint_template.format(project=project)

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.close()

    async def _ensure_session(self) -> aiohttp.ClientSession:
        """Ensure session exists, creating it lazily if needed."""
        if not self._session:
            timeout = ClientTimeout(total=self.timeout, connect=10)
            self._session = aiohttp.ClientSession(
                headers={"Content-Type": "application/json"},
                timeout=timeout,
            )
        return self._session

    async def close(self) -> None:
        """Close the HTTP client session."""
        if self._session:
            await self._session.close()
            self._session = None

    async def post(
        self,
        data: dict[str, Any] | list[dict[str, Any]],
        shard: str | None = None,
    ) -> int:
        """Post data to NVDataflow.

        Args:
            data: A dictionary or list of dictionaries to post.
            shard: Optional shard value to add to each record.

        Returns:
            HTTP status code (201 for success, 400/500 for failure).
        """
        logger.info("Posting to NVDataflow endpoint: %s", self.endpoint)

        # Normalize data to list
        records = [data] if isinstance(data, dict) else list(data)

        # Add shard if specified
        if shard is not None:
            for record in records:
                record["_shard"] = shard

        # Split into payload chunks
        payload_max_bytes = self.payload_max * 1_000_000
        chunks = self._split_into_chunks(records, payload_max_bytes)

        # Post each chunk
        total_records = 0
        http_response_code = 400
        session = await self._ensure_session()

        for chunk in chunks:
            # Serialize chunk as JSON array
            payload = "[" + ",".join(json.dumps(record) for record in chunk) + "]"

            logger.info("Posting batch of %d records to NVDataflow", len(chunk))

            # Make request with retry logic
            http_response_code = await self._post_with_retry(session, payload)

            if http_response_code in (201, 202):
                total_records += len(chunk)
                logger.info("Successfully posted %d records", len(chunk))
            else:
                logger.error(
                    "Failed to post batch. HTTP status: %d",
                    http_response_code,
                )
                return http_response_code

        logger.info("Total records posted: %d", total_records)
        return http_response_code

    @staticmethod
    def _split_into_chunks(
        records: list[dict[str, Any]], max_bytes: int
    ) -> list[list[dict[str, Any]]]:
        """Split records into chunks that fit within max_bytes."""
        chunks: list[list[dict[str, Any]]] = []
        current_chunk: list[dict[str, Any]] = []
        current_size = 0

        for record in records:
            record_json = json.dumps(record)
            record_size = len(record_json.encode("utf-8"))

            # If adding this record would exceed the limit, start a new chunk
            if current_chunk and current_size + record_size > max_bytes:
                chunks.append(current_chunk)
                current_chunk = []
                current_size = 0

            current_chunk.append(record)
            current_size += record_size

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    async def _post_with_retry(
        self,
        session: aiohttp.ClientSession,
        payload: str,
    ) -> int:
        """Make POST request with retry logic for 500 errors."""
        current_interval = self.retry_interval

        for attempt in range(self.retry_attempt_max + 1):
            try:
                async with session.post(self.endpoint, data=payload) as response:
                    status_code = response.status

                    if status_code in (201, 202):
                        return status_code

                    if status_code == 500 and attempt < self.retry_attempt_max:
                        logger.warning(
                            "Server error (500). Retry attempt %d/%d in %d seconds...",
                            attempt + 1,
                            self.retry_attempt_max,
                            current_interval,
                        )
                        await asyncio.sleep(current_interval)
                        current_interval += self.retry_interval_increase
                        continue

                    # Non-retryable error or max retries exceeded
                    response_text = await response.text()
                    logger.error(
                        "Request failed with status %d: %s",
                        status_code,
                        response_text[:500] if response_text else "(no response body)",
                    )
                    return status_code

            except aiohttp.ClientError as e:
                logger.error("Request error: %s", e)
                if attempt < self.retry_attempt_max:
                    logger.warning(
                        "Retry attempt %d/%d in %d seconds...",
                        attempt + 1,
                        self.retry_attempt_max,
                        current_interval,
                    )
                    await asyncio.sleep(current_interval)
                    current_interval += self.retry_interval_increase
                    continue
                return 500

        return 500
