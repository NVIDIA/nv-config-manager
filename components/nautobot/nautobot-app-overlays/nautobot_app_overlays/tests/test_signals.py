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

"""Tests for signal handlers that create custom fields."""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from nautobot.extras.models import CustomField

from nautobot_app_overlays.signals import ensure_custom_fields


class EnsureCustomFieldsTestCase(TestCase):
    """Test that ensure_custom_fields creates the expected custom fields."""

    def test_creates_ib_guid_field(self):
        """Test that the ib_guid custom field is created."""
        CustomField.objects.filter(key="ib_guid").delete()

        ensure_custom_fields(sender=None)

        cf = CustomField.objects.get(key="ib_guid")
        self.assertEqual(cf.type, "text")
        self.assertEqual(cf.label, "InfiniBand GUID")

    def test_ib_guid_assigned_to_interface_content_type(self):
        """Test that the ib_guid field is attached to dcim.interface."""
        CustomField.objects.filter(key="ib_guid").delete()

        ensure_custom_fields(sender=None)

        cf = CustomField.objects.get(key="ib_guid")
        interface_ct = ContentType.objects.get(app_label="dcim", model="interface")
        self.assertIn(interface_ct, cf.content_types.all())

    def test_idempotent_on_repeated_calls(self):
        """Test that calling ensure_custom_fields twice doesn't duplicate."""
        CustomField.objects.filter(key="ib_guid").delete()

        ensure_custom_fields(sender=None)
        ensure_custom_fields(sender=None)

        self.assertEqual(CustomField.objects.filter(key="ib_guid").count(), 1)

    def test_does_not_overwrite_existing_description(self):
        """Test that an existing custom field's description is not overwritten."""
        CustomField.objects.filter(key="ib_guid").delete()
        interface_ct = ContentType.objects.get(app_label="dcim", model="interface")
        cf = CustomField.objects.create(
            key="ib_guid",
            type="text",
            label="My Custom Label",
            description="User-modified description",
        )
        cf.content_types.add(interface_ct)

        ensure_custom_fields(sender=None)

        cf.refresh_from_db()
        self.assertEqual(cf.description, "User-modified description")
        self.assertEqual(cf.label, "My Custom Label")
