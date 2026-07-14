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
"""Tests for shared DHCP Redis state."""

from unittest.mock import AsyncMock, MagicMock, patch

from nv_config_manager.dhcp.redis import COLLECTION_INVALIDATION_CHANNEL, RedisClient


async def test_persist_kea_config_publishes_collection_invalidation() -> None:
    """Notify every API process after persisting refreshed KEA configuration."""
    client = RedisClient(host="redis.example.com")
    pipeline = MagicMock()
    pipeline.execute = AsyncMock(return_value=[True, True, 1])

    with patch.object(client.redis, "pipeline", return_value=pipeline):
        await client.persist_kea_config(4, {"Dhcp4": {}})

    pipeline.publish.assert_called_once_with(COLLECTION_INVALIDATION_CHANNEL, "4")


async def test_flush_kea_config_publishes_collection_invalidation() -> None:
    """Notify every API process after deleting cached KEA configuration."""
    client = RedisClient(host="redis.example.com")
    pipeline = MagicMock()
    pipeline.execute = AsyncMock(return_value=[2, 1])

    with patch.object(client.redis, "pipeline", return_value=pipeline):
        deleted = await client.flush_kea_config(6)

    assert deleted is True
    pipeline.publish.assert_called_once_with(COLLECTION_INVALIDATION_CHANNEL, "6")


async def test_collection_invalidation_pubsub_round_trip() -> None:
    """Publish and consume address-family invalidation messages."""
    client = RedisClient(host="redis.example.com")
    publish = AsyncMock()
    pubsub = MagicMock()
    pubsub.subscribe = AsyncMock()
    pubsub.unsubscribe = AsyncMock()
    pubsub.close = AsyncMock()

    async def messages():
        yield {"type": "subscribe", "data": 1}
        yield {"type": "message", "data": b"4"}

    pubsub.listen = messages
    with (
        patch.object(client.redis, "publish", publish),
        patch.object(client.redis, "pubsub", return_value=pubsub),
    ):
        await client.publish_collection_invalidation(4)
        invalidations = [version async for version in client.listen_collection_invalidations()]

    publish.assert_awaited_once_with(COLLECTION_INVALIDATION_CHANNEL, "4")
    assert invalidations == [4]
    pubsub.unsubscribe.assert_awaited_once_with(COLLECTION_INVALIDATION_CHANNEL)
    pubsub.close.assert_awaited_once()
