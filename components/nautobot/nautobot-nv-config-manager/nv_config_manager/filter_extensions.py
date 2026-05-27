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
"""Extensions to built-in Nautobot filters."""

from django import forms
from nautobot.apps.filters import (
    FilterExtension,
    RelatedMembershipBooleanFilter,
)
from nautobot.apps.forms import StaticSelect2
from nautobot.core.forms.constants import BOOLEAN_WITH_BLANK_CHOICES


class DeviceFilterExtension(FilterExtension):  # pylint: disable=too-few-public-methods
    """Add `nv_config_manager_device_status` boolean filter to Device.

    Filter name is prefixed with AppConfig.name per Nautobot's
    register_filter_extensions check.
    """

    model = "dcim.device"

    filterset_fields = {
        "nv_config_manager_device_status": RelatedMembershipBooleanFilter(
            field_name="configmanagerdevicestatus",
            label="Config Manager Enabled",
        ),
    }

    filterform_fields = {
        "nv_config_manager_device_status": forms.NullBooleanField(
            required=False,
            label="Config Manager Enabled",
            widget=StaticSelect2(choices=BOOLEAN_WITH_BLANK_CHOICES),
        ),
    }


filter_extensions = [DeviceFilterExtension]
