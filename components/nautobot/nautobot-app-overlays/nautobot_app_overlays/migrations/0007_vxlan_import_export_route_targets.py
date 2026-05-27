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
# Generated manually for VXLAN import/export route targets.

from django.db import migrations, models


class Migration(migrations.Migration):
    """Add M2M import/export route targets to VXLAN."""

    dependencies = [
        ("nautobot_app_overlays", "0006_rename_nmx_m_to_nvlink_partition"),
    ]

    operations = [
        migrations.AddField(
            model_name="vxlan",
            name="export_targets",
            field=models.ManyToManyField(
                blank=True,
                help_text="Export route targets for this VNI.",
                related_name="exporting_vxlans",
                to="ipam.routetarget",
            ),
        ),
        migrations.AddField(
            model_name="vxlan",
            name="import_targets",
            field=models.ManyToManyField(
                blank=True,
                help_text="Import route targets for this VNI.",
                related_name="importing_vxlans",
                to="ipam.routetarget",
            ),
        ),
    ]
