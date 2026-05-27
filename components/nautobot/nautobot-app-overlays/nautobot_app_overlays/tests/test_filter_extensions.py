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

"""Tests for Overlays filter extensions."""

from django.contrib.contenttypes.models import ContentType
from django.test import SimpleTestCase, TestCase
from nautobot.dcim.models import Device, Interface
from nautobot.extras.models import Status
from nautobot.ipam.models import VLAN, VRF

from nautobot_app_overlays import models
from nautobot_app_overlays.filter_extensions import (
    DeviceFilterExtension,
    InterfaceFilterExtension,
    OverlayAssignmentFilter,
    VLANFilterExtension,
    VRFFilterExtension,
)
from nautobot_app_overlays.tests.fixtures import (
    create_assignment_test_data,
    create_overlay_test_data,
)


class OverlayAssignmentFilterMethodTestCase(SimpleTestCase):
    """Guard against Nautobot add_filter + _generate_lookup_expression_filters with field_name=None."""

    def test_overlay_assignment_filter_exposes_method(self):
        """Custom method must be set so Nautobot skips ORM lookup generation."""
        filt = OverlayAssignmentFilter(model_name="device", app_label="dcim")
        self.assertIsNotNone(filt.method)


class FilterExtensionFieldsTestCase(TestCase):
    """Test that filter extensions define correct filterset fields."""

    def test_device_extension_has_overlay_filter(self):
        """Test that DeviceFilterExtension has overlay filter."""
        self.assertIn(
            "nautobot_app_overlays_device_overlay",
            DeviceFilterExtension.filterset_fields,
        )

    def test_interface_extension_has_overlay_filter(self):
        """Test that InterfaceFilterExtension has overlay filter."""
        self.assertIn(
            "nautobot_app_overlays_interface_overlay",
            InterfaceFilterExtension.filterset_fields,
        )

    def test_vrf_extension_has_overlay_filter(self):
        """Test that VRFFilterExtension has overlay filter."""
        self.assertIn(
            "nautobot_app_overlays_vrf_overlay",
            VRFFilterExtension.filterset_fields,
        )

    def test_vlan_extension_has_overlay_filter(self):
        """Test that VLANFilterExtension has overlay filter."""
        self.assertIn(
            "nautobot_app_overlays_vlan_overlay",
            VLANFilterExtension.filterset_fields,
        )


