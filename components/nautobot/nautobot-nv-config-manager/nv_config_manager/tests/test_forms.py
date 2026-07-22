#  SPDX-FileCopyrightText: Copyright (c) "2025" NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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
"""Tests for nv_config_manager forms."""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from nautobot.dcim.models import Device, DeviceType, Location, LocationType, Manufacturer
from nautobot.extras.models import Role, Status
from nautobot.tenancy.models import Tenant

from nv_config_manager.forms import ConfigManagerDeviceStatusBulkAddForm
from nv_config_manager.models import ConfigManagerDeviceStatus
from nv_config_manager.tests.fixtures import mock_data as data
from nv_config_manager.utils import (
    bulk_create_managed_devices,
    get_eligible_unmanaged_devices,
    nullbool_to_bool,
)


class EligibleDeviceQueryTestCase(TestCase):
    """Tests for unmanaged-device candidate selection."""

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name=data.MANUFACTURER_NAME)
        site_type = LocationType.objects.create(name="Bulk Add Site Type")
        module_type = LocationType.objects.create(name="Bulk Add Module Type", parent=site_type)
        location_status = Status.objects.get_for_model(Location).first()
        device_status = Status.objects.get_for_model(Device).first()

        cls.parent_location = Location.objects.create(
            name="Bulk Parent",
            location_type=site_type,
            status=location_status,
        )
        cls.child_location = Location.objects.create(
            name="Bulk Child",
            location_type=module_type,
            parent=cls.parent_location,
            status=location_status,
        )
        cls.tenant_a = Tenant.objects.create(name="Bulk Tenant A")
        cls.tenant_b = Tenant.objects.create(name="Bulk Tenant B")
        cls.device_type = DeviceType.objects.create(
            manufacturer=manufacturer,
            model=data.DEVICE_TYPE_MODEL,
        )
        cls.network_role = Role.objects.create(name="Bulk Network Role", color="111111")
        cls.compute_role = Role.objects.create(name="Bulk Compute Role", color="222222")

        cls.parent_network = Device.objects.create(
            name="bulk-parent-network",
            location=cls.parent_location,
            device_type=cls.device_type,
            role=cls.network_role,
            tenant=cls.tenant_a,
            status=device_status,
        )
        cls.child_network = Device.objects.create(
            name="bulk-child-network",
            location=cls.child_location,
            device_type=cls.device_type,
            role=cls.network_role,
            tenant=cls.tenant_a,
            status=device_status,
        )
        cls.child_compute = Device.objects.create(
            name="bulk-child-compute",
            location=cls.child_location,
            device_type=cls.device_type,
            role=cls.compute_role,
            tenant=cls.tenant_a,
            status=device_status,
        )
        cls.other_tenant_device = Device.objects.create(
            name="bulk-other-tenant",
            location=cls.child_location,
            device_type=cls.device_type,
            role=cls.network_role,
            tenant=cls.tenant_b,
            status=device_status,
        )
        cls.managed_device = Device.objects.create(
            name="bulk-managed",
            location=cls.child_location,
            device_type=cls.device_type,
            role=cls.network_role,
            tenant=cls.tenant_a,
            status=device_status,
        )
        ConfigManagerDeviceStatus.objects.create(device=cls.managed_device)

    def test_includes_descendant_locations(self):
        """Eligible query includes devices from child locations."""
        eligible = get_eligible_unmanaged_devices(self.parent_location, [self.network_role])
        names = set(eligible.values_list("name", flat=True))
        self.assertIn(self.parent_network.name, names)
        self.assertIn(self.child_network.name, names)

    def test_filters_by_multiple_roles(self):
        """Eligible query matches any selected role."""
        eligible = get_eligible_unmanaged_devices(
            self.parent_location,
            [self.network_role, self.compute_role],
        )
        names = set(eligible.values_list("name", flat=True))
        self.assertIn(self.child_network.name, names)
        self.assertIn(self.child_compute.name, names)

    def test_excludes_managed_devices(self):
        """Already-managed devices are not returned."""
        eligible = get_eligible_unmanaged_devices(self.child_location, [self.network_role])
        self.assertNotIn(self.managed_device.name, set(eligible.values_list("name", flat=True)))

    def test_nullbool_to_bool_defaults_false(self):
        """Tri-state booleans default to False."""
        self.assertFalse(nullbool_to_bool(None))
        self.assertFalse(nullbool_to_bool(False))
        self.assertTrue(nullbool_to_bool(True))

    def test_bulk_create_managed_devices_applies_defaults(self):
        """Bulk create enrolls devices with shared service settings."""
        created_count, skipped_count = bulk_create_managed_devices(
            [self.parent_network, self.child_network],
            render_enabled=True,
            is_aggregate_managed=True,
        )
        self.assertEqual(created_count, 2)
        self.assertEqual(skipped_count, 0)
        managed = ConfigManagerDeviceStatus.objects.get(device=self.parent_network)
        self.assertTrue(managed.render_enabled)
        self.assertTrue(managed.is_aggregate_managed)

    def test_bulk_create_skips_existing_managed_devices(self):
        """Bulk create skips devices that became managed concurrently."""
        created_count, skipped_count = bulk_create_managed_devices(
            [self.managed_device],
        )
        self.assertEqual(created_count, 0)
        self.assertEqual(skipped_count, 1)


