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
from nautobot.tenancy.models import Tenant

from nv_config_manager.models import ConfigManagerDeviceStatus


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


class ConfigManagerDeviceStatusAddForm(NautobotModelForm):  # pylint: disable=too-many-ancestors
    """Add form for ConfigManagerDeviceStatus."""

    tenant = DynamicModelChoiceField(queryset=Tenant.objects.all(), label="Tenant")
    location = DynamicModelChoiceField(
        queryset=Location.objects.all(),
        query_params={
            "tenant": "$tenant",
        },
        label="Location",
        required=False,
    )
    device = DynamicModelChoiceField(
        queryset=Device.objects.all(),
        query_params={
            "location": "$location",
            "tenant": "$tenant",
            "nv_config_manager_device_status": False,
        },
        label="Device",
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

        model = ConfigManagerDeviceStatus
        fields = [
            "location",
            "tenant",
            "device",
            "render_enabled",
            "ztp_enabled",
            "deploy_enabled",
            "backup_enabled",
            "is_aggregate_managed",
        ]


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
