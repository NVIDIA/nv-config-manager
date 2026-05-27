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
"""Tests for table definitions."""

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from nautobot.apps.tables import BooleanColumn
from nautobot.dcim.models import (
    Device,
    DeviceType,
    Location,
    LocationType,
    Manufacturer,
    Platform,
    Rack,
)
from nautobot.extras.models import Role, Status
from nautobot.tenancy.models import Tenant

from nv_config_manager.models import BackupConfig, ConfigManagerDeviceStatus, IntendedConfig
from nv_config_manager.tables import ConfigManagerDeviceStatusTable
from nv_config_manager.tests.fixtures import mock_data as data


def create_table_test_data():  # pylint: disable=too-many-locals
    """Create shared mock-topology-shaped data for table column tests."""
    region_type = LocationType.objects.create(name="Region")
    site_type = LocationType.objects.create(name="Site")
    location_status = Status.objects.get_for_model(Location).first()
    device_status = Status.objects.get_for_model(Device).first()
    rack_status = Status.objects.get_for_model(Rack).first()

    region = Location.objects.create(name=data.REGION_NAME, location_type=region_type, status=location_status)
    second_region = Location.objects.create(name="EMEA", location_type=region_type, status=location_status)
    site = Location.objects.create(
        name=data.SITE_NAME,
        parent=region,
        location_type=site_type,
        status=location_status,
    )
    second_site = Location.objects.create(
        name=data.SECOND_SITE_NAME,
        parent=second_region,
        location_type=site_type,
        status=location_status,
    )
    third_site = Location.objects.create(name="LAS01", location_type=site_type, status=location_status)
    first_rack = Rack.objects.create(name=data.RACK_2_NAME, location=site, status=rack_status)
    second_rack = Rack.objects.create(name=data.RACK_1_NAME, location=second_site, status=rack_status)
    first_tenant = Tenant.objects.create(name=data.TENANT_NAME)
    second_tenant = Tenant.objects.create(name=data.SECOND_TENANT_NAME)

    first_role = Role.objects.create(name=data.CORE_ROLE_NAME)
    second_role = Role.objects.create(name=data.LEAF_ROLE_NAME)
    third_role = Role.objects.create(name=data.SPINE_ROLE_NAME)
    manufacturer = Manufacturer.objects.create(name=data.MANUFACTURER_NAME)
    mellanox = Manufacturer.objects.create(name=data.MELLANOX_MANUFACTURER_NAME)
    first_platform = Platform.objects.create(name=data.PLATFORM_NAME, napalm_driver="cumulus")
    second_platform = Platform.objects.create(name=data.SECOND_PLATFORM_NAME, napalm_driver="cumulus")
    first_device_type = DeviceType.objects.create(
        manufacturer=mellanox,
        model=data.THIRD_DEVICE_TYPE_MODEL,
        u_height="2",
    )
    second_device_type = DeviceType.objects.create(
        manufacturer=mellanox,
        model=data.SECOND_DEVICE_TYPE_MODEL,
        u_height="2",
    )
    third_device_type = DeviceType.objects.create(
        manufacturer=manufacturer,
        model=data.DEVICE_TYPE_MODEL,
        u_height="2",
    )
    first_device = Device.objects.create(
        name=data.FOURTH_DEVICE_NAME,
        location=site,
        rack=first_rack,
        tenant=first_tenant,
        device_type=first_device_type,
        role=first_role,
        platform=first_platform,
        status=device_status,
    )
    first_managed_device = ConfigManagerDeviceStatus.objects.create(device=first_device)
    first_managed_device.intended_config = IntendedConfig.objects.create(
        device_id=first_managed_device,
        config_store_instance=data.CONFIG_STORE_UI_URL,
        path=data.CONFIG_PATH,
        commit_id=data.TEST_INTENDED_COMMIT_ID,
        updated=timezone.now(),
        updated_by=data.TEST_RENDER_USER,
        commit_message=data.TEST_COMMIT_MESSAGE,
        template_version=data.TEMPLATE_VERSION,
    )
    first_managed_device.backup_config = BackupConfig.objects.create(
        device_id=first_managed_device,
        config_store_instance=data.CONFIG_STORE_UI_URL,
        path=data.BACKUP_CONFIG_PATH,
        commit_id=data.TEST_BACKUP_COMMIT_ID,
        updated=timezone.now(),
        updated_by=data.TEST_RENDER_USER,
        commit_message=data.TEST_BACKUP_COMMIT_MESSAGE,
        workflow_id=data.TEST_WORKFLOW_ID,
        deployed_commit_id=data.TEST_PENDING_DEPLOYED_COMMIT_ID,
    )

    second_device = Device.objects.create(
        name=data.DEVICE_NAME,
        location=second_site,
        rack=second_rack,
        tenant=second_tenant,
        device_type=second_device_type,
        role=second_role,
        platform=second_platform,
        status=device_status,
    )
    second_managed_device = ConfigManagerDeviceStatus.objects.create(device=second_device)
    second_managed_device.intended_config = IntendedConfig.objects.create(
        device_id=second_managed_device,
        config_store_instance=data.CONFIG_STORE_UI_URL,
        path=data.CONFIG_PATH,
        commit_id=data.TEST_INTENDED_COMMIT_ID,
        updated=timezone.now() - timedelta(hours=73),
        updated_by=data.TEST_RENDER_USER,
        commit_message=data.TEST_COMMIT_MESSAGE,
        template_version=data.TEMPLATE_VERSION,
    )
    second_managed_device.backup_config = BackupConfig.objects.create(
        device_id=second_managed_device,
        config_store_instance=data.CONFIG_STORE_UI_URL,
        path=data.BACKUP_CONFIG_PATH,
        commit_id=data.TEST_BACKUP_COMMIT_ID,
        updated=timezone.now() - timedelta(hours=73),
        updated_by=data.TEST_RENDER_USER,
        commit_message=data.TEST_BACKUP_COMMIT_MESSAGE,
        workflow_id=data.TEST_WORKFLOW_ID,
        deployed_commit_id=data.TEST_PENDING_DEPLOYED_COMMIT_ID,
    )
    third_device = Device.objects.create(
        name=data.THIRD_DEVICE_NAME,
        location=third_site,
        device_type=third_device_type,
        role=third_role,
        status=device_status,
    )
    ConfigManagerDeviceStatus.objects.create(device=third_device)


