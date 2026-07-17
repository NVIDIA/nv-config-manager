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
"""Tests for DHCP Redis state."""

from unittest.mock import AsyncMock, MagicMock, call, patch

from nv_config_manager.dhcp.redis import RedisClient


async def test_persist_kea_config_writes_config_and_timestamp_atomically() -> None:
    """Persist refreshed configuration and its timestamp in one pipeline."""
    client = RedisClient(host="redis.example.com")
    pipeline = MagicMock()
    pipeline.execute = AsyncMock(return_value=[True, True])

    with (
        patch.object(client.redis, "pipeline", return_value=pipeline),
        patch("nv_config_manager.dhcp.redis.time.time", return_value=123.0),
    ):
        await client.persist_kea_config(4, {"Dhcp4": {}})

    pipeline.set.assert_has_calls(
        [
            call(client.config_key(4), b'{"Dhcp4": {}}'),
            call(client.refresh_timestamp_key(4), "123.0"),
        ]
    )
    pipeline.execute.assert_awaited_once()


async def test_flush_kea_config_deletes_config_and_timestamp() -> None:
    """Delete cached configuration and its timestamp in one command."""
    client = RedisClient(host="redis.example.com")
    delete = AsyncMock(return_value=2)

    with patch.object(client.redis, "delete", delete):
        deleted = await client.flush_kea_config(6)

    assert deleted is True
    delete.assert_awaited_once_with(
        client.config_key(6),
        client.refresh_timestamp_key(6),
    )
