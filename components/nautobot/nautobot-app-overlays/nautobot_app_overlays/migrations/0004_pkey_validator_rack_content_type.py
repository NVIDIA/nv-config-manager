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
"""Migration: add RegexValidator to InfiniBandPKey.pkey and add 'rack' to OverlayAssignment content type choices."""

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_app_overlays", "0003_infinibandmkey_assigned_object_id_index"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        # Add RegexValidator to InfiniBandPKey.pkey (was a plain CharField with no validator)
        migrations.AlterField(
            model_name="infinibandpkey",
            name="pkey",
            field=models.CharField(
                max_length=10,
                help_text="Partition Key value (e.g., '0x8001')",
                validators=[
                    django.core.validators.RegexValidator(
                        r"^0x[0-9a-fA-F]{1,4}$",
                        message="PKey must be a hex value like '0x8001'",
                    )
                ],
            ),
        ),
        # Add 'rack' to the allowed content types for OverlayAssignment
        migrations.AlterField(
            model_name="overlayassignment",
            name="assigned_object_type",
            field=models.ForeignKey(
                help_text="Type of assigned object",
                limit_choices_to={"model__in": ["device", "interface", "rack", "vrf", "vlan", "prefix"]},
                on_delete=django.db.models.deletion.CASCADE,
                to="contenttypes.contenttype",
            ),
        ),
    ]
