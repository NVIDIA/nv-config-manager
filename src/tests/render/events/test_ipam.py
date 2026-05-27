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
from typing import Any
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from nv_config_manager.render.events.ipam import (
    ipaddress,
    prefix,
    vrf,
)


@pytest.mark.asyncio
@patch("nv_config_manager.render.events.ipam.queue_render", new_callable=AsyncMock)
async def test_vrf(mock_enqueue: Mock, base_message: dict[str, Any]):
    test_uuids = [uuid4() for i in range(3)]
    vrf_uuid = uuid4()
    base_message["model"] = "ipam.vrf"
    base_message["event"] = "update"
    base_message["record"]["id"] = vrf_uuid
    base_message["record"]["name"] = "test-vrf"

    with patch(
        "nv_config_manager.render.events.ipam.get_managed_device_uuids_for_vrf",
        return_value=test_uuids,
    ) as nb_mock:
        await vrf(base_message)
        nb_mock.assert_called_with(vrf_uuid)

    assert mock_enqueue.call_count == 3
    for uuid in test_uuids:
        expected_message = (
            "Triggered from nb ipam.vrf update on test-vrf by testuser at 2024-01-16T21:46:05Z"
        )
        mock_enqueue.assert_any_call(
            device_uuid=uuid,
            commit_message=expected_message,
            user="testuser",
            timestamp="2024-01-16T21:46:05Z",
        )

    mock_enqueue.reset_mock()
    # Confirm that a delete does not result in a render
    base_message["event"] = "delete"
    await vrf(base_message)
    mock_enqueue.assert_not_called()


@pytest.mark.asyncio
@patch("nv_config_manager.render.events.ipam.queue_render", new_callable=AsyncMock)
async def test_prefix_with_location(mock_enqueue: Mock, base_message: dict[str, Any]):
    test_uuids = [uuid4() for i in range(2)]
    prefix_uuid = uuid4()
    location_uuid = uuid4()
    base_message["model"] = "ipam.prefix"
    base_message["event"] = "create"
    base_message["record"]["id"] = prefix_uuid
    base_message["record"]["prefix"] = "192.168.1.0/24"
    base_message["record"]["locations"] = [{"id": location_uuid}]

    with patch(
        "nv_config_manager.render.events.ipam.get_managed_device_uuids", return_value=test_uuids
    ) as nb_mock:
        await prefix(base_message)
        nb_mock.assert_called_with(locations=[location_uuid])

    assert mock_enqueue.call_count == 2
    for uuid in test_uuids:
        expected_message = "Triggered from nb ipam.prefix create on 192.168.1.0/24 by testuser at 2024-01-16T21:46:05Z"
        mock_enqueue.assert_any_call(
            device_uuid=uuid,
            commit_message=expected_message,
            user="testuser",
            timestamp="2024-01-16T21:46:05Z",
        )

    mock_enqueue.reset_mock()
    # Confirm that a delete does not result in a render
    base_message["event"] = "delete"
    await prefix(base_message)
    mock_enqueue.assert_not_called()


@pytest.mark.asyncio
@patch("nv_config_manager.render.events.ipam.queue_render", new_callable=AsyncMock)
async def test_prefix_without_location(mock_enqueue: Mock, base_message: dict[str, Any]):
    prefix_uuid = uuid4()
    base_message["model"] = "ipam.prefix"
    base_message["event"] = "create"
    base_message["record"]["id"] = prefix_uuid
    base_message["record"]["prefix"] = "192.168.1.0/24"
    base_message["record"]["locations"] = []

    await prefix(base_message)

    # Should not queue any renders when no location is specified
    mock_enqueue.assert_not_called()


@pytest.mark.asyncio
@patch("nv_config_manager.render.events.ipam.queue_render", new_callable=AsyncMock)
async def test_ipaddress(mock_enqueue: Mock, base_message: dict[str, Any]):
    test_uuids = [uuid4()]
    ip_uuid = uuid4()
    base_message["model"] = "ipam.ipaddress"
    base_message["event"] = "update"
    base_message["record"]["id"] = ip_uuid
    base_message["record"]["address"] = "192.168.1.10/24"

    with patch(
        "nv_config_manager.render.events.ipam.get_managed_device_uuids_for_ipaddress",
        return_value=test_uuids,
    ) as nb_mock:
        await ipaddress(base_message)
        nb_mock.assert_called_with(ip_uuid)

    assert mock_enqueue.call_count == 1
    for uuid in test_uuids:
        expected_message = "Triggered from nb ipam.ipaddress update on 192.168.1.10/24 by testuser at 2024-01-16T21:46:05Z"
        mock_enqueue.assert_any_call(
            device_uuid=uuid,
            commit_message=expected_message,
            user="testuser",
            timestamp="2024-01-16T21:46:05Z",
        )

    mock_enqueue.reset_mock()
    # Confirm that a delete does not result in a render
    base_message["event"] = "delete"
    await ipaddress(base_message)
    mock_enqueue.assert_not_called()


@pytest.mark.asyncio
@patch("nv_config_manager.render.events.ipam.queue_render", new_callable=AsyncMock)
async def test_no_affected_devices(mock_enqueue: Mock, base_message: dict[str, Any]):
    """Test that no renders are queued when no devices are affected."""
    vrf_uuid = uuid4()
    base_message["model"] = "ipam.vrf"
    base_message["event"] = "update"
    base_message["record"]["id"] = vrf_uuid
    base_message["record"]["name"] = "test-vrf"

    with patch(
        "nv_config_manager.render.events.ipam.get_managed_device_uuids_for_vrf", return_value=[]
    ) as nb_mock:
        await vrf(base_message)
        nb_mock.assert_called_with(vrf_uuid)

    mock_enqueue.assert_not_called()
