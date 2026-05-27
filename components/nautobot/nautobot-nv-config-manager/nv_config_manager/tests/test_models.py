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
"""Tests for nv_config_manager models."""

from datetime import timedelta

from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db.utils import IntegrityError
from django.test import TestCase
from django.utils import timezone
from nautobot.dcim.models import (
    Device,
    DeviceType,
    Location,
    LocationType,
    Manufacturer,
)
from nautobot.extras.models import Role, Status

from nv_config_manager.models import BackupConfig, ConfigManagerDeviceStatus, IntendedConfig
from nv_config_manager.tests.fixtures import mock_data as data


def create_device_environment():
    """Create the shared Nautobot objects used by the model tests."""
    manufacturer, _ = Manufacturer.objects.get_or_create(name=data.MANUFACTURER_NAME)
    site_type, _ = LocationType.objects.get_or_create(name="Site")
    location_status = Status.objects.get_for_model(Location).first()
    device_status = Status.objects.get_for_model(Device).first()
    site, _ = Location.objects.get_or_create(
        name=data.SITE_NAME,
        location_type=site_type,
        status=location_status,
    )
    device_type, _ = DeviceType.objects.get_or_create(
        manufacturer=manufacturer,
        model=data.DEVICE_TYPE_MODEL,
    )
    device_role, _ = Role.objects.get_or_create(
        name=data.LEAF_ROLE_NAME,
        color="ff0000",
    )
    non_managed_device, _ = Device.objects.get_or_create(
        device_type=device_type,
        role=device_role,
        name=data.NON_MANAGED_DEVICE_NAME,
        location=site,
        status=device_status,
    )
    device, _ = Device.objects.get_or_create(
        device_type=device_type,
        role=device_role,
        name=data.DEVICE_NAME,
        location=site,
        status=device_status,
    )
    managed_device, _ = ConfigManagerDeviceStatus.objects.get_or_create(device=device)
    return site, device_type, device_role, non_managed_device, device, managed_device


