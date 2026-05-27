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

"""Test fixtures for Overlays app."""

from django.contrib.contenttypes.models import ContentType
from nautobot.dcim.models import Device, DeviceType, Location, LocationType, Manufacturer
from nautobot.extras.models import Role, Status
from nautobot.ipam.models import VLAN, Namespace, Prefix
from nautobot.tenancy.models import Tenant

from nautobot_app_overlays import choices, models


def get_or_create_status_for_model(model_class, status_name="Active"):
    """Get or create a status for a model, ensuring it's associated with the model's content type."""
    content_type = ContentType.objects.get_for_model(model_class)

    # Try to get the status by name first
    status = Status.objects.filter(name=status_name).first()
    if status is None:
        # Create a new status if it doesn't exist
        status = Status.objects.create(name=status_name)

    # Ensure the content type is associated with this status
    if not status.content_types.filter(pk=content_type.pk).exists():
        status.content_types.add(content_type)

    return status


def create_common_test_data(cls):
    """Create common test data shared across multiple test classes."""
    # Create LocationType and Location
    cls.location_type, _ = LocationType.objects.get_or_create(name="Test Site Type")
    cls.location_type.content_types.add(ContentType.objects.get_for_model(Device))
    cls.location_type.content_types.add(ContentType.objects.get_for_model(VLAN))
    cls.location_type.content_types.add(ContentType.objects.get_for_model(Prefix))

    location_status = Status.objects.get_for_model(Location).first()
    cls.location, _ = Location.objects.get_or_create(
        name="Test Site 1",
        defaults={
            "location_type": cls.location_type,
            "status": location_status,
        },
    )
    cls.location2, _ = Location.objects.get_or_create(
        name="Test Site 2",
        defaults={
            "location_type": cls.location_type,
            "status": location_status,
        },
    )

    # Create Tenant
    cls.tenant, _ = Tenant.objects.get_or_create(name="Test Tenant 1")
    cls.tenant2, _ = Tenant.objects.get_or_create(name="Test Tenant 2")

    # Create Manufacturer, DeviceType, and Role for Devices
    cls.manufacturer, _ = Manufacturer.objects.get_or_create(name="Test Manufacturer")
    cls.device_type, _ = DeviceType.objects.get_or_create(
        manufacturer=cls.manufacturer,
        model="Test Model",
    )
    cls.device_role, _ = Role.objects.get_or_create(name="Test Device Role")
    cls.device_role.content_types.add(ContentType.objects.get_for_model(Device))

    # Get statuses - ensure they exist and are associated with our models
    cls.device_status = Status.objects.get_for_model(Device).first()
    cls.overlay_status = get_or_create_status_for_model(models.Overlay)
    cls.assignment_status = get_or_create_status_for_model(models.OverlayAssignment)
    cls.vxlan_status = get_or_create_status_for_model(models.VXLAN)
    cls.pkey_status = get_or_create_status_for_model(models.InfiniBandPKey)
    # Create Namespace for VXLAN and VRF
    cls.namespace = Namespace.objects.first() or Namespace.objects.create(name="Global")


def create_overlay_test_data(cls):
    """Create Overlay-specific test data."""
    create_common_test_data(cls)

    cls.overlays = [
        models.Overlay.objects.create(
            name="Test Overlay 1",
            tenant=cls.tenant,
            location=cls.location,
            isolation_type=choices.IsolationTypeChoices.VXLAN_EVPN,
            status=cls.overlay_status,
        ),
        models.Overlay.objects.create(
            name="Test Overlay 2",
            tenant=cls.tenant,
            location=cls.location,
            isolation_type=choices.IsolationTypeChoices.NVLINK_PARTITION,
            status=cls.overlay_status,
        ),
        models.Overlay.objects.create(
            name="Test Overlay 3",
            tenant=cls.tenant2,
            location=cls.location2,
            isolation_type=choices.IsolationTypeChoices.IB_PKEY,
            status=cls.overlay_status,
        ),
    ]


def create_device_test_data(cls):
    """Create Device test data for overlay assignment tests."""
    cls.devices = []
    for i in range(1, 7):
        device, _ = Device.objects.get_or_create(
            name=f"Test Device {i}",
            defaults={
                "device_type": cls.device_type,
                "role": cls.device_role,
                "location": cls.location,
                "status": cls.device_status,
            },
        )
        cls.devices.append(device)


