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
"""Utility methods for parsing NB NATS messages."""

from __future__ import annotations

import asyncio
import inspect
import json
import logging
from typing import TYPE_CHECKING, Any, cast

import nats.js

from nv_config_manager.common.config import (
    LogCategory,
    NATSConnectionManager,
    get_logger,
    is_aggregate_environment,
    is_local_environment,
    nats_config_manager_api_prefix,
    nats_connection,
    nats_render_change_config,
    pynautobot_client,
    redis_client,
)
from nv_config_manager.render.events.exceptions import EventParseError
from nv_config_manager.render.exceptions import NautobotException

if TYPE_CHECKING:
    from typing import Any

    from nv_config_manager.common.client import RedisClient


class DeviceNotEnabledError(Exception):
    """To be raised if a device is not enabled for NVIDIA Config Manager."""


# How long a device stays deduped while its render is queued but not yet
# processed. This has to cover worst-case queue latency: a change to one shared
# Nautobot object fans out to every attached device, so if the flag expires
# before the render runs, the next change re-publishes the same device and the
# queue amplifies by one copy per change.
QUEUED_FLAG_TTL_SECONDS = 3600


def _get_queue_redis_client() -> RedisClient | None:
    """Create a Redis client for queue operations."""
    if is_local_environment():
        return None

    return redis_client(db_key="lock_db")


async def _close_queue_redis_client(client: RedisClient | None) -> None:
    """Close a queue Redis client if one was created for this operation."""
    if client is None:
        return
    close = getattr(client, "close", None)
    if close is None:
        return
    result = close()
    if inspect.isawaitable(result):
        await result


async def mark_queued(device_uuid: str, client: RedisClient | None = None) -> None:
    """Mark a device as queued for rendering."""
    owned_client = client is None
    client = client or _get_queue_redis_client()
    if client is None:
        # Local environment, skip Redis operations
        return

    try:
        queue_key = f"{device_uuid}_queued"
        await client.setex(queue_key, QUEUED_FLAG_TTL_SECONDS, 1, serialize=False)
    finally:
        if owned_client:
            await _close_queue_redis_client(client)


async def claim_queued(device_uuid: str, client: RedisClient | None = None) -> bool:
    """Atomically claim the render queue slot for a device.

    Returns True when the caller won the claim and should publish, False when a
    render is already queued. Separate ``exists`` and ``setex`` calls let
    concurrent producers both observe an unset flag and both publish, so the
    check and the set have to happen in one ``SET NX EX``.
    """
    owned_client = client is None
    client = client or _get_queue_redis_client()
    if client is None:
        # Local environment, never dedup
        return True

    try:
        queue_key = f"{device_uuid}_queued"
        claimed = await client.redis.set(queue_key, b"1", ex=QUEUED_FLAG_TTL_SECONDS, nx=True)
        return bool(claimed)
    finally:
        if owned_client:
            await _close_queue_redis_client(client)


async def is_queued(device_uuid: str, client: RedisClient | None = None) -> bool:
    """Check if a device is already queued for rendering."""
    owned_client = client is None
    client = client or _get_queue_redis_client()
    if client is None:
        # Local environment, never consider as queued
        return False

    try:
        queue_key = f"{device_uuid}_queued"
        return await client.exists(queue_key)
    finally:
        if owned_client:
            await _close_queue_redis_client(client)


async def clear_queued(device_uuid: str, client: RedisClient | None = None) -> None:
    """Clear the queued flag for a device."""
    owned_client = client is None
    client = client or _get_queue_redis_client()
    if client is None:
        # Local environment, skip Redis operations
        return

    try:
        queue_key = f"{device_uuid}_queued"
        await client.delete(queue_key)
    finally:
        if owned_client:
            await _close_queue_redis_client(client)


def should_run(device_uuid: str) -> bool:
    """Return true if device is enabled for rendering."""
    nb = pynautobot_client()
    try:
        device = nb.plugins.nv_config_manager.configmanagerdevicestatus.get(device_uuid)
        if device is None:
            return False
    except Exception as exc:
        raise NautobotException(f"Failed to query {device_uuid} in nautobot: {exc}") from exc

    # mypy lacks context that the render_enabled field is a bool
    if not bool(device.render_enabled):
        return False

    env_aggregate_managed = is_aggregate_environment()
    device_aggregate_managed = bool(device.is_aggregate_managed)

    return env_aggregate_managed == device_aggregate_managed


def extract_user(data: dict[str, Any]) -> str:
    """Extract the user responsible for the change."""
    try:
        user: str = data["request"]["user"]
        return user
    except KeyError as err:
        raise EventParseError("Failed to extract metadata from request.") from err


