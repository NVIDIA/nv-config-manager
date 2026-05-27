#  SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

"""Tests for the app rename migration (0001_rename_from_fabric_partitions).

Covers four database scenarios:
1. Fresh install: no old app, no new tables -> no-op
2. New tables exist, no old records -> fixup migration chain only
3. New tables exist WITH old records (Kind cluster) -> drop old tables + clean up records
4. Only old app exists (pure dev upgrade) -> full rename of tables/content types/FKs
"""

import importlib
from unittest.mock import MagicMock

from django.test import TestCase

_migration_mod = importlib.import_module("nautobot_app_overlays.migrations.0001_rename_from_fabric_partitions")
rename_app = _migration_mod.rename_app
OLD_APP = _migration_mod.OLD_APP
NEW_APP = _migration_mod.NEW_APP
OLD_TABLES = _migration_mod.OLD_TABLES
TABLE_RENAMES = _migration_mod.TABLE_RENAMES
CONTENT_TYPE_MODEL_RENAMES = _migration_mod.CONTENT_TYPE_MODEL_RENAMES
FK_COLUMN_RENAMES = _migration_mod.FK_COLUMN_RENAMES


class MockCursor:
    """Mock database cursor that tracks executed SQL.

    The migration checks (in order):
      1. _new_tables_exist  -> information_schema query
      2. _old_app_exists    -> django_migrations query (only if #1 is False)
         OR _old_app_exists -> django_migrations query (called inside _cleanup_existing_deployment)

    fetchone() responses are driven by a stack so callers can define
    the exact sequence of results.
    """

    def __init__(self, fetchone_results):
        self._fetchone_results = list(fetchone_results)
        self._fetchone_idx = 0
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchone(self):
        if self._fetchone_idx < len(self._fetchone_results):
            result = self._fetchone_results[self._fetchone_idx]
            self._fetchone_idx += 1
            return result
        return None


class RenameAppFreshInstallTestCase(TestCase):
    """Scenario 1: Fresh install (no new tables, no old app)."""

    def test_noop_when_no_old_app(self):
        """Only runs the two existence checks, no mutations."""
        cursor = MockCursor(fetchone_results=[None, None])
        schema_editor = MagicMock()
        schema_editor.connection.cursor.return_value = cursor

        rename_app(apps=None, schema_editor=schema_editor)

        self.assertEqual(len(cursor.executed), 2, "Should only execute the two existence checks")

    def test_first_check_is_new_tables(self):
        """The first query should check information_schema for the new table."""
        cursor = MockCursor(fetchone_results=[None, None])
        schema_editor = MagicMock()
        schema_editor.connection.cursor.return_value = cursor

        rename_app(apps=None, schema_editor=schema_editor)

        sql, params = cursor.executed[0]
        self.assertIn("information_schema", sql)
        self.assertIn(f"{NEW_APP}_overlay", params)

    def test_second_check_is_old_app(self):
        """The second query should check django_migrations for the old app."""
        cursor = MockCursor(fetchone_results=[None, None])
        schema_editor = MagicMock()
        schema_editor.connection.cursor.return_value = cursor

        rename_app(apps=None, schema_editor=schema_editor)

        sql, params = cursor.executed[1]
        self.assertIn("django_migrations", sql)
        self.assertEqual(params, [OLD_APP])


