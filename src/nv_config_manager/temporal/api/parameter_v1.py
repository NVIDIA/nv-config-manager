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
"""Parameter Routes for populating Workflow UI Forms."""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from temporalio.exceptions import ApplicationError

from nv_config_manager.common.log import LogCategory, get_logger
from nv_config_manager.temporal.client.nautobot import OVERLAYS_PLUGIN_BASE, NautobotClient
from nv_config_manager.temporal.common.mixins.device import NetworkDeviceData, Platform
from nv_config_manager.temporal.ngc.activities.diagnostics import get_available_commands

logger = get_logger(__name__, category=LogCategory.TEMPORAL_API)


class Device(BaseModel):
    """Device data for dropdown population."""

    id: str
    name: str
    platform: str | None = None


class Location(BaseModel):
    """Site data for dropdown population."""

    id: str
    name: str


class Secret(BaseModel):
    """Secret data for dropdown population."""

    name: str
    description: str | None = None


router = APIRouter(prefix="/parameter", tags=["parameters"])


@router.get("/site")
async def get_sites() -> list[Location]:
    """Return a list of NVIDIA Config Manager-managed sites."""
    client = NautobotClient()
    query = """
        query {
            locations(location_type:"Site") {
                id
                name
            }
        }
    """
    location_key = "locations"

    async with client:
        data = await client.graphql_query(query)

    return [Location(id=site["id"], name=site["name"]) for site in data["data"][location_key]]


@router.get("/location")
async def get_locations(
    location_type: Annotated[list[str] | None, Query()] = None,
) -> list[Location]:
    """Return a list of NVIDIA Config Manager-managed sites."""
    client = NautobotClient()
    query = """
        query ($location_type: [String]) {
            locations(location_type: $location_type) {
                id
                name
            }
        }
    """
    variables = {"location_type": location_type}
    async with client:
        data = await client.graphql_query(query, variables=variables)

    return [Location(id=loc["id"], name=loc["name"]) for loc in data["data"]["locations"]]


class Tenant(BaseModel):
    """Tenant data for dropdown population."""

    id: str
    name: str


class Role(BaseModel):
    """Role data for dropdown population."""

    id: str
    name: str


class Tag(BaseModel):
    """Tag data for dropdown population."""

    id: str
    name: str


class Overlay(BaseModel):
    """Overlay data for dropdown population."""

    id: str
    name: str


# Minimal managed-device query for unique tenants only
NV_CONFIG_MANAGER_DEVICES_TENANTS_QUERY = """
    query ($limit: Int!, $offset: Int!) {
        config_manager_devices(limit: $limit, offset: $offset) {
            device {
                tenant {
                    id
                    name
                }
            }
        }
    }
"""

# Minimal managed-device query for unique roles only
NV_CONFIG_MANAGER_DEVICES_ROLES_QUERY = """
    query ($limit: Int!, $offset: Int!) {
        config_manager_devices(limit: $limit, offset: $offset) {
            device {
                role {
                    id
                    name
                }
            }
        }
    }
"""


async def _get_managed_device_tenants() -> list[dict]:
    """Query managed device records and return unique tenants."""
    client = NautobotClient()
    seen: dict[str, dict] = {}
    page_size = 1000
    offset = 0

    async with client:
        while True:
            data = await client.graphql_query(
                NV_CONFIG_MANAGER_DEVICES_TENANTS_QUERY,
                variables={"limit": page_size, "offset": offset},
            )
            managed_devices = data.get("data", {}).get("config_manager_devices", [])

            if not managed_devices:
                break

            for entry in managed_devices:
                tenant = (entry.get("device") or {}).get("tenant")
                if tenant and tenant.get("name"):
                    tid = tenant.get("id") or tenant["name"]
                    seen[tid] = {"id": tid, "name": tenant["name"]}

            if len(managed_devices) < page_size:
                break
            offset += page_size

    return list(seen.values())


async def _get_managed_device_roles() -> list[dict]:
    """Query managed device records and return unique roles."""
    client = NautobotClient()
    seen: dict[str, dict] = {}
    page_size = 1000
    offset = 0

    async with client:
        while True:
            data = await client.graphql_query(
                NV_CONFIG_MANAGER_DEVICES_ROLES_QUERY,
                variables={"limit": page_size, "offset": offset},
            )
            managed_devices = data.get("data", {}).get("config_manager_devices", [])

            if not managed_devices:
                break

            for entry in managed_devices:
                role = (entry.get("device") or {}).get("role")
                if role and role.get("name"):
                    rid = role.get("id") or role["name"]
                    seen[rid] = {"id": rid, "name": role["name"]}

            if len(managed_devices) < page_size:
                break
            offset += page_size

    return list(seen.values())


