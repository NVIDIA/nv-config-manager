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
"""Nautobot activities for InfiniBand overlay management."""

from __future__ import annotations

import logging
import re
from typing import Any

from pydantic import BaseModel, field_validator
from temporalio import activity
from temporalio.exceptions import ApplicationError

from nv_config_manager.temporal.client.nautobot import NautobotClient
from nv_config_manager.temporal.common.mixins.stage import StageOutput

log = logging.getLogger(__name__)

PLUGIN_BASE = "plugins/overlays"
ISOLATION_TYPE_IB_PKEY = "ib_pkey"
DEFAULT_STATUS_NAME = "Active"

DEFAULT_MEMBERSHIP_TYPE = "full"
_VALID_MEMBERSHIP_TYPES = frozenset({"full", "limited"})

_IPV4_PATTERN = re.compile(r"^\d{1,3}(\.\d{1,3}){3}$")
_PKEY_PATTERN = re.compile(r"^0[xX][0-9a-fA-F]{1,4}$")


def normalize_membership_type(membership_type: object) -> str:
    """Normalize membership to 'full'/'limited'.

    None or a blank string defaults to 'full'; any other type or value raises ValueError.
    """
    if membership_type is None:
        return DEFAULT_MEMBERSHIP_TYPE
    if not isinstance(membership_type, str):
        raise ValueError("membership_type must be 'full' or 'limited'")
    normalized = membership_type.strip().lower()
    if not normalized:
        return DEFAULT_MEMBERSHIP_TYPE
    if normalized not in _VALID_MEMBERSHIP_TYPES:
        raise ValueError("membership_type must be 'full' or 'limited'")
    return normalized


