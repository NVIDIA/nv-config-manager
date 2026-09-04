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
"""Process-local runtime configuration for reusable workflow activities."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

from temporalio.exceptions import ApplicationError

from nv_config_manager_workflows.lock import configure_lock_backend

if TYPE_CHECKING:
    from redis.asyncio import Redis


class RuntimeConfigurationError(ApplicationError):
    """Non-retryable failure caused by missing process startup configuration."""

    def __init__(self, message: str) -> None:
        """Initialize a permanent activity configuration failure."""
        super().__init__(message, non_retryable=True)


class NatsNotConfiguredError(RuntimeConfigurationError):
    """Raised when NATS configuration is read before startup configured it."""


class SlackNotConfiguredError(RuntimeConfigurationError):
    """Raised when Slack configuration is read before startup configured it."""


class UIBaseURLNotConfiguredError(RuntimeConfigurationError):
    """Raised when the UI base URL is unavailable to a workflow activity."""


class _Unset:
    """Distinguish an omitted startup call from an intentionally disabled resource."""


_UNSET: Final = _Unset()

_nats: tuple[str | None, str | None] | _Unset = _UNSET
_slack: tuple[str | None, str | None] | _Unset = _UNSET
_ui_base_url: str | None | _Unset = _UNSET


def configure_nats(stream: str | None, subject: str | None) -> None:
    """Configure the archive stream and default subject used by NATS activities."""
    global _nats  # noqa: PLW0603
    _nats = (stream, subject)


def configure_slack(token: str | None, channel: str | None) -> None:
    """Configure Slack credentials, or disable Slack when either value is absent."""
    global _slack  # noqa: PLW0603
    _slack = (token, channel)


def configure_ui_base_url(url: str | None) -> None:
    """Configure the user-facing NVCM workflow UI base URL."""
    global _ui_base_url  # noqa: PLW0603
    _ui_base_url = url


def get_nats_configuration() -> tuple[str, str]:
    """Return configured NATS archive settings or fail with a startup hint."""
    if isinstance(_nats, _Unset):
        raise NatsNotConfiguredError(
            "NATS runtime is not configured. Call configure_nats(stream, subject) "
            "or configure_runtime() at application startup."
        )
    stream, subject = _nats
    if stream is None or subject is None:
        raise NatsNotConfiguredError("NATS runtime is disabled or incomplete")
    return stream, subject


def get_slack_configuration() -> tuple[str | None, str | None]:
    """Return configured Slack settings, including an intentional disabled state."""
    if isinstance(_slack, _Unset):
        raise SlackNotConfiguredError(
            "Slack runtime is not configured. Call configure_slack(token, channel) "
            "or configure_runtime() at application startup."
        )
    return _slack


def get_ui_base_url() -> str:
    """Return the configured NVCM UI base URL or a clear configuration error."""
    if isinstance(_ui_base_url, _Unset):
        raise UIBaseURLNotConfiguredError(
            "UI base URL is not configured. Call configure_ui_base_url(url) "
            "or configure_runtime() at application startup."
        )
    if _ui_base_url is None:
        raise UIBaseURLNotConfiguredError("UI base URL is disabled")
    return _ui_base_url


def configure_runtime(
    *,
    lock_redis: Redis | None = None,
    nats_stream: str | None = None,
    nats_subject: str | None = None,
    slack_token: str | None = None,
    slack_channel: str | None = None,
    ui_base_url: str | None = None,
) -> None:
    """Apply every process-local workflow resource configuration in one call."""
    configure_lock_backend(lock_redis)
    configure_nats(nats_stream, nats_subject)
    configure_slack(slack_token, slack_channel)
    configure_ui_base_url(ui_base_url)


__all__ = [
    "NatsNotConfiguredError",
    "RuntimeConfigurationError",
    "SlackNotConfiguredError",
    "UIBaseURLNotConfiguredError",
    "configure_nats",
    "configure_runtime",
    "configure_slack",
    "configure_ui_base_url",
    "get_nats_configuration",
    "get_slack_configuration",
    "get_ui_base_url",
]
