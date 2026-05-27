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
"""Tests for InfiniBand Nautobot overlay management activities."""

import re
from configparser import ConfigParser
from unittest.mock import patch

import pytest
from aioresponses import aioresponses
from temporalio.exceptions import ApplicationError

from nv_config_manager.temporal.ngc.activities.ib_nautobot import (
    CreatePartitionInNautobotInput,
    ResolveGuidsToInterfacesInput,
    create_partition_in_nautobot,
    resolve_guids_to_interfaces,
)

NB_URL = "https://nautobot.example.com"
NB_API = f"{NB_URL}/api"
PLUGIN = f"{NB_API}/plugins/overlays"

LOCATION_UUID = "aaa-111"
TENANT_UUID = "bbb-222"
STATUS_UUID = "ccc-333"
OVERLAY_UUID = "ddd-444"
PKEY_UUID = "eee-555"

_NB_LOCATIONS = re.compile(rf"{re.escape(NB_API)}/dcim/locations/.*")
_NB_TENANTS = re.compile(rf"{re.escape(NB_API)}/tenancy/tenants/.*")
_NB_STATUSES = re.compile(rf"{re.escape(NB_API)}/extras/statuses/.*")
_NB_OVERLAYS = re.compile(rf"{re.escape(PLUGIN)}/overlays/.*")
_NB_PKEYS = re.compile(rf"{re.escape(PLUGIN)}/pkeys/.*")


def _nb_config() -> ConfigParser:
    config = ConfigParser()
    config.add_section("nautobot")
    config.set("nautobot", "server", NB_URL)
    config.set("nautobot", "token", "test-token")
    config.set("nautobot", "verify", "false")
    return config


@pytest.fixture(autouse=True)
def mock_nb_config():
    with patch("nv_config_manager.temporal.client.nautobot.load_config") as mock:
        mock.return_value = _nb_config()
        yield mock


def _stub_lookups(m: aioresponses, *, with_tenant: bool = False) -> None:
    m.get(_NB_LOCATIONS, payload={"results": [{"id": LOCATION_UUID, "name": "UFM Lab"}]})
    if with_tenant:
        m.get(_NB_TENANTS, payload={"results": [{"id": TENANT_UUID, "name": "tenant-a"}]})
    m.get(_NB_STATUSES, payload={"results": [{"id": STATUS_UUID, "name": "Active"}]})


