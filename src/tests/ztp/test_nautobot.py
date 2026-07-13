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
import asyncio
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import aiohttp
import pytest

from nv_config_manager.ztp.nautobot import (
    DeviceData,
    NautobotClient,
    NautobotUnavailableError,
    NotFoundError,
)


@pytest.mark.asyncio
async def test_device_data(mock_device_data):
    with patch(
        "nv_config_manager.ztp.nautobot.NautobotClient.graphql_query",
        new_callable=AsyncMock,
        return_value=mock_device_data,
    ):
        nb = NautobotClient()
        async with nb:
            device_data = await nb.get_device_data(uuid4())
        expected = DeviceData(
            id="80ce0a9a-d3c8-5b8e-b755-e9c16d92237b",
            name="rno1-m04-c10-spine1-hss-tan-lab1",
            addresses=["10.180.166.13", "10.180.166.130"],
            platform_name="Cumulus Linux",
            version="5.7.0",
            config_store_instance="https://api-mtls.config-store.config-manager.example.com/",
        )

        assert device_data == expected


@pytest.mark.asyncio
async def test_get_device_data_caches_within_ttl(mock_device_data):
    """A second lookup within the TTL is served from cache (no extra query)."""
    device_id = str(uuid4())
    with patch(
        "nv_config_manager.ztp.nautobot.NautobotClient.graphql_query",
        new_callable=AsyncMock,
        return_value=mock_device_data,
    ) as mock_query:
        nb = NautobotClient()
        first = await nb.get_device_data(device_id)
        second = await nb.get_device_data(device_id)

        assert first == second
        mock_query.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_device_data_single_flight(mock_device_data):
    """Concurrent lookups for the same device coalesce into one query."""
    device_id = str(uuid4())

    async def slow_query(*_args, **_kwargs):
        await asyncio.sleep(0.05)
        return mock_device_data

    with patch(
        "nv_config_manager.ztp.nautobot.NautobotClient.graphql_query",
        side_effect=slow_query,
    ) as mock_query:
        nb = NautobotClient()
        results = await asyncio.gather(*(nb.get_device_data(device_id) for _ in range(10)))

        assert all(r == results[0] for r in results)
        mock_query.assert_awaited_once()


@pytest.mark.asyncio
async def test_not_found_does_not_trip_breaker(mock_not_found_data):
    """A device that legitimately has no data is not a Nautobot health failure."""
    with patch(
        "nv_config_manager.ztp.nautobot.NautobotClient.graphql_query",
        new_callable=AsyncMock,
        return_value=mock_not_found_data,
    ):
        nb = NautobotClient()
        nb._breaker_threshold = 3
        for _ in range(5):
            with pytest.raises(NotFoundError):
                await nb.get_device_data(str(uuid4()))
        assert nb._consecutive_failures == 0
        assert nb._breaker_open_until == 0.0


@pytest.mark.asyncio
async def test_circuit_breaker_opens_on_transient_failures():
    """Repeated Nautobot errors open the breaker, then it fails fast."""
    with patch(
        "nv_config_manager.ztp.nautobot.NautobotClient.graphql_query",
        new_callable=AsyncMock,
        side_effect=aiohttp.ClientError("boom"),
    ) as mock_query:
        nb = NautobotClient()
        nb._breaker_threshold = 3

        for _ in range(3):
            with pytest.raises(aiohttp.ClientError):
                await nb.get_device_data(str(uuid4()))

        assert mock_query.await_count == 3

        # Breaker now open: fails fast without hitting Nautobot again.
        with pytest.raises(NautobotUnavailableError):
            await nb.get_device_data(str(uuid4()))
        assert mock_query.await_count == 3


@pytest.mark.asyncio
async def test_concurrency_limit_sheds_load(mock_device_data):
    """When all slots are held, a new caller fails fast with 503-worthy error."""

    async def never_returns(*_args, **_kwargs):
        await asyncio.sleep(10)
        return mock_device_data

    with patch(
        "nv_config_manager.ztp.nautobot.NautobotClient.graphql_query",
        side_effect=never_returns,
    ):
        nb = NautobotClient()
        # Saturate the single slot and make acquisition give up immediately.
        nb._semaphore = asyncio.Semaphore(1)
        nb._acquire_timeout = 0.05

        holder = asyncio.ensure_future(nb.get_device_data(str(uuid4())))
        await asyncio.sleep(0.01)  # let the holder grab the only slot
        try:
            with pytest.raises(NautobotUnavailableError):
                await nb.get_device_data(str(uuid4()))
        finally:
            holder.cancel()
