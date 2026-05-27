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
"""Tests for the event utility functions."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from nv_config_manager.render.events.exceptions import EventParseError
from nv_config_manager.render.events.util import (
    DeviceNotEnabledError,
    build_commit_message,
    clear_queued,
    extract_user,
    get_managed_device_uuids,
    is_queued,
    mark_queued,
    queue_render,
    should_run,
)


@pytest.fixture
def mock_nautobot_client():
    """Mock Nautobot client."""
    with patch("nv_config_manager.render.events.util.pynautobot_client") as mock:
        mock_instance = MagicMock()
        mock_instance.plugins.nv_config_manager.configmanagerdevicestatus.get.return_value = None
        mock_instance.graphql.query.return_value.json = {"data": {"devices": []}}

        # Set up the module bays chain
        mock_instance.configure_mock(
            dcim=MagicMock(module_bays=MagicMock(get=MagicMock(return_value=None)))
        )

        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_nats_connection():
    """Mock NATS connection."""
    with patch("nv_config_manager.render.events.util.nats_connection") as mock:
        mock_conn = AsyncMock()
        mock_js = MagicMock()  # Use MagicMock for jetstream object
        mock_js.publish = AsyncMock()  # Make publish an async method
        mock_conn.jetstream = MagicMock(return_value=mock_js)  # jetstream() should return sync
        mock_conn.is_closed = False
        mock.return_value = mock_conn
        yield mock_conn


@pytest.fixture
def mock_nats_connection_manager():
    """Mock NATS connection manager."""
    with patch("nv_config_manager.render.events.util.NATSConnectionManager") as mock:
        mock_manager = MagicMock()
        mock_manager.get_connection.return_value = None  # Force creation of new connection
        mock.return_value = mock_manager
        yield mock_manager


def test_should_run_enabled_device(mock_nautobot_client):
    """Test should_run with enabled device."""
    mock_device = MagicMock()
    mock_device.render_enabled = True
    mock_device.is_aggregate_managed = False
    mock_nautobot_client.plugins.nv_config_manager.configmanagerdevicestatus.get.return_value = (
        mock_device
    )

    with patch.dict("os.environ", {"IS_AGGREGATE_MANAGED": "false"}):
        result = should_run("test-device")
        assert result is True


def test_should_run_disabled_device(mock_nautobot_client):
    """Test should_run with disabled device."""
    mock_device = MagicMock()
    mock_device.render_enabled = False
    mock_device.is_aggregate_managed = False
    mock_nautobot_client.plugins.nv_config_manager.configmanagerdevicestatus.get.return_value = (
        mock_device
    )

    with patch.dict("os.environ", {"IS_AGGREGATE_MANAGED": "false"}):
        result = should_run("test-device")
        assert result is False


def test_should_run_nonexistent_device(mock_nautobot_client):
    """Test should_run with nonexistent device."""
    mock_nautobot_client.plugins.nv_config_manager.configmanagerdevicestatus.get.return_value = None

    result = should_run("test-device")
    assert result is False


def test_should_run_error(mock_nautobot_client):
    """Test should_run with Nautobot error."""
    mock_nautobot_client.plugins.nv_config_manager.configmanagerdevicestatus.get.side_effect = (
        Exception("Test error")
    )

    with pytest.raises(Exception, match="Failed to query test-device in nautobot: Test error"):
        should_run("test-device")


def test_should_run_aggregate_mismatch_env_true_device_false(mock_nautobot_client, custom_ini):
    """Test should_run with aggregate mismatch: env=true, device=false."""
    custom_ini("""
[aggregate]
is_aggregate_environment=true
""")
    mock_device = MagicMock()
    mock_device.render_enabled = True
    mock_device.is_aggregate_managed = False
    mock_nautobot_client.plugins.nv_config_manager.configmanagerdevicestatus.get.return_value = (
        mock_device
    )

    result = should_run("test-device")
    assert result is False


def test_should_run_aggregate_mismatch_env_false_device_true(mock_nautobot_client, custom_ini):
    """Test should_run with aggregate mismatch: env=false, device=true."""
    custom_ini("""
[aggregate]
is_aggregate_environment=false

[nats]
""")
    mock_device = MagicMock()
    mock_device.render_enabled = True
    mock_device.is_aggregate_managed = True
    mock_nautobot_client.plugins.nv_config_manager.configmanagerdevicestatus.get.return_value = (
        mock_device
    )

    result = should_run("test-device")
    assert result is False


def test_should_run_aggregate_match_both_true(mock_nautobot_client, custom_ini):
    """Test should_run with aggregate match: both env and device are true."""
    custom_ini("""
[aggregate]
is_aggregate_environment=true
""")
    mock_device = MagicMock()
    mock_device.render_enabled = True
    mock_device.is_aggregate_managed = True
    mock_nautobot_client.plugins.nv_config_manager.configmanagerdevicestatus.get.return_value = (
        mock_device
    )

    result = should_run("test-device")
    assert result is True


def test_should_run_aggregate_match_both_false(mock_nautobot_client, custom_ini):
    """Test should_run with aggregate match: both env and device are false."""
    custom_ini("""
