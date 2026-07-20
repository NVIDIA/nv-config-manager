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
"""Tests for the IB PKey per-resource lock host canonicalization mixin."""

import pytest
from pydantic import BaseModel

from nv_config_manager.temporal.common.lock import WorkflowLockSpec, build_workflow_lock_key
from nv_config_manager.temporal.common.mixins.metadata import WorkflowMetadataMixin
from nv_config_manager.temporal.ngc.workflows import REGISTERED_WORKFLOWS
from nv_config_manager.temporal.ngc.workflows._ib_pkey_lock import UFMHostLockMixin


class _HostInput(BaseModel):
    host: str
    pkey: str = "0x0100"


@pytest.mark.asyncio
async def test_canonicalizes_host_before_run(mocker):
    """The mixin rewrites host so name and IP collapse to one lock key."""
    mocker.patch(
        "nv_config_manager.temporal.ngc.activities.ib_nautobot.canonicalize_ufm_host",
        new=mocker.AsyncMock(return_value="10.0.0.5"),
    )
    body = _HostInput(host="ufm01")

    result = await UFMHostLockMixin.canonicalize_input(body)

    assert result.host == "10.0.0.5"
    assert result.pkey == "0x0100"


@pytest.mark.asyncio
async def test_host_spellings_collapse_to_one_lock_key(mocker):
    """Name and IP that resolve to the same device produce one lock key.

    Guards the end-to-end contract the lock relies on: canonicalization at the API
    boundary plus deterministic key construction must serialize equivalent hosts.
    """
    mocker.patch(
        "nv_config_manager.temporal.ngc.activities.ib_nautobot.canonicalize_ufm_host",
        new=mocker.AsyncMock(return_value="10.0.0.5"),
    )
    spec = WorkflowLockSpec(key_fields=["host", "pkey"])

    by_name = await UFMHostLockMixin.canonicalize_input(_HostInput(host="ufm01"))
    by_ip = await UFMHostLockMixin.canonicalize_input(_HostInput(host="10.0.0.5"))

    key_from_name = build_workflow_lock_key(
        spec, workflow_name="IBPKeyMemberAdd", namespace="ngc", workflow_input=by_name
    )
    key_from_ip = build_workflow_lock_key(
        spec, workflow_name="IBPKeyMemberAdd", namespace="ngc", workflow_input=by_ip
    )

    assert key_from_name == key_from_ip == "wf-lock:ngc:host=10.0.0.5:pkey=0x0100"


def _host_keyed_locked_workflows() -> list[type]:
    """Registered workflows whose lock key includes the host field."""
    keyed: list[type] = []
    for workflow_class in REGISTERED_WORKFLOWS:
        spec = getattr(workflow_class, "workflow_lock", None)
        if spec is not None and "host" in spec.key_fields:
            keyed.append(workflow_class)
    return keyed


@pytest.mark.parametrize("workflow_class", _host_keyed_locked_workflows())
def test_host_keyed_lock_requires_canonicalization(workflow_class):
    """A workflow that locks on ``host`` must normalize it before the run.

    The lock key is built from raw workflow input, so a host-keyed lock that
    inherits the no-op ``canonicalize_input`` would let a device name and its IP
    map to different keys and defeat serialization. Fail loudly if a new locked
    workflow forgets to override canonicalization.
    """
    assert (
        workflow_class.canonicalize_input.__func__
        is not WorkflowMetadataMixin.canonicalize_input.__func__
    ), (
        f"{workflow_class.__name__} locks on 'host' but does not override "
        "canonicalize_input; its lock key would not be canonical"
    )