def _normalize_membership_override(value: object) -> str | None:
    """Normalize an optional per-port membership override; blank/None stays None."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("membership must be 'full' or 'limited'")
    if not value.strip():
        return None
    return normalize_membership_type(value)


class CreatePartitionInNautobotInput(BaseModel):
    """Parameters for recording an IB overlay partition in Nautobot."""

    pkey: str
    partition_name: str | None = None
    location_name: str
    tenant_name: str | None = None
    membership_type: str = "full"


class CreatePartitionInNautobotOutput(StageOutput):
    """Nautobot IDs for the created or reused overlay and PKey objects."""

    partition_id: str
    partition_name: str
    pkey_id: str
    pkey: str


@activity.defn
async def create_partition_in_nautobot(
    input: CreatePartitionInNautobotInput,
) -> CreatePartitionInNautobotOutput:
    """Create an Overlay and InfiniBandPKey record in Nautobot."""
    partition_name = input.partition_name or f"ib-pkey-{input.pkey}"

    client = NautobotClient()
    async with client:
        location = await _lookup_by_name(client, "dcim/locations/", input.location_name, "Location")
        location_id: str = location["id"]

        tenant_id: str | None = None
        if input.tenant_name:
            tenant = await _lookup_by_name(client, "tenancy/tenants/", input.tenant_name, "Tenant")
            tenant_id = tenant["id"]

        status_id = await _resolve_status_id(client)

        existing_overlay = await _find_existing_overlay(client, partition_name, location_id)
        if existing_overlay:
            partition_id: str = existing_overlay["id"]
            log.info("Overlay '%s' already exists (%s), reusing", partition_name, partition_id)
        else:
            overlay_payload: dict[str, Any] = {
                "name": partition_name,
                "location": location_id,
                "isolation_type": ISOLATION_TYPE_IB_PKEY,
                "status": status_id,
            }
            if tenant_id:
                overlay_payload["tenant"] = tenant_id
            log.info("Creating Overlay '%s' in Nautobot", partition_name)
            overlay = await client.post(f"{PLUGIN_BASE}/overlays/", data=overlay_payload)
            partition_id = overlay["id"]

        existing_pkey = await _find_existing_pkey(client, input.pkey, partition_id)
        if existing_pkey:
            pkey_id: str = existing_pkey["id"]
            log.info("InfiniBandPKey '%s' already exists (%s), reusing", input.pkey, pkey_id)
        else:
            pkey_payload: dict[str, Any] = {
                "pkey": input.pkey,
                "name": f"PKey-{input.pkey}",
                "overlay": partition_id,
                "membership_type": input.membership_type,
                "status": status_id,
            }
            if tenant_id:
                pkey_payload["tenant"] = tenant_id
            log.info("Creating InfiniBandPKey %s in Nautobot", input.pkey)
            pkey_record = await client.post(f"{PLUGIN_BASE}/pkeys/", data=pkey_payload)
            pkey_id = pkey_record["id"]

    return CreatePartitionInNautobotOutput(
        partition_id=partition_id,
        partition_name=partition_name,
        pkey_id=pkey_id,
        pkey=input.pkey,
        display=f"Partition '{partition_name}' and PKey {input.pkey} recorded in Nautobot",
    )


class RecordIBPKeyInNautobotInput(BaseModel):
    """Parameters for recording an InfiniBandPKey in Nautobot."""

    pkey: str


class RecordIBPKeyInNautobotOutput(StageOutput):
    """Nautobot ID for the created or reused InfiniBandPKey."""

    pkey_id: str
    pkey: str


class InterfaceRef(BaseModel):
    """A device/interface name pair used to look up an interface in Nautobot.

    ``membership`` is an optional per-port override ("full"/"limited"); when unset
    the caller's workflow-level default is applied.
    """

    device: str
    interface: str
    membership: str | None = None

    @field_validator("membership", mode="before")
    @classmethod
    def _normalize_membership(cls, v: object) -> str | None:
        return _normalize_membership_override(v)


class ResolvedInterface(BaseModel):
    """An interface that has been resolved to its Nautobot UUID and IB GUID.

    ``membership`` is the effective membership for this port (per-port override
    if supplied, otherwise the workflow default).
    """

    device: str
    interface: str
    interface_id: str
    guid: str
    membership: str = DEFAULT_MEMBERSHIP_TYPE


class ResolveInterfaceGuidsInput(BaseModel):
    """Device/interface pairs to resolve into GUIDs."""

    interfaces: list[InterfaceRef]
    default_membership: str = DEFAULT_MEMBERSHIP_TYPE


class ResolveInterfaceGuidsOutput(StageOutput):
    """Resolved interfaces with their Nautobot UUIDs and IB GUIDs."""

    resolved: list[ResolvedInterface]


class ResolveGuidsToInterfacesInput(BaseModel):
    """A list of IB GUIDs to resolve back to Nautobot interface records.

    ``guid_memberships`` is an optional per-GUID membership list index-aligned
    with ``guids``; any GUID without an entry falls back to ``default_membership``.
    """

    guids: list[str]
    default_membership: str = DEFAULT_MEMBERSHIP_TYPE
    guid_memberships: list[str] | None = None


class ResolveGuidsToInterfacesOutput(StageOutput):
    """Interfaces resolved from a list of IB GUIDs."""

    resolved: list[ResolvedInterface]


class RecordPKeyAssignmentsInput(BaseModel):
    """Parameters for creating OverlayAssignment records for a set of resolved interfaces."""

    overlay_id: str
    resolved: list[ResolvedInterface]
    membership_type: str = "full"


class RecordPKeyAssignmentsOutput(StageOutput):
    """IDs of the created or reused OverlayAssignment records."""

    assignment_ids: list[str]


class RemovePKeyAssignmentsInput(BaseModel):
    """Parameters for deleting OverlayAssignment records by interface."""

    overlay_id: str
    interface_ids: list[str]


class RemovePKeyAssignmentsOutput(StageOutput):
    """IDs of the deleted OverlayAssignment records."""

    assignment_ids_removed: list[str]
    interface_ids_not_assigned: list[str]


async def _lookup_by_name(
    client: NautobotClient,
    path: str,
    name: str,
    entity_label: str,
) -> dict[str, Any]:
    """Look up a single Nautobot object by name, raising on not-found."""
    results = await client.get(path, params={"name": name})
    items = results.get("results", [])
    if not items:
        raise ApplicationError(
            f"{entity_label} '{name}' not found in Nautobot",
            non_retryable=True,
        )
    result: dict[str, Any] = items[0]
    return result


async def _resolve_status_id(client: NautobotClient) -> str:
    """Resolve the UUID of the 'Active' status."""
    status = await _lookup_by_name(client, "extras/statuses/", DEFAULT_STATUS_NAME, "Status")
    status_id: str = status["id"]
    return status_id


async def _find_existing_overlay(
    client: NautobotClient,
    name: str,
    location_id: str,
) -> dict[str, Any] | None:
    """Return an existing Overlay if one matches name + location."""
    results = await client.get(
        f"{PLUGIN_BASE}/overlays/",
        params={"name": name, "location": location_id},
    )
    items = results.get("results", [])
    return items[0] if items else None


async def _find_existing_pkey(
    client: NautobotClient,
    pkey: str,
    overlay_id: str,
) -> dict[str, Any] | None:
    """Return an existing InfiniBandPKey if one matches pkey + overlay."""
    results = await client.get(
        f"{PLUGIN_BASE}/pkeys/",
        params={"pkey": pkey, "overlay": overlay_id},
    )
    items = results.get("results", [])
    return items[0] if items else None


async def _find_orphan_pkey(
    client: NautobotClient,
    pkey: str,
) -> dict[str, Any] | None:
    """Return an existing InfiniBandPKey with this pkey value and no overlay."""
    results = await client.get(
        f"{PLUGIN_BASE}/pkeys/",
        params={"pkey": pkey},
    )
    items = [item for item in results.get("results", []) if item.get("overlay") is None]
    if len(items) > 1:
        details = ", ".join(
            f"id={item.get('id', '<missing>')}, name={item.get('name', '<missing>')}"
            for item in items
        )
        raise ApplicationError(
            f"Multiple orphan InfiniBandPKey rows found for {pkey}: {details}",
            non_retryable=True,
        )
    return items[0] if items else None


@activity.defn
async def record_ib_pkey_in_nautobot(
    input: RecordIBPKeyInNautobotInput,
) -> RecordIBPKeyInNautobotOutput:
    """Record an InfiniBandPKey in Nautobot."""
    name = f"PKey-{input.pkey}"

    client = NautobotClient()
    async with client:
        existing = await _find_orphan_pkey(client, input.pkey)
        if existing:
            pkey_id: str = existing["id"]
            log.info(
                "InfiniBandPKey %s already recorded (id=%s, no overlay), reusing",
                input.pkey,
                pkey_id,
            )
        else:
            status_id = await _resolve_status_id(client)
            payload: dict[str, Any] = {
                "name": name,
                "pkey": input.pkey,
                "status": status_id,
            }
            log.info("Creating InfiniBandPKey %s in Nautobot", input.pkey)
            record = await client.post(f"{PLUGIN_BASE}/pkeys/", data=payload)
            pkey_id = record["id"]

    return RecordIBPKeyInNautobotOutput(
        pkey_id=pkey_id,
        pkey=input.pkey,
        display=f"PKey {input.pkey} recorded in Nautobot (id={pkey_id})",
    )


class CurrentAssignment(BaseModel):
    """A single OverlayAssignment record from Nautobot."""

    assignment_id: str
    interface_id: str
    guid: str
    membership_type: str = DEFAULT_MEMBERSHIP_TYPE


class FetchPKeyAssignmentsInput(BaseModel):
    """Overlay ID whose assignments should be fetched."""

    overlay_id: str


class FetchPKeyAssignmentsOutput(StageOutput):
    """Current OverlayAssignment records for the given overlay."""

    assignments: list[CurrentAssignment]


class SyncPKeyAssignmentsInput(BaseModel):
    """Desired state for a PKey overlay's member list."""

    overlay_id: str
    desired: list[ResolvedInterface]
    membership_type: str = "full"


