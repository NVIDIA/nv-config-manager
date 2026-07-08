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
    GetAvailableRouteDistinguishersInput,
    ProvisionVrfInput,
    ReconcileSpXOverlayAssignmentsInput,
    VrfDeletionActivityInput,
    _vni_from_rd,
    delete_overlay,
    delete_vrf,
    get_available_route_distinguishers,
    provision_vrf,
    reconcile_spx_overlay_assignments,
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
ASSIGNMENT_ID = "99990000-0000-0000-0000-000000000001"
NS_ID = "11110000-0000-0000-0000-000000000001"


def _r(url):
    """Regex that matches url as a prefix, ignoring query params."""
    return re.compile(re.escape(url))


def _lookup(id_):
    return {"results": [{"id": id_}]}


def _request_json(mocked, method, url):
    for (request_method, request_url), calls in mocked.requests.items():
        if request_method.lower() == method.lower() and str(request_url) == url:
            return calls[0].kwargs["json"]
    raise AssertionError(f"No {method.upper()} request found for {url}")


def _namespace_graphql_response(*rds, namespace_id=NS_ID, namespace_name="spectrumx_rno1"):
    return {
        "data": {
            "namespaces": [
                {
                    "id": namespace_id,
                    "name": namespace_name,
                    "vrfs": [{"rd": rd} for rd in rds],
                }
            ]
        }
    }


# ---------------------------------------------------------------------------
# reconcile_spx_overlay_assignments
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reconcile_spx_overlay_assignments_moves_port_between_overlays():
    device_id = "22220000-0000-0000-0000-000000000001"
    interface_id = "33330000-0000-0000-0000-000000000001"
    existing_interface_id = "33330000-0000-0000-0000-000000000002"
    old_overlay_id = "44440000-0000-0000-0000-000000000001"
    ib_overlay_id = "55550000-0000-0000-0000-000000000001"
    old_assignment_id = "66660000-0000-0000-0000-000000000001"

    with aioresponses() as m:
        m.get(
            _r(f"{OVERLAYS_BASE}/overlays/"),
            payload={
                "results": [
                    {
                        "id": OVERLAY_ID,
                        "name": "Panda",
                        "isolation_type": "spectrum_x_vrf",
                    }
                ]
            },
        )
        m.get(
            _r(f"{OVERLAYS_BASE}/overlay-assignments/"),
            payload={
                "results": [
                    {
                        "id": "device-assignment",
                        "overlay": {
                            "id": OVERLAY_ID,
                            "isolation_type": "spectrum_x_vrf",
                        },
                    }
                ]
            },
        )
        m.get(
            _r(f"{OVERLAYS_BASE}/overlay-assignments/"),
            payload={
                "results": [
                    {
                        "id": "ib-assignment",
                        "overlay": {
                            "id": ib_overlay_id,
                            "isolation_type": "ib_pkey",
                        },
                    },
                ],
                "next": (
                    f"{OVERLAYS_BASE}/overlay-assignments/"
                    f"?assigned_object_id={interface_id}&depth=1&limit=50&offset=50"
                ),
            },
        )
        m.get(
            _r(f"{OVERLAYS_BASE}/overlay-assignments/"),
            payload={
                "results": [
                    {
                        "id": old_assignment_id,
                        "overlay": {
                            "id": old_overlay_id,
                            "isolation_type": "spectrum_x_vrf",
                        },
                    }
                ],
                "next": None,
            },
        )
        m.delete(
            f"{OVERLAYS_BASE}/overlay-assignments/{old_assignment_id}/",
            status=204,
        )
        m.get(
            _r(f"{NAUTOBOT}/api/extras/statuses/"),
            payload={"results": [{"id": STATUS_ID}]},
        )
        m.post(
            f"{OVERLAYS_BASE}/overlay-assignments/",
            payload={"id": "new-interface-assignment"},
        )
        m.get(
            _r(f"{OVERLAYS_BASE}/overlay-assignments/"),
            payload={
                "results": [
                    {
                        "id": "existing-interface-assignment",
                        "overlay": {
                            "id": OVERLAY_ID,
                            "isolation_type": "spectrum_x_vrf",
                        },
                    }
                ]
            },
        )

        result = await reconcile_spx_overlay_assignments(
            ReconcileSpXOverlayAssignmentsInput(
                overlay_id="Panda",
                site=LOCATION_ID,
                device_id=device_id,
                interface_ids=[interface_id, existing_interface_id],
            )
        )

    assert result.created == 1
    assert result.removed == 1
    assert _request_json(m, "post", f"{OVERLAYS_BASE}/overlay-assignments/") == {
        "overlay": OVERLAY_ID,
        "assigned_object_type": "dcim.interface",
        "assigned_object_id": interface_id,
        "status": STATUS_ID,
    }
    assignment_mutations = [
        request_method.lower()
        for (request_method, request_url) in m.requests
        if str(request_url).startswith(f"{OVERLAYS_BASE}/overlay-assignments/")
        and request_method.lower() in {"post", "delete"}
    ]
    assert assignment_mutations == ["post", "delete"]