def build_commit_message(data: dict[str, Any]) -> str:
    """Build a commit message from the event metadata."""
    try:
        user = data["request"]["user"]
        event = data["event"]
        model = data["model"]
        timestamp = data["@timestamp"]
        name = data["record"].get("name")
        if name:
            return f"Triggered from nb {model} {event} on {name} by {user} at {timestamp}"
        return f"Triggered from nb {model} {event} by {user} at {timestamp}"
    except KeyError as err:
        raise EventParseError("Failed to extract metadata from request.") from err


async def _process_single_device_enqueue(
    device_uuid: str,
    commit_message: str,
    user: str,
    timestamp: str,
    jetstream: nats.js.JetStreamContext,
    logger: logging.Logger | logging.LoggerAdapter,
    queue_client: RedisClient | None,
) -> dict[str, str] | None:
    """
    Process a single device render operation.

    Args:
        device_uuid: Device UUID to process
        commit_message: Commit message for the render
        user: User initiating the render
        timestamp: Timestamp for the render
        jetstream: NATS JetStream instance to use for publishing
        logger: Logger instance

    Returns:
        None if successful, dict with error details if failed
    """
    try:
        # Claim before the Nautobot lookup so that concurrent producers collapse
        # to a single publish per device rather than one publish per change.
        if not await claim_queued(device_uuid, queue_client):
            logger.info(
                "Device %s already has a pending render, skipping duplicate queue request",
                device_uuid,
            )
            return None

        # Check if device should run (this hits Nautobot API)
        if not should_run(device_uuid):
            await clear_queued(device_uuid, queue_client)
            return {
                "device_uuid": device_uuid,
                "error": f"{device_uuid} is not enabled for configuration renders.",
            }

        # Publish message using provided jetstream connection
        message = {
            "device_id": device_uuid,
            "commit_message": commit_message,
            "user": user,
            "@timestamp": timestamp,
        }

        stream, subject = nats_render_change_config()
        await jetstream.publish(
            subject=subject,
            payload=json.dumps(message).encode("utf-8"),
            stream=stream,
        )

        logger.debug(f"Successfully queued device {device_uuid}")
        return None  # Success case

    except Exception as exc:
        # Clear the queued flag if we set it but publishing failed
        await clear_queued(device_uuid, queue_client)
        error_msg = str(exc)
        logger.warning(f"Failed to queue device {device_uuid}: {error_msg}")
        return {"device_uuid": device_uuid, "error": error_msg}


async def queue_render(device_uuid: str, commit_message: str, user: str, timestamp: str) -> None:
    """Queue a device render via NATS."""
    logger = get_logger(__name__, category=LogCategory.RENDER_EVENT)

    # Try to use shared connection first, fallback to creating new one
    connection_manager = NATSConnectionManager()
    nats_conn = connection_manager.get_connection()

    if nats_conn is None or nats_conn.is_closed:
        # Fallback to creating a new connection if no shared connection available
        logger.info("No shared NATS connection available, creating new one")
        nats_conn = await nats_connection()
        should_close = True
    else:
        should_close = False

    try:
        jetstream = nats_conn.jetstream(prefix=nats_config_manager_api_prefix())
        queue_client = _get_queue_redis_client()

        # Use the shared processing function
        try:
            result = await _process_single_device_enqueue(
                device_uuid,
                commit_message,
                user,
                timestamp,
                jetstream,
                logger,
                queue_client,
            )
        finally:
            await _close_queue_redis_client(queue_client)

        if result is not None:
            # There was an error
            error_msg = result["error"]
            if "not enabled for configuration renders" in error_msg:
                raise DeviceNotEnabledError(error_msg)
            else:
                raise Exception(error_msg)

        # Log successful publishing for backward compatibility
        logger.info("Published message for device %s to NATS stream", device_uuid)

    finally:
        # Only close if we created the connection ourselves
        if should_close:
            await nats_conn.close()