class TableTestCase(TestCase):
    """Test cases for tables."""

    def test_model_table_orderable(self):
        """Assert that orderable is set to True by default."""
        with self.subTest(table=ConfigManagerDeviceStatusTable):
            queryset = ConfigManagerDeviceStatusTable.Meta.model.objects.all()
            self.assertTrue(ConfigManagerDeviceStatusTable(queryset).orderable)


class ColumnTestCases:  # pylint: disable=too-few-public-methods
    """Wrapper class for columns tests."""

    class CustomColumnTestCase(TestCase):
        """Test Pending Column."""

        column_name: str

        @classmethod
        def setUpTestData(cls):
            create_table_test_data()

        def test_columns(self):
            """Test is_pending column"""
            queryset = ConfigManagerDeviceStatus.objects.all()

            column = ConfigManagerDeviceStatusTable.base_columns[  # pylint: disable=no-member
                self.column_name
            ]
            ordered_queryset, _ = column.order(queryset, is_descending=False)
            ordered_results = list(ordered_queryset)

            # Ascending order
            self.assertEqual(
                getattr(ordered_results[0], self.column_name),
                False,
            )
            self.assertEqual(
                getattr(ordered_results[1], self.column_name),
                True,
            )
            self.assertEqual(
                getattr(ordered_results[2], self.column_name),
                True,
            )

            # Descending order
            ordered_queryset, _ = column.order(queryset, is_descending=True)
            ordered_results = list(ordered_queryset)
            self.assertEqual(
                getattr(ordered_results[2], self.column_name),
                False,
            )
            self.assertEqual(
                getattr(ordered_results[1], self.column_name),
                True,
            )
            self.assertEqual(
                getattr(ordered_results[0], self.column_name),
                True,
            )

    class ColumnTestCase(TestCase):
        """Assert that columns are orderable."""

        obj_key: str
        column_name: str
        asc_first_obj_name: str
        asc_second_obj_name: str
        asc_third_obj_name = "None"

        @classmethod
        def setUpTestData(cls):
            """Set up test data for the entire TestCase."""
            create_table_test_data()

        def test_column_ordering(self):
            """Test column ordering."""
            queryset = ConfigManagerDeviceStatus.objects.all()

            column = ConfigManagerDeviceStatusTable.base_columns[  # pylint: disable=no-member
                self.column_name
            ]
            ordered_queryset, _ = column.order(queryset, is_descending=False)
            ordered_results = list(ordered_queryset)

            # Ascending order
            self.assertEqual(
                str(getattr(ordered_results[0].device, self.obj_key)),
                self.asc_first_obj_name,
            )
            self.assertEqual(
                str(getattr(ordered_results[1].device, self.obj_key)),
                self.asc_second_obj_name,
            )
            self.assertEqual(
                str(getattr(ordered_results[2].device, self.obj_key)),
                self.asc_third_obj_name,
            )

            # Descending order
            ordered_queryset, _ = column.order(queryset, is_descending=True)
            ordered_results = list(ordered_queryset)
            self.assertEqual(
                str(getattr(ordered_results[2].device, self.obj_key)),
                self.asc_first_obj_name,
            )
            self.assertEqual(
                str(getattr(ordered_results[1].device, self.obj_key)),
                self.asc_second_obj_name,
            )
            self.assertEqual(
                str(getattr(ordered_results[0].device, self.obj_key)),
                self.asc_third_obj_name,
            )


class RoleColumnTest(ColumnTestCases.ColumnTestCase):
    """Test Device Role Column is orderable."""

    column_name = "device_role"
    obj_key = "role"
    asc_first_obj_name = data.CORE_ROLE_NAME
    asc_second_obj_name = data.LEAF_ROLE_NAME
    asc_third_obj_name = data.SPINE_ROLE_NAME  # NOTE: device role is required so it will never be blank


