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
"""Tests for the DHCP CLI sync loop, especially KEA-side divergence recovery.

Background: a transient postgres outage can cause the ``kea`` container's
livenessProbe to recycle it, which reloads the baked-in bootstrap
``/etc/kea/kea-dhcp4.conf`` from the image (no shared volume for ``/etc/kea/``).
That bootstrap lacks the ``lease-database`` section that ``inject_lease_db_config``
adds at sync time. The pre-fix sync loop only re-applied on Redis change, so
the pod would deadlock with ``/healthcheck`` returning 500 forever. These tests
exercise the divergence-detection helper and the loop's re-apply behaviour.
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from nv_config_manager.dhcp.cli import (
    _kea_running_config_is_bootstrap,
    _sync_kea_configuration_async,
)

# A "healthy" Kea running config — has the postgres lease-database that
# ``inject_lease_db_config`` adds at sync time.
RUNNING_HEALTHY = [
    {
        "result": 0,
        "arguments": {
            "Dhcp4": {
                "interfaces-config": {"interfaces": ["eth0"]},
                "lease-database": {
                    "type": "postgresql",
                    "host": "dhcp-db.example.local",
                    "name": "kea_dhcp",
                },
            }
        },
    }
]

# What Kea reports after the kubelet recycles its container: the bootstrap
# config baked into the image, with no ``lease-database`` entry.
RUNNING_BOOTSTRAP = [
    {
        "result": 0,
        "arguments": {
            "Dhcp4": {
                "interfaces-config": {"interfaces": ["eth0"]},
                # No lease-database; Kea defaulted to memfile.
            }
        },
    }
]

# The config we keep in Redis (no secrets — lease-db is injected at sync time).
REDIS_CONFIG = {
    "Dhcp4": {
        "interfaces-config": {"interfaces": ["eth0"]},
        "subnet4": [],
    }
}


@pytest.mark.asyncio
async def test_kea_running_config_is_bootstrap_when_lease_db_missing() -> None:
    """If remote lease-db is configured but Kea has none, this is bootstrap state."""
    kea_client = AsyncMock()
    kea_client.get_config = AsyncMock(return_value=RUNNING_BOOTSTRAP)

    is_bootstrap = await _kea_running_config_is_bootstrap(kea_client, 4, remote_lease_db=True)

    assert is_bootstrap is True
    kea_client.get_config.assert_awaited_once_with(version=4)


@pytest.mark.asyncio
async def test_kea_running_config_not_bootstrap_when_lease_db_present() -> None:
    """A healthy postgres lease-database in the running config is not bootstrap state."""
    kea_client = AsyncMock()
    kea_client.get_config = AsyncMock(return_value=RUNNING_HEALTHY)

    is_bootstrap = await _kea_running_config_is_bootstrap(kea_client, 4, remote_lease_db=True)

    assert is_bootstrap is False


@pytest.mark.asyncio
async def test_kea_running_config_not_checked_when_local_lease_db() -> None:
    """Local memfile mode skips the check entirely (no remote DB to drift from)."""
    kea_client = AsyncMock()
    kea_client.get_config = AsyncMock(return_value=RUNNING_BOOTSTRAP)

    is_bootstrap = await _kea_running_config_is_bootstrap(kea_client, 4, remote_lease_db=False)

    assert is_bootstrap is False
    kea_client.get_config.assert_not_awaited()


@pytest.mark.asyncio
async def test_kea_running_config_is_bootstrap_swallows_query_errors() -> None:
    """If we can't query KEA at all, fall back to non-bootstrap (best-effort)."""
    kea_client = AsyncMock()
    kea_client.get_config = AsyncMock(side_effect=ConnectionError("boom"))

    is_bootstrap = await _kea_running_config_is_bootstrap(kea_client, 4, remote_lease_db=True)

    assert is_bootstrap is False


@pytest.mark.asyncio
async def test_sync_loop_reapplies_when_kea_diverges() -> None:
    """End-to-end: when Kea drops back to bootstrap, the loop force-resyncs.

    Reproduces the deadlock incident: Redis content stays constant across
    iterations, but Kea's running config drifts back to the bootstrap (no
    lease-database). The loop must detect this and call ``set_config``
    regardless of the Redis-change comparison.
    """
    redis_client = AsyncMock()
    redis_client.load_kea_config = AsyncMock(return_value=REDIS_CONFIG)
    redis_client.close = AsyncMock()

    kea_client = AsyncMock()
    # Initial set_config (line "Run once" in the source) plus the loop iteration.
    kea_client.set_config = AsyncMock()
    # Loop iteration sees Kea reverted to bootstrap.
    kea_client.get_config = AsyncMock(return_value=RUNNING_BOOTSTRAP)
    kea_client.close = AsyncMock()

    # Cancel after a single loop tick so the test terminates.
    real_sleep = asyncio.sleep
    sleep_calls = {"n": 0}

    async def fake_sleep(seconds: float) -> None:
        sleep_calls["n"] += 1
        if sleep_calls["n"] >= 1:
            raise asyncio.CancelledError
        await real_sleep(0)

    with (
        patch("nv_config_manager.dhcp.cli.KeaClient.from_config", return_value=kea_client),
        patch("nv_config_manager.dhcp.cli.RedisClient.from_config", return_value=redis_client),
        patch("nv_config_manager.dhcp.cli.asyncio.sleep", side_effect=fake_sleep),
    ):
        with pytest.raises(asyncio.CancelledError):
            await _sync_kea_configuration_async(ip_version=4, refresh_interval=10, debug=False)

    # set_config was called twice: once for the initial "Run once" sync at startup,
    # and once more from the bootstrap-driven re-apply during the loop iteration.
    assert kea_client.set_config.await_count == 2
    # The bootstrap check must have actually probed Kea's running config.
    kea_client.get_config.assert_awaited_with(version=4)


@pytest.mark.asyncio
async def test_sync_loop_skips_reapply_when_no_change_and_no_divergence() -> None:
    """The opposite case: Redis stable AND Kea healthy means no re-apply."""
    redis_client = AsyncMock()
    redis_client.load_kea_config = AsyncMock(return_value=REDIS_CONFIG)
    redis_client.close = AsyncMock()

    kea_client = AsyncMock()
    kea_client.set_config = AsyncMock()
    # Loop iteration sees a healthy lease-database — not bootstrap state.
    kea_client.get_config = AsyncMock(return_value=RUNNING_HEALTHY)
    kea_client.close = AsyncMock()

    real_sleep = asyncio.sleep
    sleep_calls = {"n": 0}

    async def fake_sleep(seconds: float) -> None:
        sleep_calls["n"] += 1
        if sleep_calls["n"] >= 1:
            raise asyncio.CancelledError
        await real_sleep(0)

    with (
        patch("nv_config_manager.dhcp.cli.KeaClient.from_config", return_value=kea_client),
        patch("nv_config_manager.dhcp.cli.RedisClient.from_config", return_value=redis_client),
        patch("nv_config_manager.dhcp.cli.asyncio.sleep", side_effect=fake_sleep),
    ):
        with pytest.raises(asyncio.CancelledError):
            await _sync_kea_configuration_async(ip_version=4, refresh_interval=10, debug=False)

    # Only the initial "Run once" set_config; the loop body found nothing to do.
    assert kea_client.set_config.await_count == 1
