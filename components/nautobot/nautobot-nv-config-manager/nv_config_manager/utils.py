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

from django.db import transaction
from nautobot.dcim.models import Device, Location
from nautobot.extras.models import Role

from nv_config_manager import models


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
) -> tuple[int, int]:
    """Create managed-device rows for devices, skipping existing enrollments."""
    defaults = {
        "render_enabled": nullbool_to_bool(render_enabled),
        "ztp_enabled": nullbool_to_bool(ztp_enabled),
        "deploy_enabled": nullbool_to_bool(deploy_enabled),
        "backup_enabled": nullbool_to_bool(backup_enabled),
        "is_aggregate_managed": nullbool_to_bool(is_aggregate_managed),
    }
    created_count = 0
    skipped_count = 0

    with transaction.atomic():
        for device in devices:
            _, created = models.ConfigManagerDeviceStatus.objects.get_or_create(
                device=device,
                defaults=defaults,
            )
            if created:
                created_count += 1
            else:
                skipped_count += 1

    return created_count, skipped_count


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