class RenameAppNewTablesNoOldRecordsTestCase(TestCase):
    """Scenario 2: New tables already exist, no old app records.

    This happens when the app was deployed fresh with the old squashed 0001_initial.
    Should only fix migration records.
    """

    def setUp(self):
        # _new_tables_exist -> True, then _old_app_exists (inside cleanup) -> False
        self.cursor = MockCursor(fetchone_results=[(1,), None])
        self.schema_editor = MagicMock()
        self.schema_editor.connection.cursor.return_value = self.cursor
        rename_app(apps=None, schema_editor=self.schema_editor)

    def test_does_not_rename_tables(self):
        alter_stmts = [sql for sql, _ in self.cursor.executed if "RENAME TO" in sql]
        self.assertEqual(len(alter_stmts), 0)

    def test_does_not_update_content_types(self):
        ct_updates = [sql for sql, _ in self.cursor.executed if "UPDATE django_content_type" in sql]
        self.assertEqual(len(ct_updates), 0)

    def test_does_not_drop_old_tables(self):
        drop_stmts = [sql for sql, _ in self.cursor.executed if "DROP TABLE" in sql]
        self.assertEqual(len(drop_stmts), 0)

    def test_fakes_0002_initial(self):
        """Should INSERT a fake record for 0002_initial only (Django records 0001 automatically)."""
        insert_stmts = [sql for sql, _ in self.cursor.executed if "INSERT INTO django_migrations" in sql]
        self.assertEqual(len(insert_stmts), 1)
        self.assertIn("0002_initial", insert_stmts[0])
        self.assertNotIn("0001_rename_from_fabric_partitions", insert_stmts[0])


class RenameAppNewTablesWithOldRecordsTestCase(TestCase):
    """Scenario 3: New tables exist AND old app records remain (Kind cluster state).

    Should drop old tables, delete old content types/migrations, and fix migration chain.
    """

    def setUp(self):
        # _new_tables_exist -> True, then _old_app_exists (inside cleanup) -> True
        self.cursor = MockCursor(fetchone_results=[(1,), (1,)])
        self.schema_editor = MagicMock()
        self.schema_editor.connection.cursor.return_value = self.cursor
        rename_app(apps=None, schema_editor=self.schema_editor)

    def test_drops_all_old_tables(self):
        drop_stmts = [sql for sql, _ in self.cursor.executed if "DROP TABLE" in sql]
        self.assertEqual(len(drop_stmts), len(OLD_TABLES))
        for table, sql in zip(OLD_TABLES, drop_stmts):
            self.assertIn(table, sql)

    def test_leaves_old_content_types_intact(self):
        """Old content types have cascading FK refs, so we intentionally keep them."""
        ct_deletes = [sql for sql, _ in self.cursor.executed if "DELETE FROM django_content_type" in sql]
        self.assertEqual(len(ct_deletes), 0)

    def test_deletes_old_migration_records(self):
        mig_deletes = [(sql, params) for sql, params in self.cursor.executed if "DELETE FROM django_migrations" in sql]
        old_app_deletes = [(s, p) for s, p in mig_deletes if p and p == [OLD_APP]]
        self.assertEqual(len(old_app_deletes), 1)

    def test_fakes_0002_initial(self):
        """Should INSERT a fake record for 0002_initial only (Django records 0001 automatically)."""
        insert_stmts = [sql for sql, _ in self.cursor.executed if "INSERT INTO django_migrations" in sql]
        self.assertEqual(len(insert_stmts), 1)
        self.assertIn("0002_initial", insert_stmts[0])
        self.assertNotIn("0001_rename_from_fabric_partitions", insert_stmts[0])

    def test_does_not_rename_tables(self):
        alter_stmts = [sql for sql, _ in self.cursor.executed if "ALTER TABLE" in sql and "RENAME TO" in sql]
        self.assertEqual(len(alter_stmts), 0)


