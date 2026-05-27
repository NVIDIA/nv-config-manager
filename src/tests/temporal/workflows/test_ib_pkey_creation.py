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
"""Tests for InfiniBand PKey Creation Workflow."""

import re
import uuid
from configparser import ConfigParser
from unittest.mock import AsyncMock, patch

import pytest
from aioresponses import aioresponses
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker

from nv_config_manager.temporal.common.secrets import clear_secrets_cache
from nv_config_manager.temporal.ngc.activities.ib_nautobot import record_ib_pkey_in_nautobot
from nv_config_manager.temporal.ngc.activities.ib_pkey import (
    create_pkey_on_ufm,
    validate_pkey_available,
    verify_pkey_created,
)
from nv_config_manager.temporal.ngc.activities.nats import publish_nats
from nv_config_manager.temporal.ngc.workflows.ib_pkey_creation import (
    IBPKeyCreationInput,
    IBPKeyCreationWorkflow,
    IBPKeyCreationWorkflowOutput,
)

UFM_BASE = "https://ufm.example.com/ufmRest"


def _create_config(sections: dict[str, dict[str, str]]) -> ConfigParser:
    config = ConfigParser()
    for section, values in sections.items():
        config.add_section(section)
        for key, value in values.items():
            config.set(section, key, value)
    return config


@pytest.fixture(autouse=True)
def reset_secrets_cache():
    clear_secrets_cache()
    yield
    clear_secrets_cache()


@pytest.fixture(autouse=True)
def _mock_nats():
    """Prevent real NATS connections from ArchiveMixin."""
    mock_producer = AsyncMock()
    mock_producer.__aenter__ = AsyncMock(return_value=mock_producer)
    mock_producer.__aexit__ = AsyncMock(return_value=False)
    with patch(
        "nv_config_manager.temporal.ngc.activities.nats.NatsProducer",
        return_value=mock_producer,
    ):
        yield


@pytest.fixture()
def mock_config():
    with patch("nv_config_manager.temporal.client.ufm.load_config") as mock:
        mock.return_value = _create_config(
            {"ufm": {"ufm_api_user": "admin", "ufm_api_token_r1": "password"}}
        )
        yield mock


@pytest.mark.asyncio
async def test_ib_pkey_creation_with_specific_pkey(mock_config):
    """Full workflow: validate, create, verify with a specific PKey."""
    task_queue = str(uuid.uuid4())

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[IBPKeyCreationWorkflow],
            activities=[
                validate_pkey_available,
                create_pkey_on_ufm,
                verify_pkey_created,
                publish_nats,
            ],
        ):
            with aioresponses() as m:
                m.get(
                    f"{UFM_BASE}/resources/pkeys",
                    payload={"0x7fff": {"partition": "management"}},
                )
                m.post(f"{UFM_BASE}/resources/pkeys/add", payload={})
                m.get(
                    f"{UFM_BASE}/resources/pkeys/0x8001",
                    payload={"partition": "new-tenant", "guids": []},
                )

                result = await env.client.execute_workflow(
                    IBPKeyCreationWorkflow.run,
                    IBPKeyCreationInput(
                        host="ufm.example.com",
                        pkey="0x8001",
                    ),
                    id=str(uuid.uuid4()),
                    task_queue=task_queue,
                )

            assert isinstance(result, IBPKeyCreationWorkflowOutput)
            assert result.pkey == "0x8001"
            assert result.auto_assigned is False
            assert result.created is True
            assert result.verified is True


@pytest.mark.asyncio
async def test_ib_pkey_creation_with_auto_assign(mock_config):
    """Full workflow: auto-assign PKey when none specified."""
    task_queue = str(uuid.uuid4())

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[IBPKeyCreationWorkflow],
            activities=[
                validate_pkey_available,
                create_pkey_on_ufm,
                verify_pkey_created,
                publish_nats,
            ],
        ):
            with aioresponses() as m:
                m.get(
                    f"{UFM_BASE}/resources/pkeys",
                    payload={"0x7fff": {"partition": "management"}},
                )
                m.post(f"{UFM_BASE}/resources/pkeys/add", payload={})
                m.get(
                    re.compile(rf"{re.escape(UFM_BASE)}/resources/pkeys/0x[0-9a-fA-F]+$"),
                    payload={"partition": "auto-assigned", "guids": []},
                )

                result = await env.client.execute_workflow(
                    IBPKeyCreationWorkflow.run,
                    IBPKeyCreationInput(
                        host="ufm.example.com",
                        pkey=None,
                    ),
                    id=str(uuid.uuid4()),
                    task_queue=task_queue,
                )

            assert result.pkey == "0x0001"
            assert result.auto_assigned is True
            assert result.created is True
            assert result.verified is True


@pytest.mark.asyncio
async def test_ib_pkey_creation_stages_queryable(mock_config):
    """Verify stages are queryable during workflow execution."""
    task_queue = str(uuid.uuid4())

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[IBPKeyCreationWorkflow],
            activities=[
                validate_pkey_available,
                create_pkey_on_ufm,
                verify_pkey_created,
                publish_nats,
            ],
        ):
            with aioresponses() as m:
                m.get(
                    f"{UFM_BASE}/resources/pkeys",
                    payload={"0x7fff": {"partition": "management"}},
                )
                m.post(f"{UFM_BASE}/resources/pkeys/add", payload={})
                m.get(
                    f"{UFM_BASE}/resources/pkeys/0x8001",
                    payload={"partition": "test", "guids": []},
                )

                handle = await env.client.start_workflow(
                    IBPKeyCreationWorkflow.run,
                    IBPKeyCreationInput(host="ufm.example.com", pkey="0x8001"),
                    id=str(uuid.uuid4()),
                    task_queue=task_queue,
                )

                result = await handle.result()

            assert result.verified is True

            stages = await handle.query(IBPKeyCreationWorkflow.stages)
            stage_names = [s.name for s in stages]
            assert "validate_pkey" in stage_names
            assert "create_pkey" in stage_names
            assert "verify_pkey" in stage_names
            assert "record_nautobot" in stage_names


