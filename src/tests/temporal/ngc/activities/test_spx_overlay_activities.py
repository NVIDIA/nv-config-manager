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
"""Unit tests for SpX Overlay activity logic."""

import re

import pytest
from aioresponses import aioresponses
from temporalio.exceptions import ApplicationError

from nv_config_manager.common.client.nautobot import NautobotException
from nv_config_manager.temporal.client.nautobot import NautobotClient
from nv_config_manager.temporal.ngc.activities.nautobot import (
    DeleteOverlayInput,
    ProvisionVrfInput,
    VrfDeletionActivityInput,
    _vni_from_rd,
    delete_overlay,
    delete_vrf,
    provision_vrf,
)

NAUTOBOT = "https://nautobot.example.com"
OVERLAYS_BASE = f"{NAUTOBOT}/api/plugins/overlays"

# Shared UUIDs
STATUS_ID = "aaaa0000-0000-0000-0000-000000000001"
LOCATION_ID = "bbbb0000-0000-0000-0000-000000000001"
TENANT_ID = "cccc0000-0000-0000-0000-000000000001"
OVERLAY_ID = "dddd0000-0000-0000-0000-000000000001"
VRF_ID = "eeee0000-0000-0000-0000-000000000001"
VXLAN_ID = "ffff0000-0000-0000-0000-000000000001"
NS_ID = "11110000-0000-0000-0000-000000000001"


def _r(url):
    """Regex that matches url as a prefix, ignoring query params."""
    return re.compile(re.escape(url))


def _lookup(id_):
    return {"results": [{"id": id_}]}


# ---------------------------------------------------------------------------
# _vni_from_rd
# ---------------------------------------------------------------------------


def test_vni_from_rd_valid():
    assert _vni_from_rd("*:60004") == 60004


def test_vni_from_rd_missing_colon():
    with pytest.raises(ValueError, match="Invalid route distinguisher"):
        _vni_from_rd("60004")


def test_vni_from_rd_non_numeric():
    with pytest.raises(ValueError, match="Invalid route distinguisher"):
        _vni_from_rd("*:abc")


def test_vni_from_rd_extra_colons():
    with pytest.raises(ValueError, match="Invalid route distinguisher"):
        _vni_from_rd("1:2:3")


# ---------------------------------------------------------------------------
# provision_vrf
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provision_vrf_creates_overlay_vrf_vxlan():
    with aioresponses() as m:
        m.get(_r(f"{NAUTOBOT}/api/extras/statuses/"), payload=_lookup(STATUS_ID))
        m.get(_r(f"{NAUTOBOT}/api/tenancy/tenants/"), payload=_lookup(TENANT_ID))
        m.get(_r(f"{OVERLAYS_BASE}/overlays/"), payload={"results": []})
        m.post(f"{OVERLAYS_BASE}/overlays/", payload={"id": OVERLAY_ID})
        m.post(f"{NAUTOBOT}/api/ipam/vrfs/", payload={"id": VRF_ID})
        m.post(f"{OVERLAYS_BASE}/vxlans/", payload={"id": VXLAN_ID})

        await provision_vrf(
            ProvisionVrfInput(
                namespaces=[NS_ID],
                route_distinguisher="*:60004",
                overlay_id="test-overlay-001",
                site=LOCATION_ID,
                tenant="Public Demo",
            )
        )


@pytest.mark.asyncio
async def test_provision_vrf_reuses_existing_overlay():
    with aioresponses() as m:
        m.get(_r(f"{NAUTOBOT}/api/extras/statuses/"), payload=_lookup(STATUS_ID))
        m.get(_r(f"{NAUTOBOT}/api/tenancy/tenants/"), payload=_lookup(TENANT_ID))
        m.get(
            _r(f"{OVERLAYS_BASE}/overlays/"),
            payload={"results": [{"id": OVERLAY_ID}]},
        )
        # No create_overlay call — overlay already exists
        m.post(f"{NAUTOBOT}/api/ipam/vrfs/", payload={"id": VRF_ID})
        m.post(f"{OVERLAYS_BASE}/vxlans/", payload={"id": VXLAN_ID})

        await provision_vrf(
            ProvisionVrfInput(
                namespaces=[NS_ID],
                route_distinguisher="*:60004",
                overlay_id="test-overlay-001",
                site=LOCATION_ID,
                tenant="Public Demo",
            )
        )


