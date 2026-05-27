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
"""NB NATS nautobot_bgp_models.* Event Handlers."""

from typing import Any

from nv_config_manager.common.log import LogCategory, get_logger
from nv_config_manager.render.events.util import (
    DeviceNotEnabledError,
    build_commit_message,
    extract_user,
    get_managed_device_uuid_for_bgp_routing_instance,
    get_managed_device_uuids_for_autonomous_system,
    get_managed_device_uuids_for_bgp_peering,
    queue_render,
)

logger = get_logger(__name__, category=LogCategory.RENDER_EVENT)


async def autonomoussystem(data: dict[str, Any]) -> None:
    """nautobot_bgp_models.autonomoussystem event handler."""
    if data["event"] == "delete":
        # Cannot load devices from a non-existent Autonomous System
        return

    asn = data["record"]["asn"]
    affected_devices = get_managed_device_uuids_for_autonomous_system(asn)

    if affected_devices:
        logger.info(
            "Identified %s affected managed devices for Autonomous System update %s",
            len(affected_devices),
            asn,
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
            logger.exception("Error queuing render jobs for Autonomous System update %s", asn)
        logger.info(
            "Queued %s render jobs for Autonomous System update %s",
            len(affected_devices),
            asn,
        )
    else:
        logger.info("No affected managed devices found for Autonomous System update %s", asn)


async def peering(data: dict[str, Any]) -> None:
    """nautobot_bgp_models.peering event handler."""
    if data["event"] == "delete":
        # Cannot load devices from a non-existent BGP Peering
        return

    peering_id = data["record"]["id"]
    peering_name = data["record"].get("name", peering_id)
    affected_devices = get_managed_device_uuids_for_bgp_peering(peering_id)

    if affected_devices:
        logger.info(
            "Identified %s affected managed devices for BGP Peering update %s",
            len(affected_devices),
            peering_name,
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
            logger.exception("Error queuing render jobs for BGP Peering update %s", peering_name)
        logger.info(
            "Queued %s render jobs for BGP Peering update %s",
            len(affected_devices),
            peering_name,
        )
    else:
        logger.info("No affected managed devices found for BGP Peering update %s", peering_name)


async def peergroup(data: dict[str, Any]) -> None:
    """nautobot_bgp_models.peergroup event handler."""
    peer_group_id = data["record"]["id"]
    peer_group_name = data["record"].get("name", peer_group_id)
    routing_instance_id = data["record"]["routing_instance"]["id"]
    device_uuid = get_managed_device_uuid_for_bgp_routing_instance(routing_instance_id)

    if device_uuid:
        logger.info(
            "Identified affected managed device for BGP Peer Group update %s: %s",
            peer_group_name,
            device_uuid,
        )
        await queue_render(
            device_uuid=device_uuid,
            commit_message=build_commit_message(data),
            user=extract_user(data),
            timestamp=data["@timestamp"],
        )
    else:
        logger.info(
            "No affected managed device found for BGP Peer Group update %s",
            peer_group_name,
        )


async def bgproutinginstance(data: dict[str, Any]) -> None:
    """nautobot_bgp_models.bgproutinginstance event handler."""
    device_uuid = data["record"]["device"]["id"]
    await queue_render(
        device_uuid=device_uuid,
        commit_message=build_commit_message(data),
        user=extract_user(data),
        timestamp=data["@timestamp"],
    )


async def peerendpoint(data: dict[str, Any]) -> None:
    """nautobot_bgp_models.peerendpoint event handler."""
    peer_endpoint_id = data["record"]["id"]
    peer_endpoint_name = data["record"].get("name", peer_endpoint_id)
    routing_instance_id = data["record"]["routing_instance"]["id"]
    device_uuid = get_managed_device_uuid_for_bgp_routing_instance(routing_instance_id)

    if device_uuid:
        logger.info(
            "Identified affected managed device for BGP Peer Endpoint update %s: %s",
            peer_endpoint_name,
            device_uuid,
        )
        await queue_render(
            device_uuid=device_uuid,
            commit_message=build_commit_message(data),
            user=extract_user(data),
            timestamp=data["@timestamp"],
        )
    else:
        logger.info(
            "No affected managed device found for BGP Peer Endpoint update %s",
            peer_endpoint_name,
        )
