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

"""Tests for Overlays table extensions."""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from nautobot.dcim.models import Interface
from nautobot.extras.models import Status
from nautobot.ipam.models import VRF

from nautobot_app_overlays import models
from nautobot_app_overlays.table_extensions import (
    InterfaceTableExtension,
    OverlayColumn,
    VLANTableExtension,
    VRFTableExtension,
)
from nautobot_app_overlays.tests.fixtures import (
    create_assignment_test_data,
    create_overlay_test_data,
)


class TableExtensionColumnsTestCase(TestCase):
    """Test that table extensions define correct columns."""

    def test_interface_extension_has_overlay_column(self):
        """Test that InterfaceTableExtension has overlay column."""
        self.assertIn(
            "nautobot_app_overlays_overlay",
            InterfaceTableExtension.table_columns,
        )
        self.assertIsInstance(
            InterfaceTableExtension.table_columns["nautobot_app_overlays_overlay"],
            OverlayColumn,
        )

    def test_vrf_extension_has_overlay_column(self):
        """Test that VRFTableExtension has overlay column using OverlayAssignment."""
        self.assertIn(
            "nautobot_app_overlays_overlay",
            VRFTableExtension.table_columns,
        )
        self.assertIsInstance(
            VRFTableExtension.table_columns["nautobot_app_overlays_overlay"],
            OverlayColumn,
        )

    def test_vlan_extension_has_overlay_column(self):
        """Test that VLANTableExtension has overlay column using OverlayAssignment."""
        self.assertIn(
            "nautobot_app_overlays_overlay",
            VLANTableExtension.table_columns,
        )
        self.assertIsInstance(
            VLANTableExtension.table_columns["nautobot_app_overlays_overlay"],
            OverlayColumn,
        )


class OverlayColumnTestCase(TestCase):
    """Test OverlayColumn rendering."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        create_assignment_test_data(cls)

        cls.interface = Interface.objects.create(
            device=cls.devices[0],
            name="eth0",
            type="1000base-t",
            status=Status.objects.get_for_model(Interface).first(),
        )

        cls.interface_ct = ContentType.objects.get_for_model(Interface)

    def test_render_with_no_assignment(self):
        """Test column renders dash when no overlay assignment."""
        column = OverlayColumn()
        result = column.render(self.interface)
        self.assertEqual(result, "—")

    def test_render_with_assignment(self):
        """Test column renders overlay link when assignment exists."""
        models.OverlayAssignment.objects.create(
            overlay=self.overlays[0],
            assigned_object_type=self.interface_ct,
            assigned_object_id=self.interface.pk,
            status=self.assignment_status,
        )

        column = OverlayColumn()
        result = column.render(self.interface)

        self.assertIn(self.overlays[0].name, result)
        self.assertIn("href=", result)


class VRFOverlayColumnTestCase(TestCase):
    """Test OverlayColumn rendering for VRF objects."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        create_overlay_test_data(cls)

        vrf_status = Status.objects.get_for_model(VRF).first()
        assignment_status = Status.objects.get_for_model(models.OverlayAssignment).first()
        cls.vrf = VRF.objects.create(
            name="Test VRF Column",
            namespace=cls.namespace,
            status=vrf_status,
        )
        vrf_ct = ContentType.objects.get_for_model(VRF)
        models.OverlayAssignment.objects.create(
            overlay=cls.overlays[0],
            assigned_object_type=vrf_ct,
            assigned_object_id=cls.vrf.pk,
            status=assignment_status,
        )

    def test_render_with_assignment(self):
        """Test column renders overlay links when assignment exists."""
        column = OverlayColumn()
        result = column.render(self.vrf)

        self.assertIn(self.overlays[0].name, result)
        self.assertIn("href=", result)