class SyncPKeyAssignmentsOutput(StageOutput):
    """Counts of assignments added, removed, and left unchanged during sync."""

    added: list[str]
    removed: list[str]
    unchanged: list[str]


async def _find_existing_assignment(
    client: NautobotClient,
    overlay_id: str,
    interface_id: str,
) -> dict[str, Any] | None:
    """Return an existing OverlayAssignment for this overlay + interface, if any."""
    results = await client.get(
        f"{PLUGIN_BASE}/overlay-assignments/",
        params={"overlay": overlay_id, "assigned_object_id": interface_id},
    )
    items = results.get("results", [])
    return items[0] if items else None


@activity.defn
async def resolve_interface_guids(
    input: ResolveInterfaceGuidsInput,
) -> ResolveInterfaceGuidsOutput:
    """Resolve Nautobot interface records to their IB GUIDs."""
    resolved: list[ResolvedInterface] = []

    client = NautobotClient()
    async with client:
        for ref in input.interfaces:
            results = await client.get(
                "dcim/interfaces/",
                params={"device": ref.device, "name": ref.interface},
            )
            items = results.get("results", [])

            if not items:
                raise ApplicationError(
                    f"Interface '{ref.interface}' on device '{ref.device}' not found in Nautobot",
                    non_retryable=True,
                )

            iface = items[0]
            guid = (iface.get("custom_fields") or {}).get("ib_guid") or ""

            if not guid:
                raise ApplicationError(
                    f"Interface '{ref.interface}' on device '{ref.device}' "
                    "has no IB GUID (cf_ib_guid) set in Nautobot",
                    non_retryable=True,
                )

            resolved.append(
                ResolvedInterface(
                    device=ref.device,
                    interface=ref.interface,
                    interface_id=iface["id"],
                    guid=guid,
                    membership=ref.membership or input.default_membership,
                )
            )
            log.info(
                "Resolved %s/%s → GUID %s (id=%s)",
                ref.device,
                ref.interface,
                guid,
                iface["id"],
            )

    return ResolveInterfaceGuidsOutput(
        resolved=resolved,
        display=f"Resolved {len(resolved)} interface GUID(s) from Nautobot",
    )


_RESOLVE_GUIDS_QUERY = """
query ($guids: [String]) {
  interfaces(cf_ib_guid__ie: $guids) {
    id
    name
    cf_ib_guid
    device {
      name
    }
  }
}
"""


def _normalize_ib_guid(guid: str) -> str:
    """Normalize an IB GUID for matching: trim, drop an optional ``0x`` prefix, lowercase.

    UFM and Nautobot store port GUIDs as bare hex (e.g. ``946dae0300598000``),
    but users commonly enter the ``0x``-prefixed form. Normalizing both sides
    lets either representation resolve.
    """
    normalized = (guid or "").strip().lower()
    if normalized.startswith("0x"):
        normalized = normalized[2:]
    return normalized


def _index_resolved_interfaces(
    interfaces: list[dict[str, Any]],
    default_membership: str,
    membership_by_guid: dict[str, str] | None = None,
) -> dict[str, ResolvedInterface]:
    """Group GraphQL interface results by normalized GUID.

    Skips entries with no ``cf_ib_guid`` set. Raises ``ApplicationError`` if
    any GUID has more than one matching interface. Each match takes its per-GUID
    membership from ``membership_by_guid`` (keyed by normalized GUID), falling
    back to ``default_membership``.
    """
    membership_by_guid = membership_by_guid or {}
    grouped: dict[str, list[ResolvedInterface]] = {}
    for iface in interfaces:
        original_guid = iface.get("cf_ib_guid") or ""
        guid_key = _normalize_ib_guid(original_guid)
        if not guid_key:
            continue
        device = (iface.get("device") or {}).get("name") or ""
        grouped.setdefault(guid_key, []).append(
            ResolvedInterface(
                device=device,
                interface=iface.get("name") or "",
                interface_id=iface.get("id") or "",
                guid=original_guid,
                membership=membership_by_guid.get(guid_key, default_membership),
            )
        )

    duplicates = {
        g: [r.interface_id for r in matches] for g, matches in grouped.items() if len(matches) > 1
    }
    if duplicates:
        raise ApplicationError(
            f"GUID(s) matched multiple Nautobot interfaces: {duplicates}",
            non_retryable=True,
        )
    return {g: matches[0] for g, matches in grouped.items()}


