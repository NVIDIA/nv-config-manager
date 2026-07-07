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
"""Tests for the shared Redis-backed distributed lock."""

import pytest
from redis.asyncio.lock import Lock as AsyncRedisLock

from nv_config_manager.common import lock as lock_module
from nv_config_manager.common.lock import (
    _FakeLock,
    acquire_lock,
    create_lock,
    release_lock,
    renew_lock,
)


@pytest.fixture(autouse=True)
def _reset_lock_client(monkeypatch):
    """Clear the module-level Redis client cached between calls."""
    monkeypatch.setattr(lock_module, "_lock_redis_client", None)


class TestFakeLock:
    @pytest.mark.asyncio
    async def test_acquire_and_release_are_noops(self):
        fake = _FakeLock()
        assert await fake.acquire() is True
        assert await fake.release() is True

    @pytest.mark.asyncio
    async def test_usable_as_async_context_manager(self):
        entered = False
        async with _FakeLock():
            entered = True
        assert entered is True


class TestCreateLock:
    @pytest.mark.asyncio
    async def test_returns_fake_lock_in_local_environment(self, monkeypatch):
        monkeypatch.setattr(lock_module, "is_local_environment", lambda: True)

        lock = await create_lock("resource-a")

        assert isinstance(lock, _FakeLock)

    @pytest.mark.asyncio
    async def test_returns_redis_lock_outside_local_environment(self, monkeypatch):
        monkeypatch.setattr(lock_module, "is_local_environment", lambda: False)

        lock = await create_lock("resource-b", timeout=42, blocking_timeout=7)

        assert isinstance(lock, AsyncRedisLock)
        assert lock.name == "resource-b"
        assert lock.timeout == 42
        assert lock.blocking_timeout == 7

    @pytest.mark.asyncio
    async def test_redis_client_is_reused_across_calls(self, monkeypatch):
        monkeypatch.setattr(lock_module, "is_local_environment", lambda: False)

        first = await create_lock("resource-c")
        second = await create_lock("resource-d")

        assert first.redis is second.redis


class TestTokenHelpersLocalNoop:
    """Without a shared Redis, the token helpers are no-ops that report success."""

    @pytest.fixture(autouse=True)
    def _force_local(self, monkeypatch):
        monkeypatch.setattr(lock_module, "is_local_environment", lambda: True)

    @pytest.mark.asyncio
    async def test_acquire_returns_true(self):
        assert await acquire_lock("k", "token", timeout=30) is True

    @pytest.mark.asyncio
    async def test_renew_returns_true(self):
        assert await renew_lock("k", "token", timeout=30) is True

    @pytest.mark.asyncio
    async def test_release_returns_true(self):
        assert await release_lock("k", "token") is True
