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
"""Tests for the built-in provider's Render contract implementation."""

from unittest.mock import AsyncMock

import pytest
from nv_config_manager_dcim_nautobot_2x.provider import NautobotDCIMClient

from nv_config_manager.dcim import IntendedConfigurationUpdate, RenderDataRequest


def _client() -> NautobotDCIMClient:
    """Build a provider client without opening an HTTP session."""
    return NautobotDCIMClient("https://nautobot.example", "token")


@pytest.mark.asyncio
async def test_get_render_data_loads_provider_owned_queries():
    """The provider owns both template data queries and location resolution."""
    client = _client()
    client.graphql_query = AsyncMock(
        side_effect=[
            {
                "data": {
                    "device": {
                        "id": "device-id",
                        "name": "leaf-1",
                        "platform": {"name": "Cumulus Linux"},
                        "role": {"name": "Leaf"},
                        "device_type": {"model": "SN5600"},
                        "tags": [],
                        "interfaces": [],
                        "config_context": {},
                        "location": {
                            "name": "Rack 1",
                            "location_type": {"name": "Rack"},
                            "parent": {
                                "name": "Site A",
                                "location_type": {"name": "Site"},
                                "parent": None,
                            },
                        },
                    }
                }
            },
            {
                "data": {
                    "locations": [
                        {
                            "name": "Site A",
                            "location_type": {"name": "Site"},
                            "config_contexts": [],
                        }
                    ]
                }
            },
        ]
    )

    render_data = await client.get_render_data(RenderDataRequest(device_id="device-id"))

    assert render_data.device.identity.location.name == "Rack 1"
    assert render_data.location.location.name == "Site A"
    first_call, second_call = client.graphql_query.await_args_list
    assert first_call.args[1] == {"id": "device-id", "id_str": "device-id"}
    assert second_call.args[1] == {"location": "Site A"}


@pytest.mark.asyncio
async def test_render_state_operations_map_to_normalized_models():
    """Provider-normalized state hides Nautobot query and REST details."""
    client = _client()
    client.graphql_query = AsyncMock(
        side_effect=[
            {
                "data": {
                    "config_manager_device": {
                        "render_enabled": True,
                        "is_aggregate_managed": False,
                    }
                }
            },
            {
                "data": {
                    "config_manager_devices": [
                        {"id": "device-1"},
                        {"id": "device-2"},
                    ]
                }
            },
            {"data": {"devices": []}},
        ]
    )

    status = await client.get_render_device_status("device-1")
    enabled_ids = await client.get_render_enabled_device_ids(False)
    assert status and status.render_enabled is True
    assert enabled_ids == ["device-1", "device-2"]
    assert client.graphql_query.await_args_list[1].args[1] == {"is_aggregate_managed": False}


@pytest.mark.asyncio
async def test_intended_configuration_writes_are_provider_owned():
    """Render code supplies intent, while the provider owns plugin REST paths."""
    client = _client()
    client.post = AsyncMock()
    client.patch = AsyncMock()
    update = IntendedConfigurationUpdate(
        device_id="device-id",
        config_store_instance="https://config-store/",
        path="startup.yaml",
        commit_id="commit-id",
        updated="2026-07-20T00:00:00+00:00",
        updated_by="user",
        commit_message="render",
        template_version="version",
    )

    await client.upsert_intended_configuration(update)
    await client.update_render_template_version("device-id", "next-version")

    client.post.assert_awaited_once_with(
        "plugins/nv-config-manager/intendedconfig/",
        {
            "device_id": "device-id",
            "config_store_instance": "https://config-store/",
            "path": "startup.yaml",
            "commit_id": "commit-id",
            "updated": "2026-07-20T00:00:00+00:00",
            "updated_by": "user",
            "commit_message": "render",
            "template_version": "version",
        },
    )
    client.patch.assert_awaited_once_with(
        "plugins/nv-config-manager/intendedconfig/device-id/",
        {"template_version": "next-version"},
    )


@pytest.mark.asyncio
async def test_intended_interface_neighbors_are_provider_owned():
    """Temporal activities receive normalized neighbor records, not GraphQL access."""
    client = _client()
    client.graphql_query = AsyncMock(
        return_value={
            "data": {
                "interfaces": [
                    {
                        "name": "swp1",
                        "tags": [],
                        "connected_interface": {
                            "name": "swp2",
                            "mac_address": "00:11:22:33:44:55",
                            "device": {
                                "name": "leaf-2",
                                "serial": "serial-2",
                                "position": 10,
                                "role": {"name": "Leaf"},
                                "rack": {"name": "rack-1"},
                            },
                        },
                    }
                ]
            }
        }
    )

    interfaces = await client.get_intended_interface_neighbors("device-id")

    assert len(interfaces) == 1
    assert interfaces[0].name == "swp1"
    assert interfaces[0].connected_interface_name == "swp2"
    assert interfaces[0].connected_device and interfaces[0].connected_device.name == "leaf-2"
    assert client.graphql_query.await_args.args[1] == {"device_id": "device-id"}
