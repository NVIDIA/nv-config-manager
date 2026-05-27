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
"""Migration: add InfiniBandMKey model and db_index to OverlayAssignment.assigned_object_id."""

import uuid

import django.core.serializers.json
import django.core.validators
import django.db.models.deletion
import nautobot.core.models.fields
import nautobot.extras.models.mixins
import nautobot.extras.models.statuses
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("nautobot_app_overlays", "0002_initial"),
        ("extras", "0125_jobresult_date_started"),
        ("tenancy", "0009_update_all_charfields_max_length_to_255"),
        ("dcim", "0075_interface_duplex_interface_speed_and_more"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [
        # Add db_index to assigned_object_id for faster GenericFK lookups
        migrations.AlterField(
            model_name="overlayassignment",
            name="assigned_object_id",
            field=models.UUIDField(db_index=True, help_text="ID of assigned object"),
        ),
        migrations.CreateModel(
            name="InfiniBandMKey",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False, unique=True
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True, null=True)),
                ("last_updated", models.DateTimeField(auto_now=True, null=True)),
                (
                    "_custom_field_data",
                    models.JSONField(blank=True, default=dict, encoder=django.core.serializers.json.DjangoJSONEncoder),
                ),
                ("name", models.CharField(max_length=255, help_text="Descriptive name")),
                (
                    "mkey_value",
                    models.CharField(
                        max_length=18,
                        help_text="64-bit Management Key hex value (e.g., '0x0000000000a12c30')",
                        validators=[
                            django.core.validators.RegexValidator(
                                "^0x[0-9a-fA-F]{1,16}$",
                                message="Must be a 64-bit hex value (e.g., '0x0000000000a12c30')",
                            )
                        ],
                    ),
                ),
                (
                    "mkey_per_port",
                    models.BooleanField(
                        default=False,
                        help_text="Derive a unique MKey per HCA port instead of using a global key",
                    ),
                ),
                (
                    "mkey_lease_period",
                    models.PositiveIntegerField(
                        default=60,
                        validators=[django.core.validators.MaxValueValidator(65535)],
                        help_text="MKey lease period in seconds (0=infinite, 1-65535)",
                    ),
                ),
                (
                    "protect_bits",
                    models.IntegerField(
                        default=0,
                        validators=[
                            django.core.validators.MinValueValidator(0),
                            django.core.validators.MaxValueValidator(3),
                        ],
                        help_text="MKey protection bits: 0/1=partial enforcement, 2/3=full enforcement",
                    ),
                ),
                (
                    "mkey_global_seed",
                    models.CharField(
                        blank=True,
                        max_length=18,
                        help_text="64-bit hex seed for per-port MKey derivation (only used when mkey_per_port is True)",
                        validators=[
                            django.core.validators.RegexValidator(
                                "^(0x[0-9a-fA-F]{1,16})?$",
                                message="Must be a 64-bit hex value (e.g., '0x0000000000a12c30') or empty",
                            )
                        ],
                    ),
                ),
                (
                    "ufm_device",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="infiniband_mkeys",
                        to="dcim.device",
                        help_text="UFM server device (target for SCP delivery of opensm.conf)",
                    ),
                ),
                (
                    "overlay",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="mkeys",
                        to="nautobot_app_overlays.overlay",
                        help_text="Associated IB MKey overlay",
                    ),
                ),
                (
                    "tenant",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="infiniband_mkeys",
                        to="tenancy.tenant",
                        help_text="Owning tenant",
                    ),
                ),
                (
                    "status",
                    nautobot.extras.models.statuses.StatusField(
                        on_delete=django.db.models.deletion.PROTECT, to="extras.status"
                    ),
                ),
                ("tags", nautobot.core.models.fields.TagsField(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={
                "verbose_name": "InfiniBand MKey",
                "verbose_name_plural": "InfiniBand MKeys",
                "ordering": ["name"],
            },
            bases=(
                nautobot.extras.models.mixins.DynamicGroupMixin,
                nautobot.extras.models.mixins.NotesMixin,
                models.Model,
            ),
        ),
        migrations.AlterUniqueTogether(
            name="infinibandmkey",
            unique_together={("name", "overlay")},
        ),
    ]
