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
"""Unit tests for DeviceCacheService nautobot URL handling.

Covers the public_url config option: when set, device metadata nautobot_url
uses the public URL (for user-facing links); when unset, it falls back to server.
"""

from configparser import ConfigParser
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nv_config_manager.config_store.client.nautobot import DeviceMetadata
from nv_config_manager.config_store.core.device_cache_redis import DeviceCacheService


@pytest.fixture
def mock_redis():
    """Redis client mock with async ping for from_config."""
    redis = MagicMock()
    redis.ping = AsyncMock(return_value=True)
    redis.get = AsyncMock(return_value=None)  # cache miss
    redis.set = AsyncMock(return_value=None)
    redis.setex = AsyncMock(return_value=None)
    redis.hset = AsyncMock(return_value=None)
    redis.hdel = AsyncMock(return_value=None)
    redis.keys = AsyncMock(return_value=[])
    redis.hgetall = AsyncMock(return_value={})
    return redis


@pytest.fixture
def mock_nautobot_client():
    """Nautobot client that returns a single device for get_device."""
    client = MagicMock()
    metadata = DeviceMetadata(
        device_id="abc-123-def",
        name="test-device",
        site="TestSite",
        platform="Cumulus Linux",
        role="Leaf",
        rack="R1",
    )
    client.get_device = AsyncMock(return_value=metadata)
    client.get_all_devices = AsyncMock(return_value=[])
    return client


@pytest.mark.asyncio
async def test_refresh_device_uses_nautobot_base_url_for_link(mock_redis, mock_nautobot_client):
    """refresh_device sets metadata.nautobot_url using nautobot_base_url (e.g. public URL)."""
    public_base = "https://nautobot.example.com"
    service = DeviceCacheService(
        redis_client=mock_redis,
        nautobot_client=mock_nautobot_client,
        nautobot_base_url=public_base,
    )
    device_uuid = uuid4()

    result = await service.refresh_device(device_uuid)

    assert result is not None
    assert result.nautobot_url == "https://nautobot.example.com/dcim/devices/abc-123-def/"


@pytest.mark.asyncio
async def test_refresh_device_strips_trailing_slash_from_base(mock_redis, mock_nautobot_client):
    """nautobot_base_url with trailing slash is normalized so the device URL has no double slash."""
    service = DeviceCacheService(
        redis_client=mock_redis,
        nautobot_client=mock_nautobot_client,
        nautobot_base_url="https://public.nautobot.local/",
    )
    device_uuid = uuid4()

    result = await service.refresh_device(device_uuid)

    assert result is not None
    assert result.nautobot_url == "https://public.nautobot.local/dcim/devices/abc-123-def/"


@pytest.mark.asyncio
async def test_from_config_uses_public_url_when_set(mock_redis):
    """from_config uses nautobot.public_url for device links when present."""
    config = ConfigParser()
    config.read_string(
        """
[redis]
host = localhost
port = 6379
db = 0
ssl = false
socket_timeout = 5
socket_connect_timeout = 5

[nautobot]
server = http://nautobot-internal:8000
public_url = https://nautobot.example.com
token = dummy
cache_ttl = 3600
"""
    )
    mock_nb_client = MagicMock()
    with (
        patch(
            "nv_config_manager.config_store.core.device_cache_redis.redis_client",
            return_value=mock_redis,
        ),
        patch(
            "nv_config_manager.config_store.core.device_cache_redis.NautobotClient",
        ) as mock_nb_class,
    ):
        mock_nb_class.from_config.return_value = mock_nb_client
        service = await DeviceCacheService.from_config(config=config)

    assert service.nautobot_base_url == "https://nautobot.example.com"


