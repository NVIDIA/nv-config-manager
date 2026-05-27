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
# pylint: disable=too-many-lines,too-many-ancestors,too-many-public-methods,too-many-instance-attributes
"""API Unit tests for nv_config_manager"""

import uuid
from datetime import datetime
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from nautobot.core.testing.api import APITestCase, APITransactionTestCase
from nautobot.dcim.models import (
    Device,
    DeviceType,
    Location,
    LocationType,
    Manufacturer,
)
from nautobot.extras.models import Role, Status
from rest_framework import status

from nv_config_manager.models import BackupConfig, ConfigManagerDeviceStatus, IntendedConfig
from nv_config_manager.tests.fixtures import mock_data


class ConfigManagerAPITestMixin:
    """Shared setup for Config Manager API tests."""

    def setUp(self):
        """Use an explicit host allowed by the test Nautobot config."""
        super().setUp()
        self.header = {**self.header, "HTTP_HOST": mock_data.TEST_HTTP_HOST}


class ManagedDevicesTest(  # pylint: disable=too-many-ancestors,too-many-public-methods
    ConfigManagerAPITestMixin, APITestCase
):
    """Test module for GET all managed devices API."""

    model = ConfigManagerDeviceStatus

    @classmethod
    def setUpTestData(cls):  # pylint: disable=invalid-name
        """Set up data for the tests."""

        manufacturer, _ = Manufacturer.objects.get_or_create(name=mock_data.MANUFACTURER_NAME)
        location_type, _ = LocationType.objects.get_or_create(name="Site Type")
        location_status = Status.objects.get_for_model(Location).first()

        cls.status_provisioning, _ = Status.objects.get_or_create(
            name="Provisioning", defaults={"description": "Provisioning"}
        )
        cls.site, _ = Location.objects.get_or_create(
            name=mock_data.SITE_NAME,
            location_type=location_type,
            status=location_status,
        )
        cls.device_type, _ = DeviceType.objects.get_or_create(
            manufacturer=manufacturer,
            model=mock_data.DEVICE_TYPE_MODEL,
        )
        cls.device_role, _ = Role.objects.get_or_create(
            name=mock_data.LEAF_ROLE_NAME,
            color="ff0000",
        )
        device_names = [mock_data.DEVICE_NAME, mock_data.SECOND_DEVICE_NAME, mock_data.THIRD_DEVICE_NAME]
        for device_name in device_names:
            _ = Device.objects.get_or_create(
                device_type=cls.device_type,
                role=cls.device_role,
                name=device_name,
                location=cls.site,
                status=cls.status_provisioning,
            )

        cls.devices = Device.objects.all()
        cls.managed_devices = []
        cls.intended_configs = []
        cls.backup_configs = []

        for num in range(3):
            date = timezone.now()
            device = cls.devices[num]

            managed_device, _ = ConfigManagerDeviceStatus.objects.get_or_create(device=device)
            intended_config, _ = IntendedConfig.objects.get_or_create(
                device_id=managed_device,
                config_store_instance=mock_data.CONFIG_STORE_UI_URL,
                path=mock_data.CONFIG_PATH,
                commit_id=mock_data.TEST_INTENDED_COMMIT_ID,
                updated=date,
                updated_by=mock_data.TEST_RENDER_USER,
                commit_message=mock_data.TEST_COMMIT_MESSAGE,
                template_version=mock_data.TEMPLATE_VERSION,
            )
            backup_config, _ = BackupConfig.objects.get_or_create(
                device_id=managed_device,
                config_store_instance=mock_data.CONFIG_STORE_UI_URL,
                path=mock_data.CONFIG_PATH,
                commit_id=mock_data.TEST_INTENDED_COMMIT_ID,
                deployed_commit_id=mock_data.TEST_INTENDED_COMMIT_ID,
                workflow_id=mock_data.TEST_BACKUP_WORKFLOW_ID,
                updated=date,
                updated_by=mock_data.TEST_RENDER_USER,
                commit_message=mock_data.TEST_COMMIT_MESSAGE,
            )
            cls.managed_devices.append(managed_device)
            cls.intended_configs.append(intended_config)
            cls.backup_configs.append(backup_config)

    def test_get_all_managed_devices(self):
        """Test getting all managed devices."""
        self.add_permissions("nv_config_manager.view_configmanagerdevicestatus")
        url = reverse(
            "plugins-api:nv_config_manager-api:configmanagerdevicestatus-list",
        )
        response = self.client.get(f"{url}", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)

    def test_get_single_managed_device_with_device_id(self):
        """Test getting a single managed Device."""
        self.add_permissions("nv_config_manager.view_configmanagerdevicestatus")
        url = reverse(
            "plugins-api:nv_config_manager-api:configmanagerdevicestatus-detail",
            kwargs={"pk": self.devices[0].pk},
        )

        device = self.devices[0]
        managed_device = self.managed_devices[0]

        response = self.client.get(f"{url}?format=api", **self.header)
        fetched_device = response.data["device"]

        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["display"], device.name)
        self.assertEqual(fetched_device["id"], device.id)
        self.assertEqual(fetched_device["id"], managed_device.id)

    def test_get_single_managed_device_with_invalid_device_id(self):
        """Test fetching a managed device with a device id that isn't a managed device"""
        self.add_permissions("nv_config_manager.view_configmanagerdevicestatus")
        url = reverse(
            "plugins-api:nv_config_manager-api:configmanagerdevicestatus-detail",
            kwargs={"pk": "invalid-id"},
        )
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_404_NOT_FOUND)

    def test_create_config_with_valid_store_instance(self):
        """Test creating config with an invalid config instance url."""
        self.add_permissions("nv_config_manager.add_configmanagerdevicestatus")
        self.add_permissions("nv_config_manager.view_configmanagerdevicestatus")
        self.add_permissions("nv_config_manager.add_intendedconfig")
        self.add_permissions("nv_config_manager.view_intendedconfig")

        device = Device.objects.create(
            device_type=self.device_type,
            role=self.device_role,
            name=mock_data.FOURTH_DEVICE_NAME,
            location=self.site,
            status=self.status_provisioning,
        )
        device2 = Device.objects.create(
            device_type=self.device_type,
            role=self.device_role,
            name=mock_data.FIFTH_DEVICE_NAME,
            location=self.site,
            status=self.status_provisioning,
        )
        managed_device, _ = ConfigManagerDeviceStatus.objects.get_or_create(device=device)
        managed_device2, _ = ConfigManagerDeviceStatus.objects.get_or_create(device=device2)

        data = {
            "device_id": managed_device.id,
            "config_store_instance": mock_data.CONFIG_STORE_UI_URL,
            "path": mock_data.CONFIG_PATH,
            "commit_id": mock_data.TEST_INTENDED_COMMIT_ID,
            "updated": mock_data.TEST_API_TIMESTAMP,
            "updated_by": mock_data.TEST_RENDER_USER,
            "commit_message": mock_data.TEST_COMMIT_MESSAGE,
            "template_version": mock_data.TEMPLATE_VERSION,
        }
        data2 = {
            "device_id": managed_device2.id,
            "config_store_instance": mock_data.CONFIG_STORE_HTTP_URL,
            "path": mock_data.CONFIG_PATH,
            "commit_id": mock_data.TEST_INTENDED_COMMIT_ID,
            "updated": mock_data.TEST_API_TIMESTAMP,
            "updated_by": mock_data.TEST_RENDER_USER,
            "commit_message": mock_data.TEST_COMMIT_MESSAGE,
            "template_version": mock_data.TEMPLATE_VERSION,
        }
        intended_config_url = reverse(
            "plugins-api:nv_config_manager-api:intendedconfig-list",
        )

        response = self.client.post(intended_config_url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        response = self.client.post(intended_config_url, data2, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

    def test_create_config_with_invalid_store_instance(self):
        """Test creating config with an invalid config instance url."""
        self.add_permissions("nv_config_manager.add_configmanagerdevicestatus")
        self.add_permissions("nv_config_manager.view_configmanagerdevicestatus")
        self.add_permissions("nv_config_manager.add_intendedconfig")
        self.add_permissions("nv_config_manager.view_intendedconfig")

        device = Device.objects.create(
            device_type=self.device_type,
            role=self.device_role,
            name=mock_data.FOURTH_DEVICE_NAME,
            location=self.site,
            status=self.status_provisioning,
        )
        device2 = Device.objects.create(
            device_type=self.device_type,
            role=self.device_role,
            name=mock_data.FIFTH_DEVICE_NAME,
            location=self.site,
            status=self.status_provisioning,
        )
        managed_device, _ = ConfigManagerDeviceStatus.objects.get_or_create(device=device)
        managed_device2, _ = ConfigManagerDeviceStatus.objects.get_or_create(device=device2)

        data = {
            "device_id": managed_device.id,
            "config_store_instance": "no-https.com",
            "path": mock_data.CONFIG_PATH,
            "commit_id": mock_data.TEST_INTENDED_COMMIT_ID,
            "updated": mock_data.TEST_API_TIMESTAMP,
            "updated_by": mock_data.TEST_RENDER_USER,
            "commit_message": mock_data.TEST_COMMIT_MESSAGE,
            "template_version": mock_data.TEMPLATE_VERSION,
        }
        data2 = {
            "device_id": managed_device2.id,
            "config_store_instance": "no-http.com",
            "path": mock_data.CONFIG_PATH,
            "commit_id": mock_data.TEST_INTENDED_COMMIT_ID,
            "updated": mock_data.TEST_API_TIMESTAMP,
            "updated_by": mock_data.TEST_RENDER_USER,
            "commit_message": mock_data.TEST_COMMIT_MESSAGE,
            "template_version": mock_data.TEMPLATE_VERSION,
        }
        intended_config_url = reverse(
            "plugins-api:nv_config_manager-api:intendedconfig-list",
        )

        response = self.client.post(intended_config_url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        response = self.client.post(intended_config_url, data2, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)

    def test_creating_intended_config_with_invalid_device_id(self):
        """Test pushing an intended config to an invalid device"""
        self.add_permissions("nv_config_manager.add_intendedconfig")
        url = reverse(
            "plugins-api:nv_config_manager-api:intendedconfig-list",
        )
        data = {
            "device_id": "invalid-id",
            "config_store_instance": mock_data.CONFIG_STORE_UI_URL,
            "path": mock_data.CONFIG_PATH,
            "commit_id": mock_data.TEST_INTENDED_COMMIT_ID,
            "updated": mock_data.TEST_API_TIMESTAMP,
            "updated_by": mock_data.TEST_RENDER_USER,
            "commit_message": mock_data.TEST_COMMIT_MESSAGE,
            "template_version": mock_data.TEMPLATE_VERSION,
        }
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_get_all_managed_intended_configs(self):
        """Test getting all managed Intended Configs."""
        self.add_permissions("nv_config_manager.view_intendedconfig")
        url = reverse(
            "plugins-api:nv_config_manager-api:intendedconfig-list",
        )
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)

    def test_get_single_managed_intended_config_success(self):
        """Test getting single managed Intended Config."""
        self.add_permissions("nv_config_manager.view_intendedconfig")
        url = reverse(
            "plugins-api:nv_config_manager-api:intendedconfig-detail",
            kwargs={"pk": self.intended_configs[0].pk},
        )
        response = self.client.get(url, **self.header)
        intended_config = self.intended_configs[0]
        fetched_intended_config = response.data

        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(
            fetched_intended_config["config_store_instance"],
            intended_config.config_store_instance,
        )
        self.assertEqual(fetched_intended_config["path"], intended_config.path)
        self.assertEqual(str(fetched_intended_config["commit_id"]), str(intended_config.commit_id))
        self.assertEqual(
            fetched_intended_config["updated"],
            intended_config.updated.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(fetched_intended_config["updated_by"], intended_config.updated_by)
        self.assertEqual(fetched_intended_config["commit_message"], intended_config.commit_message)

    def test_get_all_managed_backup_configs(self):
        """Test getting all managed Backup Configs."""
        self.add_permissions("nv_config_manager.view_backupconfig")
        url = reverse(
            "plugins-api:nv_config_manager-api:backupconfig-list",
        )
        response = self.client.get(url, **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 3)

    def test_get_single_managed_backup_config(self):
        """Test getting single managed Backup Config."""
        self.add_permissions("nv_config_manager.view_backupconfig")
        url = reverse(
            "plugins-api:nv_config_manager-api:backupconfig-detail",
            kwargs={"pk": self.backup_configs[0].pk},
        )
        response = self.client.get(url, **self.header)
        backup_config = self.backup_configs[0]
        fetched_backup_config = response.data

        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(
            fetched_backup_config["config_store_instance"],
            backup_config.config_store_instance,
        )
        self.assertEqual(fetched_backup_config["path"], backup_config.path)
        self.assertEqual(str(fetched_backup_config["commit_id"]), str(backup_config.commit_id))
        self.assertEqual(
            fetched_backup_config["updated"],
            backup_config.updated.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        )
        self.assertEqual(fetched_backup_config["updated_by"], backup_config.updated_by)
        self.assertEqual(fetched_backup_config["commit_message"], backup_config.commit_message)
        self.assertEqual(fetched_backup_config["workflow_id"], backup_config.workflow_id)

    def test_creating_backup_config_with_invalid_device_id(self):
        """Test pushing an backup config to an invalid device"""
        self.add_permissions("nv_config_manager.add_backupconfig")
        url = reverse(
            "plugins-api:nv_config_manager-api:backupconfig-list",
        )
        data = {
            "device_id": "invalid-id",
            "config_store_instance": mock_data.CONFIG_STORE_UI_URL,
            "path": mock_data.CONFIG_PATH,
            "commit_id": mock_data.TEST_INTENDED_COMMIT_ID,
            "updated": mock_data.TEST_API_TIMESTAMP,
            "updated_by": mock_data.TEST_RENDER_USER,
            "commit_message": mock_data.TEST_COMMIT_MESSAGE,
            "deployed_commit_id": mock_data.TEST_INTENDED_COMMIT_ID,
            "workflow_id": mock_data.TEST_BACKUP_WORKFLOW_ID,
        }
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_500_INTERNAL_SERVER_ERROR)

    def test_creating_intended_config_to_new_managed_device_transaction_fail(self):
        """Test that a failure to create the intended config after creating the
        managed device results in a rollback."""
        self.add_permissions("nv_config_manager.add_configmanagerdevicestatus")
        self.add_permissions("nv_config_manager.view_configmanagerdevicestatus")
        self.add_permissions("nv_config_manager.add_intendedconfig")
        intended_config_url = reverse(
            "plugins-api:nv_config_manager-api:intendedconfig-list",
        )

        device = Device.objects.create(
            device_type=self.device_type,
            role=self.device_role,
            name=mock_data.FOURTH_DEVICE_NAME,
            location=self.site,
            status=self.status_provisioning,
        )
        managed_device_url = reverse(
            "plugins-api:nv_config_manager-api:configmanagerdevicestatus-detail",
            kwargs={"pk": device.pk},
        )

        response = self.client.get(managed_device_url, **self.header)
        self.assertHttpStatus(response, status.HTTP_404_NOT_FOUND)

        data = {
            "device_id": device.id,
            "config_store_instance": mock_data.CONFIG_STORE_UI_URL,
            "path": mock_data.CONFIG_PATH,
            "commit_id": mock_data.TEST_INTENDED_COMMIT_ID,
            "updated": mock_data.TEST_API_TIMESTAMP,
            "updated_by": mock_data.TEST_RENDER_USER,
            "commit_message": mock_data.TEST_COMMIT_MESSAGE,
            "template_version": mock_data.TEMPLATE_VERSION,
        }

        # Force the intended config creation to fail after device is created
        with patch(
            "nv_config_manager.api.views.IntendedConfig.objects.create",
            side_effect=Exception(),
        ):
            response = self.client.post(intended_config_url, data, format="json", **self.header)
            self.assertHttpStatus(response, status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Confirm the device creation was rolled back
        response = self.client.get(managed_device_url, **self.header)
        self.assertHttpStatus(response, status.HTTP_404_NOT_FOUND)

    def test_creating_intended_config_invalid_device_id(self):
        """Test creating managed device with invalid device id."""
        self.add_permissions("nv_config_manager.add_configmanagerdevicestatus")
        self.add_permissions("nv_config_manager.view_configmanagerdevicestatus")
        self.add_permissions("nv_config_manager.add_intendedconfig")
        intended_config_url = reverse(
            "plugins-api:nv_config_manager-api:intendedconfig-list",
        )

        data = {
            "device_id": uuid.uuid4(),
            "config_store_instance": mock_data.CONFIG_STORE_UI_URL,
            "path": mock_data.CONFIG_PATH,
            "commit_id": mock_data.TEST_INTENDED_COMMIT_ID,
            "updated": mock_data.TEST_API_TIMESTAMP,
            "updated_by": mock_data.TEST_RENDER_USER,
            "commit_message": mock_data.TEST_COMMIT_MESSAGE,
            "template_version": mock_data.TEMPLATE_VERSION,
        }

        response = self.client.post(intended_config_url, data, format="json", **self.header)
        self.assertHttpStatus(response, 404)

    def test_creating_backup_config_invalid_device_id(self):
        """Test creating managed device with invalid device id."""
        self.add_permissions("nv_config_manager.add_configmanagerdevicestatus")
        self.add_permissions("nv_config_manager.view_configmanagerdevicestatus")
        self.add_permissions("nv_config_manager.add_backupconfig")
        backup_config_url = reverse(
            "plugins-api:nv_config_manager-api:backupconfig-list",
        )

        data = {
            "device_id": uuid.uuid4(),
            "config_store_instance": mock_data.CONFIG_STORE_UI_URL,
            "path": mock_data.CONFIG_PATH,
            "commit_id": mock_data.TEST_INTENDED_COMMIT_ID,
            "updated": mock_data.TEST_API_TIMESTAMP,
            "updated_by": mock_data.TEST_RENDER_USER,
            "commit_message": mock_data.TEST_COMMIT_MESSAGE,
            "deployed_commit_id": mock_data.TEST_INTENDED_COMMIT_ID,
            "workflow_id": mock_data.TEST_BACKUP_WORKFLOW_ID,
        }

        response = self.client.post(backup_config_url, data, format="json", **self.header)
        self.assertHttpStatus(response, 404)

    def test_is_aggregate_managed_field_in_api_response(self):
        """Test that is_aggregate_managed field is included in API responses."""
        self.add_permissions("nv_config_manager.view_configmanagerdevicestatus")

        # Update one of the managed devices to have is_aggregate_managed=True
        managed_device = self.managed_devices[0]
        managed_device.is_aggregate_managed = True
        managed_device.save()

        url = reverse(
            "plugins-api:nv_config_manager-api:configmanagerdevicestatus-detail",
            kwargs={"pk": managed_device.pk},
        )

        response = self.client.get(f"{url}?format=api", **self.header)

        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertIn("is_aggregate_managed", response.data)
        self.assertTrue(response.data["is_aggregate_managed"])


class ManagedDevicesTransactionTest(ConfigManagerAPITestMixin, APITransactionTestCase):
    """Test module for managed-device tests that require immediate database commits."""

    model = ConfigManagerDeviceStatus

    def setUp(self):  # pylint: disable=invalid-name
        """Set up data for each test."""
        # Call parent setUp to initialize user and other APITransactionTestCase setup
        super().setUp()

        manufacturer, _ = Manufacturer.objects.get_or_create(name=mock_data.MANUFACTURER_NAME)
        location_type, _ = LocationType.objects.get_or_create(name="Site Type")
        location_status = Status.objects.get_for_model(Location).first()

        self.status_provisioning, _ = Status.objects.get_or_create(
            name="Provisioning", defaults={"description": "Provisioning"}
        )
        self.site, _ = Location.objects.get_or_create(
            name=mock_data.SITE_NAME, location_type=location_type, status=location_status
        )
        self.device_type, _ = DeviceType.objects.get_or_create(
            manufacturer=manufacturer,
            model=mock_data.DEVICE_TYPE_MODEL,
        )
        self.device_role, _ = Role.objects.get_or_create(
            name=mock_data.LEAF_ROLE_NAME,
            color="ff0000",
        )

        # Create test devices and fixture data for update tests
        self.devices = []
        self.managed_devices = []
        self.intended_configs = []
        self.backup_configs = []

        device_names = [
            mock_data.CONFIG_STORE_DEVICE_NAME,
            mock_data.ARISTA_DEVICE_NAME,
            mock_data.SECOND_ARISTA_DEVICE_NAME,
        ]
        for device_name in device_names:
            device = Device.objects.create(
                device_type=self.device_type,
                role=self.device_role,
                name=device_name,
                location=self.site,
                status=self.status_provisioning,
            )

            managed_device = ConfigManagerDeviceStatus.objects.create(device=device)
            intended_config = IntendedConfig.objects.create(
                device_id=managed_device,
                config_store_instance=mock_data.CONFIG_STORE_UI_URL,
                path=mock_data.CONFIG_PATH,
                commit_id=mock_data.TEST_INTENDED_COMMIT_ID,
                updated=timezone.now(),
                updated_by=mock_data.TEST_RENDER_USER,
                commit_message=mock_data.TEST_COMMIT_MESSAGE,
                template_version=mock_data.TEMPLATE_VERSION,
            )
            backup_config = BackupConfig.objects.create(
                device_id=managed_device,
                config_store_instance=mock_data.CONFIG_STORE_UI_URL,
                path=mock_data.CONFIG_PATH,
                commit_id=mock_data.TEST_INTENDED_COMMIT_ID,
                deployed_commit_id=mock_data.TEST_INTENDED_COMMIT_ID,
                workflow_id=mock_data.TEST_BACKUP_WORKFLOW_ID,
                updated=timezone.now(),
                updated_by=mock_data.TEST_RENDER_USER,
                commit_message=mock_data.TEST_COMMIT_MESSAGE,
            )

            self.devices.append(device)
            self.managed_devices.append(managed_device)
            self.intended_configs.append(intended_config)
            self.backup_configs.append(backup_config)

    def test_create_single_managed_device_no_config(self):
        """Test creating a single managed device with no config."""
        self.add_permissions("dcim.add_device")
        device = Device.objects.create(
            device_type=self.device_type,
            role=self.device_role,
            name=mock_data.FOURTH_DEVICE_NAME,
            location=self.site,
            status=self.status_provisioning,
        )
        url = reverse(
            "plugins-api:nv_config_manager-api:configmanagerdevicestatus-list",
        )

        data = {"device": device.id}

        self.add_permissions("nv_config_manager.add_configmanagerdevicestatus")
        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

    def test_create_managed_device_with_is_aggregate_managed(self):
        """Test creating a managed device with is_aggregate_managed field."""
        self.add_permissions("dcim.add_device")
        self.add_permissions("nv_config_manager.add_configmanagerdevicestatus")

        device = Device.objects.create(
            device_type=self.device_type,
            role=self.device_role,
            name=mock_data.AGGREGATE_DEVICE_NAME,
            location=self.site,
            status=self.status_provisioning,
        )

        url = reverse("plugins-api:nv_config_manager-api:configmanagerdevicestatus-list")
        data = {
            "device": device.id,
            "is_aggregate_managed": True,
            "render_enabled": False,
            "ztp_enabled": False,
            "deploy_enabled": False,
            "backup_enabled": False,
        }

        response = self.client.post(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertTrue(response.data["is_aggregate_managed"])

        # Verify in database
        created_managed_device = ConfigManagerDeviceStatus.objects.get(device=device)
        self.assertTrue(created_managed_device.is_aggregate_managed)

    def test_create_single_managed_device_with_intended_config(self):
        """Test creating a single managed device by pushing an intended config."""
        self.add_permissions("nv_config_manager.add_configmanagerdevicestatus")
        self.add_permissions("nv_config_manager.view_configmanagerdevicestatus")
        self.add_permissions("nv_config_manager.add_intendedconfig")
        intended_config_url = reverse(
            "plugins-api:nv_config_manager-api:intendedconfig-list",
        )

        device = Device.objects.create(
            device_type=self.device_type,
            role=self.device_role,
            name=mock_data.FOURTH_DEVICE_NAME,
            location=self.site,
            status=self.status_provisioning,
        )
        managed_device_url = reverse(
            "plugins-api:nv_config_manager-api:configmanagerdevicestatus-detail",
            kwargs={"pk": device.pk},
        )

        response = self.client.get(f"{managed_device_url}?format=api", **self.header)
        self.assertHttpStatus(response, status.HTTP_404_NOT_FOUND)

        data = {
            "device_id": device.id,
            "config_store_instance": mock_data.CONFIG_STORE_UI_URL,
            "path": mock_data.CONFIG_PATH,
            "commit_id": mock_data.TEST_INTENDED_COMMIT_ID,
            "updated": mock_data.TEST_API_TIMESTAMP,
            "updated_by": mock_data.TEST_RENDER_USER,
            "commit_message": mock_data.TEST_COMMIT_MESSAGE,
            "template_version": mock_data.TEMPLATE_VERSION,
        }

        response = self.client.post(intended_config_url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)

        response = self.client.get(f"{managed_device_url}?format=api", **self.header)
        fetched_device = response.data["device"]
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data["display"], device.name)
        self.assertEqual(fetched_device["id"], device.id)

    def test_create_intended_config_for_managed_device(self):
        """Test creating an Intended config for a managed device."""
        self.add_permissions("nv_config_manager.add_intendedconfig")
        url = reverse(
            "plugins-api:nv_config_manager-api:intendedconfig-list",
        )
        device = Device.objects.create(
            device_type=self.device_type,
            role=self.device_role,
            name=mock_data.FOURTH_DEVICE_NAME,
            location=self.site,
            status=self.status_provisioning,
        )

        data = {
            "device_id": device.id,
            "config_store_instance": mock_data.CONFIG_STORE_UI_URL,
            "path": mock_data.CONFIG_PATH,
            "commit_id": mock_data.TEST_INTENDED_COMMIT_ID,
            "updated": mock_data.TEST_API_TIMESTAMP,
            "updated_by": mock_data.TEST_RENDER_USER,
            "commit_message": mock_data.TEST_COMMIT_MESSAGE,
            "template_version": mock_data.TEMPLATE_VERSION,
        }
        response = self.client.post(url, data, format="json", **self.header)
        intended_config_response = response.data
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(
            intended_config_response["config_store_instance"],
            data["config_store_instance"],
        )
        self.assertEqual(intended_config_response["path"], data["path"])
        self.assertEqual(str(intended_config_response["commit_id"]), str(data["commit_id"]))
        original_datetime = datetime.fromisoformat(data["updated"])

        utc_datetime_str = original_datetime.replace(tzinfo=None).isoformat() + "Z"
        self.assertEqual(intended_config_response["updated"], utc_datetime_str)
        self.assertEqual(intended_config_response["updated_by"], data["updated_by"])
        self.assertEqual(intended_config_response["commit_message"], data["commit_message"])
        self.assertEqual(intended_config_response["template_version"], data["template_version"])

    def test_create_backup_config_for_managed_device(self):
        """Test creating an Backup config for a managed device."""
        self.add_permissions("nv_config_manager.add_backupconfig")
        url = reverse(
            "plugins-api:nv_config_manager-api:backupconfig-list",
        )
        device = Device.objects.create(
            device_type=self.device_type,
            role=self.device_role,
            name=mock_data.FOURTH_DEVICE_NAME,
            location=self.site,
            status=self.status_provisioning,
        )
        data = {
            "device_id": device.id,
            "config_store_instance": mock_data.CONFIG_STORE_UI_URL,
            "path": mock_data.CONFIG_PATH,
            "commit_id": mock_data.TEST_INTENDED_COMMIT_ID,
            "updated": mock_data.TEST_API_TIMESTAMP,
            "updated_by": mock_data.TEST_RENDER_USER,
            "commit_message": mock_data.TEST_COMMIT_MESSAGE,
            "deployed_commit_id": mock_data.TEST_INTENDED_COMMIT_ID,
            "workflow_id": mock_data.TEST_BACKUP_WORKFLOW_ID,
        }
        response = self.client.post(url, data, format="json", **self.header)
        backup_config_response = response.data
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(
            backup_config_response["config_store_instance"],
            data["config_store_instance"],
        )
        self.assertEqual(backup_config_response["path"], data["path"])
        self.assertEqual(str(backup_config_response["commit_id"]), str(data["commit_id"]))
        original_datetime = datetime.fromisoformat(data["updated"])

        utc_datetime_str = original_datetime.replace(tzinfo=None).isoformat() + "Z"
        self.assertEqual(backup_config_response["updated"], utc_datetime_str)
        self.assertEqual(backup_config_response["updated_by"], data["updated_by"])
        self.assertEqual(backup_config_response["commit_message"], data["commit_message"])
        self.assertEqual(str(backup_config_response["deployed_commit_id"]), str(data["deployed_commit_id"]))
        self.assertEqual(backup_config_response["workflow_id"], data["workflow_id"])

    def test_creating_intended_config_to_new_managed_device(self):
        """Test pushing a intended config to a managed device with no configs"""
        self.add_permissions("nv_config_manager.add_configmanagerdevicestatus")
        self.add_permissions("nv_config_manager.view_configmanagerdevicestatus")
        self.add_permissions("nv_config_manager.add_intendedconfig")
        self.add_permissions("nv_config_manager.view_intendedconfig")
        self.add_permissions("dcim.add_device")
        device = Device.objects.create(
            device_type=self.device_type,
            role=self.device_role,
            name=mock_data.FOURTH_DEVICE_NAME,
            location=self.site,
            status=self.status_provisioning,
        )
        create_managed_device_url = reverse(
            "plugins-api:nv_config_manager-api:configmanagerdevicestatus-list",
        )
        create_intended_config_url = reverse("plugins-api:nv_config_manager-api:intendedconfig-list")
        get_intended_config_url = reverse(
            "plugins-api:nv_config_manager-api:intendedconfig-detail",
            kwargs={"pk": device.id},
        )

        data = {"device": device.id}

        create_managed_response = self.client.post(create_managed_device_url, data, format="json", **self.header)
        self.assertHttpStatus(create_managed_response, status.HTTP_201_CREATED)

        get_intended_config_response = self.client.get(get_intended_config_url, **self.header)
        self.assertHttpStatus(get_intended_config_response, status.HTTP_404_NOT_FOUND)

        data = {
            "device_id": device.id,
            "config_store_instance": mock_data.CONFIG_STORE_UI_URL,
            "path": mock_data.CONFIG_PATH,
            "commit_id": mock_data.TEST_INTENDED_COMMIT_ID,
            "updated": mock_data.TEST_API_TIMESTAMP,
            "updated_by": mock_data.TEST_RENDER_USER,
            "commit_message": mock_data.TEST_COMMIT_MESSAGE,
            "template_version": mock_data.TEMPLATE_VERSION,
        }

        response = self.client.post(create_intended_config_url, data, format="json", **self.header)
        response_data = response.data
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(uuid.UUID(response_data["id"]), device.id)
        self.assertEqual(response_data["config_store_instance"], data["config_store_instance"])
        self.assertEqual(response_data["path"], data["path"])
        self.assertEqual(str(response_data["commit_id"]), str(data["commit_id"]))
        original_datetime = datetime.fromisoformat(data["updated"])
        utc_datetime_str = original_datetime.replace(tzinfo=None).isoformat() + "Z"
        self.assertEqual(response_data["updated"], utc_datetime_str)
        self.assertEqual(response_data["updated_by"], data["updated_by"])
        self.assertEqual(response_data["commit_message"], data["commit_message"])
        self.assertEqual(response_data["template_version"], data["template_version"])

    def test_creating_backup_config_to_new_managed_device(self):
        """Test pushing a backup config to a managed device with no configs"""
        self.add_permissions("nv_config_manager.add_configmanagerdevicestatus")
        self.add_permissions("nv_config_manager.view_configmanagerdevicestatus")
        self.add_permissions("nv_config_manager.view_backupconfig")
        self.add_permissions("nv_config_manager.add_backupconfig")
        self.add_permissions("dcim.add_device")
        device = Device.objects.create(
            device_type=self.device_type,
            role=self.device_role,
            name=mock_data.FOURTH_DEVICE_NAME,
            location=self.site,
            status=self.status_provisioning,
        )
        create_managed_device_url = reverse(
            "plugins-api:nv_config_manager-api:configmanagerdevicestatus-list",
        )
        get_backup_config_url = reverse(
            "plugins-api:nv_config_manager-api:backupconfig-detail",
            kwargs={"pk": device.id},
        )

        data = {"device": device.id}

        create_managed_response = self.client.post(create_managed_device_url, data, format="json", **self.header)
        self.assertHttpStatus(create_managed_response, status.HTTP_201_CREATED)

        get_backup_config_response = self.client.get(get_backup_config_url, **self.header)
        self.assertHttpStatus(get_backup_config_response, status.HTTP_404_NOT_FOUND)

        data = {
            "device_id": device.id,
            "config_store_instance": mock_data.CONFIG_STORE_HTTP_URL,
            "path": mock_data.CONFIG_PATH,
            "commit_id": mock_data.TEST_INTENDED_COMMIT_ID,
            "updated": mock_data.TEST_API_TIMESTAMP,
            "updated_by": mock_data.TEST_RENDER_USER,
            "commit_message": mock_data.TEST_COMMIT_MESSAGE,
            "deployed_commit_id": mock_data.TEST_INTENDED_COMMIT_ID,
            "workflow_id": mock_data.TEST_BACKUP_WORKFLOW_ID,
        }

        create_backup_config_url = reverse("plugins-api:nv_config_manager-api:backupconfig-list")
        response = self.client.post(create_backup_config_url, data, format="json", **self.header)
        response_data = response.data
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(uuid.UUID(response_data["id"]), device.id)
        self.assertEqual(response_data["config_store_instance"], data["config_store_instance"])
        self.assertEqual(response_data["path"], data["path"])
        self.assertEqual(str(response_data["commit_id"]), str(data["commit_id"]))
        original_datetime = datetime.fromisoformat(data["updated"])
        utc_datetime_str = original_datetime.replace(tzinfo=None).isoformat() + "Z"
        self.assertEqual(response_data["updated"], utc_datetime_str)
        self.assertEqual(response_data["updated_by"], data["updated_by"])
        self.assertEqual(response_data["commit_message"], data["commit_message"])
        self.assertEqual(str(response_data["deployed_commit_id"]), str(data["deployed_commit_id"]))
        self.assertEqual(response_data["workflow_id"], data["workflow_id"])

    def test_get_single_managed_intended_config_fail(self):
        """Test getting single managed Intended Config from a managed device with no config."""
        self.add_permissions("nv_config_manager.add_configmanagerdevicestatus")
        self.add_permissions("nv_config_manager.view_configmanagerdevicestatus")
        self.add_permissions("nv_config_manager.view_intendedconfig")
        self.add_permissions("dcim.add_device")
        device = Device.objects.create(
            device_type=self.device_type,
            role=self.device_role,
            name=mock_data.FOURTH_DEVICE_NAME,
            location=self.site,
            status=self.status_provisioning,
        )
        create_managed_device_url = reverse(
            "plugins-api:nv_config_manager-api:configmanagerdevicestatus-list",
        )
        get_intended_config_url = reverse(
            "plugins-api:nv_config_manager-api:intendedconfig-detail",
            kwargs={"pk": device.id},
        )

        data = {"device": device.id}

        create_managed_response = self.client.post(create_managed_device_url, data, format="json", **self.header)
        self.assertHttpStatus(create_managed_response, status.HTTP_201_CREATED)

        get_intended_config_response = self.client.get(get_intended_config_url, **self.header)
        self.assertHttpStatus(get_intended_config_response, status.HTTP_404_NOT_FOUND)

    def test_update_single_managed_device_with_intended_config(self):
        """Test updating an existing managed device's intended config."""
        self.add_permissions("nv_config_manager.change_intendedconfig")
        self.add_permissions("nv_config_manager.view_intendedconfig")
        url = reverse(
            "plugins-api:nv_config_manager-api:intendedconfig-list",
        )
        config_to_update = self.intended_configs[0]
        data = [
            {
                "id": config_to_update.id,
                "device_id": config_to_update.id,
                "config_store_instance": mock_data.CONFIG_STORE_UI_URL,
                "path": "updated_path",
                "commit_id": mock_data.TEST_UPDATED_COMMIT_ID,
                "updated": mock_data.TEST_API_TIMESTAMP,
                "updated_by": "updated user",
                "commit_message": "updated commit message",
                "template_version": "updated version",
            }
        ]

        response = self.client.put(url, data, format="json", **self.header)
        response_data = response.data[0]
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(uuid.UUID(response_data["id"]), config_to_update.id)

        data = data[0]
        self.assertEqual(response_data["config_store_instance"], data["config_store_instance"])
        self.assertEqual(response_data["path"], data["path"])
        self.assertEqual(str(response_data["commit_id"]), str(data["commit_id"]))
        original_datetime = datetime.fromisoformat(data["updated"])
        utc_datetime_str = original_datetime.replace(tzinfo=None).isoformat() + "Z"
        self.assertEqual(response_data["updated"], utc_datetime_str)
        self.assertEqual(response_data["updated_by"], data["updated_by"])
        self.assertEqual(response_data["commit_message"], data["commit_message"])
        self.assertEqual(response_data["template_version"], data["template_version"])

    def test_update_single_managed_device_with_backup_config(self):
        """Test updating an existing managed device's backup config."""
        self.add_permissions("nv_config_manager.change_backupconfig")
        self.add_permissions("nv_config_manager.view_backupconfig")
        url = reverse(
            "plugins-api:nv_config_manager-api:backupconfig-list",
        )
        config_to_update = self.backup_configs[0]
        data = [
            {
                "id": config_to_update.id,
                "device_id": config_to_update.id,
                "config_store_instance": mock_data.CONFIG_STORE_HTTP_URL,
                "path": "updated_path",
                "commit_id": mock_data.TEST_UPDATED_COMMIT_ID,
                "updated": mock_data.TEST_API_TIMESTAMP,
                "updated_by": "updated user",
                "commit_message": "updated commit message",
                "deployed_commit_id": mock_data.TEST_INTENDED_COMMIT_ID,
                "workflow_id": mock_data.TEST_BACKUP_WORKFLOW_ID,
            }
        ]

        response = self.client.patch(url, data, format="json", **self.header)
        response_data = response.data[0]
        self.assertHttpStatus(response, status.HTTP_200_OK)

        data = data[0]
        self.assertEqual(uuid.UUID(response_data["id"]), config_to_update.id)
        self.assertEqual(response_data["config_store_instance"], data["config_store_instance"])
        self.assertEqual(response_data["path"], data["path"])
        self.assertEqual(str(response_data["commit_id"]), str(data["commit_id"]))
        original_datetime = datetime.fromisoformat(data["updated"])
        utc_datetime_str = original_datetime.replace(tzinfo=None).isoformat() + "Z"
        self.assertEqual(response_data["updated"], utc_datetime_str)
        self.assertEqual(response_data["updated_by"], data["updated_by"])
        self.assertEqual(response_data["commit_message"], data["commit_message"])
        self.assertEqual(str(response_data["deployed_commit_id"]), str(data["deployed_commit_id"]))
        self.assertEqual(response_data["workflow_id"], data["workflow_id"])
