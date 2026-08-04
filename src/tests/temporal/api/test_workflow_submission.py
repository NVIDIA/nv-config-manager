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
"""Tests for API-only workflow reference validation and enrichment."""

from typing import Annotated
from unittest.mock import ANY, AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import BaseModel

from nv_config_manager.temporal.api.workflow_submission import resolve_workflow_references
from nv_config_manager.temporal.common.search_attributes import (
    DEVICE_ID_SEARCH_ATTRIBUTE,
    DEVICE_NAME_SEARCH_ATTRIBUTE,
    SITE_SEARCH_ATTRIBUTE,
)
from nv_config_manager.temporal.common.workflow_references import (
    DEVICE_REFERENCE,
    DeviceReference,
    DeviceReferences,
    LocationReference,
)
from nv_config_manager.temporal.ngc.workflows.cable_validation import (
    DeviceCableValidationInput,
)
from nv_config_manager.temporal.ngc.workflows.config_diff import ConfigDiffInput
from nv_config_manager.temporal.ngc.workflows.deploy import TenantDeployInput
from nv_config_manager.temporal.ngc.workflows.ib_pkey_creation import IBPKeyCreationInput
from nv_config_manager.temporal.ngc.workflows.lldp import PortLLDPInfoInput
from nv_config_manager.temporal.ngc.workflows.multi_deploy import MultiDeployInput
from nv_config_manager.temporal.ngc.workflows.spx_overlay import SpXOverlayAssignmentInput

DEVICE_ID = "910b85f8-e83c-48ad-9bbd-12b15e97a2d4"
DEVICE_ID_V5 = "7a8ca199-040a-5994-916f-c6de90cc9959"
OTHER_DEVICE_ID = "83db83ba-f626-4566-9f93-8bd0ccbe7182"
LOCATION_ID = "b6f4972a-c6ab-4be1-96ac-72f4efc4f328"


class DeviceCollectionInput(BaseModel):
    """Input containing an enriched primary device and validated related devices."""

    primary_device: DeviceReference
    related_devices: DeviceReferences


class LocationAndDeviceInput(BaseModel):
    """Input whose explicit location controls the legacy Site search attribute."""

    location_scope: LocationReference
    target_device: DeviceReference


class ConventionOnlyInput(BaseModel):
    """An unannotated conventional field name must not trigger API resolution."""

    device_id: str


class PreloadedDevice(BaseModel):
    """Minimal preloaded device used to verify cross-field consistency."""

    id: str


class DeviceAndPreloadedInput(BaseModel):
    """Input that supports trusted preloaded data outside the Workflow API."""

    device_id: DeviceReference
    device: Annotated[PreloadedDevice | None, DEVICE_REFERENCE] = None


def _client() -> MagicMock:
    client = MagicMock()
    client.__aenter__.return_value = client
    client.get = AsyncMock()
    client.get_devices = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_device_references_are_batched_and_enriched_from_same_query() -> None:
    """A single Nautobot response must provide validation and search metadata."""
    client = _client()
    client.get_devices.return_value = [
        {
            "id": DEVICE_ID,
            "name": "LEAF01",
            "role": None,
            "platform": None,
            "location": None,
        },
        {
            "id": OTHER_DEVICE_ID,
            "name": "LEAF02",
            "role": None,
            "platform": None,
            "location": None,
        },
    ]
    body = DeviceCollectionInput(
        primary_device=DEVICE_ID,
        related_devices=[DEVICE_ID, OTHER_DEVICE_ID],
    )

    with patch(
        "nv_config_manager.temporal.api.workflow_submission.NautobotClient",
        return_value=client,
    ):
        attributes = await resolve_workflow_references(body)

    client.get_devices.assert_awaited_once_with(
        ANY,
        device_ids=[DEVICE_ID, OTHER_DEVICE_ID],
    )
    assert attributes == {
        DEVICE_ID_SEARCH_ATTRIBUTE: [DEVICE_ID],
        DEVICE_NAME_SEARCH_ATTRIBUTE: ["LEAF01"],
    }


@pytest.mark.asyncio
async def test_uuid_v5_device_reference_is_accepted() -> None:
    """Nautobot device IDs may be deterministic UUIDv5 values."""
    client = _client()
    client.get_devices.return_value = [
        {
            "id": DEVICE_ID_V5,
            "name": "UFM01",
            "role": None,
            "platform": {"name": "UFM"},
            "location": None,
        }
    ]
    body = DeviceCollectionInput(primary_device=DEVICE_ID_V5, related_devices=[])

    with patch(
        "nv_config_manager.temporal.api.workflow_submission.NautobotClient",
        return_value=client,
    ):
        attributes = await resolve_workflow_references(body)

    client.get_devices.assert_awaited_once_with(ANY, device_ids=[DEVICE_ID_V5])
    assert attributes[DEVICE_ID_SEARCH_ATTRIBUTE] == [DEVICE_ID_V5]
    assert attributes[DEVICE_NAME_SEARCH_ATTRIBUTE] == ["UFM01"]


