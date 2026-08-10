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
"""NVCM service adapter for the standalone DCIM SDK.

This module is intentionally the only INI-aware layer. The SDK and provider
packages receive an explicit provider name and a plain settings mapping.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable, Mapping
from configparser import ConfigParser
from contextlib import asynccontextmanager
from typing import Any, cast

from nv_config_manager_dcim import (
    DCIMChangeEvent,
    DCIMClient,
    DCIMEventProvider,
    DCIMInvalidDataError,
    DCIMProviderConfigurationError,
    DCIMProviderNotFoundError,
    NautobotMCPClient,
    NautobotMCPProvider,
)
from nv_config_manager_dcim import (
    create_dcim_client as create_sdk_dcim_client,
)
from nv_config_manager_dcim import (
    discover_dcim_providers as discover_sdk_dcim_providers,
)
from nv_config_manager_dcim import (
    get_dcim_provider as get_sdk_dcim_provider,
)

DCIM_PROVIDER_ENTRY_POINT_GROUP = "nv_config_manager.dcim"
DEFAULT_DCIM_PROVIDER = "nautobot-2x"


def discover_dcim_providers() -> dict[str, Any]:
    """Return installed providers from the standalone SDK discovery layer."""
    return discover_sdk_dcim_providers()


def configured_dcim_provider_name(config: ConfigParser | None = None) -> str:
    """Return the service-selected provider, defaulting to Nautobot 2.x."""
    if config is None:
        from nv_config_manager.common.config import load_config  # avoid circular import

        config = load_config()
    if not config.has_section("dcim"):
        return DEFAULT_DCIM_PROVIDER
    name = config.get("dcim", "provider", fallback=DEFAULT_DCIM_PROVIDER).strip()
    if not name:
        raise DCIMProviderConfigurationError("[dcim] provider must not be empty")
    return name


def provider_settings(config: ConfigParser, provider_name: str | None = None) -> dict[str, str]:
    """Translate NVCM INI sections into explicit provider settings.

    ``[dcim]`` and ``[dcim.options]`` are the portable service configuration
    surface. A provider-specific ``[dcim.<provider>]`` section takes
    precedence without leaking ``ConfigParser`` into the provider SDK.
    """
    provider_name = provider_name or configured_dcim_provider_name(config)
    settings: dict[str, str] = {}
    for section in (
        "dcim",
        "dcim.options",
        f"dcim.{provider_name}",
    ):
        if config.has_section(section):
            for key, value in config.items(section):
                if key != "provider":
                    settings[key] = value
    return settings


def get_dcim_provider(config: ConfigParser | None = None) -> Any:
    """Return the provider selected by this NVCM service configuration."""
    if config is None:
        from nv_config_manager.common.config import load_config  # avoid circular import

        config = load_config()
    return get_sdk_dcim_provider(configured_dcim_provider_name(config))


def create_dcim_client(config: ConfigParser | None = None) -> DCIMClient:
    """Create one broad client using the service's INI configuration."""
    if config is None:
        from nv_config_manager.common.config import load_config  # avoid circular import

        config = load_config()
    name = configured_dcim_provider_name(config)
    return create_sdk_dcim_client(name, provider_settings(config, name))


def create_dcim_workflow_client(config: ConfigParser | None = None) -> DCIMClient:
    """Return a service-managed client compatible with legacy workflow callers."""
    return cast(DCIMClient, _ManagedDCIMClient(create_dcim_client(config)))


def create_dcim_parameter_client(config: ConfigParser | None = None) -> DCIMClient:
    """Return a service-managed client compatible with legacy API callers."""
    return cast(DCIMClient, _ManagedDCIMClient(create_dcim_client(config)))


def create_nautobot_mcp_client(
    headers: Callable[[], dict[str, str]], config: ConfigParser | None = None
) -> NautobotMCPClient | None:
    """Create the optional Nautobot-specific MCP adapter when supported."""
    if config is None:
        from nv_config_manager.common.config import load_config  # avoid circular import

        config = load_config()
    name = configured_dcim_provider_name(config)
    provider = get_sdk_dcim_provider(name)
    if not isinstance(provider, NautobotMCPProvider):
        return None
    settings = provider_settings(config, name)
    provider.validate_settings(settings)
    return provider.create_nautobot_mcp_client(settings, headers)


def supports_nautobot_mcp(config: ConfigParser | None = None) -> bool:
    """Return whether the selected provider implements the Nautobot MCP capability.

    This is deliberately a capability check rather than a provider-name check.
    Nautobot 2.x and 3.x providers can expose the same MCP surface by implementing
    :class:`NautobotMCPProvider`; an unknown provider simply leaves those optional
    tools unavailable.
    """
    if config is None:
        from nv_config_manager.common.config import load_config  # avoid circular import

        config = load_config()
    try:
        provider = get_sdk_dcim_provider(configured_dcim_provider_name(config))
    except DCIMProviderNotFoundError:
        return False
    return isinstance(provider, NautobotMCPProvider)


def normalize_dcim_event(
    payload: Mapping[str, Any], config: ConfigParser | None = None
) -> DCIMChangeEvent:
    """Validate generic events or normalize the selected provider's legacy payload."""
    if config is None:
        from nv_config_manager.common.config import load_config  # avoid circular import

        config = load_config()
    provider = get_dcim_provider(config)
    try:
        event = DCIMChangeEvent.from_dict(payload)
    except DCIMInvalidDataError as error:
        if not isinstance(provider, DCIMEventProvider):
            raise error
        event = provider.normalize_event(payload)
    if event.provider != provider.metadata.name:
        raise DCIMInvalidDataError(
            f'DCIM event provider "{event.provider}" does not match configured provider '
            f'"{provider.metadata.name}"'
        )
    return event


@asynccontextmanager
async def dcim_client_session(config: ConfigParser | None = None) -> AsyncIterator[DCIMClient]:
    """Yield a configured client and always release provider resources."""
    client = create_dcim_client(config)
    try:
        yield client
    finally:
        await client.close()


class _ManagedDCIMClient:
    """Service-side lifecycle adapter for legacy ``async with client`` callers.

    Third-party providers only implement the SDK's explicit ``close()`` method.
    This adapter keeps legacy workflow code working without requiring providers
    to implement Python's asynchronous context-manager protocol.
    """

    def __init__(self, client: DCIMClient) -> None:
        self._client = client
        self._closed = False

    async def __aenter__(self) -> _ManagedDCIMClient:
        """Enter a legacy workflow client scope."""
        return self

    async def __aexit__(
        self,
        _exception_type: type[BaseException] | None,
        _exception: BaseException | None,
        _traceback: object,
    ) -> None:
        """Close the provider client at the service lifecycle boundary."""
        await self.close()

    async def close(self) -> None:
        """Release provider resources exactly once per workflow scope."""
        if self._closed:
            return
        self._closed = True
        await self._client.close()

    def __getattr__(self, name: str) -> Any:
        """Delegate SDK operations to the selected provider client."""
        return getattr(self._client, name)