async def queue_render_batch(
    device_uuids: list[str],
    commit_message: str,
    user: str,
    timestamp: str,
    max_concurrency: int = 20,
) -> tuple[int, list[dict[str, str]]]:
    """
    Queue renders for multiple devices in parallel with controlled concurrency.

    Args:
        device_uuids: List of device UUIDs to queue renders for
        commit_message: Commit message for all renders
        user: User initiating the renders
        timestamp: Timestamp for all renders
        max_concurrency: Maximum number of concurrent operations

    Returns:
        Tuple of (queued_count, failed_devices)
    """

    logger = get_logger(__name__, category=LogCategory.RENDER_EVENT)
    logger.info(
        f"Starting batch queue operation for {len(device_uuids)} devices with max concurrency {max_concurrency}"
    )

    # Pre-establish connections for reuse
    nats_conn = None
    nats_should_close = False

    try:
        # Set up shared NATS connection
        connection_manager = NATSConnectionManager()
        nats_conn = connection_manager.get_connection()

        if nats_conn is None or nats_conn.is_closed:
            logger.info("Establishing shared NATS connection for batch operation")
            nats_conn = await nats_connection()
            connection_manager.set_connection(nats_conn)
            nats_should_close = True

        # Pre-warm Nautobot connection (it's already shared via singleton)
        pynautobot_client()

        jetstream = nats_conn.jetstream(prefix=nats_config_manager_api_prefix())
        queue_client = _get_queue_redis_client()

        # Create semaphore to limit concurrency across all devices
        semaphore = asyncio.Semaphore(max_concurrency)

        async def process_single_device(device_uuid: str) -> dict[str, str] | None:
            """Process a single device with concurrency control."""
            async with semaphore:
                return await _process_single_device_enqueue(
                    device_uuid,
                    commit_message,
                    user,
                    timestamp,
                    jetstream,
                    logger,
                    queue_client,
                )

        try:
            # Process all devices concurrently with controlled concurrency
            tasks = [process_single_device(device_uuid) for device_uuid in device_uuids]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        finally:
            await _close_queue_redis_client(queue_client)

        failed_devices = []

        for result in results:
            if isinstance(result, Exception):
                # This shouldn't happen due to our exception handling, but just in case
                failed_devices.append({"device_uuid": "unknown", "error": str(result)})
            elif isinstance(result, dict):
                # Failed device (result is dict[str, str])
                failed_devices.append(result)
            # If result is None, it was successful - no action needed

        queued_count = len(device_uuids) - len(failed_devices)
        logger.info(
            f"Batch operation completed: {queued_count} queued, {len(failed_devices)} failed"
        )
        return queued_count, failed_devices

    finally:
        # Clean up NATS connection if we created it
        if nats_should_close and nats_conn and not nats_conn.is_closed:
            connection_manager.clear_connection()
            await nats_conn.close()


def get_managed_device_uuids(
    **filter_kwargs: Any,
) -> list[str]:
    """Load managed device UUIDs from nautobot based on filters."""
    nb = pynautobot_client()
    try:
        query = """
query(
  $names: [String],
  $locations: [String],
  $roles: [String],
  $device_types: [String],
  $platforms: [String],
  $tenant_groups: [String],
  $tenants: [String],
  $device_redundancy_groups: [String],
  $tags: [String]
) {
  devices(
    name: $names,
    location: $locations,
    role: $roles,
    device_type: $device_types,
    platform: $platforms,
    tenant_group: $tenant_groups,
    tenant: $tenants,
    device_redundancy_group: $device_redundancy_groups,
    tags: $tags,
    nv_config_manager_device_status: true
  ) {
    id
    configmanagerdevicestatus {
      render_enabled
    }
  }
}
"""
        rsp = nb.graphql.query(query, filter_kwargs)
        devices = rsp.json["data"]["devices"]
        return [
            device["id"]
            for device in devices
            if device["configmanagerdevicestatus"]
            and device["configmanagerdevicestatus"]["render_enabled"]
        ]
    except Exception as exc:
        raise NautobotException(
            f"Failed to query devices with filter {filter_kwargs}: {exc}"
        ) from exc


def get_module_bay(uuid: str) -> dict[str, Any]:
    """Load module-bays from nautobot based on filters."""
    nb = pynautobot_client()
    try:
        module_bay = nb.dcim.module_bays.get(id=uuid)
        return dict(module_bay)
    except Exception as exc:
        raise NautobotException(f"Failed to query module-bay with id {uuid}: {exc}") from exc


def get_managed_device_uuids_for_vrf(
    vrf_id: str,
) -> list[str]:
    """Load managed device UUIDs affected by VRF changes."""
    nb = pynautobot_client()
    try:
        query = """
        query ($vrf_id: ID) {
            vrf(id: $vrf_id) {
                devices{
                    id
                    configmanagerdevicestatus{
                        render_enabled
                    }
                }
            }
        }
        """
        variables = {"vrf_id": vrf_id}
        rsp = nb.graphql.query(query, variables)
        devices = rsp.json["data"]["vrf"]["devices"]
        return [
            device["id"]
            for device in devices
            if device["configmanagerdevicestatus"]
            and device["configmanagerdevicestatus"]["render_enabled"]
        ]
    except Exception as exc:
        raise NautobotException(f"Failed to query devices for VRF changes: {exc}") from exc


