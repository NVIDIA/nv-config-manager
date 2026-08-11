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
"""Tests for mocked device interactions used by Backbone sandbox workflows."""

from unittest.mock import patch

import pytest

from nv_config_manager.temporal.bb_sandbox import activities
from nv_config_manager.temporal.bb_sandbox.activities import (
    MOCK_DRAIN_METRIC,
    ActivateBackboneRoutingInput,
    ApplyBackboneAddressingInput,
    DrainApplyInput,
    DrainCandidateInput,
    MockDiffInput,
    MockPingInput,
    _next_common_lag_name,
    _point_to_point_addresses,
    activate_backbone_routing,
    apply_backbone_addressing,
    apply_drain_candidate,
    build_mock_candidate_diff,
    mock_ping_rtt,
    perform_drain_candidate_diff,
)
from nv_config_manager.temporal.bb_sandbox.workflows import InternalBackboneBringupInput
from nv_config_manager.temporal.client.device import DiffChangedException, MockNetworkConnection
from nv_config_manager.temporal.client.nautobot import NautobotClient
from nv_config_manager.temporal.common.mixins.device import NetworkDeviceData


@pytest.mark.asyncio
async def test_drain_diff_uses_template_drain_metric() -> None:
    """The approval fixture mirrors the metric rendered for Maintenance."""
    result = await build_mock_candidate_diff(
        MockDiffInput(phase="drain", device="SJC0C-BBR-01", ports=["ae100"])
    )

    assert result.diff == (
        "[edit protocols isis interface ae100]\n"
        f"-   level 2 metric 10;\n+   level 2 metric {MOCK_DRAIN_METRIC};"
    )
    assert result.mocked


_JUNOS_DEVICE = NetworkDeviceData(
    id="c8f7a95e-4b2a-4e8c-9d5f-1a2b3c4d5e6f",
    name="SJC0C-BBR-01",
    role="backbone-router",
    platform="juniper-junos",
    site="SJC0C",
    device_type="ptx10002-36qdd",
    primary_ip4="192.0.2.1",
    primary_ip6=None,
)


@patch("nv_config_manager.temporal.bb_sandbox.activities.NetworkConnection.from_device_data")
def test_drain_mock_diff_is_focused_junos_output(mock_connection) -> None:
    """Local drains show only the interface metric transition from the entrypoint."""
    mock_connection.return_value = MockNetworkConnection.__new__(MockNetworkConnection)

    result = perform_drain_candidate_diff(
        DrainCandidateInput(
            device_data=_JUNOS_DEVICE,
            configuration="rendered interfaces entrypoint",
            interface_name="ae101",
            current_metric=250,
        )
    )

    assert result.mocked
    assert result.diff == (
        "[edit protocols isis interface ae101.0]\n"
        f"-   level 2 metric 250;\n+   level 2 metric {MOCK_DRAIN_METRIC};"
    )


@patch("nv_config_manager.temporal.bb_sandbox.activities.NetworkConnection.from_device_data")
def test_drain_mock_apply_rejects_unapproved_diff(mock_connection) -> None:
    """The focused mock still guards against applying a different approval artifact."""
    mock_connection.return_value = MockNetworkConnection.__new__(MockNetworkConnection)

    with pytest.raises(DiffChangedException, match="changed since approval"):
        apply_drain_candidate(
            DrainApplyInput(
                device_data=_JUNOS_DEVICE,
                configuration="rendered interfaces entrypoint",
                interface_name="ae101",
                current_metric=250,
                approved_diff="different diff",
            )
        )


@pytest.mark.asyncio
async def test_mock_ping_rtt() -> None:
    """The deterministic RTT fixture passes while preserving the requested ceiling."""
    result = await mock_ping_rtt(
        MockPingInput(source="192.0.2.0", destination="192.0.2.1", expected_rtt_ms=25)
    )

    assert result.received == result.transmitted == 5
    assert result.average_rtt_ms == 20
    assert result.healthy
    assert result.mocked