@pytest.mark.asyncio
async def test_provision_vrf_rolls_back_on_vxlan_failure():
    with aioresponses() as m:
        m.get(_r(f"{NAUTOBOT}/api/extras/statuses/"), payload=_lookup(STATUS_ID))
        m.get(_r(f"{NAUTOBOT}/api/tenancy/tenants/"), payload=_lookup(TENANT_ID))
        m.get(_r(f"{OVERLAYS_BASE}/overlays/"), payload={"results": []})
        m.post(f"{OVERLAYS_BASE}/overlays/", payload={"id": OVERLAY_ID})
        m.post(f"{NAUTOBOT}/api/ipam/vrfs/", payload={"id": VRF_ID})
        # vxlan creation fails
        m.post(f"{OVERLAYS_BASE}/vxlans/", status=400, payload={"detail": "bad"})
        # rollback: delete vrf (no vxlans were created)
        m.delete(f"{NAUTOBOT}/api/ipam/vrfs/{VRF_ID}/", status=204)

        with pytest.raises(ApplicationError, match="Failed to provision VPC"):
            await provision_vrf(
                ProvisionVrfInput(
                    namespaces=[NS_ID],
                    route_distinguisher="*:60004",
                    overlay_id="test-overlay-001",
                    site=LOCATION_ID,
                    tenant="Public Demo",
                )
            )


@pytest.mark.asyncio
async def test_provision_vrf_missing_status_raises():
    with aioresponses() as m:
        m.get(_r(f"{NAUTOBOT}/api/extras/statuses/"), payload={"results": []})

        with pytest.raises(ApplicationError, match="Status 'Active' not found"):
            await provision_vrf(
                ProvisionVrfInput(
                    namespaces=[NS_ID],
                    route_distinguisher="*:60004",
                    overlay_id="test-overlay-001",
                    site=LOCATION_ID,
                    tenant="Public Demo",
                )
            )


@pytest.mark.asyncio
async def test_provision_vrf_missing_tenant_raises():
    with aioresponses() as m:
        m.get(_r(f"{NAUTOBOT}/api/extras/statuses/"), payload=_lookup(STATUS_ID))
        m.get(_r(f"{NAUTOBOT}/api/tenancy/tenants/"), payload={"results": []})

        with pytest.raises(ApplicationError, match="Tenant 'Public Demo' not found"):
            await provision_vrf(
                ProvisionVrfInput(
                    namespaces=[NS_ID],
                    route_distinguisher="*:60004",
                    overlay_id="test-overlay-001",
                    site=LOCATION_ID,
                    tenant="Public Demo",
                )
            )


# ---------------------------------------------------------------------------
# delete_vrf
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_vrf_deletes_vxlan_then_vrf():
    with aioresponses() as m:
        m.get(
            _r(f"{OVERLAYS_BASE}/vxlans/"),
            payload={"results": [{"id": VXLAN_ID, "namespace": {"name": "SuperPOD Demo"}}]},
        )
        m.delete(f"{OVERLAYS_BASE}/vxlans/{VXLAN_ID}/", status=204)
        m.delete(f"{NAUTOBOT}/api/ipam/vrfs/{VRF_ID}/", status=204)

        await delete_vrf(
            VrfDeletionActivityInput(vrf_id=VRF_ID, vnid=60004, namespace="SuperPOD Demo")
        )


@pytest.mark.asyncio
async def test_delete_vrf_skips_vxlan_from_different_namespace():
    with aioresponses() as m:
        m.get(
            _r(f"{OVERLAYS_BASE}/vxlans/"),
            payload={"results": [{"id": VXLAN_ID, "namespace": {"name": "other-ns"}}]},
        )
        # No VXLAN delete — only VRF delete
        m.delete(f"{NAUTOBOT}/api/ipam/vrfs/{VRF_ID}/", status=204)

        await delete_vrf(
            VrfDeletionActivityInput(vrf_id=VRF_ID, vnid=60004, namespace="SuperPOD Demo")
        )