@router.get("/tenant")
async def get_tenants(
    managed_only: Annotated[
        bool, Query(description="Limit to tenants with managed devices")
    ] = False,
) -> list[Tenant]:
    """Return a list of tenants. Default: all. With managed_only=true: only those with managed devices."""
    if managed_only:
        tenants = await _get_managed_device_tenants()
    else:
        client = NautobotClient()
        query = """
            query {
                tenants {
                    id
                    name
                }
            }
        """
        async with client:
            data = await client.graphql_query(query)
        tenants = [{"id": t["id"], "name": t["name"]} for t in data["data"]["tenants"]]

    return [Tenant(id=t["id"], name=t["name"]) for t in tenants]


@router.get("/role")
async def get_roles(
    managed_only: Annotated[bool, Query(description="Limit to roles with managed devices")] = False,
) -> list[Role]:
    """Return a list of roles. Default: all. With managed_only=true: only those with managed devices."""
    if managed_only:
        roles = await _get_managed_device_roles()
    else:
        client = NautobotClient()
        query = """
            query {
                roles {
                    id
                    name
                }
            }
        """
        async with client:
            data = await client.graphql_query(query)
        roles = [{"id": r["id"], "name": r["name"]} for r in data["data"]["roles"]]

    return [Role(id=r["id"], name=r["name"]) for r in roles]


@router.get("/namespace-tag")
async def get_namespace_tags(
    location: Annotated[
        str | None, Query(description="Limit to namespace tags at this location")
    ] = None,
) -> list[Tag]:
    """Return a list of tags used by Nautobot namespaces."""
    client = NautobotClient()
    query = """
        query ($location: String) {
            namespaces(location: $location) {
                tags {
                    name
                }
            }
        }
    """
    variables = {"location": location}

    try:
        async with client:
            data = await client.graphql_query(query, variables=variables)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Failed to query Nautobot namespace tags.",
        ) from exc

    namespaces = data.get("data", {}).get("namespaces") if isinstance(data, dict) else None
    if not isinstance(namespaces, list):
        raise HTTPException(
            status_code=500,
            detail="Malformed Nautobot namespace tag response.",
        )

    tag_names: set[str] = set()
    for namespace in namespaces:
        if not isinstance(namespace, dict):
            raise HTTPException(
                status_code=500,
                detail="Malformed Nautobot namespace tag response.",
            )
        tags = namespace.get("tags", [])
        if not isinstance(tags, list):
            raise HTTPException(
                status_code=500,
                detail="Malformed Nautobot namespace tag response.",
            )
        for tag in tags:
            if not isinstance(tag, dict):
                raise HTTPException(
                    status_code=500,
                    detail="Malformed Nautobot namespace tag response.",
                )
            tag_name = tag.get("name")
            if isinstance(tag_name, str) and tag_name:
                tag_names.add(tag_name)
    return [Tag(id=name, name=name) for name in sorted(tag_names)]


@router.get("/overlay")
async def get_overlays(
    location: Annotated[str | None, Query(description="Limit to overlays at this location")] = None,
    isolation_type: Annotated[
        str | None, Query(description="Limit to overlays with this isolation type")
    ] = None,
) -> list[Overlay]:
    """Return overlays, optionally filtered by location and isolation type."""
    params: dict[str, str] = {}
    if location:
        params["location"] = location
    if isolation_type:
        params["isolation_type"] = isolation_type

    client = NautobotClient()
    try:
        async with client:
            overlays = await client.get_all(
                f"{OVERLAYS_PLUGIN_BASE}/overlays/",
                params=params,
            )
    except Exception as exc:
        logger.exception("Failed to query Nautobot overlays", exc_info=exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to query Nautobot overlays.",
        ) from exc

    result: list[Overlay] = []
    for overlay in overlays:
        overlay_id = overlay.get("id")
        name = overlay.get("name")
        if not isinstance(overlay_id, str) or not isinstance(name, str):
            raise HTTPException(
                status_code=500,
                detail="Malformed Nautobot overlay response.",
            )
        result.append(Overlay(id=overlay_id, name=name))
    return sorted(result, key=lambda overlay: overlay.name)


