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
"""Util Functions."""

import logging
import uuid

from django.db import transaction
from nautobot.dcim.models import Device, Location
from nautobot.extras.choices import ObjectChangeActionChoices, ObjectChangeEventContextChoices
from nautobot.extras.models import Role

from nv_config_manager import models

logger = logging.getLogger(__name__)


def get_all_descendants(node: Location):
    """Get all descendant location IDs using Nautobot's built-in tree query API.

    Uses the TreeModel.descendants() method which efficiently queries all descendants
    in a single recursive query.

    Args:
        node: A Location instance

    Returns:
        List of location IDs including the node and all its descendants
    """
    # Use Nautobot's built-in TreeModel method for efficient tree traversal
    # Return only IDs as a list for better performance
    return list(node.descendants(include_self=True).values_list("id", flat=True))


def get_eligible_unmanaged_devices(
    location: Location,
    roles: list[Role] | tuple[Role, ...],
):
    """Return unmanaged devices in a location tree matching the given roles."""
    location_ids = get_all_descendants(location)
    return (
        Device.objects.filter(
            location_id__in=location_ids,
            role__in=roles,
            configmanagerdevicestatus__isnull=True,
        )
        .select_related("location", "role")
        .order_by("name")
    )


def nullbool_to_bool(value: bool | None) -> bool:
    """Map form values to boolean model values."""
    return bool(value) if value is not None else False


def bulk_create_managed_devices(
    devices,
    *,
    render_enabled: bool | None = None,
    ztp_enabled: bool | None = None,
    deploy_enabled: bool | None = None,
    backup_enabled: bool | None = None,
    is_aggregate_managed: bool | None = None,
    user=None,
    request_id=None,
) -> tuple[int, int]:
    """Create managed-device rows for devices, skipping existing enrollments."""
    defaults = {
        "render_enabled": nullbool_to_bool(render_enabled),
        "ztp_enabled": nullbool_to_bool(ztp_enabled),
        "deploy_enabled": nullbool_to_bool(deploy_enabled),
        "backup_enabled": nullbool_to_bool(backup_enabled),
        "is_aggregate_managed": nullbool_to_bool(is_aggregate_managed),
    }
    device_list = list(devices)
    already_managed_ids = set(
        models.ConfigManagerDeviceStatus.objects.filter(device__in=device_list).values_list("device_id", flat=True)
    )

    to_create = []
    seen_ids: set = set()
    for device in device_list:
        if device.pk in already_managed_ids or device.pk in seen_ids:
            continue
        seen_ids.add(device.pk)
        # ConfigManagerDeviceStatus.save() pins its pk to the device pk; replicate that
        # here since bulk_create bypasses save().
        to_create.append(models.ConfigManagerDeviceStatus(id=device.pk, device=device, **defaults))

    with transaction.atomic():
        models.ConfigManagerDeviceStatus.objects.bulk_create(to_create)
        _log_created_object_changes(to_create, user=user, request_id=request_id)

    created_count = len(to_create)
    skipped_count = len(device_list) - created_count
    if to_create:
        logger.info(
            "Enrolled %d device(s) into Config Manager: %s",
            created_count,
            ", ".join(sorted(status.device.name for status in to_create)),
        )
    return created_count, skipped_count


def _log_created_object_changes(instances, *, user=None, request_id=None):
    """Emit a Nautobot change-log entry for each managed device created via bulk_create.

    bulk_create bypasses save() and its post_save signals, so the change-log
    entries Nautobot would normally record are written explicitly here.
    """
    if not instances:
        return
    request_id = request_id or uuid.uuid4()
    for instance in instances:
        change = instance.to_objectchange(ObjectChangeActionChoices.ACTION_CREATE)
        if change is None:
            continue
        change.user = user
        change.request_id = request_id
        change.change_context = ObjectChangeEventContextChoices.CONTEXT_WEB
        change.change_context_detail = "bulk add managed devices"
        change.save()


def generate_config_store_url(
    config: models.IntendedConfig | models.BackupConfig,
    url_type: str,
) -> str | None:
    """Generate URLs for the config store.

    Args:
        config: IntendedConfig or BackupConfig instance
        url_type: Either "commit" or "history"

    Returns:
        URL string or None if config is None
    """
    if not config:
        return None

    # All configs use the central Config Store
    device_uuid = config.device_id.pk
    config_store_instance = config.config_store_instance.rstrip("/")
    filename = config.path
    version = config.commit_id

    # Determine file_type from the config type
    if isinstance(config, models.IntendedConfig):
        file_type = "intended"
    else:
        file_type = "backup"

    base = f"{config_store_instance}/device/{device_uuid}/{filename}"

    if url_type == "commit":
        return f"{base}?file_type={file_type}&version={version}"
    if url_type == "history":
        return f"{base}/history?file_type={file_type}"

    return None