@pytest.mark.asyncio
async def test_reconcile_spx_overlay_assignments_rejects_non_spx_overlay():
    with aioresponses() as m:
        m.get(
            _r(f"{OVERLAYS_BASE}/overlays/"),
            payload={
                "results": [
                    {
                        "id": OVERLAY_ID,
                        "name": "Panda",
                        "isolation_type": "ib_pkey",
                    }
                ]
            },
        )

        with pytest.raises(ApplicationError, match="is not a spectrum_x_vrf overlay"):
            await reconcile_spx_overlay_assignments(
                ReconcileSpXOverlayAssignmentsInput(
                    overlay_id="Panda",
                    site=LOCATION_ID,
                    device_id="22220000-0000-0000-0000-000000000001",
                    interface_ids=["33330000-0000-0000-0000-000000000001"],
                )
            )

    assert all("overlay-assignments" not in str(request_url) for _, request_url in m.requests)


@pytest.mark.asyncio
async def test_reconcile_spx_overlay_assignments_keeps_old_assignment_if_create_fails():
    device_id = "22220000-0000-0000-0000-000000000001"
    interface_id = "33330000-0000-0000-0000-000000000001"
    old_assignment_id = "66660000-0000-0000-0000-000000000001"

    with aioresponses() as m:
        m.get(
            _r(f"{OVERLAYS_BASE}/overlays/"),
            payload={
                "results": [
                    {
                        "id": OVERLAY_ID,
                        "name": "Panda",
                        "isolation_type": "spectrum_x_vrf",
                    }
                ]
            },
        )
        m.get(
            _r(f"{OVERLAYS_BASE}/overlay-assignments/"),
            payload={
                "results": [
                    {
                        "id": "device-assignment",
                        "overlay": {
                            "id": OVERLAY_ID,
                            "isolation_type": "spectrum_x_vrf",
                        },
                    }
                ]
            },
        )
        m.get(
            _r(f"{OVERLAYS_BASE}/overlay-assignments/"),
            payload={
                "results": [
                    {
                        "id": old_assignment_id,
                        "overlay": {
                            "id": "44440000-0000-0000-0000-000000000001",
                            "isolation_type": "spectrum_x_vrf",
                        },
                    }
                ]
            },
        )
        m.get(
            _r(f"{NAUTOBOT}/api/extras/statuses/"),
            payload={"results": [{"id": STATUS_ID}]},
        )
        m.post(
            f"{OVERLAYS_BASE}/overlay-assignments/",
            status=400,
            payload={"detail": "replacement rejected"},
        )
        m.delete(
            f"{OVERLAYS_BASE}/overlay-assignments/{old_assignment_id}/",
            status=204,
        )

        with pytest.raises(NautobotException, match="replacement rejected"):
            await reconcile_spx_overlay_assignments(
                ReconcileSpXOverlayAssignmentsInput(
                    overlay_id="Panda",
                    site=LOCATION_ID,
                    device_id=device_id,
                    interface_ids=[interface_id],
                )
            )

    assert all(request_method.lower() != "delete" for request_method, _ in m.requests)


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
# get_available_route_distinguishers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_available_route_distinguishers_returns_namespace_ids():
    with aioresponses() as m:
        m.post(
            f"{NAUTOBOT}/api/graphql/",
            payload=_namespace_graphql_response("*:60000"),
        )

        result = await get_available_route_distinguishers(
            GetAvailableRouteDistinguishersInput(
                site=LOCATION_ID,
                namespace_tag="spectrumx",
                rd_min=60000,
                rd_max=65000,
            )
        )

    assert result.namespaces == [NS_ID]
    assert result.route_distinguisher == "*:60001"


