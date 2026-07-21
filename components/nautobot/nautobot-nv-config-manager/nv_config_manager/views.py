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
"""Views."""

import logging

from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from nautobot.core.views import generic
from nautobot.core.views.mixins import ObjectPermissionRequiredMixin
from nautobot.dcim.models import Device, Location

from nv_config_manager import filters, forms, models, tables
from nv_config_manager.utils import (
    bulk_create_managed_devices,
    generate_config_store_url,
    get_all_descendants,
)

logger = logging.getLogger(__name__)


def generate_config_urls(instance):
    """Handle URL formatting and generation for configs."""
    config_store_links = {
        "intended_config_version": None,
        "intended_config_history": None,
        "last_config_backup": None,
        "backup_history": None,
    }

    if instance:
        intended_config = getattr(instance, "intended_config", None)
        backup_config = getattr(instance, "backup_config", None)

        if intended_config:
            config_store_links.update(
                {
                    "intended_config_version": generate_config_store_url(intended_config, "commit"),
                    "intended_config_history": generate_config_store_url(intended_config, "history"),
                }
            )

        if backup_config:
            config_store_links.update(
                {
                    "last_config_backup": generate_config_store_url(backup_config, "commit"),
                    "backup_history": generate_config_store_url(backup_config, "history"),
                }
            )
    return config_store_links


class ConfigManagerDeviceStatusListView(generic.ObjectListView):
    """List view for ConfigManagerDeviceStatus."""

    queryset = models.ConfigManagerDeviceStatus.objects.all()
    table = tables.ConfigManagerDeviceStatusTable
    filterset = filters.ConfigManagerDeviceStatusFilterSet
    filterset_form = forms.ConfigManagerDeviceStatusFilterForm
    action_buttons = ("add",)
    template_name = "nv_config_manager/configmanagerdevicestatus_list.html"

    def extra_context(self):
        """Return extra data for populating stats."""
        context = super().extra_context()
        queryset = models.ConfigManagerDeviceStatus.objects.all()
        context["managed_devices_count"] = queryset.count()
        context["managed_devices_pending_count"] = sum(1 for device in queryset if device.is_pending)

        return context