class ConfigManagerDeviceStatusTestCase(TestCase):
    """Test case for ConfigManagerDeviceStatus model."""

    def setUp(self):
        """Setup objects for the tests."""
        (
            self.site,
            self.device_type,
            self.device_role,
            self.non_managed_device,
            self.device,
            self.managed_device,
        ) = create_device_environment()

    def test_create_managed_device_status_success(self):
        """Succesful creation of managed device."""
        managed_device = ConfigManagerDeviceStatus.objects.create(device=self.non_managed_device)
        self.assertIsNotNone(managed_device)

    def test_create_managed_device_unique_failure(self):
        """Try to instantiate a managed device on an existing device."""
        with self.assertRaises(IntegrityError):
            ConfigManagerDeviceStatus.objects.create(device=self.device)

    def test_delete_managed_device_success(self):
        """Try to delete a managed device."""
        self.assertIsNotNone(self.managed_device)

        self.managed_device.delete()

        with self.assertRaises(ConfigManagerDeviceStatus.DoesNotExist):
            ConfigManagerDeviceStatus.objects.get(pk=self.device.pk)

    def test_is_pending_fail_backup_dne(self):
        """Test is_pending fails due to backup config DNE."""
        self.managed_device.intended_config = IntendedConfig.objects.create(
            device_id=self.managed_device,
            config_store_instance=data.CONFIG_STORE_UI_URL,
            path=data.CONFIG_PATH,
            commit_id=data.TEST_INTENDED_COMMIT_ID,
            updated=timezone.now(),
            updated_by=data.TEST_RENDER_USER,
            commit_message=data.TEST_COMMIT_MESSAGE,
            template_version=data.TEMPLATE_VERSION,
        )
        self.assertFalse(self.managed_device.is_pending)

    def test_is_pending_fail_intended_dne(self):
        """Test is_pending fails due to intended config DNE."""
        self.managed_device.backup_config = BackupConfig.objects.create(
            device_id=self.managed_device,
            config_store_instance=data.CONFIG_STORE_UI_URL,
            path=data.BACKUP_CONFIG_PATH,
            commit_id=data.TEST_BACKUP_COMMIT_ID,
            updated=timezone.now(),
            updated_by=data.TEST_RENDER_USER,
            commit_message=data.TEST_BACKUP_COMMIT_MESSAGE,
            workflow_id=data.TEST_WORKFLOW_ID,
            deployed_commit_id=data.TEST_INTENDED_COMMIT_ID,
        )
        self.assertFalse(self.managed_device.is_pending)

    def test_is_pending_true(self):
        """Test is_pending correctly returns True."""
        self.managed_device.intended_config = IntendedConfig.objects.create(
            device_id=self.managed_device,
            config_store_instance=data.CONFIG_STORE_UI_URL,
            path=data.CONFIG_PATH,
            commit_id=data.TEST_INTENDED_COMMIT_ID,
            updated=timezone.now(),
            updated_by=data.TEST_RENDER_USER,
            commit_message=data.TEST_COMMIT_MESSAGE,
            template_version=data.TEMPLATE_VERSION,
        )
        self.managed_device.backup_config = BackupConfig.objects.create(
            device_id=self.managed_device,
            config_store_instance=data.CONFIG_STORE_UI_URL,
            path=data.BACKUP_CONFIG_PATH,
            commit_id=data.TEST_BACKUP_COMMIT_ID,
            updated=timezone.now() - timedelta(hours=2),
            updated_by=data.TEST_RENDER_USER,
            commit_message=data.TEST_BACKUP_COMMIT_MESSAGE,
            workflow_id=data.TEST_WORKFLOW_ID,
            deployed_commit_id=data.TEST_PENDING_DEPLOYED_COMMIT_ID,
        )

        self.assertTrue(self.managed_device.is_pending)

    def test_is_pending_false(self):
        """Test is_pending correctly returns False."""
        self.managed_device.intended_config = IntendedConfig.objects.create(
            device_id=self.managed_device,
            config_store_instance=data.CONFIG_STORE_UI_URL,
            path=data.CONFIG_PATH,
            commit_id=data.TEST_MATCHING_COMMIT_ID,
            updated=timezone.now(),
            updated_by=data.TEST_RENDER_USER,
            commit_message=data.TEST_COMMIT_MESSAGE,
            template_version=data.TEMPLATE_VERSION,
        )
        self.managed_device.backup_config = BackupConfig.objects.create(
            device_id=self.managed_device,
            config_store_instance=data.CONFIG_STORE_UI_URL,
            path=data.BACKUP_CONFIG_PATH,
            commit_id=data.TEST_BACKUP_COMMIT_ID,
            updated=timezone.now() + timedelta(hours=2),
            updated_by=data.TEST_RENDER_USER,
            commit_message=data.TEST_BACKUP_COMMIT_MESSAGE,
            workflow_id=data.TEST_WORKFLOW_ID,
            deployed_commit_id=data.TEST_MATCHING_COMMIT_ID,
        )

        self.assertFalse(self.managed_device.is_pending)

    def test_is_aggregate_managed_default_false(self):
        """Test is_aggregate_managed correctly defaults to False."""
        self.assertFalse(self.managed_device.is_aggregate_managed)

    def test_is_aggregate_managed_can_be_set_true(self):
        """Test is_aggregate_managed can be set to True."""
        self.managed_device.is_aggregate_managed = True
        self.managed_device.save()
        self.managed_device.refresh_from_db()
        self.assertTrue(self.managed_device.is_aggregate_managed)

    def test_is_aggregate_managed_can_be_set_false(self):
        """Test is_aggregate_managed can be set to False."""
        self.managed_device.is_aggregate_managed = True
        self.managed_device.save()
        self.managed_device.is_aggregate_managed = False
        self.managed_device.save()
        self.managed_device.refresh_from_db()
        self.assertFalse(self.managed_device.is_aggregate_managed)


