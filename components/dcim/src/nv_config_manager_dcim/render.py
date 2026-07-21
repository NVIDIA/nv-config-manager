# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Provider-neutral models required by a template render.

The provider SDK deliberately models render *concepts*, not a source DCIM's
HTTP or GraphQL response. Providers map their native inventory and intent
records into these models before a template consumer receives them.
"""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import Field, JsonValue

from nv_config_manager_dcim.models import DCIMModel

RENDER_DATA_CACHE_SCHEMA_VERSION = 2
"""Version of the portable, provider-neutral ``RenderData`` cache envelope."""


class RenderLocation(DCIMModel):
    """One location in a device's provider-neutral location hierarchy."""

    name: str
    id: str | None = None
    kind: str | None = None
    tags: tuple[str, ...] = ()
    parent: RenderLocation | None = None


class RenderDeviceIdentity(DCIMModel):
    """Stable identity and placement values used to choose templates."""

    id: str
    name: str
    platform: str
    role: str
    model: str
    location: RenderLocation
    tags: tuple[str, ...] = ()


class DeviceRenderData(DCIMModel):
    """Normalized device data supplied to a template render.

    ``intent`` holds desired configuration values, regardless of whether a
    provider stores them in first-class fields, policy records, or custom data.
    ``inventory`` holds additional normalized inventory relationships that are
    not yet represented by a dedicated SDK model.  Both are JSON-only so they
    remain portable in a render-data cache.
    """

    identity: RenderDeviceIdentity
    interfaces: tuple[dict[str, JsonValue], ...] = ()
    inventory: Mapping[str, JsonValue] = Field(default_factory=dict)
    intent: Mapping[str, JsonValue] = Field(default_factory=dict)


class LocationRenderData(DCIMModel):
    """Normalized location data supplied to a template render."""

    location: RenderLocation
    inventory: Mapping[str, JsonValue] = Field(default_factory=dict)
    intent: Mapping[str, JsonValue] = Field(default_factory=dict)


class RenderDataRequirement(DCIMModel):
    """One named extension-data requirement declared by a template plugin."""

    parameters: Mapping[str, JsonValue] = Field(default_factory=dict)


class RenderDataRequest(DCIMModel):
    """The complete data request passed from a render consumer to a provider."""

    device_id: str
    plugin_data_requirements: Mapping[str, RenderDataRequirement] = Field(default_factory=dict)


class RenderData(DCIMModel):
    """Complete provider-owned payload required for one device render."""

    device: DeviceRenderData
    location: LocationRenderData
    plugin_data: Mapping[str, JsonValue] = Field(default_factory=dict)

    def to_cache(self) -> dict[str, JsonValue]:
        """Serialize this payload using the portable render-data cache envelope."""
        return {
            "schema_version": RENDER_DATA_CACHE_SCHEMA_VERSION,
            "device": self.device.model_dump(mode="json"),
            "location": self.location.model_dump(mode="json"),
            "plugin_data": dict(self.plugin_data),
        }

    @classmethod
    def from_cache(cls, payload: Mapping[str, JsonValue]) -> RenderData:
        """Deserialize a portable provider-neutral render-data cache envelope."""
        schema_version = payload.get("schema_version")
        if schema_version != RENDER_DATA_CACHE_SCHEMA_VERSION:
            raise ValueError(
                "Unsupported RenderData cache schema version "
                f"{schema_version!r}; expected {RENDER_DATA_CACHE_SCHEMA_VERSION}"
            )
        try:
            return cls.model_validate(
                {
                    "device": payload["device"],
                    "location": payload["location"],
                    "plugin_data": payload.get("plugin_data", {}),
                }
            )
        except (KeyError, ValueError) as exc:
            raise ValueError(f"Invalid RenderData cache: {exc}") from exc