@pytest.mark.asyncio
async def test_refresh_all_devices_updates_active_set(mock_redis, mock_nautobot_client):
    """refresh_all_devices replaces the active device set in Redis."""
    uid1, uid2 = str(uuid4()), str(uuid4())
    device1 = DeviceMetadata(device_id=uid1, name="dev1", site="S1")
    device2 = DeviceMetadata(device_id=uid2, name="dev2", site="S2")
    mock_nautobot_client.get_all_devices = AsyncMock(return_value=[device1, device2])

    mock_pipeline = MagicMock()
    mock_pipeline.delete = MagicMock()
    mock_pipeline.sadd = MagicMock()
    mock_pipeline.execute = AsyncMock(return_value=[True, True])
    mock_redis.redis = MagicMock()
    mock_redis.redis.pipeline = MagicMock(return_value=mock_pipeline)

    service = DeviceCacheService(
        redis_client=mock_redis,
        nautobot_client=mock_nautobot_client,
        nautobot_base_url="https://nautobot.example.com",
    )

    count = await service.refresh_all_devices()
    assert count == 2
    mock_pipeline.delete.assert_called_once_with(DeviceCacheService.ACTIVE_SET_KEY)
    mock_pipeline.sadd.assert_called_once()
    mock_pipeline.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_is_device_active(mock_redis):
    """is_device_active checks Redis set membership."""
    mock_redis.redis = MagicMock()
    mock_redis.redis.sismember = AsyncMock(return_value=True)

    service = DeviceCacheService(
        redis_client=mock_redis,
        nautobot_client=MagicMock(),
        nautobot_base_url="https://nautobot.example.com",
    )
    device_uuid = uuid4()

    result = await service.is_device_active(device_uuid)

    assert result is True
    mock_redis.redis.sismember.assert_awaited_once_with(
        DeviceCacheService.ACTIVE_SET_KEY, str(device_uuid)
    )


@pytest.mark.asyncio
async def test_is_device_active_returns_true_on_error(mock_redis):
    """is_device_active defaults to True when Redis fails (avoid hiding devices on error)."""
    mock_redis.redis = MagicMock()
    mock_redis.redis.sismember = AsyncMock(side_effect=Exception("Redis down"))

    service = DeviceCacheService(
        redis_client=mock_redis,
        nautobot_client=MagicMock(),
        nautobot_base_url="https://nautobot.example.com",
    )

    result = await service.is_device_active(uuid4())
    assert result is True


@pytest.mark.asyncio
async def test_get_active_device_uuids(mock_redis):
    """get_active_device_uuids returns the set from Redis."""
    uid1 = uuid4()
    uid2 = uuid4()
    mock_redis.redis = MagicMock()
    mock_redis.redis.smembers = AsyncMock(return_value={str(uid1).encode(), str(uid2).encode()})

    service = DeviceCacheService(
        redis_client=mock_redis,
        nautobot_client=MagicMock(),
        nautobot_base_url="https://nautobot.example.com",
    )

    result = await service.get_active_device_uuids()
    assert result == {uid1, uid2}


@pytest.mark.asyncio
async def test_delete_device_removes_from_active_set(mock_redis, mock_nautobot_client):
    """delete_device removes the device from the active set."""
    mock_redis.delete = AsyncMock(return_value=None)
    mock_redis.redis = MagicMock()
    mock_redis.redis.srem = AsyncMock(return_value=1)

    service = DeviceCacheService(
        redis_client=mock_redis,
        nautobot_client=mock_nautobot_client,
        nautobot_base_url="https://nautobot.example.com",
    )
    device_uuid = uuid4()

    await service.delete_device(device_uuid)

    mock_redis.redis.srem.assert_awaited_once_with(
        DeviceCacheService.ACTIVE_SET_KEY, str(device_uuid)
    )


@pytest.mark.asyncio
async def test_from_config_falls_back_to_server_when_public_url_absent(mock_redis):
    """from_config falls back to nautobot.server when public_url is not set."""
    config = ConfigParser()
    config.read_string(
        """
[redis]
host = localhost
port = 6379
db = 0
ssl = false
socket_timeout = 5
socket_connect_timeout = 5

[nautobot]
server = http://nautobot-internal:8000
token = dummy
cache_ttl = 3600
"""
    )
    mock_nb_client = MagicMock()
    with (
        patch(
            "nv_config_manager.config_store.core.device_cache_redis.redis_client",
            return_value=mock_redis,
        ),
        patch(
            "nv_config_manager.config_store.core.device_cache_redis.NautobotClient",
        ) as mock_nb_class,
    ):
        mock_nb_class.from_config.return_value = mock_nb_client
        service = await DeviceCacheService.from_config(config=config)

    assert service.nautobot_base_url == "http://nautobot-internal:8000"
