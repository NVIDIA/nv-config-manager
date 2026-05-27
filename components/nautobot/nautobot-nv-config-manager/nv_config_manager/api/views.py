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
"""API views for nv_config_manager models."""

from datetime import datetime

from django.db import transaction
from nautobot.dcim.models import Device
from nautobot.extras.api.views import NautobotModelViewSet
from rest_framework import status
from rest_framework.response import Response

from nv_config_manager import filters
from nv_config_manager.api import serializers
from nv_config_manager.models import BackupConfig, ConfigManagerDeviceStatus, IntendedConfig


class ConfigManagerDeviceStatusAPIView(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """Device-status API viewset."""

    queryset = ConfigManagerDeviceStatus.objects.all()
    serializer_class = serializers.ConfigManagerDeviceStatusSerializer
    filterset_class = filters.ConfigManagerDeviceStatusFilterSet


class IntendedConfigAPIView(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """IntendedConfig API View."""

    queryset = IntendedConfig.objects.prefetch_related("device_id")
    serializer_class = serializers.IntendedConfigSerializer
    filterset_class = filters.IntendedConfigFilterSet

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Automatically instantiate a device as a managed device when pushing/updating a config."""
        device_id = request.data.get("device_id")

        try:
            device = Device.objects.get(pk=device_id)

            managed_device, _ = ConfigManagerDeviceStatus.objects.get_or_create(device=device)
            data = request.data.copy()
            data["device_id"] = managed_device.id
            data["updated"] = datetime.fromisoformat(data["updated"])

            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)

            if not IntendedConfig.objects.filter(pk=device_id).exists():
                intended_config = IntendedConfig.objects.create(**serializer.validated_data)
            else:
                IntendedConfig.objects.filter(pk=device_id).update(**serializer.validated_data)
                intended_config = IntendedConfig.objects.get(pk=device_id)

            serializer = self.serializer_class(intended_config, context={"request": request})

            return Response(
                self.get_serializer(intended_config).data,
                status=status.HTTP_201_CREATED,
            )
        except Device.DoesNotExist:
            return Response(
                {"error": f"Device not found with ID: {device_id}"},
                status=status.HTTP_404_NOT_FOUND,
            )


class BackupConfigAPIView(NautobotModelViewSet):  # pylint: disable=too-many-ancestors
    """BackupConfig API View."""

    queryset = BackupConfig.objects.prefetch_related("device_id")
    serializer_class = serializers.BackupConfigSerializer
    filterset_class = filters.BackupConfigFilterSet

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Automatically instantiate a device as a managed device when pushing/updating a config."""
        device_id = request.data.get("device_id")

        try:
            device = Device.objects.get(pk=device_id)

            managed_device, _ = ConfigManagerDeviceStatus.objects.get_or_create(device=device)
            request.data["device_id"] = managed_device

            request.data["updated"] = datetime.fromisoformat(request.data["updated"])

            if not BackupConfig.objects.filter(pk=device_id).exists():
                backup_config = BackupConfig.objects.create(**request.data)
            else:
                BackupConfig.objects.filter(pk=device_id).update(**request.data)
                backup_config = BackupConfig.objects.get(pk=device_id)

            serializer = self.serializer_class(backup_config, context={"request": request})

            return Response(
                serializer.data,
                status=status.HTTP_201_CREATED,
            )
        except Device.DoesNotExist:
            return Response(
                {"error": f"Device not found with ID: {device_id}"},
                status=status.HTTP_404_NOT_FOUND,
            )
