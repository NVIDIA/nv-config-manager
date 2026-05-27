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

"""Tests for Overlays navigation."""

from django.test import TestCase

from nautobot_app_overlays import navigation


def _group_by_name(name):
    """Return the named group from the first menu tab."""
    tab = navigation.menu_items[0]
    return next(g for g in tab.groups if g.name == name)


class NavigationTestCase(TestCase):
    """Test cases for navigation menu items."""

    def test_menu_tab_name(self):
        """Tab is labelled Multi-Tenancy."""
        self.assertEqual(navigation.menu_items[0].name, "Multi-Tenancy")

    def test_overlay_items_use_view_overlay_permission(self):
        """All Overlays group items require view_overlay permission."""
        group = _group_by_name("Overlays")
        for item in group.items:
            self.assertIn("nautobot_app_overlays.view_overlay", item.permissions, f"'{item.name}' missing permission")

    def test_fabric_record_items_use_model_specific_permissions(self):
        """Fabric Records items use their own model permissions, not view_overlay."""
        group = _group_by_name("Fabric Records")
        for item in group.items:
            self.assertNotIn(
                "nautobot_app_overlays.view_overlay",
                item.permissions,
                f"'{item.name}' should not use view_overlay permission",
            )
