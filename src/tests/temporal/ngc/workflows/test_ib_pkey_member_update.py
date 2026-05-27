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
"""Tests for IBPKeyMemberUpdateWorkflow."""

import re
import uuid
from configparser import ConfigParser
from unittest.mock import AsyncMock, patch

import pytest
from aioresponses import aioresponses
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from nv_config_manager.temporal.common.secrets import clear_secrets_cache
from nv_config_manager.temporal.ngc.activities.ib_nautobot import (
    fetch_pkey_assignments,
    resolve_guids_to_interfaces,
    resolve_interface_guids,
    sync_pkey_assignments,
)
from nv_config_manager.temporal.ngc.activities.ib_pkey import (
    add_guids_to_pkey,
    remove_guids_from_pkey,
    verify_pkey_members,
)
from nv_config_manager.temporal.ngc.activities.nats import publish_nats
from nv_config_manager.temporal.ngc.workflows.ib_pkey_member_update import (
    IBPKeyMemberUpdateInput,
    IBPKeyMemberUpdateOutput,
    IBPKeyMemberUpdateWorkflow,
    InterfaceRef,
)
from tests.temporal.ib_helpers import stub_graphql_resolve_guids

UFM_BASE = "https://ufm.example.com/ufmRest"
NB_URL = "https://nautobot.example.com"
NB_API = f"{NB_URL}/api"
PLUGIN = f"{NB_API}/plugins/overlays"

OVERLAY_UUID = "ddd-444"
STATUS_UUID = "ccc-333"
IFACE_UUID_1 = "iface-001"
IFACE_UUID_2 = "iface-002"
IFACE_UUID_3 = "iface-003"
ASSIGNMENT_UUID_1 = "asgn-001"
ASSIGNMENT_UUID_2 = "asgn-002"
ASSIGNMENT_UUID_3 = "asgn-003"

GUID_1 = "0002c903000e0b72"
GUID_2 = "0002c903000e0b73"
GUID_3 = "0002c903000e0b74"

_NB_INTERFACES = re.compile(rf"{re.escape(NB_API)}/dcim/interfaces/.*")
_NB_STATUSES = re.compile(rf"{re.escape(NB_API)}/extras/statuses/.*")
_NB_ASSIGNMENTS = re.compile(rf"{re.escape(PLUGIN)}/overlay-assignments/.*")


def _ufm_config() -> ConfigParser:
    config = ConfigParser()
    config.add_section("ufm")
    config.set("ufm", "ufm_api_user", "admin")
    config.set("ufm", "ufm_api_token_r1", "password")
    return config


def _nb_config() -> ConfigParser:
    config = ConfigParser()
    config.add_section("nautobot")
    config.set("nautobot", "server", NB_URL)
    config.set("nautobot", "token", "test-token")
    config.set("nautobot", "verify", "false")
    return config


@pytest.fixture(autouse=True)
def reset_secrets_cache():
    clear_secrets_cache()
    yield
    clear_secrets_cache()


@pytest.fixture()
def mock_all_configs():
    mock_producer = AsyncMock()
    mock_producer.publish = AsyncMock(return_value=None)
    with (
        patch("nv_config_manager.temporal.client.ufm.load_config", return_value=_ufm_config()),
        patch("nv_config_manager.temporal.client.nautobot.load_config", return_value=_nb_config()),
        patch(
            "nv_config_manager.temporal.ngc.activities.nats.NatsProducer",
            return_value=mock_producer,
        ),
    ):
        yield


_ALL_ACTIVITIES = [
    resolve_interface_guids,
    resolve_guids_to_interfaces,
    fetch_pkey_assignments,
    sync_pkey_assignments,
    remove_guids_from_pkey,
    add_guids_to_pkey,
    verify_pkey_members,
    publish_nats,
]


def _pkey_verify_url(pkey: str) -> str:
    return f"{UFM_BASE}/resources/pkeys/{pkey}?guids_data=true"


def _stub_resolve_interfaces(m: aioresponses, iface_guid_pairs: list[tuple]) -> None:
    """Register Nautobot interface resolution responses."""
    for iface_uuid, guid in iface_guid_pairs:
        m.get(
            _NB_INTERFACES,
            payload={
                "results": [
                    {
                        "id": iface_uuid,
                        "name": "mlx5_0",
                        "custom_fields": {"ib_guid": guid},
                    }
                ]
            },
        )


def _stub_status(m: aioresponses) -> None:
    m.get(
        _NB_STATUSES,
        payload={"results": [{"id": STATUS_UUID, "name": "Active"}]},
    )


