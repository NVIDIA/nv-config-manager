# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Tests for portable provider-neutral render-data cache envelopes."""

from __future__ import annotations

import pytest
from nv_config_manager_dcim import (
    DeviceRenderData,
    LocationRenderData,
    RenderData,
    RenderDeviceIdentity,
    RenderLocation,
)


def test_render_data_cache_round_trip() -> None:
    """The cache envelope preserves all provider-owned render data."""
    original = RenderData(
        device=DeviceRenderData(
            identity=RenderDeviceIdentity(
                id="device-1",
                name="leaf-1",
                platform="Cumulus Linux",
                role="Leaf",
                model="SN5600",
                location=RenderLocation(id="location-1", name="site-1", kind="Site"),
            )
        ),
        location=LocationRenderData(
            location=RenderLocation(id="location-1", name="site-1", kind="Site")
        ),
        plugin_data={"example": {"enabled": True}},
    )

    restored = RenderData.from_cache(original.to_cache())

    assert restored == original


def test_render_data_cache_rejects_unknown_schema_version() -> None:
    """A cache produced by an incompatible CLI fails with a clear error."""
    with pytest.raises(ValueError, match="schema version"):
        RenderData.from_cache({"schema_version": 99})
