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
"""Abstract ticketing provider interface and provider registry.

All ticketing integrations must implement TicketingProvider.  The registry
(TICKETING_PROVIDERS) is populated by each provider module at import time, so
adding a new backend only requires:

  1. Implementing TicketingProvider in a new module.
  2. Registering it:  TICKETING_PROVIDERS["myplatform"] = MyProvider

The factory get_ticketing_provider(platform) is the single entry-point used by
Temporal activities — it resolves the provider class from the registry, then
calls from_config() to build a fully-configured instance.

No Temporal imports — this file is intentionally framework-agnostic.
"""

from __future__ import annotations

import types
from abc import ABC, abstractmethod
from typing import Any, Self


class TicketingProvider(ABC):
    """Common interface that every ticketing backend must satisfy.

    Providers are async context managers — use them as:
        async with get_ticketing_provider(platform) as provider:
            await provider.validate_issue(...)
    """

    max_attachment_size: int | None = None  # bytes; None = no size limit enforced

    @classmethod
    @abstractmethod
    def from_config(cls) -> Self:
        """Instantiate the provider from nv_config_manager.ini (using the platform's config section)."""
        raise NotImplementedError()

    @abstractmethod
    async def __aenter__(self) -> Self:
        raise NotImplementedError()

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: types.TracebackType | None,
    ) -> None:
        raise NotImplementedError()

    @abstractmethod
    async def validate_issue(self, issue_key: str) -> dict[str, Any]:
        """Confirm the issue exists and return its metadata.

        Args:
            issue_key: Platform-native ticket identifier, e.g. "GNI-1234".

        Returns:
            A dict of issue metadata (fields vary by platform).

        Raises:
            An appropriate exception if the issue is not found or unreachable.
        """
        raise NotImplementedError()

    @abstractmethod
    async def upload_attachment(
        self,
        issue_key: str,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> str:
        """Upload a file as a direct attachment on the issue.

        Args:
            issue_key:    Platform-native ticket identifier.
            filename:     Name to give the attachment (e.g. "diagnostics.txt").
            content:      Raw file bytes.
            content_type: MIME type, e.g. "text/plain" or "application/gzip".

        Returns:
            The attachment URL or ID returned by the ticketing system.
        """
        raise NotImplementedError()

    @abstractmethod
    async def add_comment(self, issue_key: str, body: str) -> str:
        """Post a plain-text comment on the issue.

        Args:
            issue_key: Platform-native ticket identifier.
            body:      Plain-text comment body.  Implementations are responsible
                       for any platform-specific formatting (e.g. ADF for Jira).

        Returns:
            The ID of the created comment as a string.
        """
        raise NotImplementedError()


# Registry — each provider module populates this at import time, e.g.:
#   TICKETING_PROVIDERS["jira"] = JiraTicketingProvider
TICKETING_PROVIDERS: dict[str, type[TicketingProvider]] = {}


def get_ticketing_provider(platform: str) -> TicketingProvider:
    """Return a configured TicketingProvider for the given platform name.

    Looks up the provider class in TICKETING_PROVIDERS and calls from_config()
    to build an instance. Use as an async context manager:

        async with get_ticketing_provider("jira") as provider:
            await provider.validate_issue("GNI-1234")

    Raises:
        ValueError: If no provider is registered for the given platform name.
    """
    cls = TICKETING_PROVIDERS.get(platform)
    if cls is None:
        raise ValueError(
            f"Unknown ticketing platform: {platform!r}. Registered: {list(TICKETING_PROVIDERS)}"
        )
    return cls.from_config()