@activity.defn
async def resolve_guids_to_interfaces(
    input: ResolveGuidsToInterfacesInput,
) -> ResolveGuidsToInterfacesOutput:
    """Reverse-lookup IB GUIDs to Nautobot interface records.

    Each input GUID must map to exactly one Nautobot interface (via the
    ``cf_ib_guid`` custom field). Missing or duplicate matches raise a
    non-retryable error so the caller can surface the problem directly.
    """
    if not input.guids:
        return ResolveGuidsToInterfacesOutput(
            resolved=[],
            display="No GUIDs to resolve",
        )

    deduped = sorted({_normalize_ib_guid(g) for g in input.guids if _normalize_ib_guid(g)})
    if not deduped:
        raise ApplicationError("All provided GUIDs were empty", non_retryable=True)

    membership_by_guid: dict[str, str] = {}
    if input.guid_memberships is not None:
        if len(input.guid_memberships) != len(input.guids):
            raise ApplicationError(
                f"guid_memberships length ({len(input.guid_memberships)}) must match "
                f"guids length ({len(input.guids)})",
                non_retryable=True,
            )
        for guid, membership in zip(input.guids, input.guid_memberships, strict=True):
            key = _normalize_ib_guid(guid)
            if key:
                membership_by_guid[key] = membership

    client = NautobotClient()
    async with client:
        data = await client.graphql_query(
            _RESOLVE_GUIDS_QUERY,
            {"guids": deduped},
        )

    interfaces = ((data.get("data") or {}).get("interfaces")) or []
    by_guid = _index_resolved_interfaces(
        interfaces, input.default_membership, membership_by_guid
    )

    missing = [g for g in deduped if g not in by_guid]
    if missing:
        raise ApplicationError(
            f"No Nautobot interface found for GUID(s): {missing}",
            non_retryable=True,
        )

    resolved = [by_guid[g] for g in deduped]
    for r in resolved:
        log.info(
            "Resolved GUID %s → %s/%s (id=%s)",
            r.guid,
            r.device,
            r.interface,
            r.interface_id,
        )

    return ResolveGuidsToInterfacesOutput(
        resolved=resolved,
        display=f"Resolved {len(resolved)} GUID(s) to Nautobot interface(s)",
    )


@activity.defn
async def record_pkey_assignments(
    input: RecordPKeyAssignmentsInput,
) -> RecordPKeyAssignmentsOutput:
    """Create OverlayAssignment records in Nautobot for each resolved interface."""

    assignment_ids: list[str] = []

    client = NautobotClient()
    async with client:
        status_id = await _resolve_status_id(client)

        for resolved in input.resolved:
            existing = await _find_existing_assignment(
                client, input.overlay_id, resolved.interface_id
            )
            if existing:
                log.info(
                    "OverlayAssignment for %s/%s already exists (%s), reusing",
                    resolved.device,
                    resolved.interface,
                    existing["id"],
                )
                assignment_ids.append(existing["id"])
                continue

            payload: dict[str, Any] = {
                "overlay": input.overlay_id,
                "assigned_object_type": "dcim.interface",
                "assigned_object_id": resolved.interface_id,
                "guid": resolved.guid,
                "membership_type": resolved.membership or input.membership_type,
                "status": status_id,
            }

            log.info(
                "Creating OverlayAssignment for %s/%s (guid=%s, membership=%s)",
                resolved.device,
                resolved.interface,
                resolved.guid,
                payload["membership_type"],
            )
            assignment = await client.post(f"{PLUGIN_BASE}/overlay-assignments/", data=payload)
            assignment_ids.append(assignment["id"])

    return RecordPKeyAssignmentsOutput(
        assignment_ids=assignment_ids,
        display=(f"Recorded {len(assignment_ids)} OverlayAssignment(s) in Nautobot"),
    )


@activity.defn
async def remove_pkey_assignments(
    input: RemovePKeyAssignmentsInput,
) -> RemovePKeyAssignmentsOutput:
    """Delete OverlayAssignment records for the given overlay + interface IDs."""

    removed: list[str] = []
    not_assigned: list[str] = []

    client = NautobotClient()
    async with client:
        for interface_id in input.interface_ids:
            existing = await _find_existing_assignment(client, input.overlay_id, interface_id)
            if not existing:
                log.info(
                    "No OverlayAssignment for overlay=%s interface=%s, nothing to delete",
                    input.overlay_id,
                    interface_id,
                )
                not_assigned.append(interface_id)
                continue

            assignment_id = existing["id"]
            log.info(
                "Deleting OverlayAssignment %s (interface=%s)",
                assignment_id,
                interface_id,
            )
            await client.delete(f"{PLUGIN_BASE}/overlay-assignments/{assignment_id}/")
            removed.append(assignment_id)

    return RemovePKeyAssignmentsOutput(
        assignment_ids_removed=removed,
        interface_ids_not_assigned=not_assigned,
        display=(
            f"Removed {len(removed)} OverlayAssignment(s); "
            f"{len(not_assigned)} interface(s) had no assignment"
        ),
    )


def _is_auto_created_overlay_name(overlay_name: str, pkey: str) -> bool:
    """True when the overlay matches the member-add auto-created naming scheme.

    Auto-created overlays are named ``ib-pkey-overlay-<pkey>`` and exist solely as
    a container for one PKey with no members, so the delete workflow owns their lifecycle.
    Operator- or VPC-owned overlays use other names and are left untouched.
    """
    return overlay_name == f"ib-pkey-overlay-{pkey}"


class CleanupEmptyPartitionInput(BaseModel):
    """Parameters for reconciling Nautobot after a PKey partition empties out."""

    overlay_id: str
    overlay_name: str
    pkey_id: str
    pkey: str


class CleanupEmptyPartitionOutput(StageOutput):
    """Result of the post-removal Nautobot reconciliation."""

    partition_empty: bool
    pkey_deleted: bool
    overlay_deleted: bool