def create_vxlan_test_data(cls):
    """Create VXLAN-specific test data."""
    create_common_test_data(cls)

    # Create overlays inline to avoid duplicate creation
    # All overlays must be VXLAN_EVPN type since VXLANs can only be associated with this type
    cls.overlays = []
    overlay1, _ = models.Overlay.objects.get_or_create(
        name="VXLAN Test Overlay 1",
        defaults={
            "tenant": cls.tenant,
            "location": cls.location,
            "isolation_type": choices.IsolationTypeChoices.VXLAN_EVPN,
            "status": cls.overlay_status,
        },
    )
    cls.overlays.append(overlay1)
    overlay2, _ = models.Overlay.objects.get_or_create(
        name="VXLAN Test Overlay 2",
        defaults={
            "tenant": cls.tenant,
            "location": cls.location,
            "isolation_type": choices.IsolationTypeChoices.VXLAN_EVPN,
            "status": cls.overlay_status,
        },
    )
    cls.overlays.append(overlay2)

    cls.vxlans = [
        models.VXLAN.objects.create(
            vnid=10001,
            name="Test VXLAN 1",
            namespace=cls.namespace,
            overlay=cls.overlays[0],
            tenant=cls.tenant,
            status=cls.vxlan_status,
        ),
        models.VXLAN.objects.create(
            vnid=10002,
            name="Test VXLAN 2",
            namespace=cls.namespace,
            overlay=cls.overlays[0],
            tenant=cls.tenant,
            status=cls.vxlan_status,
        ),
        models.VXLAN.objects.create(
            vnid=20001,
            name="Test VXLAN 3",
            namespace=cls.namespace,
            overlay=cls.overlays[1],
            tenant=cls.tenant2,
            status=cls.vxlan_status,
        ),
    ]


def create_pkey_test_data(cls):
    """Create InfiniBandPKey-specific test data."""
    create_common_test_data(cls)

    # Create overlays inline to avoid duplicate creation
    cls.overlays = []
    overlay1, _ = models.Overlay.objects.get_or_create(
        name="PKey Test Overlay 1",
        defaults={
            "tenant": cls.tenant,
            "location": cls.location,
            "isolation_type": choices.IsolationTypeChoices.IB_PKEY,
            "status": cls.overlay_status,
        },
    )
    cls.overlays.append(overlay1)
    overlay2, _ = models.Overlay.objects.get_or_create(
        name="PKey Test Overlay 2",
        defaults={
            "tenant": cls.tenant,
            "location": cls.location,
            "isolation_type": choices.IsolationTypeChoices.IB_PKEY,
            "status": cls.overlay_status,
        },
    )
    cls.overlays.append(overlay2)

    cls.pkeys = [
        models.InfiniBandPKey.objects.create(
            pkey="0x8001",
            name="Test PKey 1",
            overlay=cls.overlays[0],
            tenant=cls.tenant,
            membership_type=choices.PKeyMembershipTypeChoices.FULL,
            status=cls.pkey_status,
        ),
        models.InfiniBandPKey.objects.create(
            pkey="0x8002",
            name="Test PKey 2",
            overlay=cls.overlays[0],
            tenant=cls.tenant,
            membership_type=choices.PKeyMembershipTypeChoices.LIMITED,
            status=cls.pkey_status,
        ),
        models.InfiniBandPKey.objects.create(
            pkey="0x8003",
            name="Test PKey 3",
            overlay=cls.overlays[1],
            tenant=cls.tenant2,
            membership_type=choices.PKeyMembershipTypeChoices.FULL,
            status=cls.pkey_status,
        ),
    ]


def create_assignment_test_data(cls):
    """Create OverlayAssignment test data."""
    create_overlay_test_data(cls)
    create_device_test_data(cls)

    cls.device_content_type = ContentType.objects.get(app_label="dcim", model="device")

    cls.assignments = [
        models.OverlayAssignment.objects.create(
            overlay=cls.overlays[0],
            assigned_object_type=cls.device_content_type,
            assigned_object_id=cls.devices[0].pk,
            role=choices.OverlayAssignmentRoleChoices.COMPUTE,
            status=cls.assignment_status,
        ),
        models.OverlayAssignment.objects.create(
            overlay=cls.overlays[0],
            assigned_object_type=cls.device_content_type,
            assigned_object_id=cls.devices[1].pk,
            role=choices.OverlayAssignmentRoleChoices.STORAGE,
            status=cls.assignment_status,
        ),
        models.OverlayAssignment.objects.create(
            overlay=cls.overlays[1],
            assigned_object_type=cls.device_content_type,
            assigned_object_id=cls.devices[2].pk,
            status=cls.assignment_status,
        ),
    ]