[aggregate]
is_aggregate_environment=false

[nats]
""")
    mock_device = MagicMock()
    mock_device.render_enabled = True
    mock_device.is_aggregate_managed = False
    mock_nautobot_client.plugins.nv_config_manager.configmanagerdevicestatus.get.return_value = (
        mock_device
    )

    result = should_run("test-device")
    assert result is True


def test_extract_user_success():
    """Test successful user extraction."""
    data = {"request": {"user": "test_user"}}

    result = extract_user(data)
    assert result == "test_user"


def test_extract_user_missing_request():
    """Test user extraction with missing request data."""
    data = {}

    with pytest.raises(EventParseError, match="Failed to extract metadata from request."):
        extract_user(data)


def test_build_commit_message_with_name():
    """Test commit message building with device name."""
    data = {
        "request": {"user": "test_user"},
        "event": "create",
        "model": "device",
        "@timestamp": "2024-01-01T00:00:00Z",
        "record": {"name": "test-device"},
    }

    result = build_commit_message(data)
    assert (
        result
        == "Triggered from nb device create on test-device by test_user at 2024-01-01T00:00:00Z"
    )


def test_build_commit_message_without_name():
    """Test commit message building without device name."""
    data = {
        "request": {"user": "test_user"},
        "event": "create",
        "model": "device",
        "@timestamp": "2024-01-01T00:00:00Z",
        "record": {},
    }

    result = build_commit_message(data)
    assert result == "Triggered from nb device create by test_user at 2024-01-01T00:00:00Z"


def test_build_commit_message_missing_data():
    """Test commit message building with missing data."""
    data = {}

    with pytest.raises(EventParseError, match="Failed to extract metadata from request."):
        build_commit_message(data)


@pytest.mark.asyncio
async def test_queue_render_disabled_device(mock_nautobot_client, mock_nats_connection):
    """Test render queueing with disabled device."""
    mock_device = MagicMock()
    mock_device.render_enabled = False
    mock_nautobot_client.plugins.nv_config_manager.configmanagerdevicestatus.get.return_value = (
        mock_device
    )

    with patch("nv_config_manager.render.events.util._get_queue_redis_client") as mock_redis_getter:
        mock_redis_client = MagicMock()
        mock_redis_client.exists = AsyncMock(return_value=False)  # Not queued
        mock_redis_getter.return_value = mock_redis_client

        with pytest.raises(
            DeviceNotEnabledError,
            match="test-device is not enabled for configuration renders.",
        ):
            await queue_render("test-device", "test message", "test_user", "2024-01-16T21:46:05Z")

    mock_js = mock_nats_connection.jetstream.return_value
    mock_js.publish.assert_not_called()


@pytest.mark.asyncio
async def test_queue_render_enabled_device_success(
    mock_nautobot_client, mock_nats_connection, mock_nats_connection_manager, custom_ini
):
    """Test render queueing with enabled device."""
    custom_ini("""
[aggregate]
is_aggregate_environment=false

[nats]
""")
    mock_device = MagicMock()
    mock_device.render_enabled = True
    mock_device.is_aggregate_managed = False
    mock_nautobot_client.plugins.nv_config_manager.configmanagerdevicestatus.get.return_value = (
        mock_device
    )

    with patch("nv_config_manager.render.events.util._get_queue_redis_client") as mock_redis_getter:
        mock_redis_client = MagicMock()
        mock_redis_client.exists = AsyncMock(return_value=False)  # Not queued
        mock_redis_client.setex = AsyncMock()
        mock_redis_getter.return_value = mock_redis_client

        await queue_render("test-device", "test message", "test_user", "2024-01-16T21:46:05Z")

        # Verify Redis operations
        mock_redis_client.exists.assert_awaited_once_with("test-device_queued")
        mock_redis_client.setex.assert_awaited_once_with(
            "test-device_queued", 60, 1, serialize=False
        )

        # Verify NATS operations
        mock_js = mock_nats_connection.jetstream.return_value
        mock_js.publish.assert_called_once()


@pytest.mark.asyncio
async def test_queue_render_already_queued(
    mock_nautobot_client, mock_nats_connection, mock_nats_connection_manager, custom_ini
):
    """Test render queueing when device is already queued."""
    custom_ini("""
[aggregate]
is_aggregate_environment=false

