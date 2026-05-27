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
"""Template extensions."""

from django.urls import reverse
from nautobot.apps.ui import TemplateExtension

from nv_config_manager.models import ConfigManagerDeviceStatus
from nv_config_manager.utils import get_all_descendants

# pylint: disable=abstract-method


class ConfigManagerExtraTabs(TemplateExtension):
    """Add Workflows tab to ConfigManagerDeviceStatus."""

    model = "nv_config_manager.configmanagerdevicestatus"

    def detail_tabs(self):
        """Add workflows tab."""
        return [
            {
                "title": "Workflows",
                "url": reverse(
                    "plugins:nv_config_manager:configmanagerdevicestatus_workflows",
                    kwargs={"pk": self.context["object"].pk},
                ),
            }
        ]


class LocationExtraTabs(TemplateExtension):
    """Add Managed Devices tab to dcim.location."""

    model = "dcim.location"

    def detail_tabs(self):
        """Add the managed-devices table to the dcim.location detail view."""
        location = self.context.get("object")
        # get_all_descendants returns a list of location IDs including the location itself
        location_ids = get_all_descendants(location)

        devices = ConfigManagerDeviceStatus.objects.filter(
            device__location__in=location_ids,
        )

        if devices.exists():
            return [
                {
                    "title": self.render(
                        "nv_config_manager/inc/tab_title.html",
                        extra_context={
                            "title": "Managed Devices",
                            "item_count": devices.count(),
                        },
                    ),
                    "url": reverse(
                        "plugins:nv_config_manager:location_managed_devices",
                        kwargs={"pk": self.context["object"].pk},
                    ),
                }
            ]
        return []


class DeviceExtraTabs(TemplateExtension):
    """Add Config Manager + Config Workflows tabs to dcim.Device."""

    model = "dcim.device"

    def detail_tabs(self):
        """Add the Config Manager tabs to the dcim.device detail view."""
        device = self.context.get("object")
        managed_device_data = ConfigManagerDeviceStatus.objects.filter(device=device)

        if managed_device_data.exists():
            return [
                {
                    "title": "Config Manager",
                    "url": reverse(
                        "plugins:nv_config_manager:device_config_manager_info",
                        kwargs={"pk": self.context["object"].pk},
                    ),
                },
                {
                    "title": "Config Workflows",
                    "url": reverse(
                        "plugins:nv_config_manager:device_config_manager_workflows",
                        kwargs={"pk": self.context["object"].pk},
                    ),
                },
            ]
        return []


template_extensions = [LocationExtraTabs, DeviceExtraTabs, ConfigManagerExtraTabs]