class RenameAppPureUpgradeTestCase(TestCase):
    """Scenario 4: Only old app exists, no new tables (pure dev upgrade).

    Should rename tables, content types, FK columns, and fix migration records.
    """

    def setUp(self):
        # _new_tables_exist -> False, _old_app_exists -> True
        self.cursor = MockCursor(fetchone_results=[None, (1,)])
        self.schema_editor = MagicMock()
        self.schema_editor.connection.cursor.return_value = self.cursor
        rename_app(apps=None, schema_editor=self.schema_editor)

    def test_updates_content_type_app_label(self):
        ct_updates = [
            (sql, params) for sql, params in self.cursor.executed if "UPDATE django_content_type SET app_label" in sql
        ]
        self.assertEqual(len(ct_updates), 1)
        _, params = ct_updates[0]
        self.assertEqual(params, [NEW_APP, OLD_APP])

    def test_renames_content_type_models(self):
        model_updates = [sql for sql, _ in self.cursor.executed if "UPDATE django_content_type SET model" in sql]
        self.assertEqual(len(model_updates), len(CONTENT_TYPE_MODEL_RENAMES))

    def test_renames_all_tables(self):
        alter_stmts = [sql for sql, _ in self.cursor.executed if "ALTER TABLE" in sql and "RENAME TO" in sql]
        self.assertEqual(len(alter_stmts), len(TABLE_RENAMES))
        for (old_name, new_name), sql in zip(TABLE_RENAMES, alter_stmts):
            self.assertIn(old_name, sql)
            self.assertIn(new_name, sql)

    def test_renames_fk_columns(self):
        col_stmts = [sql for sql, _ in self.cursor.executed if "RENAME COLUMN" in sql]
        self.assertEqual(len(col_stmts), len(FK_COLUMN_RENAMES))

    def test_fakes_0002_initial(self):
        """Should INSERT a fake record for 0002_initial only (Django records 0001 automatically)."""
        insert_stmts = [(sql, params) for sql, params in self.cursor.executed if "INSERT INTO django_migrations" in sql]
        self.assertEqual(len(insert_stmts), 1)
        sql, _ = insert_stmts[0]
        self.assertIn("0002_initial", sql)
        self.assertNotIn("0001_rename_from_fabric_partitions", sql)

    def test_cleans_migration_records_for_both_apps(self):
        """Should DELETE old+new app records, then _fake_new_migration_chain DELETEs new again."""
        delete_stmts = [(sql, params) for sql, params in self.cursor.executed if "DELETE FROM django_migrations" in sql]
        self.assertEqual(len(delete_stmts), 2)
        _, first_params = delete_stmts[0]
        self.assertIn(OLD_APP, first_params)
        self.assertIn(NEW_APP, first_params)
        _, second_params = delete_stmts[1]
        self.assertEqual(second_params, [NEW_APP])

    def test_does_not_drop_tables(self):
        drop_stmts = [sql for sql, _ in self.cursor.executed if "DROP TABLE" in sql]
        self.assertEqual(len(drop_stmts), 0)


class RenameConstantsTestCase(TestCase):
    """Test that the rename constants are correctly defined."""

    def test_table_renames_count(self):
        self.assertEqual(len(TABLE_RENAMES), 7)

    def test_old_tables_count(self):
        self.assertEqual(len(OLD_TABLES), 7)

    def test_all_old_tables_prefixed_correctly(self):
        for old_name, _ in TABLE_RENAMES:
            self.assertTrue(old_name.startswith(f"{OLD_APP}_"), f"{old_name} missing old prefix")

    def test_all_new_tables_prefixed_correctly(self):
        for _, new_name in TABLE_RENAMES:
            self.assertTrue(new_name.startswith(f"{NEW_APP}_"), f"{new_name} missing new prefix")

    def test_content_type_renames_include_both_renamed_models(self):
        old_models = {old for old, _ in CONTENT_TYPE_MODEL_RENAMES}
        self.assertIn("fabricpartition", old_models)
        self.assertIn("partitionmember", old_models)

    def test_fk_column_renames_cover_all_partition_references(self):
        tables_with_fk_rename = {table for table, _, _ in FK_COLUMN_RENAMES}
        self.assertIn(f"{NEW_APP}_infinibandpkey", tables_with_fk_rename)
        self.assertIn(f"{NEW_APP}_vxlan", tables_with_fk_rename)
        self.assertIn(f"{NEW_APP}_overlayassignment", tables_with_fk_rename)
        self.assertIn(f"{NEW_APP}_overlay_vrfs", tables_with_fk_rename)
        self.assertIn(f"{NEW_APP}_overlay_vlans", tables_with_fk_rename)
        self.assertIn(f"{NEW_APP}_overlay_route_targets", tables_with_fk_rename)