# ---------------------------------------------------------------------------
# delete_overlay
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_delete_overlay_deletes_when_no_members():
    with aioresponses() as m:
        m.get(
            _r(f"{OVERLAYS_BASE}/overlays/"),
            payload={"results": [{"id": OVERLAY_ID, "name": "test-overlay-001"}]},
        )
        m.get(
            _r(f"{OVERLAYS_BASE}/overlays/{OVERLAY_ID}/"),
            payload={"id": OVERLAY_ID, "member_count": 0},
        )
        m.get(_r(f"{OVERLAYS_BASE}/vxlans/"), payload={"results": []})
        m.delete(f"{OVERLAYS_BASE}/overlays/{OVERLAY_ID}/", status=204)

        result = await delete_overlay(
            DeleteOverlayInput(overlay_id="test-overlay-001", site=LOCATION_ID)
        )

    assert result.deleted is True
    assert result.overlay_name == "test-overlay-001"


@pytest.mark.asyncio
async def test_delete_overlay_skips_when_vxlans_remain():
    with aioresponses() as m:
        m.get(
            _r(f"{OVERLAYS_BASE}/overlays/"),
            payload={"results": [{"id": OVERLAY_ID, "name": "test-overlay-001"}]},
        )
        m.get(
            _r(f"{OVERLAYS_BASE}/overlays/{OVERLAY_ID}/"),
            payload={"id": OVERLAY_ID, "member_count": 0},
        )
        m.get(_r(f"{OVERLAYS_BASE}/vxlans/"), payload={"results": [{"id": VXLAN_ID}]})

        result = await delete_overlay(
            DeleteOverlayInput(overlay_id="test-overlay-001", site=LOCATION_ID)
        )

    assert result.deleted is False


@pytest.mark.asyncio
async def test_delete_overlay_skips_when_assignments_remain():
    with aioresponses() as m:
        m.get(
            _r(f"{OVERLAYS_BASE}/overlays/"),
            payload={"results": [{"id": OVERLAY_ID, "name": "test-overlay-001"}]},
        )
        m.get(
            _r(f"{OVERLAYS_BASE}/overlays/{OVERLAY_ID}/"),
            payload={"id": OVERLAY_ID, "member_count": 2},
        )
        m.get(_r(f"{OVERLAYS_BASE}/vxlans/"), payload={"results": []})

        result = await delete_overlay(
            DeleteOverlayInput(overlay_id="test-overlay-001", site=LOCATION_ID)
        )

    assert result.deleted is False


@pytest.mark.asyncio
async def test_delete_overlay_not_found_returns_not_deleted():
    with aioresponses() as m:
        m.get(_r(f"{OVERLAYS_BASE}/overlays/"), payload={"results": []})

        result = await delete_overlay(
            DeleteOverlayInput(overlay_id="test-overlay-001", site=LOCATION_ID)
        )

    assert result.deleted is False
    assert result.overlay_name == "test-overlay-001"


# ---------------------------------------------------------------------------
# NautobotClient.lookup_id_by_name ambiguity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lookup_id_by_name_raises_on_multiple_results():

    with aioresponses() as m:
        m.get(
            _r(f"{NAUTOBOT}/api/dcim/locations/"),
            payload={"results": [{"id": "id-1"}, {"id": "id-2"}]},
        )

        client = NautobotClient()
        async with client:
            with pytest.raises(NautobotException, match="Ambiguous name"):
                await client.lookup_id_by_name("dcim/locations/", "SPO01")


@pytest.mark.asyncio
async def test_lookup_id_by_name_returns_none_when_not_found():

    with aioresponses() as m:
        m.get(_r(f"{NAUTOBOT}/api/dcim/locations/"), payload={"results": []})

        client = NautobotClient()
        async with client:
            result = await client.lookup_id_by_name("dcim/locations/", "nonexistent")

    assert result is None


# ---------------------------------------------------------------------------
# NautobotClient.find_overlay ambiguity
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_find_overlay_raises_on_multiple_results():

    with aioresponses() as m:
        m.get(
            _r(f"{OVERLAYS_BASE}/overlays/"),
            payload={"results": [{"id": "id-1"}, {"id": "id-2"}]},
        )

        client = NautobotClient()
        async with client:
            with pytest.raises(NautobotException, match="Ambiguous overlay"):
                await client.find_overlay("test-overlay-001", LOCATION_ID)
