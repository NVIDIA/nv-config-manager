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

from nv_config_manager.render.events.nautobot_bgp_models import (
    autonomoussystem,
    bgproutinginstance,
    peerendpoint,
    peergroup,
    peering,
)


@pytest.mark.parametrize(
    "model,func",
    [
        ("bgp.autonomoussystem", autonomoussystem),
        ("bgp.peering", peering),
        ("bgp.peergroup", peergroup),
        ("bgp.peerendpoint", peerendpoint),
        ("bgp.bgproutinginstance", bgproutinginstance),
    ],
)
@pytest.mark.asyncio
@patch("nv_config_manager.render.events.nautobot_bgp_models.queue_render", new_callable=AsyncMock)
async def test_bgp_handlers(
    mock_enqueue: Mock, base_message: dict[str, Any], model: str, func: Callable
):
    test_uuids = [uuid4() for i in range(2)]
    bgp_uuid = uuid4()
    base_message["model"] = model
    base_message["event"] = "update"
    base_message["record"]["id"] = bgp_uuid
    base_message["record"]["name"] = "test-bgp-object"
    base_message["record"]["routing_instance"] = {"id": bgp_uuid}

    if model == "bgp.autonomoussystem":
        patch_target = "nv_config_manager.render.events.nautobot_bgp_models.get_managed_device_uuids_for_autonomous_system"
        base_message["record"]["asn"] = "65001"  # Add ASN field for autonomous system
        expected_call_args = ("65001",)
    elif model == "bgp.bgproutinginstance":
        # BGP routing instance directly uses device ID from record, no utility function needed
        patch_target = None
    elif model == "bgp.peering":
        patch_target = "nv_config_manager.render.events.nautobot_bgp_models.get_managed_device_uuids_for_bgp_peering"
        expected_call_args = (bgp_uuid,)
    elif model == "bgp.peergroup":
        patch_target = "nv_config_manager.render.events.nautobot_bgp_models.get_managed_device_uuid_for_bgp_routing_instance"
        expected_call_args = (bgp_uuid,)
    elif model == "bgp.peerendpoint":
        patch_target = "nv_config_manager.render.events.nautobot_bgp_models.get_managed_device_uuid_for_bgp_routing_instance"
        expected_call_args = (bgp_uuid,)

    if patch_target:
        # For peerendpoint and peergroup, return a single UUID instead of a list
        return_value = (
            test_uuids[0] if model in ["bgp.peerendpoint", "bgp.peergroup"] else test_uuids
        )
        with patch(patch_target, return_value=return_value) as nb_mock:
            await func(base_message)
            nb_mock.assert_called_with(*expected_call_args)
    else:
        # For BGP routing instance, we need to set up the device in the record
        base_message["record"]["device"] = {"id": test_uuids[0]}
        await func(base_message)

    if model in ["bgp.bgproutinginstance", "bgp.peerendpoint", "bgp.peergroup"]:
        # BGP routing instance, peer endpoint, and peer group only render one device
        assert mock_enqueue.call_count == 1
        expected_message = f"Triggered from nb {model} update on test-bgp-object by testuser at 2024-01-16T21:46:05Z"
        mock_enqueue.assert_called_once_with(
            device_uuid=test_uuids[0],
            commit_message=expected_message,
            user="testuser",
            timestamp="2024-01-16T21:46:05Z",
        )
    else:
        assert mock_enqueue.call_count == 2
        for uuid in test_uuids:
            expected_message = f"Triggered from nb {model} update on test-bgp-object by testuser at 2024-01-16T21:46:05Z"
            mock_enqueue.assert_any_call(
                device_uuid=uuid,
                commit_message=expected_message,
                user="testuser",
                timestamp="2024-01-16T21:46:05Z",
            )


@pytest.mark.asyncio
@patch("nv_config_manager.render.events.nautobot_bgp_models.queue_render", new_callable=AsyncMock)
async def test_bgp_delete_event(mock_enqueue: Mock, base_message: dict[str, Any]):
    """Test that delete events do not trigger renders."""
    bgp_uuid = uuid4()
    base_message["model"] = "bgp.autonomoussystem"
    base_message["event"] = "delete"
    base_message["record"]["id"] = bgp_uuid
    base_message["record"]["name"] = "test-as"

    await autonomoussystem(base_message)
    mock_enqueue.assert_not_called()


@pytest.mark.asyncio
@patch("nv_config_manager.render.events.nautobot_bgp_models.queue_render", new_callable=AsyncMock)
async def test_bgp_no_affected_devices(mock_enqueue: Mock, base_message: dict[str, Any]):
    """Test that no renders are queued when no devices are affected."""
    bgp_uuid = uuid4()
    base_message["model"] = "bgp.autonomoussystem"
    base_message["event"] = "update"
    base_message["record"]["id"] = bgp_uuid
    base_message["record"]["name"] = "test-as"
    base_message["record"]["asn"] = "65001"

    with patch(
        "nv_config_manager.render.events.nautobot_bgp_models.get_managed_device_uuids_for_autonomous_system",
        return_value=[],
    ) as nb_mock:
        await autonomoussystem(base_message)
        nb_mock.assert_called_with("65001")

    mock_enqueue.assert_not_called()


@pytest.mark.asyncio
@patch("nv_config_manager.render.events.nautobot_bgp_models.queue_render", new_callable=AsyncMock)
async def test_bgp_record_without_name(mock_enqueue: Mock, base_message: dict[str, Any]):
    """Test BGP handler with a record that doesn't have a name field."""
    test_uuids = [uuid4()]
    bgp_uuid = uuid4()
    base_message["model"] = "bgp.autonomoussystem"
    base_message["event"] = "create"
    base_message["record"]["id"] = bgp_uuid
    base_message["record"]["asn"] = "65001"
    # No name field in record

    with patch(
        "nv_config_manager.render.events.nautobot_bgp_models.get_managed_device_uuids_for_autonomous_system",
        return_value=test_uuids,
    ) as nb_mock:
        await autonomoussystem(base_message)
        nb_mock.assert_called_with("65001")

    assert mock_enqueue.call_count == 1
    for uuid in test_uuids:
        expected_message = (
            "Triggered from nb bgp.autonomoussystem create by testuser at 2024-01-16T21:46:05Z"
        )
        mock_enqueue.assert_any_call(
            device_uuid=uuid,
            commit_message=expected_message,
            user="testuser",
            timestamp="2024-01-16T21:46:05Z",
        )
