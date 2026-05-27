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
"""Initial schema for the nv_config_manager plugin."""

import uuid

import django.core.serializers.json
import django.db.models.deletion
import nautobot.core.models.fields
import nautobot.extras.models.mixins
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("dcim", "0075_interface_duplex_interface_speed_and_more"),
        ("extras", "0125_jobresult_date_started"),
    ]

    operations = [
        migrations.CreateModel(
            name="ConfigManagerDeviceStatus",
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
                ("render_enabled", models.BooleanField(default=False)),
                ("ztp_enabled", models.BooleanField(default=False)),
                ("deploy_enabled", models.BooleanField(default=False)),
                ("backup_enabled", models.BooleanField(default=False)),
                ("is_aggregate_managed", models.BooleanField(default=False)),
                ("device", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to="dcim.device")),
                ("tags", nautobot.core.models.fields.TagsField(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={
                "verbose_name": "Config Manager Device",
                "verbose_name_plural": "Config Manager Devices",
            },
            bases=(
                nautobot.extras.models.mixins.DynamicGroupMixin,
                nautobot.extras.models.mixins.NotesMixin,
                models.Model,
            ),
        ),
        migrations.CreateModel(
            name="IntendedConfig",
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
                ("config_store_instance", models.URLField(max_length=255)),
                ("path", models.CharField(max_length=255)),
                ("updated", models.DateTimeField()),
                ("updated_by", models.CharField(max_length=255)),
                ("commit_id", models.CharField(max_length=255)),
                ("commit_message", models.CharField(max_length=255)),
                ("template_version", models.CharField(max_length=255)),
                (
                    "device_id",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="intended_config",
                        to="nv_config_manager.configmanagerdevicestatus",
                    ),
                ),
                ("tags", nautobot.core.models.fields.TagsField(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={
                "verbose_name": "Intended Config Settings",
                "abstract": False,
            },
            bases=(
                nautobot.extras.models.mixins.DynamicGroupMixin,
                nautobot.extras.models.mixins.NotesMixin,
                models.Model,
            ),
        ),
        migrations.CreateModel(
            name="BackupConfig",
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
                ("config_store_instance", models.URLField(max_length=255)),
                ("path", models.CharField(max_length=255)),
                ("updated", models.DateTimeField()),
                ("updated_by", models.CharField(max_length=255)),
                ("commit_id", models.CharField(max_length=255)),
                ("commit_message", models.CharField(max_length=255)),
                ("deployed_commit_id", models.CharField(blank=True, max_length=255)),
                ("workflow_id", models.CharField(max_length=255)),
                (
                    "device_id",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="backup_config",
                        to="nv_config_manager.configmanagerdevicestatus",
                    ),
                ),
                ("tags", nautobot.core.models.fields.TagsField(through="extras.TaggedItem", to="extras.Tag")),
            ],
            options={
                "verbose_name": "Backup Config Settings",
                "abstract": False,
            },
            bases=(
                nautobot.extras.models.mixins.DynamicGroupMixin,
                nautobot.extras.models.mixins.NotesMixin,
                models.Model,
            ),
        ),
    ]
