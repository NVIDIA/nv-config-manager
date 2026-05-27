#  SPDX-FileCopyrightText: Copyright (c) "2025" NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#  SPDX-License-Identifier: Apache-2.0
#
#  Licensed under the Apache License, Version 2.0 (the "License")
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Filters."""

import django_filters
from django.db.models import F, Q
from nautobot.apps.filters import (
    MultiValueMACAddressFilter,
    NaturalKeyOrPKMultipleChoiceFilter,
    NautobotFilterSet,
    SearchFilter,
)
from nautobot.dcim.models import Device, DeviceType, Location, Manufacturer, Platform
from nautobot.extras.models import Role, Status
from nautobot.tenancy.models import Tenant

from nv_config_manager import models
from nv_config_manager.utils import get_all_descendants


class ConfigManagerDeviceStatusFilterSet(NautobotFilterSet):
    """ConfigManagerDeviceStatus filterset with device filters mirroring the devices query."""

    q = SearchFilter(
        filter_predicates={
            "device__name": "icontains",
            "device__serial": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "device__inventory_items__serial": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "device__asset_tag": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "device__device_type__manufacturer__name": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "device__device_type__model": {
                "lookup_expr": "icontains",
                "preprocessor": str.strip,
            },
            "device__comments": "icontains",
        },
    )

    # ConfigManager-specific filters
    render_enabled = django_filters.BooleanFilter()
    ztp_enabled = django_filters.BooleanFilter()
    deploy_enabled = django_filters.BooleanFilter()
    backup_enabled = django_filters.BooleanFilter()
    is_aggregate_managed = django_filters.BooleanFilter()
    is_pending = django_filters.BooleanFilter(method="filter_is_pending", label="Has pending configuration")
    # Device filters
    location = NaturalKeyOrPKMultipleChoiceFilter(
        method="filter_device_location", queryset=Location.objects.all(), label="Device Location"
    )
    status = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device__status", queryset=Status.objects.all(), label="Device Status"
    )
    role = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device__role", queryset=Role.objects.all(), label="Device Role"
    )
    tenant = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device__tenant", queryset=Tenant.objects.all(), label="Device Tenant"
    )
    device_type = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device__device_type", queryset=DeviceType.objects.all(), label="Device Type"
    )
    manufacturer = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device__device_type__manufacturer",
        queryset=Manufacturer.objects.all(),
        label="Device Manufacturer",
    )
    platform = NaturalKeyOrPKMultipleChoiceFilter(
        field_name="device__platform", queryset=Platform.objects.all(), label="Device Platform"
    )

    # Additional device filters for the unique fields from devices query
    has_primary_ip = django_filters.BooleanFilter(method="filter_has_primary_ip", label="Has Primary IP")
    mac_address = MultiValueMACAddressFilter(
        field_name="device__interfaces__mac_address",
        label="MAC address",
    )
    device_id = django_filters.ModelMultipleChoiceFilter(
        field_name="device", queryset=Device.objects.all(), to_field_name="id", label="Device IDs"
    )

    def filter_is_pending(self, queryset, name, value):  # pylint: disable=unused-argument
        """Filter based on pending configuration status."""
        if value:
            return queryset.filter(
                intended_config__isnull=False,
                backup_config__isnull=False,
                intended_config__commit_id__isnull=False,
                backup_config__deployed_commit_id__isnull=False,
            ).exclude(intended_config__commit_id=F("backup_config__deployed_commit_id"))

        return queryset.exclude(
            intended_config__isnull=False,
            backup_config__isnull=False,
            intended_config__commit_id__isnull=False,
            backup_config__deployed_commit_id__isnull=False,
        ).filter(intended_config__commit_id=F("backup_config__deployed_commit_id"))

    def filter_device_location(self, queryset, name, value):  # pylint: disable=unused-argument
        """Generic location filter that finds devices at specified location(s) or any descendant locations."""
        if not value:
            return queryset

        # Collect all location IDs including descendants
        all_location_ids = set()
        for location in value:
            # get_all_descendants returns a list of location IDs including the location itself
            all_location_ids.update(get_all_descendants(location))

        return queryset.filter(device__location__in=all_location_ids)

    def filter_has_primary_ip(self, queryset, name, value):  # pylint: disable=unused-argument
        """Filter for devices that have a primary IP address (IPv4 or IPv6)."""
        if value is True:
            return queryset.filter(Q(device__primary_ip4__isnull=False) | Q(device__primary_ip6__isnull=False))
        if value is False:
            return queryset.filter(device__primary_ip4__isnull=True, device__primary_ip6__isnull=True)
        return queryset

    class Meta:
        """Metaclass Attributes."""

        model = models.ConfigManagerDeviceStatus
        fields = "__all__"


class IntendedConfigFilterSet(NautobotFilterSet):  # pylint: disable=too-few-public-methods
    """IntendedConfig FilterSet."""

    class Meta:
        """Metaclass Attributes."""

        model = models.IntendedConfig
        fields = "__all__"


class BackupConfigFilterSet(NautobotFilterSet):  # pylint: disable=too-few-public-methods
    """BackupConfig FilterSet."""

    class Meta:
        """Metaclass Attributes."""

        model = models.BackupConfig
        fields = "__all__"
