# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Temporal helpers built on DCIM SDK inventory models."""

from __future__ import annotations

from nv_config_manager_dcim.workflow_models import (
    DeviceBayData,
    DeviceData,
    HostDeviceData,
    InterfaceData,
    NetworkDeviceData,
    Platform,
)

from nv_config_manager.temporal.common.mixins.base import BaseMixin
from nv_config_manager.temporal.common.search_attributes import (
    DEVICE_ID_SEARCH_ATTRIBUTE,
    DEVICE_NAME_SEARCH_ATTRIBUTE,
    DEVICE_PLATFORM_SEARCH_ATTRIBUTE,
    DEVICE_ROLE_SEARCH_ATTRIBUTE,
    SITE_SEARCH_ATTRIBUTE,
    upsert_missing_search_attributes,
)

__all__ = [
    "DeviceBayData",
    "DeviceData",
    "DeviceMixin",
    "HostDeviceData",
    "InterfaceData",
    "NetworkDeviceData",
    "Platform",
]


class DeviceMixin(BaseMixin):
    """Temporal-only behavior applied to provider-neutral device models."""

    @staticmethod
    def attach_device_search_attributes(device: DeviceData) -> None:
        """Attach normalized DCIM device metadata to workflow search attributes."""
        attributes = {
            DEVICE_ID_SEARCH_ATTRIBUTE: [device.id],
            DEVICE_ROLE_SEARCH_ATTRIBUTE: [device.role],
            SITE_SEARCH_ATTRIBUTE: [device.site],
            DEVICE_NAME_SEARCH_ATTRIBUTE: [device.name],
        }
        if isinstance(device, NetworkDeviceData):
            attributes[DEVICE_PLATFORM_SEARCH_ATTRIBUTE] = [device.platform]
        upsert_missing_search_attributes(attributes)