NB_URL = "https://nautobot.example.com"
NB_API = f"{NB_URL}/api"
PLUGIN = f"{NB_API}/plugins/overlays"


@pytest.fixture()
def mock_all_configs():
    """Mock both UFM and Nautobot config loading."""
    ufm_cfg = _create_config({"ufm": {"ufm_api_user": "admin", "ufm_api_token_r1": "password"}})
    nb_cfg = _create_config(
        {
            "nautobot": {
                "server": NB_URL,
                "token": "test-token",
                "verify": "false",
            }
        }
    )
    with (
        patch("nv_config_manager.temporal.client.ufm.load_config", return_value=ufm_cfg),
        patch("nv_config_manager.temporal.client.nautobot.load_config", return_value=nb_cfg),
    ):
        yield


@pytest.mark.asyncio
async def test_ib_pkey_creation_with_nautobot_recording(mock_all_configs):
    """Full workflow including Nautobot partition recording."""
    task_queue = str(uuid.uuid4())

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[IBPKeyCreationWorkflow],
            activities=[
                validate_pkey_available,
                create_pkey_on_ufm,
                verify_pkey_created,
                record_ib_pkey_in_nautobot,
                publish_nats,
            ],
        ):
            with aioresponses() as m:
                m.get(
                    f"{UFM_BASE}/resources/pkeys",
                    payload={"0x7fff": {"partition": "management"}},
                )
                m.post(f"{UFM_BASE}/resources/pkeys/add", payload={})
                m.get(
                    f"{UFM_BASE}/resources/pkeys/0x8001",
                    payload={"partition": "new-tenant", "guids": []},
                )

                m.get(
                    re.compile(rf"{re.escape(NB_API)}/dcim/locations/.*"),
                    payload={"results": [{"id": "loc-1", "name": "UFM Lab"}]},
                )
                m.get(
                    re.compile(rf"{re.escape(NB_API)}/tenancy/tenants/.*"),
                    payload={"results": [{"id": "ten-1", "name": "Test Tenant"}]},
                )
                m.get(
                    re.compile(rf"{re.escape(NB_API)}/extras/statuses/.*"),
                    payload={"results": [{"id": "stat-1", "name": "Active"}]},
                )
                m.get(
                    re.compile(rf"{re.escape(PLUGIN)}/overlays/.*"),
                    payload={"results": []},
                )
                m.post(
                    f"{PLUGIN}/overlays/",
                    payload={"id": "part-1", "name": "ib-pkey-0x8001"},
                )
                m.get(
                    re.compile(rf"{re.escape(PLUGIN)}/pkeys/.*"),
                    payload={"results": []},
                )
                m.post(
                    f"{PLUGIN}/pkeys/",
                    payload={"id": "pkey-1", "pkey": "0x8001"},
                )

                result = await env.client.execute_workflow(
                    IBPKeyCreationWorkflow.run,
                    IBPKeyCreationInput(
                        host="ufm.example.com",
                        pkey="0x8001",
                        location_name="UFM Lab",
                        tenant_name="Test Tenant",
                    ),
                    id=str(uuid.uuid4()),
                    task_queue=task_queue,
                )

            assert isinstance(result, IBPKeyCreationWorkflowOutput)
            assert result.pkey == "0x8001"
            assert result.created is True
            assert result.verified is True
            assert result.overlay_id == "part-1"
            assert result.overlay_name == "ib-pkey-0x8001"
            assert result.nautobot_pkey_id == "pkey-1"


@pytest.mark.asyncio
async def test_ib_pkey_creation_skips_nautobot_without_location(mock_config):
    """Nautobot recording is skipped when location_name is not provided."""
    task_queue = str(uuid.uuid4())

    async with await WorkflowEnvironment.start_time_skipping() as env:
        async with Worker(
            env.client,
            task_queue=task_queue,
            workflows=[IBPKeyCreationWorkflow],
            activities=[
                validate_pkey_available,
                create_pkey_on_ufm,
                verify_pkey_created,
                record_ib_pkey_in_nautobot,
                publish_nats,
            ],
        ):
            with aioresponses() as m:
                m.get(
                    f"{UFM_BASE}/resources/pkeys",
                    payload={"0x7fff": {"partition": "management"}},
                )
                m.post(f"{UFM_BASE}/resources/pkeys/add", payload={})
                m.get(
                    f"{UFM_BASE}/resources/pkeys/0x8001",
                    payload={"partition": "new-tenant", "guids": []},
                )

                result = await env.client.execute_workflow(
                    IBPKeyCreationWorkflow.run,
                    IBPKeyCreationInput(
                        host="ufm.example.com",
                        pkey="0x8001",
                    ),
                    id=str(uuid.uuid4()),
                    task_queue=task_queue,
                )

            assert result.pkey == "0x8001"
            assert result.overlay_id is None
            assert result.nautobot_pkey_id is None
