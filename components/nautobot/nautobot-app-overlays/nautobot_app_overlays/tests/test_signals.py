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

"""Tests for the overlays-app post_migrate handler."""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from nautobot.extras.models import CustomField, Status

from nautobot_app_overlays.models import (
    VXLAN,
    InfiniBandMKey,
    InfiniBandPKey,
    Overlay,
    OverlayAssignment,
)
from nautobot_app_overlays.signals import (
    DEFAULT_STATUSES,
    OVERLAY_MODELS,
    post_migrate_create_defaults,
)


class EnsureCustomFieldsTestCase(TestCase):
    """Verify the ib_guid CustomField is created and attached to dcim.Interface."""

    def test_creates_field_attached_to_interface(self):
        CustomField.objects.filter(key="ib_guid").delete()
        interface_ct = ContentType.objects.get(app_label="dcim", model="interface")

        post_migrate_create_defaults()

        cf = CustomField.objects.get(key="ib_guid")
        self.assertEqual(cf.type, "text")
        self.assertEqual(cf.label, "InfiniBand GUID")
        self.assertIn(interface_ct, cf.content_types.all())

    def test_idempotent(self):
        CustomField.objects.filter(key="ib_guid").delete()

        post_migrate_create_defaults()
        post_migrate_create_defaults()

        self.assertEqual(CustomField.objects.filter(key="ib_guid").count(), 1)

    def test_does_not_overwrite_user_edits(self):
        CustomField.objects.filter(key="ib_guid").delete()
        interface_ct = ContentType.objects.get(app_label="dcim", model="interface")
        cf = CustomField.objects.create(
            key="ib_guid",
            type="text",
            label="My Custom Label",
            description="User-modified description",
        )
        cf.content_types.add(interface_ct)

        post_migrate_create_defaults()

        cf.refresh_from_db()
        self.assertEqual(cf.description, "User-modified description")
        self.assertEqual(cf.label, "My Custom Label")


class EnsureOverlayStatusContentTypesTestCase(TestCase):
    """Verify default Statuses end up linked to all overlay-app ContentTypes."""

    EXPECTED_MODELS = (Overlay, InfiniBandPKey, InfiniBandMKey, VXLAN, OverlayAssignment)

    def _strip_overlay_cts(self):
        for status_name in DEFAULT_STATUSES:
            status = Status.objects.get(name=status_name)
            for model in self.EXPECTED_MODELS:
                status.content_types.remove(ContentType.objects.get_for_model(model))

    def test_all_default_statuses_get_every_overlay_ct(self):
        self._strip_overlay_cts()

        post_migrate_create_defaults()

        expected_model_names = {model._meta.model_name for model in self.EXPECTED_MODELS}
        for status_name in DEFAULT_STATUSES:
            status = Status.objects.get(name=status_name)
            attached = {ct.model for ct in status.content_types.all() if ct.app_label == "nautobot_app_overlays"}
            self.assertEqual(
                attached,
                expected_model_names,
                f"Status '{status_name}' is missing overlay content types",
            )

    def test_handler_is_idempotent(self):
        post_migrate_create_defaults()
        post_migrate_create_defaults()

        for status_name in DEFAULT_STATUSES:
            status = Status.objects.get(name=status_name)
            overlay_cts = [ct for ct in status.content_types.all() if ct.app_label == "nautobot_app_overlays"]
            self.assertEqual(len(overlay_cts), len(OVERLAY_MODELS))

    def test_missing_status_does_not_raise(self):
        """If a default Status is deleted, the handler logs a warning rather than crashing."""
        Status.objects.filter(name="Planned").delete()

        post_migrate_create_defaults()

    def test_missing_status_does_not_block_other_links(self):
        """A missing Status must not abort linkage for the remaining Statuses or models."""
        self._strip_overlay_cts()
        Status.objects.filter(name="Planned").delete()

        post_migrate_create_defaults()

        expected_model_names = {model._meta.model_name for model in self.EXPECTED_MODELS}
        for status_name in ("Active", "Deprecated"):
            status = Status.objects.get(name=status_name)
            attached = {ct.model for ct in status.content_types.all() if ct.app_label == "nautobot_app_overlays"}
            self.assertEqual(
                attached,
                expected_model_names,
                f"Status '{status_name}' is missing overlay content types after a sibling Status was removed",
            )
