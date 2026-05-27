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
"""Migration: remove vrfs/vlans/route_targets M2M from Overlay; add partition_id for NVLink Partition."""

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_app_overlays", "0004_pkey_validator_rack_content_type"),
    ]

    operations = [
        # Remove the M2M relationships that belonged to VXLAN EVPN overlays only.
        # VRF/VLAN/RouteTarget associations are now tracked via OverlayAssignment records.
        migrations.RemoveField(
            model_name="overlay",
            name="route_targets",
        ),
        migrations.RemoveField(
            model_name="overlay",
            name="vlans",
        ),
        migrations.RemoveField(
            model_name="overlay",
            name="vrfs",
        ),
        # Add partition_id for NVLink Partition overlay type (stores the integer partition ID 1-32766)
        migrations.AddField(
            model_name="overlay",
            name="partition_id",
            field=models.PositiveIntegerField(
                blank=True,
                null=True,
                validators=[
                    django.core.validators.MinValueValidator(1),
                    django.core.validators.MaxValueValidator(32766),
                ],
                help_text="NVLink Partition identifier (1-32766)",
            ),
        ),
    ]