class Status(BaseModel):
    """Status data for dropdown population."""

    id: str
    name: str


@router.get("/status")
async def get_statuses(
    content_type: Annotated[
        str | None,
        Query(description="Filter by content type (e.g. dcim.device, circuits.circuit)"),
    ] = None,
) -> list[Status]:
    """Return a list of statuses. Optional content_type filters to that object type."""
    client = NautobotClient()
    query = """
        query ($content_types: [String]) {
            statuses(content_types: $content_types) {
                id
                name
            }
        }
    """
    variables: dict[str, list[str] | None] = {"content_types": None}
    if content_type:
        variables["content_types"] = [content_type]

    async with client:
        data = await client.graphql_query(query, variables=variables)

    return [Status(id=status["id"], name=status["name"]) for status in data["data"]["statuses"]]


@router.get("/device")
async def get_devices(  # pylint: disable=R0913,R0914
    site: Annotated[list[str] | None, Query()] = None,
    status: Annotated[list[str] | None, Query()] = None,
    role: Annotated[list[str] | None, Query()] = None,
    tenant: Annotated[list[str] | None, Query()] = None,
    device_type_id: Annotated[list[str] | None, Query()] = None,
    manufacturer: Annotated[list[str] | None, Query()] = None,
    platform: Annotated[list[str] | None, Query()] = None,
    managed_only: Annotated[
        bool, Query(description="Limit to NVIDIA Config Manager-managed devices")
    ] = False,
) -> list[Device]:
    """Return a list of filtered devices."""
    client = NautobotClient()

    query = """
            query (
            $site: [String],
            $status: [String],
            $role: [String],
            $tenant: [String],
            $device_type_id: [String],
            $manufacturer: [String],
            $platform: [String],
            $managed_only: Boolean
            ) {
                devices(
                    location: $site,
                    status: $status,
                    role: $role,
                    tenant: $tenant,
                    device_type: $device_type_id,
                    manufacturer: $manufacturer,
                    platform: $platform,
                    has_primary_ip: true,
                    nv_config_manager_device_status: $managed_only
                ) {
                    id
                    name
                    platform {
                        name
                    }
                }
            }
        """

    variables: dict[str, list[str] | bool] = {}
    if site:
        variables["site"] = site
    if status:
        variables["status"] = status
    if role:
        variables["role"] = role
    if tenant:
        variables["tenant"] = tenant
    if device_type_id:
        variables["device_type_id"] = device_type_id
    if manufacturer:
        variables["manufacturer"] = manufacturer
    if platform:
        variables["platform"] = platform
    if managed_only:
        variables["managed_only"] = True

    if not variables:
        raise HTTPException(status_code=400, detail="Must apply at least one filter.")

    try:
        async with client:
            data = await client.graphql_query(query, variables)
    except ApplicationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    devices = [device for device in data["data"]["devices"] if device["name"]]

    return [
        Device(
            id=device["id"],
            name=device["name"],
            platform=NetworkDeviceData._slugify((device.get("platform") or {}).get("name") or "")
            or None,
        )
        for device in devices
    ]


class CommandEntry(BaseModel):
    """A single command in the diagnostics catalog."""

    name: str
    description: str


@router.get("/diagnostics/commands")
async def get_diagnostics_commands(
    platform: Annotated[list[str] | None, Query()] = None,
) -> list[CommandEntry]:
    """Return the diagnostics command catalog for the requested platform(s).

    Pass one or more ``?platform=<slug>`` query params (e.g. ``cumulus-linux``).
    When no platform is given, commands from all platforms are returned.
    Commands that appear on multiple platforms are deduplicated by name.
    """
    if platform:
        platforms_to_check: list[Platform] = []
        for p in platform:
            try:
                platforms_to_check.append(Platform(p))
            except ValueError:
                pass
    else:
        platforms_to_check = list(Platform)

    seen: dict[str, str] = {}
    for plat in platforms_to_check:
        for name, description in get_available_commands(plat).items():
            if name not in seen:
                seen[name] = description

    return [CommandEntry(name=name, description=desc) for name, desc in sorted(seen.items())]


