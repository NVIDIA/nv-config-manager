# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Data migration: rename isolation_type 'nmx_m' -> 'nvlink_partition'."""

from django.db import migrations


def rename_nmx_m_forward(apps, schema_editor):
    Overlay = apps.get_model("nautobot_app_overlays", "Overlay")
    Overlay.objects.filter(isolation_type="nmx_m").update(isolation_type="nvlink_partition")


def rename_nmx_m_reverse(apps, schema_editor):
    Overlay = apps.get_model("nautobot_app_overlays", "Overlay")
    Overlay.objects.filter(isolation_type="nvlink_partition").update(isolation_type="nmx_m")


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_app_overlays", "0005_overlay_remove_m2m_add_partition_id"),
    ]

    operations = [
        migrations.RunPython(rename_nmx_m_forward, rename_nmx_m_reverse),
    ]
