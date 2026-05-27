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

"""Unit tests for nautobot_app_overlays API."""

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from nautobot.core.testing import APITestCase, APIViewTestCases
from nautobot.dcim.models import Device
from rest_framework import status

from nautobot_app_overlays import choices
from nautobot_app_overlays.models import VXLAN, InfiniBandPKey, Overlay, OverlayAssignment
from nautobot_app_overlays.tests import fixtures


class AppTest(APITestCase):
    """Test the nautobot_app_overlays API root."""

    def test_root(self):
        url = reverse("plugins-api:nautobot_app_overlays-api:api-root")
        response = self.client.get(f"{url}?format=api", **self.header)
        self.assertEqual(response.status_code, 200)


class OverlayAPITest(APIViewTestCases.APIViewTestCase):
    """Test the Overlay API."""

    model = Overlay
    bulk_update_data = {
        "description": "Updated description",
    }
    choices_fields = ["isolation_type"]

    @classmethod
    def setUpTestData(cls):
        fixtures.create_overlay_test_data(cls)

        cls.create_data = [
            {
                "name": "Test Overlay 4",
                "tenant": cls.tenant.pk,
                "location": cls.location.pk,
                "isolation_type": choices.IsolationTypeChoices.VXLAN_EVPN,
                "status": cls.overlay_status.pk,
            },
            {
                "name": "Test Overlay 5",
                "tenant": cls.tenant.pk,
                "location": cls.location.pk,
                "isolation_type": choices.IsolationTypeChoices.NVLINK_PARTITION,
                "status": cls.overlay_status.pk,
            },
            {
                "name": "Test Overlay 6",
                "tenant": cls.tenant2.pk,
                "location": cls.location2.pk,
                "isolation_type": choices.IsolationTypeChoices.IB_PKEY,
                "status": cls.overlay_status.pk,
            },
        ]

    def get_deletable_object(self):
        return self.model.objects.create(
            name="Deletable Overlay",
            tenant=self.tenant,
            location=self.location,
            isolation_type=choices.IsolationTypeChoices.VXLAN_EVPN,
            status=self.overlay_status,
        )

    def get_deletable_object_pks(self):
        overlays = [
            self.model.objects.create(
                name=f"Deletable Overlay {i}",
                tenant=self.tenant,
                location=self.location,
                isolation_type=choices.IsolationTypeChoices.VXLAN_EVPN,
                status=self.overlay_status,
            )
            for i in range(1, 4)
        ]
        return [o.pk for o in overlays]


class OverlayBulkAllocationTest(APITestCase):
    """Test the bulk allocation endpoint."""

    @classmethod
    def setUpTestData(cls):
        fixtures.create_overlay_test_data(cls)
        fixtures.create_device_test_data(cls)

    def setUp(self):
        """Set up test with superuser authentication."""
        super().setUp()
        # Use superuser for bulk operations to bypass object-level permissions
        self.user.is_superuser = True
        self.user.save()

    def test_bulk_allocate_devices(self):
        overlay = self.overlays[0]
        url = reverse(
            "plugins-api:nautobot_app_overlays-api:overlay-allocate",
            kwargs={"pk": overlay.pk},
        )

        data = {
            "object_type": "device",
            "object_ids": [str(self.devices[3].pk), str(self.devices[4].pk)],
            "role": choices.OverlayAssignmentRoleChoices.COMPUTE,
        }

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["created"], 2)
        self.assertEqual(response.data["skipped"], 0)

        # Verify assignments were created
        self.assertEqual(overlay.assignments.count(), 2)

    def test_bulk_allocate_skips_existing(self):
        overlay = self.overlays[0]
        device_content_type = ContentType.objects.get(app_label="dcim", model="device")

        # Create an existing assignment
        OverlayAssignment.objects.create(
            overlay=overlay,
            assigned_object_type=device_content_type,
            assigned_object_id=self.devices[3].pk,
            status=self.assignment_status,
        )

        url = reverse(
            "plugins-api:nautobot_app_overlays-api:overlay-allocate",
            kwargs={"pk": overlay.pk},
        )

        data = {
            "object_type": "device",
            "object_ids": [str(self.devices[3].pk), str(self.devices[4].pk)],
        }

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data["created"], 1)
        self.assertEqual(response.data["skipped"], 1)

    def test_bulk_deallocate(self):
        overlay = self.overlays[0]
        device_content_type = ContentType.objects.get(app_label="dcim", model="device")

        # Create assignments
        assignment1 = OverlayAssignment.objects.create(
            overlay=overlay,
            assigned_object_type=device_content_type,
            assigned_object_id=self.devices[3].pk,
            status=self.assignment_status,
        )
        assignment2 = OverlayAssignment.objects.create(
            overlay=overlay,
            assigned_object_type=device_content_type,
            assigned_object_id=self.devices[4].pk,
            status=self.assignment_status,
        )

        url = reverse(
            "plugins-api:nautobot_app_overlays-api:overlay-deallocate",
            kwargs={"pk": overlay.pk},
        )

        data = {
            "member_ids": [str(assignment1.pk), str(assignment2.pk)],
        }

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["deleted"], 2)
        self.assertEqual(overlay.assignments.count(), 0)