class ConfigManagerDeviceStatusBulkAddFormTestCase(TestCase):
    """Tests for the bulk-add form validation."""

    @classmethod
    def setUpTestData(cls):
        manufacturer = Manufacturer.objects.create(name=data.SECOND_MANUFACTURER_NAME)
        site_type = LocationType.objects.create(name="Bulk Form Site Type")
        location_status = Status.objects.get_for_model(Location).first()
        device_status = Status.objects.get_for_model(Device).first()
        cls.location = Location.objects.create(
            name="Bulk Form Site",
            location_type=site_type,
            status=location_status,
        )
        cls.role = Role.objects.create(name="Bulk Form Role", color="333333")
        cls.role.content_types.add(ContentType.objects.get_for_model(Device))
        cls.device_type = DeviceType.objects.create(
            manufacturer=manufacturer,
            model=data.SECOND_DEVICE_TYPE_MODEL,
        )
        cls.device = Device.objects.create(
            name="bulk-form-device",
            location=cls.location,
            device_type=cls.device_type,
            role=cls.role,
            status=device_status,
        )

    def _base_data(self, **overrides):
        data = {
            "location": str(self.location.pk),
            "roles": [str(self.role.pk)],
            "devices": [str(self.device.pk)],
        }
        data.update(overrides)
        return data

    def test_requires_location_roles_and_devices(self):
        """Location, role, and devices are all required."""
        form = ConfigManagerDeviceStatusBulkAddForm({})
        self.assertFalse(form.is_valid())
        self.assertIn("location", form.errors)
        self.assertIn("roles", form.errors)
        self.assertIn("devices", form.errors)

    def test_rejects_ineligible_device_selection(self):
        """A selected device outside the location/role scope is rejected."""
        managed = Device.objects.create(
            name="bulk-form-managed",
            location=self.location,
            device_type=self.device_type,
            role=self.role,
            status=Status.objects.get_for_model(Device).first(),
        )
        ConfigManagerDeviceStatus.objects.create(device=managed)
        form = ConfigManagerDeviceStatusBulkAddForm(self._base_data(devices=[str(managed.pk)]))
        self.assertFalse(form.is_valid())
        self.assertIn("One or more selected devices are not eligible for enrollment.", form.errors["__all__"])

    def test_valid_selection_returns_devices_to_add(self):
        """A valid submission returns the selected devices."""
        form = ConfigManagerDeviceStatusBulkAddForm(self._base_data())
        self.assertTrue(form.is_valid())
        names = set(form.get_devices_to_add().values_list("name", flat=True))
        self.assertEqual(names, {self.device.name})

    def test_roles_dropdown_filtered_to_device_roles(self):
        """The role dropdown is scoped to device roles so its options match validation."""
        form = ConfigManagerDeviceStatusBulkAddForm()
        self.assertEqual(form.fields["roles"].query_params.get("content_types"), "dcim.device")

    def test_rejects_non_device_role(self):
        """A role lacking the dcim.device content type is rejected, not silently accepted."""
        non_device_role = Role.objects.create(name="Bulk Form IPAM Role", color="444444")
        non_device_role.content_types.set([ContentType.objects.get(app_label="ipam", model="prefix")])
        form = ConfigManagerDeviceStatusBulkAddForm(self._base_data(roles=[str(non_device_role.pk)]))
        self.assertFalse(form.is_valid())
        self.assertIn("roles", form.errors)
