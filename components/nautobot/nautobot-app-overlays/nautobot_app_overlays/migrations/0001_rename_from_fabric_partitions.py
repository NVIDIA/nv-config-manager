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
"""Migrate from nautobot_fabric_partitions to nautobot_app_overlays."""

from django.db import migrations

OLD_APP = "nautobot_fabric_partitions"
NEW_APP = "nautobot_app_overlays"

OLD_TABLES = [
    f"{OLD_APP}_fabricpartition",
    f"{OLD_APP}_partitionmember",
    f"{OLD_APP}_vxlan",
    f"{OLD_APP}_infinibandpkey",
    f"{OLD_APP}_fabricpartition_vrfs",
    f"{OLD_APP}_fabricpartition_vlans",
    f"{OLD_APP}_fabricpartition_route_targets",
]

TABLE_RENAMES = [
    (f"{OLD_APP}_fabricpartition", f"{NEW_APP}_overlay"),
    (f"{OLD_APP}_partitionmember", f"{NEW_APP}_overlayassignment"),
    (f"{OLD_APP}_vxlan", f"{NEW_APP}_vxlan"),
    (f"{OLD_APP}_infinibandpkey", f"{NEW_APP}_infinibandpkey"),
    (f"{OLD_APP}_fabricpartition_vrfs", f"{NEW_APP}_overlay_vrfs"),
    (f"{OLD_APP}_fabricpartition_vlans", f"{NEW_APP}_overlay_vlans"),
    (f"{OLD_APP}_fabricpartition_route_targets", f"{NEW_APP}_overlay_route_targets"),
]

CONTENT_TYPE_MODEL_RENAMES = [
    ("fabricpartition", "overlay"),
    ("partitionmember", "overlayassignment"),
]

FK_COLUMN_RENAMES = [
    (f"{NEW_APP}_infinibandpkey", "partition_id", "overlay_id"),
    (f"{NEW_APP}_vxlan", "partition_id", "overlay_id"),
    (f"{NEW_APP}_overlayassignment", "partition_id", "overlay_id"),
    (f"{NEW_APP}_overlay_vrfs", "fabricpartition_id", "overlay_id"),
    (f"{NEW_APP}_overlay_vlans", "fabricpartition_id", "overlay_id"),
    (f"{NEW_APP}_overlay_route_targets", "fabricpartition_id", "overlay_id"),
]


def _old_app_exists(cursor):
    """Check if nautobot_fabric_partitions has migration history."""
    cursor.execute(
        "SELECT 1 FROM django_migrations WHERE app = %s LIMIT 1",
        [OLD_APP],
    )
    return cursor.fetchone() is not None


def _new_tables_exist(cursor):
    """Check if the new-named tables already exist."""
    cursor.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name = %s AND table_schema = 'public' LIMIT 1",
        [f"{NEW_APP}_overlay"],
    )
    return cursor.fetchone() is not None


def _fake_new_migration_chain(cursor):
    """Replace migration records for the new app, faking 0002_initial.

    Django automatically records 0001_rename_from_fabric_partitions when
    this RunPython migration completes, so we only need to fake 0002.
    """
    cursor.execute(
        "DELETE FROM django_migrations WHERE app = %s",
        [NEW_APP],
    )
    cursor.execute(
        "INSERT INTO django_migrations (app, name, applied) VALUES (%s, '0002_initial', NOW())",
        [NEW_APP],
    )


def _drop_old_tables(cursor):
    """Drop old-named tables that are stale after a prior CreateModel deploy."""
    for table in OLD_TABLES:
        cursor.execute(f'DROP TABLE IF EXISTS "{table}" CASCADE')


def _delete_old_app_records(cursor):
    """Remove stale migration history for the old app label."""
    cursor.execute(
        "DELETE FROM django_migrations WHERE app = %s",
        [OLD_APP],
    )


def _cleanup_existing_deployment(cursor):
    """Handle clusters where new tables already exist."""
    if _old_app_exists(cursor):
        _drop_old_tables(cursor)
        _delete_old_app_records(cursor)
    _fake_new_migration_chain(cursor)


def _rename_from_old_app(cursor):
    """Full rename path: tables, content types, migration records, FK columns."""
    cursor.execute(
        "UPDATE django_content_type SET app_label = %s WHERE app_label = %s",
        [NEW_APP, OLD_APP],
    )
    for old_model, new_model in CONTENT_TYPE_MODEL_RENAMES:
        cursor.execute(
            "UPDATE django_content_type SET model = %s WHERE app_label = %s AND model = %s",
            [new_model, NEW_APP, old_model],
        )

    for old_table, new_table in TABLE_RENAMES:
        cursor.execute(f'ALTER TABLE "{old_table}" RENAME TO "{new_table}"')

    for table, old_col, new_col in FK_COLUMN_RENAMES:
        cursor.execute(f'ALTER TABLE "{table}" RENAME COLUMN "{old_col}" TO "{new_col}"')

    cursor.execute(
        "DELETE FROM django_migrations WHERE app IN (%s, %s)",
        [OLD_APP, NEW_APP],
    )
    _fake_new_migration_chain(cursor)


def rename_app(apps, schema_editor):
    """Handles scenarios for the app rename."""
    cursor = schema_editor.connection.cursor()

    if _new_tables_exist(cursor):
        _cleanup_existing_deployment(cursor)
    elif _old_app_exists(cursor):
        _rename_from_old_app(cursor)


class Migration(migrations.Migration):
    """Rename nautobot_fabric_partitions -> nautobot_app_overlays."""

    initial = True

    dependencies = []

    operations = [
        migrations.RunPython(
            rename_app,
            migrations.RunPython.noop,
            elidable=True,
        ),
    ]