@pytest.mark.asyncio
async def test_get_available_route_distinguishers_reuses_gap_below_max():
    with aioresponses() as m:
        m.post(
            f"{NAUTOBOT}/api/graphql/",
            payload=_namespace_graphql_response("*:60000", "*:60002", "*:65000"),
        )

        result = await get_available_route_distinguishers(
            GetAvailableRouteDistinguishersInput(
                site=LOCATION_ID,
                namespace_tag="tenant-a",
                rd_min=60000,
                rd_max=65000,
            )
        )

    assert result.route_distinguisher == "*:60001"
    assert result.namespaces == [NS_ID]


@pytest.mark.asyncio
async def test_get_available_route_distinguishers_raises_when_range_full():
    with aioresponses() as m:
        m.post(
            f"{NAUTOBOT}/api/graphql/",
            payload=_namespace_graphql_response("*:60000", "*:60001", "*:60002"),
        )

        with pytest.raises(ApplicationError, match="out of space for new RDs"):
            await get_available_route_distinguishers(
                GetAvailableRouteDistinguishersInput(
                    site=LOCATION_ID,
                    namespace_tag="tenant-a",
                    rd_min=60000,
                    rd_max=60002,
                )
            )


# ---------------------------------------------------------------------------
# provision_vrf
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provision_vrf_creates_overlay_vrf_assignment_and_vxlan():
    with aioresponses() as m:
        m.get(_r(f"{NAUTOBOT}/api/extras/statuses/"), payload=_lookup(STATUS_ID))
        m.get(_r(f"{NAUTOBOT}/api/tenancy/tenants/"), payload=_lookup(TENANT_ID))
        m.get(_r(f"{OVERLAYS_BASE}/overlays/"), payload={"results": []})
        m.post(f"{OVERLAYS_BASE}/overlays/", payload={"id": OVERLAY_ID})
        m.post(f"{NAUTOBOT}/api/ipam/vrfs/", payload={"id": VRF_ID})
        m.post(
            f"{OVERLAYS_BASE}/overlay-assignments/",
            payload={"id": ASSIGNMENT_ID},
        )
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

        assert _request_json(m, "post", f"{NAUTOBOT}/api/ipam/vrfs/") == {
            "name": "SpXTenant60004",
            "rd": "*:60004",
            "namespace": NS_ID,
            "tenant": TENANT_ID,
        }
        assert _request_json(m, "post", f"{OVERLAYS_BASE}/overlay-assignments/") == {
            "overlay": OVERLAY_ID,
            "assigned_object_type": "ipam.vrf",
            "assigned_object_id": VRF_ID,
            "status": STATUS_ID,
        }


@pytest.mark.asyncio
async def test_provision_vrf_reuses_existing_overlay():
    with aioresponses() as m:
        m.get(_r(f"{NAUTOBOT}/api/extras/statuses/"), payload=_lookup(STATUS_ID))
        m.get(_r(f"{NAUTOBOT}/api/tenancy/tenants/"), payload=_lookup(TENANT_ID))
        m.get(
            _r(f"{OVERLAYS_BASE}/overlays/"),
            payload={"results": [{"id": OVERLAY_ID, "tenant": {"id": TENANT_ID}}]},
        )
        # No create_overlay call — overlay already exists
        m.post(f"{NAUTOBOT}/api/ipam/vrfs/", payload={"id": VRF_ID})
        m.post(
            f"{OVERLAYS_BASE}/overlay-assignments/",
            payload={"id": ASSIGNMENT_ID},
        )
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
        m.post(
            f"{OVERLAYS_BASE}/overlay-assignments/",
            payload={"id": ASSIGNMENT_ID},
        )
        # vxlan creation fails
        m.post(f"{OVERLAYS_BASE}/vxlans/", status=400, payload={"detail": "bad"})
        # rollback: delete assignment and VRF (no VXLANs were created)
        m.delete(
            f"{OVERLAYS_BASE}/overlay-assignments/{ASSIGNMENT_ID}/",
            status=204,
        )
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
async def test_delete_vrf_deletes_vxlan_assignment_then_vrf():
    with aioresponses() as m:
        m.get(
            _r(f"{OVERLAYS_BASE}/vxlans/"),
            payload={"results": [{"id": VXLAN_ID, "vrf": {"id": VRF_ID}}]},
        )
        m.delete(f"{OVERLAYS_BASE}/vxlans/{VXLAN_ID}/", status=204)
        m.get(
            _r(f"{OVERLAYS_BASE}/overlay-assignments/"),
            payload={"results": [{"id": ASSIGNMENT_ID}]},
        )
        m.delete(
            f"{OVERLAYS_BASE}/overlay-assignments/{ASSIGNMENT_ID}/",
            status=204,
        )
        m.delete(f"{NAUTOBOT}/api/ipam/vrfs/{VRF_ID}/", status=204)

        await delete_vrf(VrfDeletionActivityInput(vrf_id=VRF_ID, vnid=60004))


