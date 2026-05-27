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

from django.contrib.contenttypes.models import ContentType
from nautobot.extras.models import CustomField, Status

logger = logging.getLogger(__name__)

CUSTOM_FIELDS = [
    {
        "key": "ib_guid",
        "type": "text",
        "label": "InfiniBand GUID",
        "description": "InfiniBand GUID.",
        "content_type_app_label": "dcim",
        "content_type_model": "interface",
    },
]

# Status names to assign to each overlay model so they can be set on creation.
OVERLAY_MODELS = [
    ("nautobot_app_overlays", "overlay"),
    ("nautobot_app_overlays", "infinibandpkey"),
    ("nautobot_app_overlays", "infinibandmkey"),
    ("nautobot_app_overlays", "vxlan"),
    ("nautobot_app_overlays", "overlayassignment"),
]

STATUS_NAMES = ["Active", "Deprecated", "Planned"]


def ensure_custom_fields(sender, **kwargs):  # noqa: ARG001 - sender required by signal
    """Create custom fields and assign status content types for the Overlays app."""
    _ensure_ib_guid_custom_field()
    _ensure_overlay_status_content_types()


def _ensure_ib_guid_custom_field():
    """Create the ib_guid custom field on dcim.Interface if absent."""
    for field_def in CUSTOM_FIELDS:
        ct = ContentType.objects.get(
            app_label=field_def["content_type_app_label"],
            model=field_def["content_type_model"],
        )

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


def _ensure_overlay_status_content_types():
    """Assign overlay model content types to the required statuses."""
    overlay_cts = []
    for app_label, model in OVERLAY_MODELS:
        try:
            ct = ContentType.objects.get(app_label=app_label, model=model)
            overlay_cts.append(ct)
        except ContentType.DoesNotExist:
            logger.debug("Content type %s.%s not found, skipping", app_label, model)

    if not overlay_cts:
        return

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
