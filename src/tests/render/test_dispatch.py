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
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from nv_config_manager.render.dispatch import EventDispatcher
from nv_config_manager.render.events import (
    autonomoussystem,
    bgproutinginstance,
    cable,
    cablepath,
    configcontext,
    configmanagerdevicestatus,
    device,
    deviceredundancygroup,
    frontport,
    interface,
    ipaddress,
    peerendpoint,
    peergroup,
    peering,
    prefix,
    rearport,
    vrf,
)


def test_dispatch_table():
    dispatcher = EventDispatcher()

    assert dispatcher.dispatch_table == {
        "nautobot_bgp_models.autonomoussystem": autonomoussystem,
        "nautobot_bgp_models.peering": peering,
        "nautobot_bgp_models.peergroup": peergroup,
        "nautobot_bgp_models.peerendpoint": peerendpoint,
        "nautobot_bgp_models.bgproutinginstance": bgproutinginstance,
        "dcim.cable": cable,
        "dcim.cablepath": cablepath,
        "extras.configcontext": configcontext,
        "dcim.device": device,
        "dcim.deviceredundancygroup": deviceredundancygroup,
        "dcim.frontport": frontport,
        "dcim.interface": interface,
        "dcim.rearport": rearport,
        "ipam.vrf": vrf,
        "ipam.prefix": prefix,
        "ipam.ipaddress": ipaddress,
        "nv_config_manager.configmanagerdevicestatus": configmanagerdevicestatus,
    }


@pytest.mark.asyncio
@patch("nv_config_manager.render.events.dcim.queue_render")
async def test_nautobot_event_dispatch(mock_enqueue, base_message):
    # Mocking at the render instead of mocking the
    # device function as that's tricky with the
    # way the events functions are imported
    test_uuid = uuid4()
    base_message["model"] = "dcim.device"
    base_message["event"] = "create"
    base_message["record"]["id"] = test_uuid
    base_message["record"]["name"] = "test-device"

    dispatcher = EventDispatcher()
    await dispatcher.nautobot_event_dispatch(base_message)
    mock_enqueue.assert_called_once_with(
        device_uuid=test_uuid,
        commit_message="Triggered from nb dcim.device create on test-device by testuser at 2024-01-16T21:46:05Z",
        user="testuser",
        timestamp="2024-01-16T21:46:05Z",
    )


@pytest.mark.asyncio
async def test_nautobot_event_dispatch_no_handler(base_message):
    dispatcher = EventDispatcher()
    dispatcher.logger.info = MagicMock()
    base_message["model"] = "extras.notes"
    await dispatcher.nautobot_event_dispatch(base_message)
    dispatcher.logger.info.assert_called_once_with(
        "No event handler implemented for %s, ignoring message.", "extras.notes"
    )


@patch("nv_config_manager.render.dispatch.execute_render")
@pytest.mark.asyncio
async def test_nautobot_change_dispatch(mock_render):
    test_uuid = uuid4()
    message = {
        "device_id": test_uuid,
        "commit_message": "test commit message",
        "user": "test",
        "@timestamp": "2025-08-13T20:00:30Z",
    }

    dispatcher = EventDispatcher()
    await dispatcher.nautobot_change_dispatch(message)
    mock_render.assert_called_once_with(
        test_uuid,
        "test commit message",
        "test",
    )