class OverlayAssignmentFilterTestCase(TestCase):
    """Test the OverlayAssignmentFilter for GenericFK-based filtering."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        create_assignment_test_data(cls)

    def test_filter_devices_by_overlay(self):
        """Test filtering devices by overlay membership."""
        overlay_filter = OverlayAssignmentFilter(
            model_name="device",
            app_label="dcim",
        )

        all_devices = Device.objects.all()
        filtered_qs = overlay_filter.filter(all_devices, [self.overlays[0]])

        self.assertEqual(filtered_qs.count(), 2)
        self.assertIn(self.devices[0], filtered_qs)
        self.assertIn(self.devices[1], filtered_qs)

    def test_filter_devices_by_overlay_empty_result(self):
        """Test filtering devices when no matches exist."""
        overlay_filter = OverlayAssignmentFilter(
            model_name="device",
            app_label="dcim",
        )

        all_devices = Device.objects.all()
        filtered_qs = overlay_filter.filter(all_devices, [self.overlays[2]])

        self.assertEqual(filtered_qs.count(), 0)

    def test_filter_with_empty_value(self):
        """Test that filter returns original queryset when value is empty."""
        overlay_filter = OverlayAssignmentFilter(
            model_name="device",
            app_label="dcim",
        )

        all_devices = Device.objects.all()
        original_count = all_devices.count()

        filtered_qs = overlay_filter.filter(all_devices, None)

        self.assertEqual(filtered_qs.count(), original_count)

    def test_filter_with_invalid_content_type(self):
        """Test that filter handles invalid content type gracefully."""
        overlay_filter = OverlayAssignmentFilter(
            model_name="nonexistent_model",
            app_label="nonexistent_app",
        )

        all_devices = Device.objects.all()
        filtered_qs = overlay_filter.filter(all_devices, [self.overlays[0]])

        self.assertEqual(filtered_qs.count(), 0)


class VRFFilterExtensionFunctionalTestCase(TestCase):
    """Test VRF filter extension functionality via OverlayAssignment."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        create_overlay_test_data(cls)

        vrf_status = Status.objects.get_for_model(VRF).first()
        assignment_status = Status.objects.get_for_model(models.OverlayAssignment).first()
        cls.vrfs = [
            VRF.objects.create(name="VRF Filter Test 1", namespace=cls.namespace, status=vrf_status),
            VRF.objects.create(name="VRF Filter Test 2", namespace=cls.namespace, status=vrf_status),
            VRF.objects.create(name="VRF Filter Test 3", namespace=cls.namespace, status=vrf_status),
        ]

        vrf_ct = ContentType.objects.get_for_model(VRF)
        # VRF 0 → overlay 0; VRF 1 → overlay 0 + overlay 1; VRF 2 → (none)
        models.OverlayAssignment.objects.create(
            overlay=cls.overlays[0],
            assigned_object_type=vrf_ct,
            assigned_object_id=cls.vrfs[0].pk,
            status=assignment_status,
        )
        models.OverlayAssignment.objects.create(
            overlay=cls.overlays[0],
            assigned_object_type=vrf_ct,
            assigned_object_id=cls.vrfs[1].pk,
            status=assignment_status,
        )
        models.OverlayAssignment.objects.create(
            overlay=cls.overlays[1],
            assigned_object_type=vrf_ct,
            assigned_object_id=cls.vrfs[1].pk,
            status=assignment_status,
        )

    def test_vrf_filter_uses_overlay_assignment(self):
        """Test that VRF filter uses OverlayAssignment."""
        vrf_filter_def = VRFFilterExtension.filterset_fields["nautobot_app_overlays_vrf_overlay"]
        self.assertIsInstance(vrf_filter_def, OverlayAssignmentFilter)

    def test_filter_vrfs_by_overlay(self):
        """Test filtering VRFs by overlay membership via OverlayAssignment."""
        overlay_filter = OverlayAssignmentFilter(model_name="vrf", app_label="ipam")
        all_vrfs = VRF.objects.filter(pk__in=[v.pk for v in self.vrfs])

        filtered_qs = overlay_filter.filter(all_vrfs, [self.overlays[0]])
        self.assertEqual(filtered_qs.count(), 2)
        self.assertIn(self.vrfs[0], filtered_qs)
        self.assertIn(self.vrfs[1], filtered_qs)

    def test_filter_vrfs_empty_overlay(self):
        """Test filtering VRFs by an overlay with no VRF assignments returns empty."""
        overlay_filter = OverlayAssignmentFilter(model_name="vrf", app_label="ipam")
        all_vrfs = VRF.objects.filter(pk__in=[v.pk for v in self.vrfs])

        filtered_qs = overlay_filter.filter(all_vrfs, [self.overlays[2]])
        self.assertEqual(filtered_qs.count(), 0)


