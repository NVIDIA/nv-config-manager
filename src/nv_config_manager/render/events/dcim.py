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
"""NB NATS dcim.* Event Handlers."""

from typing import Any

from nv_config_manager.render.events.exceptions import EventParseError
from nv_config_manager.render.events.util import (
    build_commit_message,
    extract_user,
    get_managed_device_uuids,
    get_module_bay,
    queue_render,
)


async def device(data: dict[str, Any]) -> None:
    """dcim.device event handler."""
    if data["event"] == "delete":
        # No need to perform a render on device delete
        return
    device_uuid = data["record"]["id"]
    await queue_render(
        device_uuid=device_uuid,
        commit_message=build_commit_message(data),
        user=extract_user(data),
        timestamp=data["@timestamp"],
    )


async def _device_port(data: dict[str, Any]) -> None:
    """Common method for interface, frontport, rearport."""
    try:
        device_uuid = data["record"]["device"]["id"]
    except (TypeError, KeyError) as exc:
        raise EventParseError(f"Failed to extract device ID from {data}") from exc

    await queue_render(
        device_uuid=device_uuid,
        commit_message=build_commit_message(data),
        user=extract_user(data),
        timestamp=data["@timestamp"],
    )


async def interface(data: dict[str, Any]) -> None:
    """dcim.interface event handler."""
    await _device_port(data)


async def rearport(data: dict[str, Any]) -> None:
    """dcim.rearport event handler."""
    await _device_port(data)


async def frontport(data: dict[str, Any]) -> None:
    """dcim.frontport event handler."""
    await _device_port(data)


async def cable(data: dict[str, Any]) -> None:
    """dcim.cable event handler."""

    def get_term_id(termination: dict[str, Any]) -> str:
        # If a module is inserted into a module bay, then fetch the parent_module_bay
        # to get the device associated with the module bay.
        # NOTE: This currently does NOT support a module with a nested module bay.
        if termination.get("module"):
            module_bay = get_module_bay(uuid=termination["module"]["parent_module_bay"]["id"])
            device_id: str = module_bay["parent_device"]["id"]
            return device_id
        try:
            device_id = termination["device"]["id"]
            return device_id
        except KeyError as exc:
            raise EventParseError(
                f"Failed to extract device ID from cabletermination {termination}."
            ) from exc

    device_uuids = {
        get_term_id(data["record"]["termination_a"]),
        get_term_id(data["record"]["termination_b"]),
    }
    # Catches if a key is missing or a nested dictionary does not exist (NoneType)

    for device_uuid in device_uuids:
        await queue_render(
            device_uuid=device_uuid,
            commit_message=build_commit_message(data),
            user=extract_user(data),
            timestamp=data["@timestamp"],
        )


async def cablepath(data: dict[str, Any]) -> None:
    """dcim.cablepath event handler."""
    try:
        device_uuid = data["record"]["origin"]["device"]["id"]
    except KeyError as exc:
        raise EventParseError(f"Failed to extract origin device ID from {data}.") from exc
    await queue_render(
        device_uuid=device_uuid,
        commit_message=build_commit_message(data),
        user=extract_user(data),
        timestamp=data["@timestamp"],
    )
    if data["record"]["destination"]:
        try:
            device_uuid = data["record"]["destination"]["device"]["id"]
        except KeyError as exc:
            raise EventParseError(f"Failed to extract destination device ID from {data}.") from exc
        await queue_render(
            device_uuid=device_uuid,
            commit_message=build_commit_message(data),
            user=extract_user(data),
            timestamp=data["@timestamp"],
        )


async def deviceredundancygroup(data: dict[str, Any]) -> None:
    """dcim.deviceredundancygroup event handler."""
    if data["event"] == "delete":
        # Cannot load devices from a non-existent DRG
        return
    drg_uuid = data["record"]["id"]
    affected_devices = get_managed_device_uuids(device_redundancy_groups=drg_uuid)
    for device_uuid in affected_devices:
        await queue_render(
            device_uuid=device_uuid,
            commit_message=build_commit_message(data),
            user=extract_user(data),
            timestamp=data["@timestamp"],
        )
