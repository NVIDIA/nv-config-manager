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

"""Template extensions for Overlays app.

Extends Device, Interface, VRF, and VLAN detail views to show overlay information.
"""

from django.contrib.contenttypes.models import ContentType
from nautobot.apps.ui import TemplateExtension

from nautobot_app_overlays.models import OverlayAssignment
from nautobot_app_overlays.tables import OverlayMembershipInlineTable


def _build_membership_panel(extension, obj):
    """Render an overlay memberships panel for a given object."""
    content_type = ContentType.objects.get_for_model(obj)
    assignments = OverlayAssignment.objects.filter(
        assigned_object_type=content_type,
        assigned_object_id=obj.pk,
    ).select_related("overlay", "overlay__tenant", "overlay__location")

    table = OverlayMembershipInlineTable(assignments)
    return extension.render(
        "nautobot_app_overlays/inc/overlay_assignments_panel.html",
        extra_context={
            "table": table,
            "panel_title": "Overlay Memberships",
            "object": obj,
            "content_type": content_type,
            "show_add_button": True,
        },
    )


class DeviceOverlayExtension(TemplateExtension):
    """Extends Device detail view to show overlay memberships."""

    model = "dcim.device"

    def right_page(self):
        """Render overlay memberships panel for device detail view."""
        obj = self.context.get("object")
        if obj is None:
            return ""
        return _build_membership_panel(self, obj)


class InterfaceOverlayExtension(TemplateExtension):
    """Extends Interface detail view to show overlay memberships."""

    model = "dcim.interface"

    def right_page(self):
        """Render overlay memberships panel for interface detail view."""
        obj = self.context.get("object")
        if obj is None:
            return ""
        return _build_membership_panel(self, obj)


class VRFOverlayExtension(TemplateExtension):
    """Extends VRF detail view to show overlay memberships via OverlayAssignment."""

    model = "ipam.vrf"

    def right_page(self):
        """Render overlay memberships panel for VRF detail view."""
        obj = self.context.get("object")
        if obj is None:
            return ""
        return _build_membership_panel(self, obj)


class VLANOverlayExtension(TemplateExtension):
    """Extends VLAN detail view to show overlay memberships via OverlayAssignment."""

    model = "ipam.vlan"

    def right_page(self):
        """Render overlay memberships panel for VLAN detail view."""
        obj = self.context.get("object")
        if obj is None:
            return ""
        return _build_membership_panel(self, obj)


# Register all template extensions
template_extensions = [
    DeviceOverlayExtension,
    InterfaceOverlayExtension,
    VRFOverlayExtension,
    VLANOverlayExtension,
]
