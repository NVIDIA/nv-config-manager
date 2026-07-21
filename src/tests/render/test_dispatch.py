# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for provider-registered render event dispatching."""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nv_config_manager.dcim import DCIMChangeEvent, RenderEventRequest
from nv_config_manager.render.dispatch import EventDispatcher


class SyntheticRenderEventProvider:
    """Small provider that proves the dispatcher owns no object-type logic."""

    def register_render_event_handlers(self, registry) -> None:
        """Register the one synthetic event type."""
        registry.register_render_event_handler("synthetic.device", self.device)

    async def device(self, event, client) -> tuple[RenderEventRequest, ...]:
        """Identify the device entirely in provider code."""
        assert client is not None
        return (RenderEventRequest(device_id=event.object_id, commit_message="synthetic change"),)


@pytest.mark.asyncio
async def test_dispatch_uses_provider_registered_handler():
    """A selected provider defines event types and affected devices."""
    dispatcher = EventDispatcher(SyntheticRenderEventProvider())
    dcim_client = AsyncMock()

    @asynccontextmanager
    async def session():
        yield dcim_client

    event = DCIMChangeEvent(
        provider="synthetic",
        operation="update",
        object_type="synthetic.device",
        object_id="device-1",
        timestamp="2026-07-20T00:00:00Z",
        actor="user",
        record={"id": "device-1"},
    )

    with (
        patch("nv_config_manager.render.dispatch.dcim_client_session", session),
        patch(
            "nv_config_manager.render.dispatch.queue_render_batch",
            new_callable=AsyncMock,
            return_value=(1, []),
        ) as queue_render_batch,
    ):
        await dispatcher.dcim_event_dispatch(event)

    queue_render_batch.assert_awaited_once_with(
        ["device-1"],
        "synthetic change",
        "user",
        "2026-07-20T00:00:00Z",
        dcim_client=dcim_client,
    )


@pytest.mark.asyncio
async def test_dispatch_ignores_unregistered_provider_event():
    """Unknown event types are safely ignored without opening a provider client."""
    dispatcher = EventDispatcher(SyntheticRenderEventProvider())
    dispatcher.logger.info = MagicMock()
    event = DCIMChangeEvent(
        provider="synthetic",
        operation="update",
        object_type="synthetic.other",
        object_id="other-1",
        timestamp="2026-07-20T00:00:00Z",
        record={"id": "other-1"},
    )

    await dispatcher.dcim_event_dispatch(event)

    dispatcher.logger.info.assert_called_once_with(
        "No event handler implemented for %s, ignoring message.", "synthetic.other"
    )


@patch("nv_config_manager.render.dispatch.execute_render")
@pytest.mark.asyncio
async def test_nautobot_change_dispatch(mock_render):
    """The existing render-work queue continues to execute a device render."""
    dispatcher = EventDispatcher(SyntheticRenderEventProvider())
    message = {
        "device_id": "device-1",
        "commit_message": "test commit message",
        "user": "test",
        "@timestamp": "2025-08-13T20:00:30Z",
    }

    await dispatcher.nautobot_change_dispatch(message)

    mock_render.assert_called_once_with("device-1", "test commit message", "test")
