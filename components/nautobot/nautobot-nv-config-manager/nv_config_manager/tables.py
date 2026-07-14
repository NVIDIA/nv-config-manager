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
"""Table definitions."""

import django_tables2 as tables
from django.conf import settings
from django.db.models import (
    BooleanField,
    Case,
    F,
    Q,
    Value,
    When,
)
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.html import format_html
from django_tables2.utils import A
from nautobot.apps.tables import BaseTable, BooleanColumn, ToggleColumn

from nv_config_manager.models import ConfigManagerDeviceStatus
from nv_config_manager.utils import generate_config_store_url

# -------------------
# Custom Columns
# -------------------


class PendingDeployColumn(tables.Column):
    """Custom Pending Deploy Column."""

    def render(self, record):  # pylint: disable=arguments-renamed
        """Render the pending deploy column."""
        site = record.device.location.name if record and record.device.location else ""
        html_content = render_to_string(
            "nv_config_manager/inc/pending_deployment.html",
            {
                "is_pending_deployment": record.is_pending,
                "temporal_url": settings.PLUGINS_CONFIG["nv_config_manager"].get("temporal_url"),
                "site": site,
                "device_id": record.device.pk,
            },
        )
        return format_html(html_content)

    def order(self, queryset, is_descending):
        """Custom ordering for Pending Deploy."""
        queryset = queryset.annotate(
            pending_status=Case(
                When(
                    Q(intended_config__isnull=False)
                    & Q(backup_config__isnull=False)
                    & Q(intended_config__commit_id__isnull=False)
                    & Q(backup_config__deployed_commit_id__isnull=False)
                    & ~Q(intended_config__commit_id=F("backup_config__deployed_commit_id")),
                    then=Value(True),
                ),
                default=Value(False),
                output_field=BooleanField(),
            ),
        ).order_by(
            ("-pending_status" if is_descending else "pending_status"),
        )

        return (queryset, True)


class SeeDiffColumn(tables.Column):
    """Per-row link to the read-only Configuration Diff workflow."""

    def render(self, record):  # pylint: disable=arguments-renamed
        """Render the See Diff button."""
        site = record.device.location.name if record and record.device.location else ""
        html_content = render_to_string(
            "nv_config_manager/inc/see_diff.html",
            {
                "temporal_url": settings.PLUGINS_CONFIG["nv_config_manager"].get("temporal_url"),
                "site": site,
                "device_id": record.device.pk,
                "tenant": getattr(record.device.tenant, "name", "") if record else "",
                "status": getattr(record.device.status, "name", "") if record else "",
            },
        )
        return format_html(html_content)


class DeviceRoleColumn(tables.Column):
    """Custom Device Role Column."""

    def render(self, record):  # pylint: disable=arguments-renamed
        """Render Device Role Column."""
        # device_role = record.device.device_role
        device_role = record.device.role
        if device_role:
            device_role_page_url = reverse(
                # "dcim:devicerole", kwargs={"pk": device_role.pk}
                "extras:role",
                kwargs={"pk": device_role.pk},
            )
            return format_html('<a href="{}">{}</a>', device_role_page_url, device_role)
        return ""

    def order(self, queryset, is_descending):
        """Custom ordering for Device Role."""
        return (
            queryset.order_by("-device__role" if is_descending else "device__role"),
            True,
        )


class DeviceTypeColumn(tables.Column):
    """Custom Device Type Column."""

    def render(self, record):  # pylint: disable=arguments-renamed
        """Render Device Type Column."""
        device_type = record.device.device_type
        if device_type:
            device_type_page_url = reverse("dcim:devicetype", kwargs={"pk": device_type.pk})
            return format_html('<a href="{}">{}</a>', device_type_page_url, device_type)
        return ""

    def order(self, queryset, is_descending):
        """Custom ordering for Device Types."""
        return (
            queryset.order_by("-device__device_type" if is_descending else "device__device_type"),
            True,
        )


class PlatformColumn(tables.Column):
    """Custom Platform Column."""

    def render(self, record):  # pylint: disable=arguments-renamed
        """Render Platform Column."""
        platform = record.device.platform
        if platform:
            platform_page_url = reverse("dcim:platform", kwargs={"pk": platform.pk})
            return format_html('<a href="{}">{}</a>', platform_page_url, platform)
        return ""

    def order(self, queryset, is_descending):
        """Custom ordering for platform."""
        return (
            queryset.order_by("-device__platform" if is_descending else "device__platform"),
            True,
        )


