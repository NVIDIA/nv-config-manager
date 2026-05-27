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
"""API serializers for nv_config_manager."""

from nautobot.core.api.fields import NautobotHyperlinkedRelatedField
from nautobot.extras.api.serializers import NautobotModelSerializer

from nv_config_manager.models import (
    BackupConfig,
    ConfigManagerDeviceStatus,
    IntendedConfig,
)


class ConfigManagerDeviceStatusSerializer(NautobotModelSerializer):
    """Device-status API serializer."""

    class Meta:
        """Metaclass Attributes."""

        model = ConfigManagerDeviceStatus
        fields = "__all__"


class IntendedConfigSerializer(NautobotModelSerializer):
    """IntendedConfig API Serializer."""

    device_id = NautobotHyperlinkedRelatedField(
        queryset=ConfigManagerDeviceStatus.objects.all(),
    )

    class Meta:
        """Metaclass Attributes."""

        model = IntendedConfig
        fields = "__all__"


class BackupConfigSerializer(NautobotModelSerializer):
    """BackupConfig API Serializer."""

    device_id = NautobotHyperlinkedRelatedField(
        queryset=ConfigManagerDeviceStatus.objects.all(),
    )

    class Meta:
        """Metaclass Attributes."""

        model = BackupConfig
        fields = "__all__"