@activity.defn
async def cleanup_empty_pkey_partition(
    input: CleanupEmptyPartitionInput,
) -> CleanupEmptyPartitionOutput:
    """Delete the Nautobot InfiniBandPKey and auto-created Overlay once empty.

    UFM auto-removes a PKey partition when its last member leaves.
    After assignments are removed, this reconciles Nautobot.
    If the overlay was auto-created and has no other PKeys, it is also deleted.
    """
    client = NautobotClient()
    async with client:
        assignments = await client.get(
            f"{PLUGIN_BASE}/overlay-assignments/",
            params={"overlay": input.overlay_id},
        )
        remaining = assignments.get("results", [])
        if remaining:
            return CleanupEmptyPartitionOutput(
                partition_empty=False,
                pkey_deleted=False,
                overlay_deleted=False,
                display=(
                    f"Overlay {input.overlay_id} still has {len(remaining)} member(s); "
                    "leaving PKey and Overlay in place"
                ),
            )

        log.info(
            "PKey partition %s (overlay=%s) is empty; deleting stale InfiniBandPKey %s",
            input.pkey,
            input.overlay_id,
            input.pkey_id,
        )
        await client.delete(f"{PLUGIN_BASE}/pkeys/{input.pkey_id}/")

        overlay_deleted = await _delete_overlay_if_auto_created(client, input)

        deleted = "InfiniBandPKey + Overlay" if overlay_deleted else "InfiniBandPKey"
        return CleanupEmptyPartitionOutput(
            partition_empty=True,
            pkey_deleted=True,
            overlay_deleted=overlay_deleted,
            display=f"Empty PKey partition reconciled; deleted {deleted}",
        )


async def _delete_overlay_if_auto_created(
    client: NautobotClient, input: CleanupEmptyPartitionInput
) -> bool:
    """Delete the overlay when it is auto-created and holds no remaining PKeys."""
    if not _is_auto_created_overlay_name(input.overlay_name, input.pkey):
        return False

    pkeys = await client.get(
        f"{PLUGIN_BASE}/pkeys/",
        params={"overlay": input.overlay_id},
    )
    remaining_pkeys = pkeys.get("results", [])
    if remaining_pkeys:
        log.info(
            "Auto-created overlay %s still has %d PKey(s); keeping overlay",
            input.overlay_name,
            len(remaining_pkeys),
        )
        return False

    log.info(
        "Deleting auto-created empty overlay %s (id=%s)",
        input.overlay_name,
        input.overlay_id,
    )
    await client.delete(f"{PLUGIN_BASE}/overlays/{input.overlay_id}/")
    return True


@activity.defn
async def fetch_pkey_assignments(
    input: FetchPKeyAssignmentsInput,
) -> FetchPKeyAssignmentsOutput:
    """Fetch current OverlayAssignment records for a PKey overlay from Nautobot."""
    client = NautobotClient()
    assignments: list[CurrentAssignment] = []

    async with client:
        results = await client.get(
            f"{PLUGIN_BASE}/overlay-assignments/",
            params={"overlay": input.overlay_id},
        )
        for item in results.get("results", []):
            assignments.append(
                CurrentAssignment(
                    assignment_id=item["id"],
                    interface_id=item.get("assigned_object_id", ""),
                    guid=item.get("guid", ""),
                    membership_type=normalize_membership_type(item.get("membership_type")),
                )
            )

    log.info(
        "Found %d existing OverlayAssignment(s) for overlay %s",
        len(assignments),
        input.overlay_id,
    )

    return FetchPKeyAssignmentsOutput(
        assignments=assignments,
        display=f"Found {len(assignments)} existing assignment(s) for overlay {input.overlay_id}",
    )


@activity.defn
async def sync_pkey_assignments(
    input: SyncPKeyAssignmentsInput,
) -> SyncPKeyAssignmentsOutput:
    """Reconcile Nautobot OverlayAssignment records to match the desired member list."""

    desired_by_iface: dict[str, ResolvedInterface] = {r.interface_id: r for r in input.desired}

    client = NautobotClient()
    added: list[str] = []
    removed: list[str] = []
    unchanged: list[str] = []

    async with client:
        status_id = await _resolve_status_id(client)

        current_results = await client.get(
            f"{PLUGIN_BASE}/overlay-assignments/",
            params={"overlay": input.overlay_id},
        )
        current_items: list[dict[str, Any]] = current_results.get("results", [])
        current_by_iface: dict[str, dict[str, Any]] = {
            item["assigned_object_id"]: item for item in current_items
        }

        for iface_id, item in current_by_iface.items():
            assignment_id = item["id"]
            if iface_id not in desired_by_iface:
                log.info(
                    "Removing stale OverlayAssignment %s (interface %s)",
                    assignment_id,
                    iface_id,
                )
                await client.delete(f"{PLUGIN_BASE}/overlay-assignments/{assignment_id}/")
                removed.append(assignment_id)
                continue

            unchanged.append(assignment_id)
            desired_membership = desired_by_iface[iface_id].membership or input.membership_type
            current_membership = normalize_membership_type(item.get("membership_type"))
            if desired_membership != current_membership:
                log.info(
                    "Updating OverlayAssignment %s membership %s -> %s",
                    assignment_id,
                    current_membership,
                    desired_membership,
                )
                await client.patch(
                    f"{PLUGIN_BASE}/overlay-assignments/{assignment_id}/",
                    data={"membership_type": desired_membership},
                )

        for iface_id, resolved in desired_by_iface.items():
            if iface_id not in current_by_iface:
                payload: dict[str, Any] = {
                    "overlay": input.overlay_id,
                    "assigned_object_type": "dcim.interface",
                    "assigned_object_id": iface_id,
                    "guid": resolved.guid,
                    "membership_type": resolved.membership or input.membership_type,
                    "status": status_id,
                }
                log.info(
                    "Creating OverlayAssignment for %s/%s (guid=%s, membership=%s)",
                    resolved.device,
                    resolved.interface,
                    resolved.guid,
                    payload["membership_type"],
                )
                new_assignment = await client.post(
                    f"{PLUGIN_BASE}/overlay-assignments/", data=payload
                )
                added.append(new_assignment["id"])

    log.info(
        "OverlayAssignment sync complete: +%d added, -%d removed, %d unchanged",
        len(added),
        len(removed),
        len(unchanged),
    )

    return SyncPKeyAssignmentsOutput(
        added=added,
        removed=removed,
        unchanged=unchanged,
        display=(
            f"Nautobot assignments synced: "
            f"+{len(added)} added, -{len(removed)} removed, {len(unchanged)} unchanged"
        ),
    )


