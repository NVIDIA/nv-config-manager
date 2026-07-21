# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Nautobot GraphQL-to-SDK render-data mapping.

This module is the only render path that understands the bundled Nautobot
queries.  The public SDK receives normalized Pydantic models, so a different
provider can use REST, GraphQL, or another data source without reproducing
this response shape.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from nv_config_manager_dcim.errors import DCIMInvalidDataError
from nv_config_manager_dcim.render import (
    DeviceRenderData,
    LocationRenderData,
    RenderData,
    RenderDeviceIdentity,
    RenderLocation,
)


def _mapping(value: object, description: str) -> Mapping[str, Any]:
    """Return one required Nautobot mapping with an SDK-level error."""
    if not isinstance(value, Mapping):
        raise DCIMInvalidDataError(f"Nautobot returned invalid {description} render data")
    return value


def _location(value: Mapping[str, Any]) -> RenderLocation:
    """Normalize one Nautobot location and its parent hierarchy."""
    location_type = value.get("location_type")
    parent = value.get("parent")
    try:
        return RenderLocation(
            id=str(value["id"]) if value.get("id") is not None else None,
            name=str(value["name"]),
            kind=str(location_type["name"])
            if isinstance(location_type, Mapping) and location_type.get("name") is not None
            else None,
            tags=tuple(
                str(tag["name"])
                for tag in value.get("tags", [])
                if isinstance(tag, Mapping) and tag.get("name") is not None
            ),
            parent=_location(_mapping(parent, "location parent"))
            if isinstance(parent, Mapping)
            else None,
        )
    except KeyError as exc:
        raise DCIMInvalidDataError("Nautobot returned an incomplete location hierarchy") from exc


def build_render_data(
    device_response: Mapping[str, Any], location_response: Mapping[str, Any]
) -> RenderData:
    """Map the two Nautobot render queries into the provider-neutral contract."""
    payload = _mapping(device_response.get("data"), "device")
    device = _mapping(payload.get("device"), "device")
    platform = _mapping(device.get("platform"), "device platform")
    role = _mapping(device.get("role"), "device role")
    device_type = _mapping(device.get("device_type"), "device type")
    location = _mapping(device.get("location"), "device location")
    tags = device.get("tags", [])
    interfaces = device.get("interfaces", [])
    if not isinstance(tags, list) or not all(isinstance(tag, Mapping) for tag in tags):
        raise DCIMInvalidDataError("Nautobot returned invalid device tags")
    if not isinstance(interfaces, list) or not all(
        isinstance(item, Mapping) for item in interfaces
    ):
        raise DCIMInvalidDataError("Nautobot returned invalid device interfaces")

    standard_keys = {
        "id",
        "name",
        "platform",
        "role",
        "device_type",
        "location",
        "tags",
        "interfaces",
        "config_context",
    }
    device_inventory = {
        key: _normalize_value(item) for key, item in payload.items() if key != "device"
    }
    device_inventory.update(
        {key: _normalize_value(item) for key, item in device.items() if key not in standard_keys}
    )
    config_context = device.get("config_context", {})
    location_payload = _mapping(location_response.get("data"), "location")
    locations = location_payload.get("locations", [])
    if not isinstance(locations, list) or not locations or not isinstance(locations[0], Mapping):
        raise DCIMInvalidDataError("Nautobot returned incomplete render location data")
    location_record = _mapping(locations[0], "location")
    site = _site_location(_location(location))
    location_tags = tuple(
        str(tag["name"])
        for tag in location_record.get("tags", [])
        if isinstance(tag, Mapping) and tag.get("name") is not None
    )
    if location_tags:
        site = site.model_copy(update={"tags": location_tags})

    return RenderData(
        device=DeviceRenderData(
            identity=RenderDeviceIdentity(
                id=str(device["id"]),
                name=str(device["name"]),
                platform=str(platform["name"]),
                role=str(role["name"]),
                model=str(device_type["model"]),
                location=_location(location),
                tags=tuple(str(tag["name"]) for tag in tags),
            ),
            interfaces=tuple(_normalize_value(item) for item in interfaces),
            inventory=device_inventory,
            intent=_normalize_value(_mapping(config_context, "device configuration intent")),
        ),
        location=LocationRenderData(
            location=site,
            inventory=_normalize_value(location_payload),
            intent=_location_intent(location_record),
        ),
    )


def _site_location(location: RenderLocation) -> RenderLocation:
    """Return the site ancestor required by site-level template filters."""
    current: RenderLocation | None = location
    while current is not None:
        if current.kind == "Site":
            return current
        current = current.parent
    raise DCIMInvalidDataError("Nautobot device location has no Site ancestor")


def _location_intent(location: Mapping[str, Any]) -> dict[str, Any]:
    """Combine Nautobot location config contexts into normalized intent data."""
    intent: dict[str, Any] = {}
    contexts = location.get("config_contexts", [])
    if not isinstance(contexts, list):
        return intent
    for context in contexts:
        if not isinstance(context, Mapping):
            continue
        data = context.get("data")
        if isinstance(data, Mapping):
            intent.update(_normalize_value(data))
    return intent


def _normalize_value(value: Any) -> Any:
    """Rename Nautobot-specific configuration containers in nested render data."""
    if isinstance(value, Mapping):
        return {
            "intent" if key == "config_context" else key: _normalize_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_normalize_value(item) for item in value]
    return value