@pytest.mark.parametrize(
    ("address", "expected"),
    [
        ("192.0.2.0/31", ("192.0.2.0/31", "192.0.2.1/31")),
        ("2001:db8::/127", ("2001:db8::/127", "2001:db8::1/127")),
    ],
)
def test_point_to_point_pair(address: str, expected: tuple[str, str]) -> None:
    """Nautobot LAG addressing resolves the opposite endpoint for v4 and v6."""
    assert _point_to_point_addresses(address) == expected


def _bringup_input(**updates: object) -> InternalBackboneBringupInput:
    values = {
        "circuit_id": "CID-1",
        "jira": "GNI-1234",
        "local_device": "SJC0C-BBR-01",
        "local_ports": ["et-0/0/0"],
        "remote_device": "SJC0C-BBR-02",
        "remote_ports": ["et-0/0/0"],
        "ipv4_prefix": "192.0.2.0/31",
        "ipv6_prefix": "2001:db8::/127",
        "expected_rtt_ms": 36.8,
        "minimum_links": 1,
    }
    values.update(updates)
    return InternalBackboneBringupInput.model_validate(values)


def test_peering_ports_must_be_unique() -> None:
    """A physical interface cannot be proposed twice in one change."""
    with pytest.raises(ValueError, match="ports must be unique"):
        _bringup_input(local_ports=["et-0/0/0", "et-0/0/0"])


def test_metric_is_calculated_once_from_rtt() -> None:
    """The default matches the Backbone RTT convention before persistence."""
    assert _bringup_input().selected_igp_metric() == 368


def test_metric_override_wins() -> None:
    """An engineering override is the value sent to Nautobot."""
    assert _bringup_input(igp_metric_override=500).selected_igp_metric() == 500


@pytest.mark.asyncio
async def test_lag_name_uses_first_sequence_free_on_both_sides() -> None:
    """Automatic allocation follows the established common ae100+ convention."""

    class InterfaceClient(NautobotClient):
        def __init__(self) -> None:
            pass

        async def get_all(self, _path: str, params: dict[str, object]) -> list[dict[str, str]]:
            if params["device"] == "local":
                return [{"name": "ae100"}, {"name": "ae101"}]
            return [{"name": "ae100"}, {"name": "ae102"}]

    assert await _next_common_lag_name(InterfaceClient(), "local", "remote", None) == "ae103"


@pytest.mark.asyncio
async def test_prefix_allocator_queries_only_role_containers_and_pool_children() -> None:
    """Prefix allocation avoids loading unrelated namespace prefixes."""

    class PrefixClient(NautobotClient):
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict[str, object]]] = []

        async def get_all(
            self, path: str, params: dict[str, object] | None = None, **_kwargs: object
        ) -> list[dict[str, object]]:
            query = params or {}
            self.calls.append((path, query))
            if path == "extras/roles/":
                return [{"id": "role-p2p", "name": "BB-P2P"}]
            if path == "ipam/namespaces/":
                return [{"id": "global", "name": "Global"}]
            if query.get("type") == "container":
                return [{"id": "pool", "prefix": "192.0.2.0/29"}]
            if query.get("within") == "192.0.2.0/29":
                return [
                    {"id": "used-1", "prefix": "192.0.2.0/31"},
                    {"id": "used-2", "prefix": "192.0.2.4/31"},
                ]
            raise AssertionError((path, query))

    client = PrefixClient()
    prefix, parent = await client.get_next_available_prefix("BB-P2P", 31)

    assert (prefix, parent) == ("192.0.2.2/31", "192.0.2.0/29")
    pool_query = next(query for path, query in client.calls if query.get("type") == "container")
    assert pool_query == {
        "namespace": "global",
        "role": "role-p2p",
        "type": "container",
    }
    assert not any(
        path == "ipam/prefixes/" and "type" not in query and "within" not in query
        for path, query in client.calls
    )


def test_optional_lag_name_is_validated() -> None:
    """A supplied common name must use Junos ae numbering."""
    assert _bringup_input(lag_name="ae222").lag_name == "ae222"
    with pytest.raises(ValueError, match="string_pattern_mismatch"):
        _bringup_input(lag_name="bundle100")


@pytest.mark.parametrize("field", ["ipv4_prefix", "ipv6_prefix"])
def test_point_to_point_prefixes_are_required(field: str) -> None:
    """The form rejects non-point-to-point networks."""
    value = "192.0.2.0/30" if field == "ipv4_prefix" else "2001:db8::/126"
    with pytest.raises(ValueError, match="point-to-point|/31|/127"):
        _bringup_input(**{field: value})


