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
"""Custom Homepage Panels."""

from nautobot.core.apps import HomePageItem, HomePagePanel

from nv_config_manager.models import ConfigManagerDeviceStatus


def get_managed_devices_pending(request):
    """Count pending managed devices where intended_config.updated > backup_config.updated."""
    queryset = ConfigManagerDeviceStatus.objects.all()
    return sum(1 for device in queryset if device.is_pending)


def get_managed_devices(request):
    """Count all managed devices."""
    return ConfigManagerDeviceStatus.objects.all().count()


layout = (
    HomePagePanel(
        name="NVIDIA Config Manager",
        weight=150,
        items=(
            HomePageItem(
                name="Managed Devices",
                link="plugins:nv_config_manager:configmanagerdevicestatus_list",
                permissions=["nv_config_manager.view_configmanagerdevicestatus"],
                custom_template="homepage_managed_devices.html",
                custom_data={
                    "managed_devices_count": get_managed_devices,
                    "managed_devices_url": "plugins:nv_config_manager:configmanagerdevicestatus_list",
                    "managed_devices_label": "Managed Devices",
                    "managed_devices_description": "All Config Manager Devices",
                    "permissions": "nv_config_manager.view_configmanagerdevicestatus",
                },
                weight=100,
            ),
            HomePageItem(
                name="Pending Deployments",
                link="plugins:nv_config_manager:configmanagerdevicestatus_list",
                custom_template="homepage_managed_devices.html",
                custom_data={
                    "managed_devices_count": get_managed_devices_pending,
                    "managed_devices_url": "plugins:nv_config_manager:configmanagerdevicestatus_list",
                    "managed_devices_label": "Pending Deployments",
                    "managed_devices_description": "Devices Pending Configuration Deployment",
                    "query": "?is_pending=True",
                    "permissions": "nv_config_manager.view_configmanagerdevicestatus",
                },
                permissions=["nv_config_manager.view_configmanagerdevicestatus"],
                weight=100,
            ),
        ),
    ),
)