@pytest.mark.asyncio
async def test_additions_only_auto_approved(mock_all_configs):
    """Workflow completes without approval gate when only adding members."""
    task_queue = str(uuid.uuid4())

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[IBPKeyMemberUpdateWorkflow],
            activities=_ALL_ACTIVITIES,
        ):
            with aioresponses() as m:
                # Stage 1: resolve desired
                _stub_resolve_interfaces(
                    m,
                    [(IFACE_UUID_1, GUID_1), (IFACE_UUID_2, GUID_2)],
                )

                # Stage 2: query current
                m.get(_NB_ASSIGNMENTS, payload={"results": []})

                # Stage 3: validate_diff auto-approved

                # Stage 4: update_nautobot
                _stub_status(m)
                m.get(_NB_ASSIGNMENTS, payload={"results": []})
                m.post(
                    f"{PLUGIN}/overlay-assignments/",
                    payload={"id": ASSIGNMENT_UUID_1},
                )
                m.post(
                    f"{PLUGIN}/overlay-assignments/",
                    payload={"id": ASSIGNMENT_UUID_2},
                )

                # Stage 5: update_ufm
                m.post(f"{UFM_BASE}/resources/pkeys/", payload={})

                # Stage 6: verify_ufm
                m.get(
                    _pkey_verify_url("0x0005"),
                    payload={
                        "guids": [
                            {"guid": GUID_1, "membership": "full"},
                            {"guid": GUID_2, "membership": "full"},
                        ]
                    },
                )

                result = await env.client.execute_workflow(
                    IBPKeyMemberUpdateWorkflow.run,
                    IBPKeyMemberUpdateInput(
                        host="ufm.example.com",
                        pkey="0x0005",
                        overlay_id=OVERLAY_UUID,
                        interfaces=[
                            InterfaceRef(device="hca01", interface="mlx5_0"),
                            InterfaceRef(device="hca01", interface="mlx5_1"),
                        ],
                    ),
                    id=str(uuid.uuid4()),
                    task_queue=task_queue,
                )

    assert isinstance(result, IBPKeyMemberUpdateOutput)
    assert result.pkey == "0x0005"
    assert result.members_added == 2
    assert result.members_removed == 0
    assert result.members_unchanged == 0
    assert result.verified is True
    assert len(result.assignment_ids_added) == 2


@pytest.mark.asyncio
async def test_no_op_when_desired_matches_current(mock_all_configs):
    """Workflow completes with no writes when desired == current."""
    task_queue = str(uuid.uuid4())

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[IBPKeyMemberUpdateWorkflow],
            activities=_ALL_ACTIVITIES,
        ):
            with aioresponses() as m:
                # Stage 1: resolve desired
                _stub_resolve_interfaces(m, [(IFACE_UUID_1, GUID_1)])

                # Stage 2: query current — same interface already assigned
                m.get(
                    _NB_ASSIGNMENTS,
                    payload={
                        "results": [
                            {
                                "id": ASSIGNMENT_UUID_1,
                                "assigned_object_id": IFACE_UUID_1,
                                "guid": GUID_1,
                            }
                        ]
                    },
                )

                # Stage 3: validate_diff auto-approved

                # Stage 4: update_nautobot — unchanged, no writes
                _stub_status(m)
                m.get(
                    _NB_ASSIGNMENTS,
                    payload={
                        "results": [
                            {
                                "id": ASSIGNMENT_UUID_1,
                                "assigned_object_id": IFACE_UUID_1,
                                "guid": GUID_1,
                            }
                        ]
                    },
                )

                # Stage 5: update_ufm — empty remove, empty add
                m.post(f"{UFM_BASE}/resources/pkeys/", payload={})

                # Stage 6: verify_ufm
                m.get(
                    _pkey_verify_url("0x0005"),
                    payload={"guids": [{"guid": GUID_1, "membership": "full"}]},
                )

                result = await env.client.execute_workflow(
                    IBPKeyMemberUpdateWorkflow.run,
                    IBPKeyMemberUpdateInput(
                        host="ufm.example.com",
                        pkey="0x0005",
                        overlay_id=OVERLAY_UUID,
                        interfaces=[
                            InterfaceRef(device="hca01", interface="mlx5_0"),
                        ],
                    ),
                    id=str(uuid.uuid4()),
                    task_queue=task_queue,
                )

    assert result.members_added == 0
    assert result.members_removed == 0
    assert result.members_unchanged == 1
    assert result.verified is True