class TenantColumn(tables.Column):
    """Custom Tenant Column."""

    def render(self, record):  # pylint: disable=arguments-renamed
        """Render Tenant Column."""
        tenant = record.device.tenant
        if tenant:
            tenant_page_url = reverse("tenancy:tenant", kwargs={"pk": tenant.pk})
            return format_html('<a href="{}">{}</a>', tenant_page_url, tenant)
        return ""

    def order(self, queryset, is_descending):
        """Custom ordering for Tenant."""
        return (
            queryset.order_by("-device__tenant" if is_descending else "device__tenant"),
            True,
        )


class LocationColumn(tables.Column):
    """Custom Location Column."""

    def render(self, record):  # pylint: disable=arguments-renamed
        """Render Location Column."""
        location = record.device.location
        if location:
            location_page_url = reverse("dcim:location", kwargs={"pk": location.pk})
            return format_html('<a href="{}">{}</a>', location_page_url, location)
        return ""

    def order(self, queryset, is_descending):
        """Custom ordering for Location."""
        return (
            queryset.order_by("-device__location" if is_descending else "device__location"),
            True,
        )


class RackColumn(tables.Column):
    """Custom Rack Column."""

    def render(self, record):  # pylint: disable=arguments-renamed
        """Render Rack Column."""
        rack = record.device.rack
        if rack:
            rack_page_url = reverse("dcim:rack", kwargs={"pk": rack.pk})
            return format_html('<a href="{}">{}</a>', rack_page_url, rack)
        return ""

    def order(self, queryset, is_descending):
        """Custom ordering for Rack."""
        return (
            queryset.order_by("-device__rack" if is_descending else "device__rack"),
            True,
        )


class ConfigManagerConfigStatusTable(BaseTable):  # pylint: disable=too-few-public-methods
    """Abstract base for config-status tables."""

    pk = ToggleColumn()
    config_store__instance = tables.Column()
    path = tables.Column()
    commit_id = tables.Column()
    # updated = tables.DateColumn(format="Y-m-d H:i:s")
    updated = tables.DateTimeColumn()
    updated_by = tables.Column()

    class Meta:  # pylint: disable=too-few-public-methods
        """Metaclass Attributes."""

        abstract = True


class ConfigManagerDeviceStatusTable(BaseTable):
    """Config Manager device-status table."""

    pk = ToggleColumn()
    device = tables.LinkColumn("plugins:nv_config_manager:configmanagerdevicestatus", args=[A("pk")])
    intended_config = tables.Column(verbose_name="Intended Config")
    backup_config = tables.Column(verbose_name="Backup Config")
    is_pending = PendingDeployColumn(verbose_name="Pending", empty_values=())
    is_aggregate_managed = BooleanColumn(verbose_name="Aggregate Managed")
    device_role = DeviceRoleColumn(verbose_name="Device Role", empty_values=())
    device_type = DeviceTypeColumn(verbose_name="Device Type", empty_values=())
    platform = PlatformColumn(verbose_name="Platform", empty_values=())
    tenant = TenantColumn(verbose_name="Tenant", empty_values=())
    location = LocationColumn(verbose_name="Location", empty_values=())
    rack = RackColumn(verbose_name="Rack", empty_values=())
    see_diff = SeeDiffColumn(verbose_name="Live Diff", empty_values=(), orderable=False)

    def render_intended_config(self, record):
        """Render date for intended config and link out to config store."""
        if record.intended_config:
            updated = record.intended_config.updated.strftime("%b %d, %Y %H:%M:%S")
            commit_message = record.intended_config.commit_message
            commit_link = generate_config_store_url(record.intended_config, "commit")

            if commit_link:
                config_store_commit_link = (
                    f'<a href={commit_link} target="_blank" title="{commit_message}">{updated}</a>'
                )
                return format_html(config_store_commit_link)
        return "—"

    def render_backup_config(self, record):
        """Render date for backup config and link out to config store."""
        if record.backup_config:
            updated = record.backup_config.updated.strftime("%b %d, %Y %H:%M:%S")
            commit_message = record.backup_config.commit_message
            commit_link = generate_config_store_url(record.backup_config, "commit")

            if commit_link:
                config_store_commit_link = (
                    f'<a href={commit_link} target="_blank" title="{commit_message}">{updated}</a>'
                )
                return format_html(config_store_commit_link)
        return "—"

    class Meta(BaseTable.Meta):  # pylint: disable=too-few-public-methods
        """Metaclass Attributes."""

        model = ConfigManagerDeviceStatus
        fields = [
            "pk",
            "device",
            "intended_config",
            "backup_config",
            "is_pending",
            "is_aggregate_managed",
            "device_role",
            "device_type",
            "platform",
            "tenant",
            "location",
            "see_diff",
        ]
        default_columns = [
            "pk",
            "device",
            "intended_config",
            "backup_config",
            "is_pending",
            "is_aggregate_managed",
            "device_role",
            "device_type",
            "platform",
            "tenant",
            "location",
            "see_diff",
        ]