class IntendedConfigTestCase(TestCase):
    """Test case for IntendedConfig model."""

    def setUp(self):
        """Setup objects for the tests."""
        (
            self.site,
            self.device_type,
            self.device_role,
            self.non_managed_device,
            self.device,
            self.managed_device,
        ) = create_device_environment()

    def test_create_intended_config_success(self):
        """Succesful creation of intended config."""
        try:
            intended_config = self.managed_device.intended_config
        except ObjectDoesNotExist:
            intended_config = None

        self.assertIsNone(intended_config)
        intended_config = IntendedConfig.objects.create(
            device_id=self.managed_device,
            config_store_instance=data.CONFIG_STORE_UI_URL,
            path=data.CONFIG_PATH,
            commit_id=data.TEST_INTENDED_COMMIT_ID,
            updated="2024-03-20T03:01:04Z",
            updated_by=data.TEST_RENDER_USER,
            commit_message=data.TEST_COMMIT_MESSAGE,
            template_version=data.TEMPLATE_VERSION,
        )

        self.assertEqual(self.managed_device.intended_config, intended_config)

    def test_create_intended_config_failure(self):
        """Try to create a new intended config on a managed device with an existing config."""
        try:
            intended_config = self.managed_device.intended_config
        except ObjectDoesNotExist:
            intended_config = None

        self.assertIsNone(intended_config)
        intended_config = IntendedConfig.objects.create(
            device_id=self.managed_device,
            config_store_instance=data.CONFIG_STORE_UI_URL,
            path=data.CONFIG_PATH,
            commit_id=data.TEST_INTENDED_COMMIT_ID,
            updated="2024-03-20T03:01:04Z",
            updated_by=data.TEST_RENDER_USER,
            commit_message=data.TEST_COMMIT_MESSAGE,
            template_version=data.TEMPLATE_VERSION,
        )

        self.assertEqual(self.managed_device.intended_config, intended_config)
        with self.assertRaises(ValidationError):
            intended_config = IntendedConfig.objects.create(
                device_id=self.managed_device,
                config_store_instance=data.CONFIG_STORE_UI_URL,
                path=data.CONFIG_PATH,
                commit_id=data.TEST_PREVIOUS_COMMIT_ID,
                updated="2024-04-20T03:01:04Z",
                updated_by=data.TEST_EVENT_USER,
                commit_message="new commit 2",
                template_version=data.TEMPLATE_VERSION,
            )

    def test_edit_intended_config_success(self):
        """Try to edit an existing intended config."""
        intended_config = IntendedConfig.objects.create(
            device_id=self.managed_device,
            config_store_instance=data.CONFIG_STORE_UI_URL,
            path=data.CONFIG_PATH,
            commit_id=data.TEST_INTENDED_COMMIT_ID,
            updated="2024-03-20T03:01:04Z",
            updated_by=data.TEST_RENDER_USER,
            commit_message=data.TEST_COMMIT_MESSAGE,
            template_version=data.TEMPLATE_VERSION,
        )
        self.assertEqual(self.managed_device.intended_config, intended_config)
        intended_config.commit_id = data.TEST_UPDATED_COMMIT_ID
        intended_config.updated = "2024-03-21T03:01:04Z"
        intended_config.commit_message = "edited commit"
        intended_config.save()

        updated_intended_config = IntendedConfig.objects.get(pk=intended_config.pk)

        self.assertEqual(int(updated_intended_config.commit_id), data.TEST_UPDATED_COMMIT_ID)
        self.assertEqual(updated_intended_config.commit_message, "edited commit")
        self.assertEqual(self.managed_device.intended_config, updated_intended_config)


class BackupConfigTestCase(TestCase):
    """Test case for BackupConfig model."""

    def setUp(self):
        """Setup objects for the tests."""
        (
            self.site,
            self.device_type,
            self.device_role,
            self.non_managed_device,
            self.device,
            self.managed_device,
        ) = create_device_environment()


