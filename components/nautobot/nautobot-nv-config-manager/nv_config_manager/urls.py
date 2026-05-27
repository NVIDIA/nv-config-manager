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
"""URL patterns for nv_config_manager."""

from django.urls import path
from nautobot.extras.views import ObjectChangeLogView

from nv_config_manager import views
from nv_config_manager.models import ConfigManagerDeviceStatus

urlpatterns = [
    path(
        "configmanagerdevicestatus/",
        views.ConfigManagerDeviceStatusListView.as_view(),
        name="configmanagerdevicestatus_list",
    ),
    path(
        "configmanagerdevicestatus/add/",
        views.ConfigManagerDeviceStatusAddView.as_view(),
        name="configmanagerdevicestatus_add",
    ),
    path(
        "configmanagerdevicestatus/<uuid:pk>/edit/",
        views.ConfigManagerDeviceStatusEditView.as_view(),
        name="configmanagerdevicestatus_edit",
    ),
    path(
        "configmanagerdevicestatus/edit/",
        views.ConfigManagerDeviceStatusBulkEditView.as_view(),
        name="configmanagerdevicestatus_bulk_edit",
    ),
    path(
        "configmanagerdevicestatus/delete/",
        views.ConfigManagerDeviceStatusBulkDeleteView.as_view(),
        name="configmanagerdevicestatus_bulk_delete",
    ),
    path(
        "configmanagerdevicestatus/<uuid:pk>/delete/",
        views.ConfigManagerDeviceStatusDeleteView.as_view(),
        name="configmanagerdevicestatus_delete",
    ),
    path(
        "configmanagerdevicestatus/<uuid:pk>/",
        views.ConfigManagerDeviceStatusDetailView.as_view(),
        name="configmanagerdevicestatus",
    ),
    path(
        "configmanagerdevicestatus/<uuid:pk>/workflows/",
        views.ConfigManagerDeviceStatusWorkflowsTab.as_view(),
        name="configmanagerdevicestatus_workflows",
    ),
    path(
        "configmanagerdevicestatus/<uuid:pk>/changelog/",
        ObjectChangeLogView.as_view(),
        name="configmanagerdevicestatus_changelog",
        kwargs={"model": ConfigManagerDeviceStatus},
    ),
    path(
        "location/<uuid:pk>/managed-devices/",
        views.LocationManagedDevicesViewTab.as_view(),
        name="location_managed_devices",
    ),
    path(
        "device/<uuid:pk>/config-manager/",
        views.DeviceConfigManagerInfoViewTab.as_view(),
        name="device_config_manager_info",
    ),
    path(
        "device/<uuid:pk>/config-workflows/",
        views.DeviceConfigManagerWorkflowsViewTab.as_view(),
        name="device_config_manager_workflows",
    ),
]
