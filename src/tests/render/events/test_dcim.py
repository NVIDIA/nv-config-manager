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
from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from nv_config_manager.render.events.dcim import (
    cable,
    cablepath,
    device,
    deviceredundancygroup,
    frontport,
    interface,
    rearport,
)


@pytest.mark.asyncio
@patch("nv_config_manager.render.events.dcim.queue_render", new_callable=AsyncMock)
async def test_device(mock_enqueue: Mock, base_message: dict[str, Any]):
    test_uuid = uuid4()
    base_message["model"] = "dcim.device"
    base_message["event"] = "create"
    base_message["record"]["id"] = test_uuid
    base_message["record"]["name"] = "test-device"

    await device(base_message)

    expected_message = (
        "Triggered from nb dcim.device create on test-device by testuser at 2024-01-16T21:46:05Z"
    )
    mock_enqueue.assert_called_once_with(
        device_uuid=test_uuid,
        commit_message=expected_message,
        user="testuser",
        timestamp="2024-01-16T21:46:05Z",
    )

    mock_enqueue.reset_mock()
    # Confirm that a delete does not result in a render
    base_message["event"] = "delete"
    await device(base_message)
    mock_enqueue.assert_not_called()


@pytest.mark.parametrize(
    "model,func",
    [
        ("dcim.interface", interface),
        ("dcim.frontport", frontport),
        ("dcim.rearport", rearport),
    ],
)
@pytest.mark.asyncio
@patch("nv_config_manager.render.events.dcim.queue_render", new_callable=AsyncMock)
async def test_any_port(
    mock_enqueue: Mock, base_message: dict[str, Any], model: str, func: Callable
):
    # Interface, FrontPort, and RearPort models all have the same relevant structure
    test_uuid = uuid4()
    base_message["model"] = model
    base_message["event"] = "create"
    base_message["record"]["id"] = uuid4()
    base_message["record"]["name"] = "eth0"
    base_message["record"]["device"] = {"id": test_uuid}

    await func(base_message)

    expected_message = (
        f"Triggered from nb {model} create on eth0 by testuser at 2024-01-16T21:46:05Z"
    )
    mock_enqueue.assert_called_once_with(
        device_uuid=test_uuid,
        commit_message=expected_message,
        user="testuser",
        timestamp="2024-01-16T21:46:05Z",
    )


@pytest.mark.asyncio
@patch("nv_config_manager.render.events.dcim.queue_render", new_callable=AsyncMock)
async def test_cable(mock_enqueue: Mock, base_message: dict[str, Any]):
    test_uuid_a = uuid4()
    test_uuid_b = uuid4()
    base_message["model"] = "dcim.cable"
    base_message["event"] = "create"
    base_message["record"]["id"] = uuid4()
    base_message["record"]["name"] = "test-cable"
    base_message["record"]["termination_a"] = {"device": {"id": test_uuid_a}}
    base_message["record"]["termination_b"] = {"device": {"id": test_uuid_b}}

    await cable(base_message)

    assert mock_enqueue.call_count == 2

    for uuid in [test_uuid_a, test_uuid_b]:
        expected_message = (
            "Triggered from nb dcim.cable create on test-cable by testuser at 2024-01-16T21:46:05Z"
        )
        mock_enqueue.assert_any_call(
            device_uuid=uuid,
            commit_message=expected_message,
            user="testuser",
            timestamp="2024-01-16T21:46:05Z",
        )


@pytest.mark.asyncio
@patch("nv_config_manager.render.events.dcim.queue_render", new_callable=AsyncMock)
async def test_cable_with_module_bay(mock_enqueue: Mock, base_message: dict[str, Any]):
    test_uuid_a = uuid4()
    test_uuid_b = uuid4()
    test_module_bay_uuid = uuid4()
    base_message["model"] = "dcim.cable"
    base_message["event"] = "create"
    base_message["record"]["id"] = uuid4()
    base_message["record"]["name"] = "test-cable"
    base_message["record"]["termination_a"] = {"device": {"id": test_uuid_a}}
    base_message["record"]["termination_b"] = {
        "device": None,
        "module": {
            "id": uuid4(),
            "object_type": "dcim.module",
            "parent_module_bay": {"id": test_module_bay_uuid},
        },
    }

    with patch(
        "nv_config_manager.render.events.dcim.get_module_bay",
        return_value={
            "id": test_module_bay_uuid,
            "object_type": "dcim.modulebay",
            "name": "Slot 1",
            "parent_device": {"id": test_uuid_b},
            "parent_module": None,
        },
    ) as nb_mock:
        await cable(base_message)
        nb_mock.assert_called_with(uuid=test_module_bay_uuid)

    assert mock_enqueue.call_count == 2

    for uuid in [test_uuid_a, test_uuid_b]:
        expected_message = (
            "Triggered from nb dcim.cable create on test-cable by testuser at 2024-01-16T21:46:05Z"
        )
        mock_enqueue.assert_any_call(
            device_uuid=uuid,
            commit_message=expected_message,
            user="testuser",
            timestamp="2024-01-16T21:46:05Z",
        )


@pytest.mark.asyncio
@patch("nv_config_manager.render.events.dcim.queue_render", new_callable=AsyncMock)
async def test_cablepath(mock_enqueue: Mock, base_message: dict[str, Any]):
    test_uuid_a = uuid4()
    test_uuid_b = uuid4()
    base_message["model"] = "dcim.cablepath"
    base_message["event"] = "create"
    base_message["record"]["id"] = uuid4()
    base_message["record"]["name"] = "test-cablepath"
    base_message["record"]["origin"] = {"device": {"id": test_uuid_a}}
    base_message["record"]["destination"] = {"device": {"id": test_uuid_b}}

    await cablepath(base_message)

    assert mock_enqueue.call_count == 2

    for uuid in [test_uuid_a, test_uuid_b]:
        expected_message = "Triggered from nb dcim.cablepath create on test-cablepath by testuser at 2024-01-16T21:46:05Z"
        mock_enqueue.assert_any_call(
            device_uuid=uuid,
            commit_message=expected_message,
            user="testuser",
            timestamp="2024-01-16T21:46:05Z",
        )


@pytest.mark.asyncio
@patch("nv_config_manager.render.events.dcim.queue_render", new_callable=AsyncMock)
async def test_deviceredundancygroup(mock_enqueue: Mock, base_message: dict[str, Any]):
    test_uuids = [uuid4() for i in range(4)]
    drg_uuid = uuid4()
    base_message["model"] = "dcim.deviceredundancygroup"
    base_message["event"] = "update"
    base_message["record"]["id"] = drg_uuid
    base_message["record"]["name"] = "test-drg"

    with patch(
        "nv_config_manager.render.events.dcim.get_managed_device_uuids", return_value=test_uuids
    ) as nb_mock:
        await deviceredundancygroup(base_message)
        nb_mock.assert_called_with(device_redundancy_groups=drg_uuid)

    assert mock_enqueue.call_count == 4
    for uuid in test_uuids:
        expected_message = "Triggered from nb dcim.deviceredundancygroup update on test-drg by testuser at 2024-01-16T21:46:05Z"
        mock_enqueue.assert_any_call(
            device_uuid=uuid,
            commit_message=expected_message,
            user="testuser",
            timestamp="2024-01-16T21:46:05Z",
        )

    mock_enqueue.reset_mock()
    # Confirm that a delete does not result in a render
    base_message["event"] = "delete"
    await deviceredundancygroup(base_message)
    mock_enqueue.assert_not_called()