class OverlayAssignmentAPITest(
    APIViewTestCases.CreateObjectViewTestCase,
    APIViewTestCases.DeleteObjectViewTestCase,
    APIViewTestCases.ListObjectsViewTestCase,
    APIViewTestCases.GetObjectViewTestCase,
):
    """Test the OverlayAssignment API."""

    model = OverlayAssignment
    choices_fields = ["role"]

    @classmethod
    def setUpTestData(cls):
        fixtures.create_assignment_test_data(cls)

        # Create additional devices for create tests
        cls.create_devices = []
        for i in range(7, 10):
            device = Device.objects.create(
                device_type=cls.device_type,
                role=cls.device_role,
                name=f"Create Test Device {i}",
                location=cls.location,
                status=cls.device_status,
            )
            cls.create_devices.append(device)

        cls.create_data = [
            {
                "overlay": cls.overlays[0].pk,
                "assigned_object_type": "dcim.device",
                "assigned_object_id": cls.create_devices[0].pk,
                "role": choices.OverlayAssignmentRoleChoices.COMPUTE,
                "status": cls.assignment_status.pk,
            },
            {
                "overlay": cls.overlays[0].pk,
                "assigned_object_type": "dcim.device",
                "assigned_object_id": cls.create_devices[1].pk,
                "status": cls.assignment_status.pk,
            },
            {
                "overlay": cls.overlays[1].pk,
                "assigned_object_type": "dcim.device",
                "assigned_object_id": cls.create_devices[2].pk,
                "role": choices.OverlayAssignmentRoleChoices.STORAGE,
                "status": cls.assignment_status.pk,
            },
        ]


class VXLANAPITest(APIViewTestCases.APIViewTestCase):
    """Test the VXLAN API."""

    model = VXLAN
    bulk_update_data = {
        "name": "Updated VXLAN Name",
    }
    choices_fields = ["vni_type"]

    @classmethod
    def setUpTestData(cls):
        fixtures.create_vxlan_test_data(cls)

        cls.create_data = [
            {
                "vnid": 30001,
                "name": "Test VXLAN 4",
                "namespace": cls.namespace.pk,
                "status": cls.vxlan_status.pk,
            },
            {
                "vnid": 30002,
                "name": "Test VXLAN 5",
                "namespace": cls.namespace.pk,
                "overlay": cls.overlays[0].pk,
                "tenant": cls.tenant.pk,
                "status": cls.vxlan_status.pk,
            },
            {
                "vnid": 30003,
                "name": "Test VXLAN 6",
                "namespace": cls.namespace.pk,
                "status": cls.vxlan_status.pk,
            },
        ]

    def get_deletable_object(self):
        return self.model.objects.create(
            vnid=99999,
            name="Deletable VXLAN",
            namespace=self.namespace,
            status=self.vxlan_status,
        )

    def get_deletable_object_pks(self):
        vxlans = [
            self.model.objects.create(
                vnid=99990 + i,
                name=f"Deletable VXLAN {i}",
                namespace=self.namespace,
                status=self.vxlan_status,
            )
            for i in range(1, 4)
        ]
        return [v.pk for v in vxlans]


class InfiniBandPKeyAPITest(APIViewTestCases.APIViewTestCase):
    """Test the InfiniBandPKey API."""

    model = InfiniBandPKey
    bulk_update_data = {
        "membership_type": choices.PKeyMembershipTypeChoices.LIMITED,
    }
    choices_fields = ["membership_type"]

    @classmethod
    def setUpTestData(cls):
        fixtures.create_pkey_test_data(cls)

        cls.create_data = [
            {
                "pkey": "0x8004",
                "name": "Test PKey 4",
                "overlay": cls.overlays[0].pk,
                "membership_type": choices.PKeyMembershipTypeChoices.FULL,
                "status": cls.pkey_status.pk,
            },
            {
                "pkey": "0x8005",
                "name": "Test PKey 5",
                "overlay": cls.overlays[0].pk,
                "tenant": cls.tenant.pk,
                "membership_type": choices.PKeyMembershipTypeChoices.LIMITED,
                "status": cls.pkey_status.pk,
            },
            {
                "pkey": "0x8006",
                "name": "Test PKey 6",
                "overlay": cls.overlays[1].pk,
                "status": cls.pkey_status.pk,
            },
        ]

    def get_deletable_object(self):
        return self.model.objects.create(
            pkey="0x9999",
            name="Deletable PKey",
            overlay=self.overlays[0],
            status=self.pkey_status,
        )

    def get_deletable_object_pks(self):
        pkeys = [
            self.model.objects.create(
                pkey=f"0x999{i}",
                name=f"Deletable PKey {i}",
                overlay=self.overlays[0],
                status=self.pkey_status,
            )
            for i in range(1, 4)
        ]
        return [p.pk for p in pkeys]