class TestCreatePartitionInNautobot:
    @pytest.mark.asyncio
    async def test_creates_overlay_and_pkey(self, mock_nb_config):
        with aioresponses() as m:
            _stub_lookups(m)
            m.get(_NB_OVERLAYS, payload={"results": []})
            m.post(f"{PLUGIN}/overlays/", payload={"id": OVERLAY_UUID, "name": "ib-pkey-0x0005"})
            m.get(_NB_PKEYS, payload={"results": []})
            m.post(f"{PLUGIN}/pkeys/", payload={"id": PKEY_UUID, "pkey": "0x0005"})

            result = await create_partition_in_nautobot(
                CreatePartitionInNautobotInput(pkey="0x0005", location_name="UFM Lab")
            )

            assert result.partition_id == OVERLAY_UUID
            assert result.partition_name == "ib-pkey-0x0005"
            assert result.pkey_id == PKEY_UUID
            assert result.pkey == "0x0005"

    @pytest.mark.asyncio
    async def test_custom_partition_name(self, mock_nb_config):
        with aioresponses() as m:
            _stub_lookups(m)
            m.get(_NB_OVERLAYS, payload={"results": []})
            m.post(f"{PLUGIN}/overlays/", payload={"id": OVERLAY_UUID, "name": "my-vpc"})
            m.get(_NB_PKEYS, payload={"results": []})
            m.post(f"{PLUGIN}/pkeys/", payload={"id": PKEY_UUID, "pkey": "0x0005"})

            result = await create_partition_in_nautobot(
                CreatePartitionInNautobotInput(
                    pkey="0x0005",
                    partition_name="my-vpc",
                    location_name="UFM Lab",
                )
            )

            assert result.partition_name == "my-vpc"

    @pytest.mark.asyncio
    async def test_with_tenant(self, mock_nb_config):
        with aioresponses() as m:
            _stub_lookups(m, with_tenant=True)
            m.get(_NB_OVERLAYS, payload={"results": []})
            m.post(f"{PLUGIN}/overlays/", payload={"id": OVERLAY_UUID, "name": "ib-pkey-0x0005"})
            m.get(_NB_PKEYS, payload={"results": []})
            m.post(f"{PLUGIN}/pkeys/", payload={"id": PKEY_UUID, "pkey": "0x0005"})

            result = await create_partition_in_nautobot(
                CreatePartitionInNautobotInput(
                    pkey="0x0005",
                    location_name="UFM Lab",
                    tenant_name="tenant-a",
                )
            )

            assert result.partition_id == OVERLAY_UUID

    @pytest.mark.asyncio
    async def test_idempotent_existing_overlay_and_pkey(self, mock_nb_config):
        """Reuses existing objects instead of creating duplicates."""
        with aioresponses() as m:
            _stub_lookups(m)
            m.get(
                _NB_OVERLAYS, payload={"results": [{"id": OVERLAY_UUID, "name": "ib-pkey-0x0005"}]}
            )
            m.get(_NB_PKEYS, payload={"results": [{"id": PKEY_UUID, "pkey": "0x0005"}]})

            result = await create_partition_in_nautobot(
                CreatePartitionInNautobotInput(pkey="0x0005", location_name="UFM Lab")
            )

            assert result.partition_id == OVERLAY_UUID
            assert result.pkey_id == PKEY_UUID

    @pytest.mark.asyncio
    async def test_location_not_found(self, mock_nb_config):
        with aioresponses() as m:
            m.get(_NB_LOCATIONS, payload={"results": []})

            with pytest.raises(ApplicationError, match="Location.*not found"):
                await create_partition_in_nautobot(
                    CreatePartitionInNautobotInput(pkey="0x0005", location_name="nonexistent")
                )

    @pytest.mark.asyncio
    async def test_tenant_not_found(self, mock_nb_config):
        with aioresponses() as m:
            m.get(_NB_LOCATIONS, payload={"results": [{"id": LOCATION_UUID, "name": "UFM Lab"}]})
            m.get(_NB_TENANTS, payload={"results": []})

            with pytest.raises(ApplicationError, match="Tenant.*not found"):
                await create_partition_in_nautobot(
                    CreatePartitionInNautobotInput(
                        pkey="0x0005",
                        location_name="UFM Lab",
                        tenant_name="ghost-tenant",
                    )
                )

    @pytest.mark.asyncio
    async def test_status_not_found(self, mock_nb_config):
        with aioresponses() as m:
            m.get(_NB_LOCATIONS, payload={"results": [{"id": LOCATION_UUID, "name": "UFM Lab"}]})
            m.get(_NB_STATUSES, payload={"results": []})

            with pytest.raises(ApplicationError, match="Status.*not found"):
                await create_partition_in_nautobot(
                    CreatePartitionInNautobotInput(pkey="0x0005", location_name="UFM Lab")
                )

    @pytest.mark.asyncio
    async def test_idempotent_retry_picks_up_existing_overlay(self, mock_nb_config):
        """On retry, existing overlay is reused and only PKey is created."""
        with aioresponses() as m:
            _stub_lookups(m)
            m.get(
                _NB_OVERLAYS, payload={"results": [{"id": OVERLAY_UUID, "name": "ib-pkey-0x0005"}]}
            )
            m.get(_NB_PKEYS, payload={"results": []})
            m.post(f"{PLUGIN}/pkeys/", payload={"id": PKEY_UUID, "pkey": "0x0005"})

            result = await create_partition_in_nautobot(
                CreatePartitionInNautobotInput(pkey="0x0005", location_name="UFM Lab")
            )

            assert result.partition_id == OVERLAY_UUID
            assert result.pkey_id == PKEY_UUID


_NB_GRAPHQL = f"{NB_API}/graphql/"


def _graphql_payload(interfaces: list[dict]) -> dict:
    return {"data": {"interfaces": interfaces}}