def get_managed_device_uuids_for_ipaddress(ip_address_id: str) -> list[str]:
    """Load managed device UUIDs affected by IPAM changes."""
    nb = pynautobot_client()
    try:
        query = """
        query($ip_address_id: ID) {
          ip_address(id: $ip_address_id) {
            interfaces {
              device {
                id
                configmanagerdevicestatus {
                  render_enabled
                }
              }
            }
          }
        }
        """

        variables = {"ip_address_id": ip_address_id}

        rsp = nb.graphql.query(query, variables)
        ip_address = rsp.json["data"]["ip_address"]

        # Collect unique device IDs that are render enabled
        affected_devices = set()
        for interface in ip_address["interfaces"]:
            device = interface["device"]
            if (
                device
                and device["configmanagerdevicestatus"]
                and device["configmanagerdevicestatus"]["render_enabled"]
            ):
                affected_devices.add(device["id"])

        return list(affected_devices)

    except Exception as exc:
        raise NautobotException(f"Failed to query devices for IPAM changes: {exc}") from exc


def get_managed_device_uuids_for_autonomous_system(asn: str) -> list[str]:
    """Load managed device UUIDs affected by Autonomous System changes."""
    nb = pynautobot_client()
    try:
        query = """
        query($as_id: [String]) {
          bgp_routing_instances(autonomous_system: $as_id) {
            device {
              id
              configmanagerdevicestatus {
                render_enabled
              }
            }
          }
        }
        """
        variables = {"as_id": [asn]}

        rsp = nb.graphql.query(query, variables)
        routing_instances = rsp.json["data"]["bgp_routing_instances"]

        affected_devices = set()
        for instance in routing_instances:
            if instance.get("device"):
                device = instance["device"]
                if (
                    device
                    and device["configmanagerdevicestatus"]
                    and device["configmanagerdevicestatus"]["render_enabled"]
                ):
                    affected_devices.add(device["id"])

        return list(affected_devices)

    except Exception as exc:
        raise NautobotException(
            f"Failed to query devices for Autonomous System {asn} changes: {exc}"
        ) from exc


def get_managed_device_uuids_for_bgp_peering(peering_id: str) -> list[str]:
    """Load managed device UUIDs affected by BGP Peering changes."""
    nb = pynautobot_client()
    try:
        query = """
        query($peering_id: ID) {
          bgp_peering(id: $peering_id) {
            endpoints {
              routing_instance {
                device {
                  id
                  configmanagerdevicestatus {
                    render_enabled
                  }
                }
              }
            }
          }
        }
        """
        variables = {"peering_id": peering_id}

        rsp = nb.graphql.query(query, variables)
        peering = rsp.json["data"]["bgp_peering"]

        affected_devices = set()
        if peering and peering.get("endpoints"):
            for endpoint in peering["endpoints"]:
                if endpoint.get("routing_instance") and endpoint["routing_instance"].get("device"):
                    device = endpoint["routing_instance"]["device"]
                    if (
                        device
                        and device["configmanagerdevicestatus"]
                        and device["configmanagerdevicestatus"]["render_enabled"]
                    ):
                        affected_devices.add(device["id"])

        return list(affected_devices)

    except Exception as exc:
        raise NautobotException(
            f"Failed to query devices for BGP Peering {peering_id} changes: {exc}"
        ) from exc


def get_managed_device_uuid_for_bgp_routing_instance(
    routing_instance_id: str,
) -> str | None:
    """Load managed device UUID affected by BGP Peer Group changes."""
    nb = pynautobot_client()
    try:
        query = """
query ($routing_instance_id: ID) {
  bgp_routing_instance(id: $routing_instance_id) {
    device {
      id
      configmanagerdevicestatus {
        render_enabled
      }
    }
  }
}
        """
        variables = {"routing_instance_id": routing_instance_id}

        rsp = nb.graphql.query(query, variables)
        routing_instance = rsp.json["data"]["bgp_routing_instance"]

        if routing_instance and routing_instance.get("device"):
            device = routing_instance["device"]
            if (
                device
                and device["configmanagerdevicestatus"]
                and device["configmanagerdevicestatus"]["render_enabled"]
            ):
                return cast(str, device["id"])

        return None

    except Exception as exc:
        raise NautobotException(
            f"Failed to query device for BGP Routing Instance {routing_instance_id} changes: {exc}"
        ) from exc