@pytest.mark.asyncio
async def test_delete_vrf_skips_vxlan_bound_to_different_vrf():
    with aioresponses() as m:
        m.get(
            _r(f"{OVERLAYS_BASE}/vxlans/"),
            payload={"results": [{"id": VXLAN_ID, "vrf": {"id": "other-vrf-id"}}]},
        )
        # No VXLAN delete — vrf_id doesn't match
        m.get(
            _r(f"{OVERLAYS_BASE}/overlay-assignments/"),
            payload={"results": []},
        )
        m.delete(f"{NAUTOBOT}/api/ipam/vrfs/{VRF_ID}/", status=204)

        await delete_vrf(VrfDeletionActivityInput(vrf_id=VRF_ID, vnid=60004))


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
        m.get(_r(f"{OVERLAYS_BASE}/vxlans/"), payload={"results": [{"id": VXLAN_ID}]})

        result = await delete_overlay(
            DeleteOverlayInput(overlay_id="test-overlay-001", site=LOCATION_ID)
        )

    assert result.deleted is False


@pytest.mark.asyncio
async def test_delete_overlay_cascades_assignments_when_no_vxlans_remain():
    with aioresponses() as m:
        m.get(
            _r(f"{OVERLAYS_BASE}/overlays/"),
            payload={"results": [{"id": OVERLAY_ID, "name": "test-overlay-001"}]},
        )
        m.get(_r(f"{OVERLAYS_BASE}/vxlans/"), payload={"results": []})
        m.delete(f"{OVERLAYS_BASE}/overlays/{OVERLAY_ID}/", status=204)

        result = await delete_overlay(
            DeleteOverlayInput(overlay_id="test-overlay-001", site=LOCATION_ID)
        )

    assert result.deleted is True


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


# ---------------------------------------------------------------------------
# NautobotClient pagination (get_all)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_vxlans_by_overlay_follows_pagination():
    """All VXLAN pages are collected, not just the first."""
    with aioresponses() as m:
        m.get(
            _r(f"{OVERLAYS_BASE}/vxlans/"),
            payload={"next": f"{OVERLAYS_BASE}/vxlans/?offset=1", "results": [{"id": "v1"}]},
        )
        m.get(
            _r(f"{OVERLAYS_BASE}/vxlans/"),
            payload={"next": None, "results": [{"id": "v2"}]},
        )

        client = NautobotClient()
        async with client:
            result = await client.get_vxlans_by_overlay(OVERLAY_ID)

    assert [v["id"] for v in result] == ["v1", "v2"]


@pytest.mark.asyncio
async def test_lookup_id_by_name_detects_ambiguity_across_pages():
    """Ambiguity is detected from the server count even when results are paginated."""
    with aioresponses() as m:
        m.get(
            _r(f"{NAUTOBOT}/api/dcim/locations/"),
            payload={
                "count": 2,
                "next": f"{NAUTOBOT}/api/dcim/locations/?offset=1",
                "results": [{"id": "id-1"}],
            },
        )

        client = NautobotClient()
        async with client:
            with pytest.raises(NautobotException, match="Ambiguous name"):
                await client.lookup_id_by_name("dcim/locations/", "SPO01")
