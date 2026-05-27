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
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    """Update limit_choices_to to include vxlan."""

    dependencies = [
        ("contenttypes", "0002_remove_content_type_name"),
        ("nautobot_app_overlays", "0008_overlayassignment_import_export_targets"),
    ]

    operations = [
        migrations.AlterField(
            model_name="overlayassignment",
            name="assigned_object_type",
            field=models.ForeignKey(
                help_text="Type of assigned object",
                limit_choices_to={"model__in": ["device", "interface", "rack", "vrf", "vlan", "prefix", "vxlan"]},
                on_delete=django.db.models.deletion.CASCADE,
                to="contenttypes.contenttype",
            ),
        ),
    ]