@router.get("/device/{device_id}/secrets")
async def get_device_secrets(device_id: str) -> list[Secret]:
    """Return a list of secrets available in device config context.

    Args:
        device_id: The UUID of the device to fetch secrets from

    Returns:
        List of secrets found in the device's config context
    """
    client = NautobotClient()

    query = """
        query ($id: ID!) {
            device(id: $id) {
                name
                config_context
            }
        }
    """

    variables = {"id": device_id}
    async with client:
        data = await client.graphql_query(query, variables)

    device_data = data["data"]["device"]

    config_context = device_data.get("config_context", {}) or {}

    secret_versions = config_context.get("secrets_versions", {})

    secrets = []
    if isinstance(secret_versions, dict):
        for secret_name, version in secret_versions.items():
            # Format as "secret_name_version" (e.g., "tacacs_key_r1")
            formatted_name = f"{secret_name}_{version}"
            secrets.append(
                Secret(name=formatted_name, description=f"{secret_name} version {version}")
            )

    return secrets


@router.get(
    "/device/{device_id}/secret_types",
    summary="Get Secret Types for Device",
)
async def get_device_users_with_versions(device_id: str) -> list[str]:
    """Get available secret types from device config context.

    Args: device_id: The UUID of the device.

    Returns:
        List of secret types plus versions from config context.
    """
    client = NautobotClient()

    query = """
        query ($id: ID!) {
            device(id: $id) {
                name
                config_context
            }
        }
    """

    variables = {"id": device_id}
    async with client:
        data = await client.graphql_query(query, variables)

    device_data = data["data"]["device"]
    config_context = device_data.get("config_context", {}) or {}

    secrets_versions = config_context.get("secrets_versions", {})

    secret_types = []
    for secret_type, version in secrets_versions.items():
        # Return formatted name like "tacacs_key_r1"
        secret_types.append(f"{secret_type}_{version}")

    if len(secret_types) == 0:
        raise HTTPException(
            status_code=400,
            detail=f"No secrets versions defined for device {device_id}.",
        )

    return secret_types


@router.get("/device/{device_id}/password_users")
async def get_device_password_users(device_id: str) -> list[Secret]:
    """Get available password users from device config context password_mappings.

    Args:
        device_id: The UUID of the device.

    Returns:
        List of password users with their secret names from password_mappings.
    """
    client = NautobotClient()

    query = """
        query ($id: ID!) {
            device(id: $id) {
                name
                config_context
            }
        }
    """

    variables = {"id": device_id}
    async with client:
        data = await client.graphql_query(query, variables)

    device_data = data["data"]["device"]
    config_context = device_data.get("config_context", {}) or {}
    password_mappings = config_context.get("password_mappings", {})

    if not password_mappings or not isinstance(password_mappings, dict):
        raise HTTPException(
            status_code=400,
            detail=f"No password mappings defined for device {device_id}.",
        )

    users = {}
    for username, user_config in password_mappings.items():
        password_type = user_config.get("password", "")
        rotation = user_config.get("rotation", "")
        users[username] = f"{password_type}_{rotation}"

    # Convert to Secret objects - use username as the name
    secrets = []
    for username, secret_name in users.items():
        # Filtering out the nv-config-manager service account temporarily.
        if username != "svc-ngc-cfa-nv-config-manager":
            secrets.append(Secret(name=username, description=f"{username} ({secret_name})"))
    return secrets


@router.get(
    "/device-id",
    summary="Get Device ID by Name",
)
async def get_device_id_by_name(device_name: str) -> Device:
    """Convert device hostname to device ID.

    Args:
        device_name: The hostname/name of the device.

    Returns:
        Device object with id and name.

    Raises:
        HTTPException: If device not found or multiple devices match.
    """
    client = NautobotClient()

    query = """
        query ($name: [String]!) {
            devices(name: $name) {
                id
                name
            }
        }
    """

    variables = {"name": device_name}
    async with client:
        data = await client.graphql_query(query, variables)

    if "errors" in data:
        raise HTTPException(status_code=400, detail=data["errors"][0]["message"])

    devices = data["data"]["devices"]

    if not devices:
        raise HTTPException(status_code=404, detail=f"Device with name '{device_name}' not found")

    if len(devices) > 1:
        raise HTTPException(
            status_code=400,
            detail=f"Multiple devices found with name '{device_name}'. Please use device ID directly.",
        )

    device = devices[0]
    return Device(id=device["id"], name=device["name"])