class ConfigManagerDeviceStatusAddView(ObjectPermissionRequiredMixin, View):
    """Bulk-add view for ConfigManagerDeviceStatus."""

    queryset = models.ConfigManagerDeviceStatus.objects.all()
    template_name = "nv_config_manager/configmanagerdevicestatus_add.html"

    def get_required_permission(self):
        """Require permission to add managed devices."""
        return "nv_config_manager.add_configmanagerdevicestatus"

    def _return_url(self):
        return reverse("plugins:nv_config_manager:configmanagerdevicestatus_list")

    def _context(self, form):
        return {
            "form": form,
            "return_url": self._return_url(),
            "editing": False,
            "obj": None,
            "obj_type": "Managed Device",
        }

    def get(self, request):
        """Render the bulk-add filter form."""
        form = forms.ConfigManagerDeviceStatusBulkAddForm()
        return render(request, self.template_name, self._context(form))

    def post(self, request):
        """Enroll the selected devices into Config Manager."""
        form = forms.ConfigManagerDeviceStatusBulkAddForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, self._context(form))

        try:
            created_count, skipped_count = bulk_create_managed_devices(
                list(form.get_devices_to_add()),
                render_enabled=form.cleaned_data.get("render_enabled"),
                ztp_enabled=form.cleaned_data.get("ztp_enabled"),
                deploy_enabled=form.cleaned_data.get("deploy_enabled"),
                backup_enabled=form.cleaned_data.get("backup_enabled"),
                is_aggregate_managed=form.cleaned_data.get("is_aggregate_managed"),
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Bulk managed-device enrollment failed")
            messages.error(request, f"Failed to add managed devices: {exc}")
            return render(request, self.template_name, self._context(form))

        if created_count:
            messages.success(request, f"Added {created_count} managed device(s) to Config Manager.")
        if skipped_count:
            messages.warning(request, f"Skipped {skipped_count} device(s) that were already managed.")
        return redirect(self._return_url())


class ConfigManagerDeviceStatusEditView(generic.ObjectEditView):
    """Edit view for ConfigManagerDeviceStatus."""

    queryset = models.ConfigManagerDeviceStatus.objects.all()
    model_form = forms.ConfigManagerDeviceStatusEditForm
    template_name = "nv_config_manager/configmanagerdevicestatus_edit.html"


class ConfigManagerDeviceStatusBulkEditView(generic.BulkEditView):
    """Bulk edit view for ConfigManagerDeviceStatus."""

    queryset = models.ConfigManagerDeviceStatus.objects.all()
    form = forms.ConfigManagerDeviceStatusBulkEditForm
    table = tables.ConfigManagerDeviceStatusTable


class ConfigManagerDeviceStatusDeleteView(generic.ObjectDeleteView):
    """Delete view for ConfigManagerDeviceStatus."""

    queryset = models.ConfigManagerDeviceStatus.objects.all()


class ConfigManagerDeviceStatusBulkDeleteView(generic.BulkDeleteView):
    """Bulk delete view for ConfigManagerDeviceStatus."""

    queryset = models.ConfigManagerDeviceStatus.objects.all()
    table = tables.ConfigManagerDeviceStatusTable


class ConfigManagerDeviceStatusDetailView(generic.ObjectView):
    """Detail view for ConfigManagerDeviceStatus."""

    queryset = models.ConfigManagerDeviceStatus.objects.all()
    template_name = "nv_config_manager/configmanagerdevicestatus_retrieve.html"

    def get_extra_context(self, request, instance=None):
        """Return extra data for populating detail view."""
        context = super().get_extra_context(request, instance)

        context["config_store_links"] = generate_config_urls(instance)
        context["temporal_url"] = settings.PLUGINS_CONFIG["nv_config_manager"].get("temporal_url")
        context["device_id"] = instance.device.pk if instance else ""
        context["site"] = instance.device.location.name if instance and instance.device.location else ""
        context["tenant"] = getattr(instance.device.tenant, "name", "") if instance else ""
        context["status"] = getattr(instance.device.status, "name", "") if instance else ""
        return context


class ConfigManagerDeviceStatusWorkflowsTab(generic.ObjectView):
    """View for displaying Workflows for a managed device."""

    queryset = models.ConfigManagerDeviceStatus.objects.all()
    template_name = "nv_config_manager/configmanagerdevicestatus_workflows_tab.html"

    def get_extra_context(self, request, instance=None):
        """Return any additional context data for the template."""
        context = super().get_extra_context(request, instance)
        context["managed_device"] = instance
        context["device_id"] = instance.device.pk if instance else ""
        context["tenant"] = getattr(instance.device.tenant, "name", "") if instance else ""
        context["status"] = getattr(instance.device.status, "name", "") if instance else ""
        context["temporal_url"] = settings.PLUGINS_CONFIG["nv_config_manager"].get("temporal_url")
        context["site"] = instance.device.location.name if instance and instance.device.location else ""

        return context


class LocationManagedDevicesViewTab(generic.ObjectView):
    """View for displaying managed devices by location."""

    queryset = Location.objects.all()
    template_name = "nv_config_manager/inc/managed_devices_table.html"

    def get_extra_context(self, request, instance=None):
        """Return any additional context data for the template."""
        context = super().get_extra_context(request, instance)

        if instance:
            # get_all_descendants returns a list of location IDs including the instance itself
            location_ids = get_all_descendants(instance)
            managed_devices = models.ConfigManagerDeviceStatus.objects.filter(
                device__location__in=location_ids
            ).select_related("device", "device__location")
            managed_devices_table = tables.ConfigManagerDeviceStatusTable(data=managed_devices, user=request.user)
            if order_by := request.GET.get("sort"):
                managed_devices_table.order_by = order_by

            context["location"] = instance
            context["managed_devices_table"] = managed_devices_table
            context["html"] = "dcim/location.html"

            is_pending = {}
            for managed_device in managed_devices:
                is_pending[managed_device] = managed_device.is_pending

            context["is_pending_deployment"] = is_pending

        return context


class DeviceConfigManagerWorkflowsViewTab(generic.ObjectView):
    """Tab to view Config Manager workflows in Device view."""

    queryset = Device.objects.all()
    template_name = "nv_config_manager/configmanagerdevicestatus_workflows_tab.html"

    def get_extra_context(self, request, instance=None):
        """Return any additional context data for the template."""
        context = super().get_extra_context(request, instance)
        managed_device = get_object_or_404(models.ConfigManagerDeviceStatus.objects, device=instance)
        context["managed_device"] = managed_device
        context["temporal_url"] = settings.PLUGINS_CONFIG["nv_config_manager"].get("temporal_url")
        context["device_id"] = managed_device.device.pk
        context["tenant"] = getattr(instance.tenant, "name", "") if instance else ""
        context["status"] = getattr(instance.status, "name", "") if instance else ""
        context["html"] = "dcim/device.html"
        context["site"] = instance.location.name if instance and instance.location else ""

        return context


class DeviceConfigManagerInfoViewTab(generic.ObjectView):
    """View for displaying Config Manager info in dcim.device."""

    queryset = Device.objects.all()
    template_name = "nv_config_manager/device_config_manager_info_tab.html"

    def get_extra_context(self, request, instance=None):
        """Return any additional context data for the template."""
        context = super().get_extra_context(request, instance)

        managed_device_instance = get_object_or_404(models.ConfigManagerDeviceStatus.objects, device=instance)
        context["managed_device_instance"] = managed_device_instance
        context["config_store_links"] = generate_config_urls(managed_device_instance)
        context["temporal_url"] = settings.PLUGINS_CONFIG["nv_config_manager"].get("temporal_url")
        context["device_id"] = managed_device_instance.device.pk
        context["site"] = instance.location.name if instance and instance.location else ""
        context["tenant"] = getattr(instance.tenant, "name", "") if instance else ""
        context["status"] = getattr(instance.status, "name", "") if instance else ""
        context["edit_url"] = reverse(
            "plugins:nv_config_manager:configmanagerdevicestatus_edit",
            kwargs={"pk": instance.pk if instance else ""},
        )
        return context
