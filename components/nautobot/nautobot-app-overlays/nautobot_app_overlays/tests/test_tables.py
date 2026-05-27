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

"""Tests for Overlays tables."""

from django.test import RequestFactory, TestCase
from django_tables2 import RequestConfig

from nautobot_app_overlays import models, tables
from nautobot_app_overlays.tests.fixtures import (
    create_assignment_test_data,
    create_overlay_test_data,
    create_pkey_test_data,
    create_vxlan_test_data,
)


class OverlayTableTestCase(TestCase):
    """Tests for OverlayTable."""

    @classmethod
    def setUpTestData(cls):
        create_overlay_test_data(cls)
        cls.factory = RequestFactory()

    def test_table_renders_all_rows(self):
        """Table renders one row per overlay."""
        table = tables.OverlayTable(models.Overlay.objects.all())
        RequestConfig(self.factory.get("/")).configure(table)
        self.assertEqual(len(table.rows), models.Overlay.objects.count())


class OverlayAssignmentTableTestCase(TestCase):
    """Tests for OverlayAssignmentTable."""

    @classmethod
    def setUpTestData(cls):
        create_assignment_test_data(cls)
        cls.factory = RequestFactory()

    def test_table_renders_all_rows(self):
        """Table renders one row per assignment."""
        table = tables.OverlayAssignmentTable(models.OverlayAssignment.objects.all())
        RequestConfig(self.factory.get("/")).configure(table)
        self.assertEqual(len(table.rows), models.OverlayAssignment.objects.count())


class OverlayAssignmentInlineTableTestCase(TestCase):
    """Tests for OverlayAssignmentInlineTable — used inside overlay detail views."""

    @classmethod
    def setUpTestData(cls):
        create_assignment_test_data(cls)

    def test_inline_table_excludes_overlay_column(self):
        """Inline table omits the overlay column (redundant inside the overlay detail view)."""
        table = tables.OverlayAssignmentInlineTable(models.OverlayAssignment.objects.all())
        self.assertNotIn("overlay", table.columns.names())


class VXLANTableTestCase(TestCase):
    """Tests for VXLANTable."""

    @classmethod
    def setUpTestData(cls):
        create_vxlan_test_data(cls)
        cls.factory = RequestFactory()

    def test_table_renders_all_rows(self):
        """Table renders one row per VXLAN."""
        table = tables.VXLANTable(models.VXLAN.objects.all())
        RequestConfig(self.factory.get("/")).configure(table)
        self.assertEqual(len(table.rows), models.VXLAN.objects.count())


class InfiniBandPKeyTableTestCase(TestCase):
    """Tests for InfiniBandPKeyTable."""

    @classmethod
    def setUpTestData(cls):
        create_pkey_test_data(cls)
        cls.factory = RequestFactory()

    def test_table_renders_all_rows(self):
        """Table renders one row per PKey."""
        table = tables.InfiniBandPKeyTable(models.InfiniBandPKey.objects.all())
        RequestConfig(self.factory.get("/")).configure(table)
        self.assertEqual(len(table.rows), models.InfiniBandPKey.objects.count())


class OverlayMembershipInlineTableTestCase(TestCase):
    """Tests for OverlayMembershipInlineTable — shown on Device/Interface/VRF/VLAN detail views."""

    @classmethod
    def setUpTestData(cls):
        create_assignment_test_data(cls)
        cls.factory = RequestFactory()

    def test_inline_table_renders_all_rows(self):
        """Table renders one row per assignment."""
        table = tables.OverlayMembershipInlineTable(models.OverlayAssignment.objects.all())
        RequestConfig(self.factory.get("/")).configure(table)
        self.assertEqual(len(table.rows), models.OverlayAssignment.objects.count())

    def test_inline_table_excludes_action_and_object_columns(self):
        """Inline table omits pk, actions, and assigned_object columns — irrelevant on a host detail view."""
        table = tables.OverlayMembershipInlineTable(models.OverlayAssignment.objects.all())
        cols = list(table.columns.names())
        for excluded in ("pk", "actions", "assigned_object", "assigned_object_type"):
            self.assertNotIn(excluded, cols)