class TestResolveGuidsToInterfaces:
    """Reverse-lookup of IB GUIDs to Nautobot interface records."""

    @pytest.mark.asyncio
    async def test_empty_input_returns_empty_resolved(self, mock_nb_config):
        result = await resolve_guids_to_interfaces(ResolveGuidsToInterfacesInput(guids=[]))
        assert result.resolved == []

    @pytest.mark.asyncio
    async def test_resolves_each_guid_to_interface(self, mock_nb_config):
        with aioresponses() as m:
            m.post(
                _NB_GRAPHQL,
                payload=_graphql_payload(
                    [
                        {
                            "id": "iface-1",
                            "name": "mlx5_0",
                            "cf_ib_guid": "0002c903000e0b72",
                            "device": {"name": "hca01"},
                        },
                        {
                            "id": "iface-2",
                            "name": "mlx5_1",
                            "cf_ib_guid": "0002c903000e0b73",
                            "device": {"name": "hca01"},
                        },
                    ]
                ),
            )

            result = await resolve_guids_to_interfaces(
                ResolveGuidsToInterfacesInput(
                    guids=["0002c903000e0b72", "0002c903000e0b73"],
                )
            )

            guids = sorted(r.guid for r in result.resolved)
            assert guids == ["0002c903000e0b72", "0002c903000e0b73"]
            iface_ids = sorted(r.interface_id for r in result.resolved)
            assert iface_ids == ["iface-1", "iface-2"]

    @pytest.mark.asyncio
    async def test_dedupes_input_guids(self, mock_nb_config):
        with aioresponses() as m:
            m.post(
                _NB_GRAPHQL,
                payload=_graphql_payload(
                    [
                        {
                            "id": "iface-1",
                            "name": "mlx5_0",
                            "cf_ib_guid": "0002c903000e0b72",
                            "device": {"name": "hca01"},
                        }
                    ]
                ),
            )

            result = await resolve_guids_to_interfaces(
                ResolveGuidsToInterfacesInput(
                    guids=["0002c903000e0b72", "0002c903000e0b72"],
                )
            )

            assert len(result.resolved) == 1

    @pytest.mark.asyncio
    async def test_missing_guid_raises(self, mock_nb_config):
        with aioresponses() as m:
            m.post(_NB_GRAPHQL, payload=_graphql_payload([]))

            with pytest.raises(ApplicationError, match="No Nautobot interface found"):
                await resolve_guids_to_interfaces(
                    ResolveGuidsToInterfacesInput(guids=["0002c903000e0b72"])
                )

    @pytest.mark.asyncio
    async def test_duplicate_match_raises(self, mock_nb_config):
        with aioresponses() as m:
            m.post(
                _NB_GRAPHQL,
                payload=_graphql_payload(
                    [
                        {
                            "id": "iface-1",
                            "name": "mlx5_0",
                            "cf_ib_guid": "0002c903000e0b72",
                            "device": {"name": "hca01"},
                        },
                        {
                            "id": "iface-2",
                            "name": "mlx5_0",
                            "cf_ib_guid": "0002c903000e0b72",
                            "device": {"name": "hca02"},
                        },
                    ]
                ),
            )

            with pytest.raises(ApplicationError, match="matched multiple"):
                await resolve_guids_to_interfaces(
                    ResolveGuidsToInterfacesInput(guids=["0002c903000e0b72"])
                )

    @pytest.mark.asyncio
    async def test_case_insensitive_guid_match(self, mock_nb_config):
        """Nautobot's __ie filter is case-insensitive; activity normalizes."""
        with aioresponses() as m:
            m.post(
                _NB_GRAPHQL,
                payload=_graphql_payload(
                    [
                        {
                            "id": "iface-1",
                            "name": "mlx5_0",
                            "cf_ib_guid": "0002C903000E0B72",
                            "device": {"name": "hca01"},
                        }
                    ]
                ),
            )

            result = await resolve_guids_to_interfaces(
                ResolveGuidsToInterfacesInput(guids=["0002c903000e0b72"])
            )

            assert len(result.resolved) == 1
            assert result.resolved[0].interface_id == "iface-1"

    @pytest.mark.asyncio
    async def test_all_empty_guids_raises(self, mock_nb_config):
        with pytest.raises(ApplicationError, match="All provided GUIDs were empty"):
            await resolve_guids_to_interfaces(ResolveGuidsToInterfacesInput(guids=["", ""]))