def test_create_backup_config_success(self):
    """Successful creation of backup config."""
    try:
        backup_config = self.managed_device.backup_config
    except ObjectDoesNotExist:
        backup_config = None

    self.assertIsNone(backup_config)
    backup_config = BackupConfig.objects.create(
        device_id=self.managed_device,
        path=data.BACKUP_CONFIG_PATH,
        commit_id=data.TEST_BACKUP_COMMIT_ID,
        updated="2024-03-20T03:01:04Z",
        updated_by=data.TEST_RENDER_USER,
        commit_message=data.TEST_BACKUP_COMMIT_MESSAGE,
        workflow_id=data.TEST_WORKFLOW_ID,
        deployed_commit_id=data.TEST_PENDING_DEPLOYED_COMMIT_ID,
    )

    self.assertEqual(self.managed_device.backup_config, backup_config)


def test_create_backup_config_failure(self):
    """Try to create a new backup config on a managed device with an existing config."""
    try:
        backup_config = self.managed_device.backup_config
    except ObjectDoesNotExist:
        backup_config = None

    self.assertIsNone(backup_config)
    backup_config = BackupConfig.objects.create(
        device_id=self.managed_device,
        config_store_instance=data.CONFIG_STORE_UI_URL,
        path=data.BACKUP_CONFIG_PATH,
        commit_id=data.TEST_BACKUP_COMMIT_ID,
        updated="2024-03-20T03:01:04Z",
        updated_by=data.TEST_RENDER_USER,
        commit_message=data.TEST_BACKUP_COMMIT_MESSAGE,
        workflow_id=data.TEST_WORKFLOW_ID,
        deployed_commit_id=data.TEST_PENDING_DEPLOYED_COMMIT_ID,
    )

    self.assertEqual(self.managed_device.backup_config, backup_config)

    with self.assertRaises(ValidationError):
        backup_config = BackupConfig.objects.create(
            device_id=self.managed_device,
            config_store_instance=data.CONFIG_STORE_UI_URL,
            path=data.BACKUP_CONFIG_PATH,
            commit_id=data.TEST_PREVIOUS_COMMIT_ID,
            updated="2024-04-20T03:01:04Z",
            updated_by=data.TEST_EVENT_USER,
            commit_message="new backup commit 2",
            workflow_id=data.TEST_WORKFLOW_ID,
            deployed_commit_id=data.TEST_PENDING_DEPLOYED_COMMIT_ID,
        )


def test_edit_backup_config_success(self):
    """Try to edit an existing backup config."""
    backup_config = BackupConfig.objects.create(
        device_id=self.managed_device,
        path=data.BACKUP_CONFIG_PATH,
        commit_id=data.TEST_BACKUP_COMMIT_ID,
        updated="2024-03-20T03:01:04Z",
        updated_by=data.TEST_RENDER_USER,
        commit_message=data.TEST_BACKUP_COMMIT_MESSAGE,
        workflow_id=data.TEST_WORKFLOW_ID,
        deployed_commit_id=data.TEST_PENDING_DEPLOYED_COMMIT_ID,
    )
    self.assertEqual(self.managed_device.backup_config, backup_config)
    backup_config.commit_id = data.TEST_UPDATED_COMMIT_ID
    backup_config.updated = "2024-03-21T03:01:04Z"
    backup_config.commit_message = "edited backup commit"
    backup_config.deployed_commit_id = data.TEST_UPDATED_DEPLOYED_COMMIT_ID
    backup_config.save()

    updated_backup_config = BackupConfig.objects.get(pk=backup_config.pk)

    self.assertEqual(int(updated_backup_config.commit_id), data.TEST_UPDATED_COMMIT_ID)
    self.assertEqual(updated_backup_config.commit_message, "edited backup commit")
    self.assertEqual(int(updated_backup_config.deployed_commit_id), data.TEST_UPDATED_DEPLOYED_COMMIT_ID)
    self.assertEqual(self.managed_device.backup_config, updated_backup_config)
