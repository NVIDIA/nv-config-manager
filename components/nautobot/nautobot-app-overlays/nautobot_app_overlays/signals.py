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

"""Signal handlers for the Overlays app."""

import logging

from django.apps import apps as global_apps
from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from nautobot.extras.models import CustomField, Status

logger = logging.getLogger(__name__)

CUSTOM_FIELDS = [
    {
        "key": "ib_guid",
        "type": "text",
        "label": "InfiniBand GUID",
        "description": "InfiniBand GUID.",
        "target_app_label": "dcim",
        "target_model": "Interface",
    },
]

OVERLAY_MODEL_NAMES = [
    "Overlay",
    "InfiniBandPKey",
    "InfiniBandMKey",
    "VXLAN",
    "OverlayAssignment",
]

STATUS_NAMES = ["Active", "Deprecated", "Planned"]


@receiver(post_migrate)
def ensure_custom_fields(sender, apps=global_apps, **kwargs):  # noqa: ARG001 - kwargs required by signal
    """Create custom fields and attach status content types after our app's migrations."""
    if sender.name != "nautobot_app_overlays":
        return
    _ensure_ib_guid_custom_field(apps)
    _ensure_overlay_status_content_types(sender)


def _ensure_ib_guid_custom_field(apps):
    """Create the ib_guid custom field on dcim.Interface if absent."""
    for field_def in CUSTOM_FIELDS:
        target_model = apps.get_model(field_def["target_app_label"], field_def["target_model"])
        ct = ContentType.objects.get_for_model(target_model)

        cf, created = CustomField.objects.get_or_create(
            key=field_def["key"],
            defaults={
                "type": field_def["type"],
                "label": field_def["label"],
                "description": field_def["description"],
            },
        )

        if ct not in cf.content_types.all():
            cf.content_types.add(ct)

        if created:
            logger.info("Created custom field '%s' on %s.%s", cf.key, ct.app_label, ct.model)
        else:
            logger.debug("Custom field '%s' already exists", cf.key)


def _ensure_overlay_status_content_types(sender):
    """Attach overlay model content types to the default Statuses."""
    overlay_cts = [ContentType.objects.get_for_model(sender.get_model(name)) for name in OVERLAY_MODEL_NAMES]

    for status_name in STATUS_NAMES:
        try:
            status = Status.objects.get(name=status_name)
        except Status.DoesNotExist:
            logger.debug("Status '%s' not found, skipping", status_name)
            continue

        for ct in overlay_cts:
            if ct not in status.content_types.all():
                status.content_types.add(ct)
                logger.info(
                    "Assigned status '%s' to content type %s.%s",
                    status_name,
                    ct.app_label,
                    ct.model,
                )
