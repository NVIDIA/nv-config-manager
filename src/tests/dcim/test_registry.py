# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for NVCM's INI-to-DCIM-SDK service adapter."""

from __future__ import annotations

from configparser import ConfigParser

import pytest
from nv_config_manager_dcim import DCIMInvalidDataError, DCIMProviderConfigurationError
from nv_config_manager_dcim import registry as sdk_registry
from nv_config_manager_dcim_nautobot.provider import NautobotDCIMClient, NautobotProvider

from nv_config_manager.dcim import (
    create_dcim_client,
    create_dcim_workflow_client,
    create_nautobot_mcp_client,
    normalize_dcim_event,
    provider_settings,
)
from nv_config_manager.dcim import registry as service_registry


class FakeEntryPoint:
    """Minimal entry point used to isolate the service adapter."""

    name = "nautobot"

    def load(self):
        """Return the provider target."""
        return NautobotProvider


@pytest.fixture(autouse=True)
def nautobot_provider(monkeypatch):
    """Install only the reference provider for each test."""
    monkeypatch.setattr(sdk_registry, "_entry_points_for_group", lambda: (FakeEntryPoint(),))


def _config() -> ConfigParser:
    config = ConfigParser()
    config.read_dict(
        {
            "dcim": {"provider": "nautobot"},
            "dcim.nautobot": {
                "server": "https://dcim.example",
                "public_url": "https://public-dcim.example",
                "token": "token",
                "verify": "false",
            },
        }
    )
    return config


def test_service_adapter_creates_the_selected_sdk_provider() -> None:
    """Core translates its INI into plain settings before creating a client."""
    client = create_dcim_client(_config())

    assert isinstance(client, NautobotDCIMClient)
    assert client.nautobot_url == "https://dcim.example/"
    assert (
        client.get_device_ui_url("device-1") == "https://public-dcim.example/dcim/devices/device-1/"
    )


def test_provider_specific_settings_override_generic_dcim_values() -> None:
    """Provider-specific INI sections remain a service concern."""
    config = _config()
    config["dcim"]["server"] = "https://generic.example"

    assert provider_settings(config)["server"] == "https://dcim.example"


def test_provider_settings_include_portable_dcim_options() -> None:
    """Generic provider options reach the SDK and override legacy fallback values."""
    config = ConfigParser()
    config.read_dict(
        {
            "nautobot": {"server": "https://legacy.example", "token": "legacy-token"},
            "dcim": {"provider": "nautobot", "server": "https://generic.example"},
            "dcim.options": {"token": "portable-token", "verify": "false"},
        }
    )

    assert provider_settings(config) == {
        "server": "https://generic.example",
        "token": "portable-token",
        "verify": "false",
    }


@pytest.mark.asyncio
async def test_workflow_client_only_requires_sdk_close(monkeypatch) -> None:
    """Legacy workflows do not require third-party clients to implement ``async with``."""
    calls: list[str] = []

    class CloseOnlyClient:
        async def close(self) -> None:
            calls.append("close")

        async def get_device_serial(self, _device_id: str) -> str:
            return "serial"

    monkeypatch.setattr(service_registry, "create_dcim_client", lambda _config=None: CloseOnlyClient())

    client = create_dcim_workflow_client(_config())
    async with client:
        assert await client.get_device_serial("device-1") == "serial"

    assert calls == ["close"]


def test_nautobot_mcp_is_gated_by_provider_capability() -> None:
    """The deliberately Nautobot-specific MCP adapter remains optional."""
    client = create_nautobot_mcp_client(lambda: {"Authorization": "Bearer caller"}, _config())

    assert isinstance(client, NautobotDCIMClient)
    assert client._resolve_headers() == {"Authorization": "Bearer caller"}


def test_legacy_nautobot_events_are_normalized_at_the_provider_boundary() -> None:
    """Core receives only the SDK event envelope."""
    event = normalize_dcim_event(
        {
            "model": "dcim.device",
            "event": "update",
            "record": {"id": "device-1", "name": "leaf-1"},
            "@timestamp": "2026-07-20T00:00:00Z",
            "request": {"user": "automation"},
        },
        _config(),
    )

    assert event.provider == "nautobot"
    assert event.object_id == "device-1"


def test_provider_settings_require_connection_details() -> None:
    """Provider validation occurs after service configuration translation."""
    config = ConfigParser()
    config.read_dict({"dcim": {"provider": "nautobot"}})

    with pytest.raises(DCIMProviderConfigurationError, match="server, token"):
        create_dcim_client(config)


def test_event_provider_mismatch_is_rejected() -> None:
    """One service deployment cannot consume another provider's event stream."""
    with pytest.raises(DCIMInvalidDataError, match="does not match configured provider"):
        normalize_dcim_event(
            {
                "contract_version": "1.0",
                "provider": "another-provider",
                "operation": "update",
                "object_type": "dcim.device",
                "object_id": "device-1",
                "timestamp": "2026-07-20T00:00:00Z",
            },
            _config(),
        )
