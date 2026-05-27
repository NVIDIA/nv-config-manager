#  SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

"""Filter extensions for Overlays app.

Extends Device, Interface, VRF, VLAN, and Prefix filters to allow filtering by overlay membership.
"""

import django_filters
from django.contrib.contenttypes.models import ContentType
from nautobot.apps.filters import FilterExtension

from nautobot_app_overlays.models import Overlay, OverlayAssignment


class OverlayAssignmentFilter(django_filters.ModelMultipleChoiceFilter):
    """Custom filter for filtering objects by overlay membership via GenericForeignKey."""

    def __init__(self, model_name, app_label, *args, **kwargs):
        """Initialize with the model info for content type lookup."""
        self.model_name = model_name
        self.app_label = app_label

        def filter_by_overlay_membership(qs, _name, value):
            if not value:
                return qs
            try:
                content_type = ContentType.objects.get(app_label=app_label, model=model_name)
            except ContentType.DoesNotExist:
                return qs.none()
            assigned_object_ids = OverlayAssignment.objects.filter(
                overlay__in=value,
                assigned_object_type=content_type,
            ).values_list("assigned_object_id", flat=True)
            return qs.filter(pk__in=assigned_object_ids)

        super().__init__(
            queryset=Overlay.objects.all(),
            to_field_name="pk",
            label="Overlay",
            method=filter_by_overlay_membership,
            *args,
            **kwargs,
        )


class DeviceFilterExtension(FilterExtension):
    """Extends dcim.device filter to include overlay membership filtering."""

    model = "dcim.device"

    filterset_fields = {
        "nautobot_app_overlays_device_overlay": OverlayAssignmentFilter(
            model_name="device",
            app_label="dcim",
        ),
    }


class InterfaceFilterExtension(FilterExtension):
    """Extends dcim.interface filter to include overlay membership filtering."""

    model = "dcim.interface"

    filterset_fields = {
        "nautobot_app_overlays_interface_overlay": OverlayAssignmentFilter(
            model_name="interface",
            app_label="dcim",
        ),
    }


class VRFFilterExtension(FilterExtension):
    """Extends ipam.vrf filter to include overlay membership filtering."""

    model = "ipam.vrf"

    filterset_fields = {
        "nautobot_app_overlays_vrf_overlay": OverlayAssignmentFilter(
            model_name="vrf",
            app_label="ipam",
        ),
    }


class VLANFilterExtension(FilterExtension):
    """Extends ipam.vlan filter to include overlay membership filtering."""

    model = "ipam.vlan"

    filterset_fields = {
        "nautobot_app_overlays_vlan_overlay": OverlayAssignmentFilter(
            model_name="vlan",
            app_label="ipam",
        ),
    }


filter_extensions = [
    DeviceFilterExtension,
    InterfaceFilterExtension,
    VRFFilterExtension,
    VLANFilterExtension,
]
