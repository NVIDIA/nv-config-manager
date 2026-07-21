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
"""Forms."""

from django import forms
from nautobot.apps.forms import (
    BootstrapMixin,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    StaticSelect2,
)
from nautobot.core.forms.constants import BOOLEAN_WITH_BLANK_CHOICES
from nautobot.dcim.models import Device, Location, Platform, Rack
from nautobot.extras.forms import (
    NautobotBulkEditForm,
    NautobotFilterForm,
    NautobotModelForm,
)
from nautobot.extras.models import Role
from nautobot.tenancy.models import Tenant

from nv_config_manager.models import ConfigManagerDeviceStatus
from nv_config_manager.utils import get_eligible_unmanaged_devices


class ConfigManagerDeviceStatusFilterForm(NautobotFilterForm):  # pylint: disable=too-many-ancestors
    """Filter form for ConfigManagerDeviceStatus."""

    model = ConfigManagerDeviceStatus

    location = DynamicModelMultipleChoiceField(
        queryset=Location.objects.all(),
        required=False,
    )
    tenant = DynamicModelMultipleChoiceField(
        queryset=Tenant.objects.all(),
        required=False,
    )
    platform = DynamicModelMultipleChoiceField(queryset=Platform.objects.all(), required=False)
    rack = DynamicModelMultipleChoiceField(queryset=Rack.objects.all(), required=False)
    is_aggregate_managed = forms.NullBooleanField(
        label="Aggregate Managed",
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )


class ConfigManagerDeviceStatusBulkAddForm(BootstrapMixin, forms.Form):
    """Bulk-add form for enrolling unmanaged devices into Config Manager."""

    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        label="Location",
        required=True,
    )
    roles = DynamicModelMultipleChoiceField(
        queryset=Role.objects.all(),
        label="Role",
        required=True,
    )
    devices = DynamicModelMultipleChoiceField(
        queryset=Device.objects.all(),
        label="Devices",
        required=True,
        query_params={
            "location": "$location",
            "role": "$roles",
            "nv_config_manager_device_status": False,
        },
    )
    render_enabled = forms.NullBooleanField(
        label="Enable Render",
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    ztp_enabled = forms.NullBooleanField(
        label="Enable ZTP",
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    deploy_enabled = forms.NullBooleanField(
        label="Enable Deploy",
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    backup_enabled = forms.NullBooleanField(
        label="Enable Backup",
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    is_aggregate_managed = forms.NullBooleanField(
        label="Aggregate Managed",
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )

    class Meta:
        """Metaclass attributes."""

        fields = [
            "location",
            "roles",
            "devices",
            "render_enabled",
            "ztp_enabled",
            "deploy_enabled",
            "backup_enabled",
            "is_aggregate_managed",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label_suffix = ""

    def clean(self):
        """Reject any selected device outside the eligible (unmanaged) set."""
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data

        eligible_ids = set(
            get_eligible_unmanaged_devices(
                cleaned_data["location"],
                cleaned_data["roles"],
            ).values_list("pk", flat=True)
        )
        selected = cleaned_data.get("devices") or []
        if any(device.pk not in eligible_ids for device in selected):
            raise forms.ValidationError("One or more selected devices are not eligible for enrollment.")

        return cleaned_data

    def get_devices_to_add(self):
        """Return the selected devices."""
        return self.cleaned_data.get("devices") or Device.objects.none()


# Backward-compatible alias for imports expecting the old add form name.
ConfigManagerDeviceStatusAddForm = ConfigManagerDeviceStatusBulkAddForm


class ConfigManagerDeviceStatusEditForm(NautobotModelForm):  # pylint: disable=too-many-ancestors
    """Edit form for ConfigManagerDeviceStatus."""

    model = ConfigManagerDeviceStatus

    render_enabled = forms.NullBooleanField(
        label="Enable Render",
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    ztp_enabled = forms.NullBooleanField(
        label="Enable ZTP", required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES)
    )
    deploy_enabled = forms.NullBooleanField(
        label="Enable Deploy",
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    backup_enabled = forms.NullBooleanField(
        label="Enable Backup",
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    is_aggregate_managed = forms.NullBooleanField(
        label="Aggregate Managed",
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )

    class Meta:
        """Metaclass attributes."""

        model = ConfigManagerDeviceStatus
        fields = [
            "render_enabled",
            "ztp_enabled",
            "deploy_enabled",
            "backup_enabled",
            "is_aggregate_managed",
        ]


class ConfigManagerDeviceStatusBulkEditForm(NautobotBulkEditForm):  # pylint: disable=too-many-ancestors
    """Bulk edit form for ConfigManagerDeviceStatus."""

    model = ConfigManagerDeviceStatus
    pk = forms.ModelMultipleChoiceField(
        queryset=ConfigManagerDeviceStatus.objects.all(),
        widget=forms.MultipleHiddenInput(),
    )
    render_enabled = forms.NullBooleanField(
        label="Enable Render",
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    ztp_enabled = forms.NullBooleanField(
        label="Enable ZTP", required=False, widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES)
    )
    deploy_enabled = forms.NullBooleanField(
        label="Enable Deploy",
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    backup_enabled = forms.NullBooleanField(
        label="Enable Backup",
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    is_aggregate_managed = forms.NullBooleanField(
        label="Aggregate Managed",
        required=False,
        widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )

    class Meta:
        """Metaclass attributes."""

        fields = [
            "render_enabled",
            "ztp_enabled",
            "deploy_enabled",
            "backup_enabled",
            "is_aggregate_managed",
        ]
