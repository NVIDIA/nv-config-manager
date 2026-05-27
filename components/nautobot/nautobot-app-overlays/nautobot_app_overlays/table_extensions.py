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

"""Table extensions for Overlays app.

Extends Device, Interface, VRF, and VLAN tables to show overlay information directly in list views.
"""

import django_tables2 as tables
from django.contrib.contenttypes.models import ContentType
from django.utils.html import format_html
from nautobot.apps.tables import TableExtension

from nautobot_app_overlays.models import OverlayAssignment


class OverlayColumn(tables.Column):
    """Custom column to display overlay membership.

    Renders overlay names as links for objects with GenericFK relationship via OverlayAssignment.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("verbose_name", "Overlay")
        kwargs.setdefault("orderable", False)
        kwargs.setdefault("empty_values", ())
        super().__init__(*args, **kwargs)

    def render(self, record):
        """Render overlay links for the record."""
        if hasattr(record, "_prefetched_overlay_assignments"):
            assignments = record._prefetched_overlay_assignments
        else:
            content_type = ContentType.objects.get_for_model(record)
            assignments = OverlayAssignment.objects.filter(
                assigned_object_type=content_type,
                assigned_object_id=record.pk,
            ).select_related("overlay")

        if not assignments:
            return "—"

        links = []
        for assignment in assignments:
            overlay = assignment.overlay
            url = overlay.get_absolute_url()
            links.append(f'<a href="{url}">{overlay.name}</a>')

        return format_html(", ".join(links))


class InterfaceTableExtension(TableExtension):
    """Extends Interface table to show overlay membership."""

    model = "dcim.interface"

    table_columns = {
        "nautobot_app_overlays_overlay": OverlayColumn(),
    }

    @classmethod
    def alter_queryset(cls, queryset):
        """No queryset modification needed; OverlayColumn fetches on demand."""
        return queryset


class VRFTableExtension(TableExtension):
    """Extends VRF table to show overlay membership via OverlayAssignment."""

    model = "ipam.vrf"

    table_columns = {
        "nautobot_app_overlays_overlay": OverlayColumn(),
    }

    @classmethod
    def alter_queryset(cls, queryset):
        """No queryset modification needed; OverlayColumn fetches on demand."""
        return queryset


class VLANTableExtension(TableExtension):
    """Extends VLAN table to show overlay membership via OverlayAssignment."""

    model = "ipam.vlan"

    table_columns = {
        "nautobot_app_overlays_overlay": OverlayColumn(),
    }

    @classmethod
    def alter_queryset(cls, queryset):
        """No queryset modification needed; OverlayColumn fetches on demand."""
        return queryset


# Register all table extensions
table_extensions = [
    InterfaceTableExtension,
    VRFTableExtension,
    VLANTableExtension,
]