# ---------------------------------------------------------------------------
# IB context resolver
#
# Lets clients call ib_pkey_member_{add,delete,update} with just (host, pkey)
# and have the workflow derive the location and overlay from Nautobot.
# ---------------------------------------------------------------------------


class ResolveIBSiteForHostInput(BaseModel):
    """Inputs for resolving the Site for a UFM host."""

    host: str


class ResolveIBSiteForHostOutput(StageOutput):
    """UFM device + Site context for an IB PKey operation."""

    ufm_device_id: str
    ufm_device_name: str
    ufm_device_primary_ip: str | None
    location_id: str
    location_name: str


class ResolveIBContextInput(BaseModel):
    """Inputs for resolving the Nautobot context of an IB PKey operation."""

    host: str
    pkey: str


class ResolveIBContextOutput(StageOutput):
    """UFM device, Site, and overlay context for an IB PKey operation."""

    ufm_device_id: str
    ufm_device_name: str
    ufm_device_primary_ip: str | None
    location_id: str
    location_name: str
    overlay_id: str
    overlay_name: str
    pkey_id: str
    pkey: str


SITE_LOCATION_TYPE_NAME = "Site"

_RESOLVE_BY_NAME_QUERY = """
query ($host: [String]) {
  devices(name: $host) {
    id
    name
    primary_ip4 { host }
    tenant { id name }
    location {
      id
      name
      location_type { name }
      overlays(isolation_type: ["ib_pkey"]) {
        id
        name
        pkeys {
          id
          pkey
        }
      }
      parent {
        id
        name
        location_type { name }
        overlays(isolation_type: ["ib_pkey"]) {
          id
          name
          pkeys {
            id
            pkey
          }
        }
        parent {
          id
          name
          location_type { name }
          overlays(isolation_type: ["ib_pkey"]) {
            id
            name
            pkeys {
              id
              pkey
            }
          }
        }
      }
    }
  }
}
"""

_RESOLVE_BY_IP_QUERY = """
query ($ip: [String]) {
  ip_addresses(address: $ip) {
    address
    interfaces {
      device {
        id
        name
        primary_ip4 { host }
        tenant { id name }
        location {
          id
          name
          location_type { name }
          overlays(isolation_type: ["ib_pkey"]) {
            id
            name
            pkeys {
              id
              pkey
            }
          }
          parent {
            id
            name
            location_type { name }
            overlays(isolation_type: ["ib_pkey"]) {
              id
              name
              pkeys {
                id
                pkey
              }
            }
            parent {
              id
              name
              location_type { name }
              overlays(isolation_type: ["ib_pkey"]) {
                id
                name
                pkeys {
                  id
                  pkey
                }
              }
            }
          }
        }
      }
    }
  }
}
"""


def _normalize_pkey(value: str) -> str:
    """Canonicalize an IB PKey to '0x' + 4 lowercase hex digits."""
    if not value or not _PKEY_PATTERN.match(value):
        raise ApplicationError(
            f"pkey {value!r} does not match required format (e.g. '0x8001')",
            non_retryable=True,
        )
    return f"0x{int(value, 16):04x}"


async def _find_device_by_name(client: NautobotClient, host: str) -> list[dict[str, Any]]:
    """Query Nautobot for devices with the given name."""
    data = await client.graphql_query(_RESOLVE_BY_NAME_QUERY, {"host": [host]})
    return ((data.get("data") or {}).get("devices")) or []


async def _find_device_by_ip(client: NautobotClient, host: str) -> list[dict[str, Any]]:
    """Query Nautobot for devices reachable via the given IPv4 address."""
    data = await client.graphql_query(_RESOLVE_BY_IP_QUERY, {"ip": [host]})
    devices: list[dict[str, Any]] = []
    for ip_record in ((data.get("data") or {}).get("ip_addresses")) or []:
        for iface in ip_record.get("interfaces") or []:
            if device := iface.get("device"):
                devices.append(device)
    return devices


async def _find_device(client: NautobotClient, host: str) -> dict[str, Any]:
    """Resolve a UFM device by name OR primary IPv4 address."""
    if _IPV4_PATTERN.match(host):
        devices = await _find_device_by_ip(client, host)
        attempted = "IPv4 address"
    else:
        devices = await _find_device_by_name(client, host)
        attempted = "name"

    if not devices:
        raise ApplicationError(
            f"UFM device {host!r} not found in Nautobot (tried as {attempted})",
            non_retryable=True,
        )

    by_id = {d["id"]: d for d in devices}
    if len(by_id) > 1:
        raise ApplicationError(
            f"Multiple UFM devices match {host!r}: {sorted(by_id.keys())}",
            non_retryable=True,
        )
    return next(iter(by_id.values()))


