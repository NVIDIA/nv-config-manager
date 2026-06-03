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
"""Shared helpers for InfiniBand PKey member workflows."""

import re
from datetime import timedelta

from temporalio import workflow
from temporalio.common import RetryPolicy

with workflow.unsafe.imports_passed_through():
    from nv_config_manager.temporal.ngc.activities.ib_nautobot import (
        InterfaceRef,
        ResolvedInterface,
        ResolveGuidsToInterfacesInput,
        ResolveGuidsToInterfacesOutput,
        ResolveIBContextInput,
        ResolveIBContextOutput,
        ResolveIBSiteForHostInput,
        ResolveIBSiteForHostOutput,
        ResolveInterfaceGuidsInput,
        ResolveInterfaceGuidsOutput,
        resolve_guids_to_interfaces,
        resolve_ib_context,
        resolve_ib_site_for_host,
        resolve_interface_guids,
    )


DEFAULT_ACTIVITY_RETRY_POLICY = RetryPolicy(maximum_attempts=3)

_PKEY_INPUT_PATTERN = re.compile(r"\A0[xX][0-9a-fA-F]{1,4}\Z")


def validate_pkey_format(pkey: str) -> str:
    """Validate and canonicalize a pkey to '0x' + 4 lowercase hex digits."""
    stripped = (pkey or "").strip()
    if not _PKEY_INPUT_PATTERN.match(stripped):
        raise ValueError("pkey must be hex like '0x8001'")
    return f"0x{int(stripped, 16):04x}"


def validate_interfaces_xor_guids(interfaces: list[InterfaceRef], guids: list[str]) -> None:
    """Raise ValueError unless exactly one of ``interfaces`` or ``guids`` is non-empty."""
    if bool(interfaces) == bool(guids):
        raise ValueError("One of 'interfaces' or 'guids' must be provided, but not both.")


async def resolve_members(
    interfaces: list[InterfaceRef], guids: list[str]
) -> tuple[list[ResolvedInterface], str]:
    """Resolve members from interfaces or GUIDs into Nautobot interface records."""

    if interfaces:
        iface_result: ResolveInterfaceGuidsOutput = await workflow.execute_activity(
            resolve_interface_guids,
            ResolveInterfaceGuidsInput(interfaces=interfaces),
            start_to_close_timeout=timedelta(minutes=2),
            retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
        )
        return iface_result.resolved, iface_result.display

    guid_result: ResolveGuidsToInterfacesOutput = await workflow.execute_activity(
        resolve_guids_to_interfaces,
        ResolveGuidsToInterfacesInput(guids=guids),
        start_to_close_timeout=timedelta(minutes=2),
        retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
    )
    return guid_result.resolved, guid_result.display


async def call_resolve_ib_context(host: str, pkey: str) -> ResolveIBContextOutput:
    """Invoke the resolve_ib_context activity from a workflow."""
    return await workflow.execute_activity(
        resolve_ib_context,
        ResolveIBContextInput(host=host, pkey=pkey),
        start_to_close_timeout=timedelta(minutes=1),
        retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
    )


async def call_resolve_ib_site_for_host(host: str) -> ResolveIBSiteForHostOutput:
    """Invoke the resolve_ib_site_for_host activity from a workflow."""
    return await workflow.execute_activity(
        resolve_ib_site_for_host,
        ResolveIBSiteForHostInput(host=host),
        start_to_close_timeout=timedelta(minutes=1),
        retry_policy=DEFAULT_ACTIVITY_RETRY_POLICY,
    )
