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
"""Redis Client for DHCP service.

Extends the common async Redis client with DHCP-specific KEA config methods.
"""

from __future__ import annotations

import json
import time
from collections.abc import AsyncIterator
from typing import Any

from nv_config_manager.common.client import RedisClient as BaseRedisClient

# Version for the KEA config cache key.
# Bump this when the cached config format becomes incompatible with new releases
# (e.g., base image changes that affect library paths, config schema changes).
# History:
#   v1: Initial version (Alpine base image)
#   v2: Ubuntu base image migration (different hooks library paths)
#   v3: Migrate from pickle to JSON serialization (security hardening)
KEA_CONFIG_VERSION = 3
COLLECTION_INVALIDATION_CHANNEL = "nv-config-manager:dhcp:collection-snapshot-invalidate"


class RedisClient(BaseRedisClient):
    """Async Redis Client for DHCP service.

    Extends the common async RedisClient with methods for storing and
    retrieving KEA DHCP server configurations.
    """

    def config_key(self, ip_version: int) -> str:
        """Generate a key for the KEA DHCP Server Configuration.

        The key includes a version suffix to invalidate cached configs when
        breaking changes occur (e.g., base image migrations).
        Hash tags ensure config and timestamp keys land in the same Redis cluster slot.
        """
        return f"{{nv-config-manager:kea-dhcp{ip_version}.conf:v{KEA_CONFIG_VERSION}}}"

    def refresh_timestamp_key(self, ip_version: int) -> str:
        """Generate a key for the cache refresh timestamp."""
        return f"{{nv-config-manager:kea-dhcp{ip_version}.conf:v{KEA_CONFIG_VERSION}}}:refreshed_at"

    async def persist_kea_config(self, ip_version: int, config: dict[str, Any]) -> None:
        """Persist the KEA DHCP Server Configuration in Redis (no expiration).

        Atomically writes both the config and a refresh timestamp so that
        cache observability metrics can report when the last successful
        refresh occurred.
        """
        value = json.dumps(config).encode()
        pipe = self._redis.pipeline()
        pipe.set(self.config_key(ip_version), value)
        pipe.set(self.refresh_timestamp_key(ip_version), str(time.time()))
        pipe.publish(COLLECTION_INVALIDATION_CHANNEL, str(ip_version))
        await pipe.execute()

    async def load_kea_config(self, ip_version: int) -> dict[str, Any] | None:
        """Load the KEA DHCP Server Configuration from Redis."""
        return await self.get(self.config_key(ip_version))

    async def load_refresh_timestamp(self, ip_version: int) -> float | None:
        """Load the last cache refresh timestamp from Redis."""
        value = await self._redis.get(self.refresh_timestamp_key(ip_version))
        if value is None:
            return None
        return float(value)

    async def flush_kea_config(self, ip_version: int) -> bool:
        """Delete the cached KEA DHCP Server Configuration and its timestamp."""
        pipe = self._redis.pipeline()
        pipe.delete(
            self.config_key(ip_version),
            self.refresh_timestamp_key(ip_version),
        )
        pipe.publish(COLLECTION_INVALIDATION_CHANNEL, str(ip_version))
        deleted, _ = await pipe.execute()
        return bool(deleted)

    async def publish_collection_invalidation(self, ip_version: int) -> None:
        """Tell every DHCP API process to clear its local collection snapshots."""
        await self._redis.publish(COLLECTION_INVALIDATION_CHANNEL, str(ip_version))

    async def listen_collection_invalidations(self) -> AsyncIterator[int]:
        """Yield address families from the shared collection invalidation channel."""
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(COLLECTION_INVALIDATION_CHANNEL)
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                try:
                    yield int(message["data"])
                except (KeyError, TypeError, ValueError):
                    continue
        finally:
            await pubsub.unsubscribe(COLLECTION_INVALIDATION_CHANNEL)
            await pubsub.close()
