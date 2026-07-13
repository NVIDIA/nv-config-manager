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
"""Shared, process-wide clients for the ZTP API.

A single Nautobot client is reused across requests so its aiohttp session
(connection pool / keepalive), concurrency limiter, device-data cache, and
circuit breaker are shared. Creating a fresh client per request would give each
request its own connection pool, defeating the global connection cap and
backpressure, and would pay a TCP+TLS handshake on every call.
"""

from __future__ import annotations

from nv_config_manager.ztp.nautobot import NautobotClient

_nautobot_client: NautobotClient | None = None


def get_nautobot_client() -> NautobotClient:
    """Return the process-wide shared ZTP Nautobot client, creating it lazily."""
    global _nautobot_client
    if _nautobot_client is None:
        _nautobot_client = NautobotClient()
    return _nautobot_client


async def close_nautobot_client() -> None:
    """Close and drop the shared Nautobot client (called on app shutdown)."""
    global _nautobot_client
    if _nautobot_client is not None:
        await _nautobot_client.close()
        _nautobot_client = None


def reset_nautobot_client() -> None:
    """Drop the shared client without awaiting (test isolation helper)."""
    global _nautobot_client
    _nautobot_client = None