@pytest.mark.asyncio
async def test_addressing_is_persisted_without_premature_isis_intent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Addressing does not imply that IS-IS has been activated."""

    class RecordingClient:
        def __init__(self) -> None:
            self.posts: list[tuple[str, dict[str, object]]] = []
            self.patches: list[tuple[str, dict[str, object]]] = []

        async def __aenter__(self) -> "RecordingClient":
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def get(
            self, path: str, params: dict[str, object] | None = None
        ) -> dict[str, object]:
            if path == "ipam/namespaces/":
                return {"results": [{"id": "namespace-global"}]}
            if path == "extras/statuses/":
                return {"results": [{"id": "status-active"}]}
            if path.startswith("dcim/interfaces/"):
                return {"id": path.split("/")[-2], "custom_fields": {"bb_min_links": 1}}
            if path.startswith("circuits/circuits/"):
                return {"id": "circuit-1", "custom_fields": {"bb_service_id": "CID-1"}}
            return {"results": []}

        async def post(self, path: str, data: dict[str, object]) -> dict[str, object]:
            self.posts.append((path, data))
            return {"id": f"created-{len(self.posts)}", **data}

        async def patch(self, path: str, data: dict[str, object]) -> dict[str, object]:
            self.patches.append((path, data))
            return {"id": path.split("/")[-2], **data}

    client = RecordingClient()
    monkeypatch.setattr(activities, "NautobotClient", lambda: client)

    await apply_backbone_addressing(
        ApplyBackboneAddressingInput(
            circuit_uuid="circuit-1",
            local_lag_id="lag-local",
            remote_lag_id="lag-remote",
            local_ipv4="192.0.2.0/31",
            remote_ipv4="192.0.2.1/31",
            local_ipv6="2001:db8::/127",
            remote_ipv6="2001:db8::1/127",
            expected_rtt_ms=36.8,
            jira="GNI-1234",
            requested_by="operator@nvidia.com",
        )
    )

    lag_patches = [data for path, data in client.patches if path.startswith("dcim/interfaces/")]
    assert lag_patches == []
    circuit_patch = next(
        data for path, data in client.patches if path == "circuits/circuits/circuit-1/"
    )
    assert circuit_patch["custom_fields"] == {
        "bb_service_id": "CID-1",
        "bb_change_ticket": "GNI-1234",
        "bb_expected_rtt_ms": "36.8",
        "bb_requested_by": "operator@nvidia.com",
    }
    assert sum(path == "ipam/prefixes/" for path, _data in client.posts) == 2
    assert sum(path == "ipam/ip-addresses/" for path, _data in client.posts) == 4
    assert sum(path == "ipam/ip-address-to-interface/" for path, _data in client.posts) == 4


@pytest.mark.asyncio
async def test_routing_activation_persists_explicit_isis_intent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The metric's presence becomes the durable IS-IS activation signal."""

    class RecordingClient:
        def __init__(self) -> None:
            self.patches: list[tuple[str, dict[str, object]]] = []

        async def __aenter__(self) -> "RecordingClient":
            return self

        async def __aexit__(self, *_args: object) -> None:
            return None

        async def get(
            self, path: str, params: dict[str, object] | None = None
        ) -> dict[str, object]:
            if path == "extras/statuses/":
                return {"results": [{"id": "status-active"}]}
            return {"id": path.split("/")[-2], "custom_fields": {"bb_min_links": 1}}

        async def patch(self, path: str, data: dict[str, object]) -> dict[str, object]:
            self.patches.append((path, data))
            return data

    client = RecordingClient()
    monkeypatch.setattr(activities, "NautobotClient", lambda: client)

    await activate_backbone_routing(
        ActivateBackboneRoutingInput(interface_ids=["lag-local", "lag-remote"], igp_metric=368)
    )

    assert len(client.patches) == 2
    assert all(data["status"] == "status-active" for _path, data in client.patches)
    assert all(data["custom_fields"]["bb_isis_metric"] == 368 for _path, data in client.patches)