@pytest.mark.asyncio
async def test_explicit_location_takes_search_attribute_precedence() -> None:
    """Device metadata must not replace the human-readable input location."""
    client = _client()
    client.get_devices.return_value = [
        {
            "id": DEVICE_ID,
            "name": "LEAF01",
            "role": None,
            "platform": None,
            "location": {
                "name": "Rack 1",
                "location_type": {"name": "Rack"},
                "parent": {
                    "name": "SJC01",
                    "location_type": {"name": "Site"},
                    "parent": None,
                },
            },
        }
    ]
    client.get.return_value = {
        "count": 1,
        "results": [{"id": LOCATION_ID, "name": "Data Hall A"}],
    }
    body = LocationAndDeviceInput(location_scope=LOCATION_ID, target_device=DEVICE_ID)

    with patch(
        "nv_config_manager.temporal.api.workflow_submission.NautobotClient",
        return_value=client,
    ):
        attributes = await resolve_workflow_references(body)

    assert attributes[SITE_SEARCH_ATTRIBUTE] == ["Data Hall A"]
    assert attributes[DEVICE_ID_SEARCH_ATTRIBUTE] == [DEVICE_ID]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        MultiDeployInput(role="leaf", location=LOCATION_ID),
        IBPKeyCreationInput(host="ufm01", site=LOCATION_ID),
    ],
)
async def test_optional_location_references_are_resolved(body: BaseModel) -> None:
    """Metadata wrapping an optional union must remain visible to the API resolver."""
    client = _client()
    client.get.return_value = {
        "count": 1,
        "results": [{"id": LOCATION_ID, "name": "Data Hall A"}],
    }

    with patch(
        "nv_config_manager.temporal.api.workflow_submission.NautobotClient",
        return_value=client,
    ):
        attributes = await resolve_workflow_references(body)

    assert attributes[SITE_SEARCH_ATTRIBUTE] == ["Data Hall A"]
    client.get.assert_awaited_once_with("dcim/locations/", params={"id": LOCATION_ID})


@pytest.mark.asyncio
async def test_optional_device_reference_is_resolved() -> None:
    """Optional device identifiers must retain validation and enrichment metadata."""
    client = _client()
    client.get_devices.return_value = [
        {
            "id": DEVICE_ID,
            "name": "LEAF01",
            "role": None,
            "platform": None,
            "location": None,
        }
    ]

    with patch(
        "nv_config_manager.temporal.api.workflow_submission.NautobotClient",
        return_value=client,
    ):
        attributes = await resolve_workflow_references(PortLLDPInfoInput(device_id=DEVICE_ID))

    assert attributes[DEVICE_ID_SEARCH_ATTRIBUTE] == [DEVICE_ID]
    assert attributes[DEVICE_NAME_SEARCH_ATTRIBUTE] == ["LEAF01"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("body", "message"),
    [
        (DeviceCollectionInput(primary_device="LEAF01", related_devices=[]), "valid UUID"),
        (LocationAndDeviceInput(location_scope=" ", target_device=DEVICE_ID), "must not be empty"),
    ],
)
async def test_invalid_reference_shape_is_rejected_only_by_api_resolution(
    body: BaseModel,
    message: str,
) -> None:
    """Models remain replay-safe while the API resolver returns semantic 422 errors."""
    client = _client()
    client.get_devices.return_value = [
        {"id": DEVICE_ID, "name": "LEAF01", "role": None, "platform": None, "location": None}
    ]

    with (
        patch(
            "nv_config_manager.temporal.api.workflow_submission.NautobotClient",
            return_value=client,
        ),
        pytest.raises(HTTPException, match=message) as exc_info,
    ):
        await resolve_workflow_references(body)

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_field_names_without_reference_metadata_are_ignored() -> None:
    """Conventional names alone must not trigger validation or Nautobot queries."""
    with patch("nv_config_manager.temporal.api.workflow_submission.NautobotClient") as client:
        attributes = await resolve_workflow_references(ConventionOnlyInput(device_id="not-a-uuid"))

    assert attributes == {}
    client.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "body",
    [
        DeviceCableValidationInput.model_construct(
            device_id=DEVICE_ID,
            device=PreloadedDevice(id=DEVICE_ID),
        ),
        ConfigDiffInput.model_construct(
            device_id=DEVICE_ID,
            device=PreloadedDevice(id=DEVICE_ID),
        ),
        TenantDeployInput.model_construct(device=PreloadedDevice(id=DEVICE_ID)),
        SpXOverlayAssignmentInput.model_construct(
            overlay_id="overlay-1",
            device=PreloadedDevice(id=DEVICE_ID),
            port_names=["Ethernet1"],
            site=LOCATION_ID,
        ),
    ],
)
async def test_api_workflow_inputs_reject_preloaded_device_objects(body: BaseModel) -> None:
    """API callers must not control device connection metadata or credentials targets."""
    client = _client()

    with (
        patch(
            "nv_config_manager.temporal.api.workflow_submission.NautobotClient",
            return_value=client,
        ),
        pytest.raises(HTTPException, match="Preloaded device objects are not accepted") as exc_info,
    ):
        await resolve_workflow_references(body)

    assert exc_info.value.status_code == 422
    client.get_devices.assert_not_awaited()


def test_preloaded_device_objects_remain_valid_for_temporal_invocations() -> None:
    """Model construction remains available to trusted parent and child workflows."""
    device = PreloadedDevice(id=DEVICE_ID)

    body = DeviceAndPreloadedInput(device_id=DEVICE_ID, device=device)

    assert body.device is device