class DeviceTypeColumnTest(ColumnTestCases.ColumnTestCase):
    """Test Device Type Column is orderable."""

    column_name = "device_type"
    obj_key = "device_type"
    asc_first_obj_name = data.THIRD_DEVICE_TYPE_MODEL
    asc_second_obj_name = data.SECOND_DEVICE_TYPE_MODEL
    asc_third_obj_name = data.DEVICE_TYPE_MODEL  # NOTE: device type is required so it will never be blank


class PlatformColumnTest(ColumnTestCases.ColumnTestCase):
    """Test Platform Column is orderable."""

    column_name = "platform"
    obj_key = "platform"
    asc_first_obj_name = data.PLATFORM_NAME
    asc_second_obj_name = data.SECOND_PLATFORM_NAME


class TenantColumnTest(ColumnTestCases.ColumnTestCase):
    """Test Tenant Column is orderable."""

    column_name = "tenant"
    obj_key = "tenant"
    asc_first_obj_name = data.TENANT_NAME
    asc_second_obj_name = data.SECOND_TENANT_NAME


class RackColumnTest(ColumnTestCases.ColumnTestCase):
    """Test Rack Column is orderable."""

    column_name = "rack"
    obj_key = "rack"
    asc_first_obj_name = data.RACK_2_NAME
    asc_second_obj_name = data.RACK_1_NAME


class PendingColumnTest(ColumnTestCases.CustomColumnTestCase):
    """Test Pending Column is orderable."""

    column_name = "is_pending"
    obj_key = "is_pending"
    asc_first_obj_name = data.RACK_2_NAME
    asc_second_obj_name = data.RACK_1_NAME


class IsAggregateManagedColumnTest(TestCase):
    """Test is_aggregate_managed column is displayed and orderable."""

    def setUp(self):
        """Set up test data."""
        manufacturer = Manufacturer.objects.create(name=data.MANUFACTURER_NAME)
        site_type, _ = LocationType.objects.get_or_create(name="Site")
        location_status = Status.objects.get_for_model(Location).first()
        device_status = Status.objects.get_for_model(Device).first()

        self.site = Location.objects.create(name=data.SITE_NAME, location_type=site_type, status=location_status)

        device_type = DeviceType.objects.create(model=data.DEVICE_TYPE_MODEL, manufacturer=manufacturer)
        device_role = Role.objects.create(name=data.AGGREGATE_ROLE_NAME)

        self.device1 = Device.objects.create(
            name=data.AGGREGATE_DEVICE_NAME,
            device_type=device_type,
            role=device_role,
            location=self.site,
            status=device_status,
        )

        self.device2 = Device.objects.create(
            name=data.DEVICE_NAME,
            device_type=device_type,
            role=device_role,
            location=self.site,
            status=device_status,
        )

        self.device3 = Device.objects.create(
            name=data.SECOND_DEVICE_NAME,
            device_type=device_type,
            role=device_role,
            location=self.site,
            status=device_status,
        )

        self.managed_device1 = ConfigManagerDeviceStatus.objects.create(device=self.device1, is_aggregate_managed=True)
        self.managed_device2 = ConfigManagerDeviceStatus.objects.create(device=self.device2, is_aggregate_managed=False)
        self.managed_device3 = ConfigManagerDeviceStatus.objects.create(device=self.device3, is_aggregate_managed=False)

    def test_is_aggregate_managed_column_in_table(self):
        """Test that is_aggregate_managed column is present in the table."""
        table = ConfigManagerDeviceStatusTable(ConfigManagerDeviceStatus.objects.all())
        self.assertIn("is_aggregate_managed", table.columns.names())

    def test_is_aggregate_managed_column_ordering(self):
        """Test that is_aggregate_managed column can be ordered using Nautobot's BooleanColumn."""
        queryset = ConfigManagerDeviceStatus.objects.all()

        # Get the BooleanColumn from the table
        table = ConfigManagerDeviceStatusTable(queryset)
        column = table.columns["is_aggregate_managed"]

        # Test that the column is a BooleanColumn
        self.assertIsInstance(column.column, BooleanColumn)

        # Test ordering through the table's sort functionality
        table_asc = ConfigManagerDeviceStatusTable(queryset.order_by("is_aggregate_managed"))
        ordered_results_asc = list(table_asc.data)

        # Should have False values first, then True values in ascending order
        false_count = sum(1 for result in ordered_results_asc if not result.is_aggregate_managed)
        true_count = sum(1 for result in ordered_results_asc if result.is_aggregate_managed)

        self.assertEqual(false_count, 2)  # Two False values
        self.assertEqual(true_count, 1)  # One True value

        # Test descending order
        table_desc = ConfigManagerDeviceStatusTable(queryset.order_by("-is_aggregate_managed"))
        ordered_results_desc = list(table_desc.data)

        # Verify we get the same count but in different order
        false_count_desc = sum(1 for result in ordered_results_desc if not result.is_aggregate_managed)
        true_count_desc = sum(1 for result in ordered_results_desc if result.is_aggregate_managed)

        self.assertEqual(false_count_desc, 2)
        self.assertEqual(true_count_desc, 1)
