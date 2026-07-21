# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Pydantic model contract tests for the provider-neutral SDK."""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ValidationError

from nv_config_manager_dcim import (
    DCIMDeviceSelection,
    DeviceMetadata,
    RenderDeviceIdentity,
    RenderLocation,
)
from nv_config_manager_dcim.render import DeviceRenderData, LocationRenderData, RenderData


def test_sdk_contract_models_are_pydantic_and_immutable() -> None:
    """Provider-neutral value contracts use Pydantic validation and immutability."""
    selection = DCIMDeviceSelection(id="device-1", name="leaf-1")
    render_data = RenderData(
        device=DeviceRenderData(
            identity=RenderDeviceIdentity(
                id="device-1",
                name="leaf-1",
                platform="Cumulus Linux",
                role="Leaf",
                model="SN5600",
                location=RenderLocation(name="site-1", kind="Site"),
            )
        ),
        location=LocationRenderData(location=RenderLocation(name="site-1", kind="Site")),
    )

    assert isinstance(selection, BaseModel)
    assert isinstance(render_data, BaseModel)
    assert render_data.model_dump() == {
        "device": {
            "identity": {
                "id": "device-1",
                "name": "leaf-1",
                "platform": "Cumulus Linux",
                "role": "Leaf",
                "model": "SN5600",
                "location": {
                    "name": "site-1",
                    "id": None,
                    "kind": "Site",
                    "tags": (),
                    "parent": None,
                },
                "tags": (),
            },
            "interfaces": (),
            "inventory": {},
            "intent": {},
        },
        "location": {
            "location": {
                "name": "site-1",
                "id": None,
                "kind": "Site",
                "tags": (),
                "parent": None,
            },
            "inventory": {},
            "intent": {},
        },
        "plugin_data": {},
    }
    with pytest.raises(ValidationError):
        selection.name = "leaf-2"


def test_device_metadata_preserves_mutable_url_and_legacy_alias() -> None:
    """Config-store enrichment can update its URL during the compatibility window."""
    metadata = DeviceMetadata(
        device_id="device-1",
        name="leaf-1",
        site="site-1",
        nautobot_url="https://dcim.example/devices/device-1",
    )

    assert isinstance(metadata, BaseModel)
    assert metadata.device_url == "https://dcim.example/devices/device-1"
    assert metadata.nautobot_url == metadata.device_url
    assert "nautobot_url" not in metadata.to_dict()

    metadata.nautobot_url = "https://dcim.example/devices/device-1/updated"

    assert metadata.device_url == "https://dcim.example/devices/device-1/updated"
