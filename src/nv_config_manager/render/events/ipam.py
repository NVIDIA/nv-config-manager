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
"""NB NATS ipam.* Event Handlers."""

from typing import Any

from nv_config_manager.common.log import LogCategory, get_logger
from nv_config_manager.render.events.util import (
    DeviceNotEnabledError,
    build_commit_message,
    extract_user,
    get_managed_device_uuids,
    get_managed_device_uuids_for_ipaddress,
    get_managed_device_uuids_for_vrf,
    queue_render,
)

logger = get_logger(__name__, category=LogCategory.RENDER_EVENT)


async def vrf(data: dict[str, Any]) -> None:
    """ipam.vrf event handler."""
    if data["event"] == "delete":
        # Cannot load devices from a non-existent VRF
        return

    vrf_uuid = data["record"]["id"]
    affected_devices = get_managed_device_uuids_for_vrf(vrf_uuid)

    if affected_devices:
        logger.info(
            "Identified %s affected managed devices for VRF update %s",
            len(affected_devices),
            data["record"].get("name", vrf_uuid),
        )
        try:
            commit_message = build_commit_message(data)
            user = extract_user(data)
            timestamp = data["@timestamp"]

            for device_uuid in affected_devices:
                try:
                    await queue_render(
                        device_uuid=device_uuid,
                        commit_message=commit_message,
                        user=user,
                        timestamp=timestamp,
                    )
                except DeviceNotEnabledError:
                    logger.info(
                        "Device %s is not enabled for configuration renders, skipping",
                        device_uuid,
                    )
        except Exception:
            logger.exception(
                "Error queuing render jobs for VRF update %s",
                data["record"].get("name", vrf_uuid),
            )
        logger.info(
            "Queued %s render jobs for VRF update %s",
            len(affected_devices),
            data["record"].get("name", vrf_uuid),
        )
    else:
        logger.info(
            "No affected managed devices found for VRF update %s",
            data["record"].get("name", vrf_uuid),
        )


async def prefix(data: dict[str, Any]) -> None:
    """ipam.prefix event handler."""
    if data["event"] == "delete":
        # Cannot load devices from a non-existent prefix
        return

    prefix_network = data["record"].get("prefix", "unknown")
    locations = [location["id"] for location in data["record"].get("locations", [])]

    # For prefixes, especially aggregate prefixes used in route maps, we need to render
    # all devices in the location since they may use this prefix in routing decisions
    if locations:
        affected_devices = get_managed_device_uuids(locations=locations)
    else:
        # If no location is specified, we can't determine affected devices for prefixes
        affected_devices = []

    if affected_devices:
        logger.info(
            "Identified %s affected managed devices for prefix update %s",
            len(affected_devices),
            prefix_network,
        )
        try:
            # Build custom commit message for prefix
            user = extract_user(data)
            event = data["event"]
            model = data["model"]
            timestamp = data["@timestamp"]
            commit_message = (
                f"Triggered from nb {model} {event} on {prefix_network} by {user} at {timestamp}"
            )

            for device_uuid in affected_devices:
                try:
                    await queue_render(
                        device_uuid=device_uuid,
                        commit_message=commit_message,
                        user=user,
                        timestamp=timestamp,
                    )
                except DeviceNotEnabledError:
                    logger.info(
                        "Device %s is not enabled for configuration renders, skipping",
                        device_uuid,
                    )
        except Exception:
            logger.exception("Error queuing render jobs for prefix update %s", prefix_network)
        logger.info(
            "Queued %s render jobs for prefix update %s",
            len(affected_devices),
            prefix_network,
        )
    else:
        logger.info("No affected managed devices found for prefix update %s", prefix_network)


async def ipaddress(data: dict[str, Any]) -> None:
    """ipam.ipaddress event handler."""
    if data["event"] == "delete":
        # Cannot load devices from a non-existent IP address
        return

    ip_uuid = data["record"]["id"]
    ip_address = data["record"].get("address", "unknown")
    affected_devices = get_managed_device_uuids_for_ipaddress(ip_uuid)

    if affected_devices:
        logger.info(
            "Identified %s affected managed devices for IP address update %s",
            len(affected_devices),
            ip_address,
        )
        try:
            # Build custom commit message for IP address
            user = extract_user(data)
            event = data["event"]
            model = data["model"]
            timestamp = data["@timestamp"]
            commit_message = (
                f"Triggered from nb {model} {event} on {ip_address} by {user} at {timestamp}"
            )

            for device_uuid in affected_devices:
                try:
                    await queue_render(
                        device_uuid=device_uuid,
                        commit_message=commit_message,
                        user=user,
                        timestamp=timestamp,
                    )
                except DeviceNotEnabledError:
                    logger.info(
                        "Device %s is not enabled for configuration renders, skipping",
                        device_uuid,
                    )
        except Exception:
            logger.exception("Error queuing render jobs for IP address update %s", ip_address)
        logger.info(
            "Queued %s render jobs for IP address update %s",
            len(affected_devices),
            ip_address,
        )
    else:
        logger.info("No affected managed devices found for IP address update %s", ip_address)
