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

"""Tests for Overlays template extensions."""

from django.contrib.contenttypes.models import ContentType
from django.test import RequestFactory, TestCase
from nautobot.dcim.models import Interface
from nautobot.extras.models import Status
from nautobot.ipam.models import VLAN, VRF

from nautobot_app_overlays import models
from nautobot_app_overlays.template_content import (
    DeviceOverlayExtension,
    InterfaceOverlayExtension,
    VLANOverlayExtension,
    VRFOverlayExtension,
)
from nautobot_app_overlays.tests.fixtures import (
    create_assignment_test_data,
    create_overlay_test_data,
)


class DeviceOverlayExtensionTestCase(TestCase):
    """Test DeviceOverlayExtension."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        create_assignment_test_data(cls)
        cls.factory = RequestFactory()

    def test_right_page_returns_empty_for_no_object(self):
        """Test that right_page returns empty string when no object in context."""
        request = self.factory.get("/")
        extension = DeviceOverlayExtension(context={"request": request})

        result = extension.right_page()
        self.assertEqual(result, "")

    def test_right_page_returns_panel_for_no_memberships(self):
        """Test that right_page returns panel with add button when device has no memberships."""
        device = self.devices[5]
        request = self.factory.get("/")
        extension = DeviceOverlayExtension(context={"object": device, "request": request})

        result = extension.right_page()
        self.assertIn("Overlay Memberships", result)
        self.assertIn("Assign to Overlay", result)

    def test_right_page_returns_html_with_memberships(self):
        """Test that right_page returns HTML when device has memberships."""
        device = self.devices[0]
        request = self.factory.get("/")
        extension = DeviceOverlayExtension(context={"object": device, "request": request})

        result = extension.right_page()
        self.assertNotEqual(result, "")
        self.assertIn("Overlay Memberships", result)


class InterfaceOverlayExtensionTestCase(TestCase):
    """Test InterfaceOverlayExtension."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        create_assignment_test_data(cls)
        cls.factory = RequestFactory()

        cls.interface = Interface.objects.create(
            device=cls.devices[0],
            name="eth0",
            type="1000base-t",
            status=Status.objects.get_for_model(Interface).first(),
        )

        cls.interface_ct = ContentType.objects.get_for_model(Interface)

    def test_right_page_returns_panel_for_no_memberships(self):
        """Test that right_page returns panel with add button when interface has no memberships."""
        request = self.factory.get("/")
        extension = InterfaceOverlayExtension(context={"object": self.interface, "request": request})

        result = extension.right_page()
        self.assertIn("Overlay Memberships", result)
        self.assertIn("Assign to Overlay", result)

    def test_right_page_returns_html_with_memberships(self):
        """Test that right_page returns HTML when interface has memberships."""
        models.OverlayAssignment.objects.create(
            overlay=self.overlays[0],
            assigned_object_type=self.interface_ct,
            assigned_object_id=self.interface.pk,
            status=self.assignment_status,
        )

        request = self.factory.get("/")
        extension = InterfaceOverlayExtension(context={"object": self.interface, "request": request})

        result = extension.right_page()
        self.assertNotEqual(result, "")
        self.assertIn("Overlay Memberships", result)


class VRFOverlayExtensionTestCase(TestCase):
    """Test VRFOverlayExtension shows overlay memberships via OverlayAssignment."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        create_overlay_test_data(cls)
        cls.factory = RequestFactory()

        vrf_status = Status.objects.get_for_model(VRF).first()
        assignment_status = Status.objects.get_for_model(models.OverlayAssignment).first()
        cls.vrfs = [
            VRF.objects.create(name="Test VRF 1", namespace=cls.namespace, status=vrf_status),
            VRF.objects.create(name="Test VRF 2", namespace=cls.namespace, status=vrf_status),
        ]

        vrf_ct = ContentType.objects.get_for_model(VRF)
        models.OverlayAssignment.objects.create(
            overlay=cls.overlays[0],
            assigned_object_type=vrf_ct,
            assigned_object_id=cls.vrfs[0].pk,
            status=assignment_status,
        )
        models.OverlayAssignment.objects.create(
            overlay=cls.overlays[1],
            assigned_object_type=vrf_ct,
            assigned_object_id=cls.vrfs[0].pk,
            status=assignment_status,
        )

    def test_vrf_with_assignments_renders_panel(self):
        """Test VRF with overlay assignments renders a panel."""
        request = self.factory.get("/")
        extension = VRFOverlayExtension(context={"object": self.vrfs[0], "request": request})
        result = extension.right_page()
        self.assertNotEqual(result, "")
        self.assertIn("Overlay Memberships", result)

    def test_vrf_without_assignments_renders_empty_panel(self):
        """Test VRF with no overlay assignments still renders a panel."""
        request = self.factory.get("/")
        extension = VRFOverlayExtension(context={"object": self.vrfs[1], "request": request})
        result = extension.right_page()
        self.assertNotEqual(result, "")


class VLANOverlayExtensionTestCase(TestCase):
    """Test VLANOverlayExtension shows overlay memberships via OverlayAssignment."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        create_overlay_test_data(cls)
        cls.factory = RequestFactory()

        vlan_status = Status.objects.get_for_model(VLAN).first()
        assignment_status = Status.objects.get_for_model(models.OverlayAssignment).first()
        cls.vlans = [
            VLAN.objects.create(vid=100, name="Test VLAN 100", location=cls.location, status=vlan_status),
            VLAN.objects.create(vid=200, name="Test VLAN 200", location=cls.location, status=vlan_status),
        ]

        vlan_ct = ContentType.objects.get_for_model(VLAN)
        models.OverlayAssignment.objects.create(
            overlay=cls.overlays[0],
            assigned_object_type=vlan_ct,
            assigned_object_id=cls.vlans[0].pk,
            status=assignment_status,
        )

    def test_vlan_with_assignments_renders_panel(self):
        """Test VLAN with overlay assignments renders a panel."""
        request = self.factory.get("/")
        extension = VLANOverlayExtension(context={"object": self.vlans[0], "request": request})
        result = extension.right_page()
        self.assertNotEqual(result, "")
        self.assertIn("Overlay Memberships", result)