@pytest.mark.asyncio
async def test_stages_queryable_after_completion(mock_all_configs):
    """All six stage names appear in query results after the workflow completes."""
    task_queue = str(uuid.uuid4())

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[IBPKeyMemberUpdateWorkflow],
            activities=_ALL_ACTIVITIES,
        ):
            with aioresponses() as m:
                _stub_resolve_interfaces(m, [(IFACE_UUID_1, GUID_1)])
                m.get(_NB_ASSIGNMENTS, payload={"results": []})
                _stub_status(m)
                m.get(_NB_ASSIGNMENTS, payload={"results": []})
                m.post(
                    f"{PLUGIN}/overlay-assignments/",
                    payload={"id": ASSIGNMENT_UUID_1},
                )
                m.post(f"{UFM_BASE}/resources/pkeys/", payload={})
                m.get(
                    _pkey_verify_url("0x0005"),
                    payload={"guids": [{"guid": GUID_1, "membership": "full"}]},
                )

                handle = await env.client.start_workflow(
                    IBPKeyMemberUpdateWorkflow.run,
                    IBPKeyMemberUpdateInput(
                        host="ufm.example.com",
                        pkey="0x0005",
                        overlay_id=OVERLAY_UUID,
                        interfaces=[
                            InterfaceRef(device="hca01", interface="mlx5_0"),
                        ],
                    ),
                    id=str(uuid.uuid4()),
                    task_queue=task_queue,
                )
                await handle.result()

            stages = await handle.query(IBPKeyMemberUpdateWorkflow.stages)

    stage_names = [s.name for s in stages]
    assert "resolve_desired" in stage_names
    assert "query_current" in stage_names
    assert "validate_diff" in stage_names
    assert "update_nautobot" in stage_names
    assert "update_ufm" in stage_names
    assert "verify_ufm" in stage_names


def test_input_rejects_neither_interfaces_nor_guids():
    """Validator rejects an input with neither interfaces nor GUIDs."""
    with pytest.raises(ValueError, match="One of 'interfaces' or 'guids'"):
        IBPKeyMemberUpdateInput(
            host="ufm.example.com",
            pkey="0x0005",
            overlay_id=OVERLAY_UUID,
        )


def test_input_rejects_both_interfaces_and_guids():
    """Validator rejects an input with both interfaces and GUIDs."""
    with pytest.raises(
        ValueError, match=r"One of 'interfaces' or 'guids' must be provided, but not both\."
    ):
        IBPKeyMemberUpdateInput(
            host="ufm.example.com",
            pkey="0x0005",
            overlay_id=OVERLAY_UUID,
            interfaces=[InterfaceRef(device="hca01", interface="mlx5_0")],
            guids=[GUID_1],
        )


def test_input_accepts_interfaces_only():
    """Validator accepts interfaces-only input."""
    payload = IBPKeyMemberUpdateInput(
        host="ufm.example.com",
        pkey="0x0005",
        overlay_id=OVERLAY_UUID,
        interfaces=[InterfaceRef(device="hca01", interface="mlx5_0")],
    )
    assert payload.guids == []
    assert len(payload.interfaces) == 1


def test_input_accepts_guids_only():
    """Validator accepts GUIDs-only input."""
    payload = IBPKeyMemberUpdateInput(
        host="ufm.example.com",
        pkey="0x0005",
        overlay_id=OVERLAY_UUID,
        guids=[GUID_1],
    )
    assert payload.guids == [GUID_1]
    assert payload.interfaces == []


@pytest.mark.asyncio
async def test_guids_only_path_resolves_via_graphql(mock_all_configs):
    """GUIDs-only input reverse-resolves to interfaces and completes the workflow."""
    task_queue = str(uuid.uuid4())

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[IBPKeyMemberUpdateWorkflow],
            activities=_ALL_ACTIVITIES,
        ):
            with aioresponses() as m:
                stub_graphql_resolve_guids(m, [(GUID_1, IFACE_UUID_1)])

                m.get(_NB_ASSIGNMENTS, payload={"results": []})

                _stub_status(m)
                m.get(_NB_ASSIGNMENTS, payload={"results": []})
                m.post(
                    f"{PLUGIN}/overlay-assignments/",
                    payload={"id": ASSIGNMENT_UUID_1},
                )

                m.post(f"{UFM_BASE}/resources/pkeys/", payload={})

                m.get(
                    _pkey_verify_url("0x0005"),
                    payload={"guids": [{"guid": GUID_1, "membership": "full"}]},
                )

                result = await env.client.execute_workflow(
                    IBPKeyMemberUpdateWorkflow.run,
                    IBPKeyMemberUpdateInput(
                        host="ufm.example.com",
                        pkey="0x0005",
                        overlay_id=OVERLAY_UUID,
                        guids=[GUID_1],
                    ),
                    id=str(uuid.uuid4()),
                    task_queue=task_queue,
                )

    assert result.members_added == 1
    assert result.members_removed == 0
    assert result.verified is True