def _walk_location_chain(location: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Return [location, parent, grandparent, ...] until parent is missing."""
    chain: list[dict[str, Any]] = []
    current = location
    while current:
        chain.append(current)
        current = current.get("parent")
    return chain


def _find_site_in_chain(chain: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the first Site-typed location in the chain, or None."""
    for location in chain:
        if (location.get("location_type") or {}).get("name") == SITE_LOCATION_TYPE_NAME:
            return location
    return None


def _iter_pkey_matches(
    chain: list[dict[str, Any]], canonical_pkey: str
) -> list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]]:
    """Collect every (location, overlay, pkey_record) triple in the chain matching canonical_pkey."""
    matches: list[tuple[dict[str, Any], dict[str, Any], dict[str, Any]]] = []
    for location in chain:
        for overlay in location.get("overlays") or []:
            for pkey_record in overlay.get("pkeys") or []:
                stored = pkey_record.get("pkey") or ""
                if not _PKEY_PATTERN.match(stored):
                    continue
                if f"0x{int(stored, 16):04x}" == canonical_pkey:
                    matches.append((location, overlay, pkey_record))
    return matches


def _select_pkey_match(
    device: dict[str, Any], canonical_pkey: str
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Select the (location, overlay, pkey_record) triple matching canonical_pkey."""
    device_location = device.get("location") or {}
    chain = _walk_location_chain(device_location)
    matches = _iter_pkey_matches(chain, canonical_pkey)

    device_loc_name = device_location.get("name") or "<unknown>"
    if not matches:
        raise ApplicationError(
            f"PKey {canonical_pkey!r} not found at or above location {device_loc_name!r}",
            non_retryable=True,
        )
    if len(matches) > 1:
        candidates = ", ".join(
            f"{loc.get('name', '<unnamed>')}/{ovl.get('name', '<unnamed>')}"
            for loc, ovl, _ in matches
        )
        raise ApplicationError(
            f"PKey {canonical_pkey!r} ambiguous near location {device_loc_name!r}: "
            f"matches [{candidates}]. Resolve the duplicate PKey/Overlay "
            f"entries in Nautobot before retrying.",
            non_retryable=True,
        )
    return matches[0]


@activity.defn
async def resolve_ib_site_for_host(
    input: ResolveIBSiteForHostInput,
) -> ResolveIBSiteForHostOutput:
    """Resolve the Site for a UFM host. Allows site specific UFM credentials."""

    client = NautobotClient()
    async with client:
        device = await _find_device(client, input.host)

    chain = _walk_location_chain(device.get("location") or {})
    site = _find_site_in_chain(chain)
    if site is None:
        chain_repr = " -> ".join(
            f"{loc.get('name', '?')}:{(loc.get('location_type') or {}).get('name', '?')}"
            for loc in chain
        )
        raise ApplicationError(
            f"No {SITE_LOCATION_TYPE_NAME}-typed location in hierarchy for device "
            f"{device.get('name')!r}: {chain_repr}",
            non_retryable=True,
        )

    primary_ip = (device.get("primary_ip4") or {}).get("host")

    log.info(
        "Resolved IB site for host=%s -> device=%s device_location=%s site=%s",
        input.host,
        device.get("name"),
        (device.get("location") or {}).get("name"),
        site.get("name"),
    )

    return ResolveIBSiteForHostOutput(
        ufm_device_id=device["id"],
        ufm_device_name=device["name"],
        ufm_device_primary_ip=primary_ip,
        location_id=site["id"],
        location_name=site["name"],
        display=f"Resolved {input.host} -> site {site.get('name')}",
    )


@activity.defn
async def resolve_ib_context(
    input: ResolveIBContextInput,
) -> ResolveIBContextOutput:
    """Resolve UFM device, location, overlay, and PKey records from (host, pkey)."""
    canonical_pkey = _normalize_pkey(input.pkey)

    client = NautobotClient()
    async with client:
        device = await _find_device(client, input.host)

    overlay_location, overlay, pkey_record = _select_pkey_match(device, canonical_pkey)

    chain = _walk_location_chain(device.get("location") or {})
    site = _find_site_in_chain(chain)
    if site is None:
        chain_repr = " -> ".join(
            f"{loc.get('name', '?')}:{(loc.get('location_type') or {}).get('name', '?')}"
            for loc in chain
        )
        raise ApplicationError(
            f"No {SITE_LOCATION_TYPE_NAME}-typed location in hierarchy for device "
            f"{device.get('name')!r}: {chain_repr}",
            non_retryable=True,
        )

    primary_ip = (device.get("primary_ip4") or {}).get("host")

    log.info(
        "Resolved IB context for host=%s pkey=%s -> device=%s "
        "device_location=%s site=%s overlay_location=%s overlay=%s",
        input.host,
        canonical_pkey,
        device.get("name"),
        (device.get("location") or {}).get("name"),
        site.get("name"),
        overlay_location.get("name"),
        overlay.get("name"),
    )

    return ResolveIBContextOutput(
        ufm_device_id=device["id"],
        ufm_device_name=device["name"],
        ufm_device_primary_ip=primary_ip,
        location_id=site["id"],
        location_name=site["name"],
        overlay_id=overlay["id"],
        overlay_name=overlay["name"],
        pkey_id=pkey_record["id"],
        pkey=canonical_pkey,
        display=f"Resolved {input.host}+{canonical_pkey} -> overlay {overlay.get('name')}",
    )


async def _create_overlay_for_orphan_pkey(
    client: NautobotClient,
    *,
    pkey_value: str,
    orphan_pkey_id: str,
    location_id: str,
    location_name: str,
    tenant_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create an Overlay at the given location and link the orphan PKey to it."""
    overlay_name = f"ib-pkey-overlay-{pkey_value}"

    overlay = await _find_existing_overlay(client, overlay_name, location_id)
    if overlay:
        log.info(
            "Reusing existing Overlay '%s' (id=%s) at location %s for orphan PKey %s",
            overlay_name,
            overlay["id"],
            location_name,
            pkey_value,
        )
    else:
        status_id = await _resolve_status_id(client)
        payload: dict[str, Any] = {
            "name": overlay_name,
            "location": location_id,
            "tenant": tenant_id,
            "isolation_type": ISOLATION_TYPE_IB_PKEY,
            "status": status_id,
            "description": f"Auto-created for orphan PKey {pkey_value} during member-add",
        }
        log.info(
            "Creating Overlay '%s' at location %s for orphan PKey %s",
            overlay_name,
            location_name,
            pkey_value,
        )
        overlay = await client.post(f"{PLUGIN_BASE}/overlays/", data=payload)

    pkey_record = await client.get(f"{PLUGIN_BASE}/pkeys/{orphan_pkey_id}/")
    raw_overlay = pkey_record.get("overlay")
    current_overlay_id = raw_overlay["id"] if isinstance(raw_overlay, dict) else raw_overlay

    if current_overlay_id is None:
        log.info(
            "Linking orphan PKey %s (id=%s) to Overlay %s",
            pkey_value,
            orphan_pkey_id,
            overlay["id"],
        )
        pkey_record = await client.patch(
            f"{PLUGIN_BASE}/pkeys/{orphan_pkey_id}/",
            data={"overlay": overlay["id"]},
        )
    elif current_overlay_id != overlay["id"]:
        raise ApplicationError(
            f"PKey {pkey_value!r} (id={orphan_pkey_id}) is already linked to "
            f"Overlay {current_overlay_id!r}; refusing to relink to "
            f"{overlay['id']!r}. Unlink the PKey from the other Overlay or "
            f"use a different PKey value.",
            non_retryable=True,
        )

    return overlay, pkey_record


@activity.defn
async def resolve_ib_context_for_add(
    input: ResolveIBContextInput,
) -> ResolveIBContextOutput:
    """Resolve UFM/site/overlay/pkey for member-add with lazy Overlay creation."""
    canonical_pkey = _normalize_pkey(input.pkey)

    client = NautobotClient()
    async with client:
        device = await _find_device(client, input.host)

        device_location = device.get("location") or {}
        chain = _walk_location_chain(device_location)
        site = _find_site_in_chain(chain)
        if site is None:
            chain_repr = " -> ".join(
                f"{loc.get('name', '?')}:{(loc.get('location_type') or {}).get('name', '?')}"
                for loc in chain
            )
            raise ApplicationError(
                f"No {SITE_LOCATION_TYPE_NAME}-typed location in hierarchy for device "
                f"{device.get('name')!r}: {chain_repr}",
                non_retryable=True,
            )

        matches = _iter_pkey_matches(chain, canonical_pkey)
        device_loc_name = device_location.get("name") or "<unknown>"
        if len(matches) > 1:
            candidates = ", ".join(
                f"{loc.get('name', '<unnamed>')}/{ovl.get('name', '<unnamed>')}"
                for loc, ovl, _ in matches
            )
            raise ApplicationError(
                f"PKey {canonical_pkey!r} ambiguous near location {device_loc_name!r}: "
                f"matches [{candidates}]. Resolve the duplicate PKey/Overlay "
                f"entries in Nautobot before retrying.",
                non_retryable=True,
            )

        if matches:
            overlay_location, overlay, pkey_record = matches[0]
        else:
            orphan = await _find_orphan_pkey(client, canonical_pkey)
            if orphan is None:
                raise ApplicationError(
                    f"PKey {canonical_pkey!r} not found in Nautobot. Run the IB "
                    f"PKey Creation workflow first to register the partition.",
                    non_retryable=True,
                )

            tenant = device.get("tenant") or {}
            tenant_id = tenant.get("id")
            if not tenant_id:
                raise ApplicationError(
                    f"Device {device.get('name')!r} has no Tenant set; cannot "
                    f"auto-create Overlay for orphan PKey {canonical_pkey}. "
                    f"Set Tenant on the device or pre-create an Overlay and "
                    f"link PKey {canonical_pkey} to it.",
                    non_retryable=True,
                )

            overlay, pkey_record = await _create_overlay_for_orphan_pkey(
                client,
                pkey_value=canonical_pkey,
                orphan_pkey_id=orphan["id"],
                location_id=device_location["id"],
                location_name=device_loc_name,
                tenant_id=tenant_id,
            )
            overlay_location = device_location

    primary_ip = (device.get("primary_ip4") or {}).get("host")

    log.info(
        "Resolved IB context (with lazy-create) for host=%s pkey=%s -> "
        "device=%s device_location=%s site=%s overlay_location=%s overlay=%s",
        input.host,
        canonical_pkey,
        device.get("name"),
        device_location.get("name"),
        site.get("name"),
        overlay_location.get("name"),
        overlay.get("name"),
    )

    return ResolveIBContextOutput(
        ufm_device_id=device["id"],
        ufm_device_name=device["name"],
        ufm_device_primary_ip=primary_ip,
        location_id=site["id"],
        location_name=site["name"],
        overlay_id=overlay["id"],
        overlay_name=overlay["name"],
        pkey_id=pkey_record["id"],
        pkey=canonical_pkey,
        display=f"Resolved {input.host}+{canonical_pkey} -> overlay {overlay.get('name')}",
    )