class VLANFilterExtensionFunctionalTestCase(TestCase):
    """Test VLAN filter extension functionality via OverlayAssignment."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        create_overlay_test_data(cls)

        vlan_status = Status.objects.get_for_model(VLAN).first()
        assignment_status = Status.objects.get_for_model(models.OverlayAssignment).first()
        cls.vlans = [
            VLAN.objects.create(vid=101, name="VLAN Filter Test 101", location=cls.location, status=vlan_status),
            VLAN.objects.create(vid=102, name="VLAN Filter Test 102", location=cls.location, status=vlan_status),
            VLAN.objects.create(vid=103, name="VLAN Filter Test 103", location=cls.location, status=vlan_status),
        ]

        vlan_ct = ContentType.objects.get_for_model(VLAN)
        models.OverlayAssignment.objects.create(
            overlay=cls.overlays[0],
            assigned_object_type=vlan_ct,
            assigned_object_id=cls.vlans[0].pk,
            status=assignment_status,
        )
        models.OverlayAssignment.objects.create(
            overlay=cls.overlays[1],
            assigned_object_type=vlan_ct,
            assigned_object_id=cls.vlans[0].pk,
            status=assignment_status,
        )
        models.OverlayAssignment.objects.create(
            overlay=cls.overlays[1],
            assigned_object_type=vlan_ct,
            assigned_object_id=cls.vlans[1].pk,
            status=assignment_status,
        )

    def test_vlan_filter_uses_overlay_assignment(self):
        """Test that VLAN filter uses OverlayAssignment."""
        vlan_filter_def = VLANFilterExtension.filterset_fields["nautobot_app_overlays_vlan_overlay"]
        self.assertIsInstance(vlan_filter_def, OverlayAssignmentFilter)

    def test_filter_vlans_by_overlay(self):
        """Test filtering VLANs by overlay membership via OverlayAssignment."""
        overlay_filter = OverlayAssignmentFilter(model_name="vlan", app_label="ipam")
        all_vlans = VLAN.objects.filter(pk__in=[v.pk for v in self.vlans])

        filtered_qs = overlay_filter.filter(all_vlans, [self.overlays[1]])
        self.assertEqual(filtered_qs.count(), 2)
        self.assertIn(self.vlans[0], filtered_qs)
        self.assertIn(self.vlans[1], filtered_qs)

    def test_filter_vlans_empty_overlay(self):
        """Test filtering VLANs by an overlay with no VLAN assignments returns empty."""
        overlay_filter = OverlayAssignmentFilter(model_name="vlan", app_label="ipam")
        all_vlans = VLAN.objects.filter(pk__in=[v.pk for v in self.vlans])

        filtered_qs = overlay_filter.filter(all_vlans, [self.overlays[2]])
        self.assertEqual(filtered_qs.count(), 0)


class InterfaceFilterExtensionFunctionalTestCase(TestCase):
    """Test Interface filter extension functionality."""

    @classmethod
    def setUpTestData(cls):
        """Set up test data."""
        create_assignment_test_data(cls)

        interface_status = Status.objects.get_for_model(Interface).first()
        cls.interfaces = [
            Interface.objects.create(
                device=cls.devices[0],
                name="eth0",
                type="1000base-t",
                status=interface_status,
            ),
            Interface.objects.create(
                device=cls.devices[0],
                name="eth1",
                type="1000base-t",
                status=interface_status,
            ),
            Interface.objects.create(
                device=cls.devices[1],
                name="eth0",
                type="1000base-t",
                status=interface_status,
            ),
        ]

        cls.interface_ct = ContentType.objects.get_for_model(Interface)
        models.OverlayAssignment.objects.create(
            overlay=cls.overlays[0],
            assigned_object_type=cls.interface_ct,
            assigned_object_id=cls.interfaces[0].pk,
            status=cls.assignment_status,
        )

    def test_filter_interfaces_by_overlay(self):
        """Test filtering interfaces by overlay membership."""
        overlay_filter = OverlayAssignmentFilter(
            model_name="interface",
            app_label="dcim",
        )

        all_interfaces = Interface.objects.filter(pk__in=[i.pk for i in self.interfaces])
        filtered_qs = overlay_filter.filter(all_interfaces, [self.overlays[0]])

        self.assertEqual(filtered_qs.count(), 1)
        self.assertIn(self.interfaces[0], filtered_qs)

    def test_filter_interfaces_no_matches(self):
        """Test filtering interfaces when no matches exist."""
        overlay_filter = OverlayAssignmentFilter(
            model_name="interface",
            app_label="dcim",
        )

        all_interfaces = Interface.objects.filter(pk__in=[i.pk for i in self.interfaces])
        filtered_qs = overlay_filter.filter(all_interfaces, [self.overlays[2]])

        self.assertEqual(filtered_qs.count(), 0)