[nats]
""")
    mock_device = MagicMock()
    mock_device.render_enabled = True
    mock_device.is_aggregate_managed = False
    mock_nautobot_client.plugins.nv_config_manager.configmanagerdevicestatus.get.return_value = (
        mock_device
    )

    with patch("nv_config_manager.render.events.util._get_queue_redis_client") as mock_redis_getter:
        mock_redis_client = MagicMock()
        mock_redis_client.exists = AsyncMock(return_value=True)  # Already queued
        mock_redis_client.setex = AsyncMock()
        mock_redis_getter.return_value = mock_redis_client

        await queue_render("test-device", "test message", "test_user", "2024-01-16T21:46:05Z")

        # Verify Redis check
        mock_redis_client.exists.assert_awaited_once_with("test-device_queued")
        # Should not call setex since already queued
        mock_redis_client.setex.assert_not_awaited()

        # Verify NATS operations not called
        mock_js = mock_nats_connection.jetstream.return_value
        mock_js.publish.assert_not_called()


@pytest.mark.asyncio
async def test_queue_render_publish_failure(
    mock_nautobot_client, mock_nats_connection, mock_nats_connection_manager, custom_ini
):
    """Test render queueing when NATS publish fails."""
    custom_ini("""
[aggregate]
is_aggregate_environment=false

[nats]
""")
    mock_device = MagicMock()
    mock_device.render_enabled = True
    mock_device.is_aggregate_managed = False
    mock_nautobot_client.plugins.nv_config_manager.configmanagerdevicestatus.get.return_value = (
        mock_device
    )

    with patch("nv_config_manager.render.events.util._get_queue_redis_client") as mock_redis_getter:
        mock_redis_client = MagicMock()
        mock_redis_client.exists = AsyncMock(return_value=False)  # Not queued
        mock_redis_client.setex = AsyncMock()
        mock_redis_client.delete = AsyncMock()
        mock_redis_getter.return_value = mock_redis_client

        # Mock jetstream.publish to raise an exception
        mock_js = mock_nats_connection.jetstream.return_value
        mock_js.publish.side_effect = Exception("NATS connection error")

        with pytest.raises(Exception, match="NATS connection error"):
            await queue_render("test-device", "test message", "test_user", "2024-01-16T21:46:05Z")

        # Verify Redis operations
        mock_redis_client.exists.assert_awaited_once_with("test-device_queued")
        mock_redis_client.setex.assert_awaited_once_with(
            "test-device_queued", 60, 1, serialize=False
        )
        # Verify the queued flag was cleared after failure
        mock_redis_client.delete.assert_awaited_once_with("test-device_queued")

        # Verify NATS publish was attempted
        mock_js.publish.assert_called_once()


@pytest.mark.asyncio
async def test_redis_deduplication_functions():
    """Test Redis deduplication functions."""
    device_uuid = "test-device-uuid"

    with patch("nv_config_manager.render.events.util._get_queue_redis_client") as mock_redis_getter:
        mock_redis_client = MagicMock()
        mock_redis_client.setex = AsyncMock()
        mock_redis_client.exists = AsyncMock()
        mock_redis_client.delete = AsyncMock()
        mock_redis_getter.return_value = mock_redis_client

        # Test mark_queued
        await mark_queued(device_uuid)
        mock_redis_client.setex.assert_awaited_once_with(
            f"{device_uuid}_queued", 60, 1, serialize=False
        )

        # Test is_queued - exists
        mock_redis_client.exists.return_value = True
        assert await is_queued(device_uuid) is True
        mock_redis_client.exists.assert_awaited_with(f"{device_uuid}_queued")

        # Test is_queued - not exists
        mock_redis_client.exists.return_value = False
        assert await is_queued(device_uuid) is False

        # Test clear_queued
        await clear_queued(device_uuid)
        mock_redis_client.delete.assert_awaited_once_with(f"{device_uuid}_queued")


@pytest.mark.asyncio
async def test_redis_deduplication_functions_local_env():
    """Test Redis deduplication functions in local environment."""
    device_uuid = "test-device-uuid"

    with patch("nv_config_manager.render.events.util._get_queue_redis_client") as mock_redis_getter:
        mock_redis_getter.return_value = None  # Local environment

        # All operations should be no-ops
        await mark_queued(device_uuid)
        assert await is_queued(device_uuid) is False
        await clear_queued(device_uuid)

        # Verify redis_getter was called but no Redis operations happened
        assert mock_redis_getter.call_count >= 3


def test_get_managed_device_uuids_success(mock_nautobot_client):
    """Test successful device UUID retrieval."""
    mock_nautobot_client.graphql.query.return_value.json = {
        "data": {
            "devices": [
                {"id": "device1", "configmanagerdevicestatus": {"render_enabled": True}},
                {"id": "device2", "configmanagerdevicestatus": {"render_enabled": True}},
            ]
        }
    }

    result = get_managed_device_uuids(names=["test"])
    assert result == ["device1", "device2"]


def test_get_managed_device_uuids_error(mock_nautobot_client):
    """Test device UUID retrieval with error."""
    mock_nautobot_client.graphql.query.side_effect = Exception("Test error")

    with pytest.raises(
        Exception,
        match=r"Failed to query devices with filter \{'names': \['test'\]\}: Test error",
    ):
        get_managed_device_uuids(names=["test"])
