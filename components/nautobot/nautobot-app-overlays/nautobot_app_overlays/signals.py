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

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from nautobot.extras.models import CustomField, Status

from nautobot_app_overlays.models import (
    VXLAN,
    InfiniBandMKey,
    InfiniBandPKey,
    Overlay,
    OverlayAssignment,
)

logger = logging.getLogger(__name__)

OVERLAY_MODELS = (Overlay, InfiniBandPKey, InfiniBandMKey, VXLAN, OverlayAssignment)
DEFAULT_STATUSES = ("Active", "Deprecated", "Planned")


def post_migrate_create_defaults(*args, **kwargs):  # noqa: ARG001 - signature required by signal
    """Create the ib_guid custom field and link overlay-app CTs to default Statuses."""
    _ensure_ib_guid_custom_field()
    _ensure_overlay_status_content_types()


def _ensure_ib_guid_custom_field():
    """Create the ib_guid custom field on dcim.Interface if absent."""
    interface_ct = ContentType.objects.get_for_model(apps.get_model("dcim", "Interface"))
    cf, created = CustomField.objects.get_or_create(
        key="ib_guid",
        defaults={"type": "text", "label": "InfiniBand GUID", "description": "InfiniBand GUID."},
    )
    cf.content_types.add(interface_ct)
    if created:
        logger.info("Created custom field 'ib_guid' on dcim.interface")


def _ensure_overlay_status_content_types():
    """Attach overlay-app content types to the default Active/Deprecated/Planned Statuses."""
    logger.info("Adding overlay models to Statuses")
    status_name = ""
    try:
        for model in OVERLAY_MODELS:
            ct = ContentType.objects.get_for_model(model)
            for status_name in DEFAULT_STATUSES:
                Status.objects.get(name=status_name).content_types.add(ct)
    except Status.DoesNotExist:
        logger.warning("Status '%s' does not exist; skipping overlay content_types linkage", status_name)
