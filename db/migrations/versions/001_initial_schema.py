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
"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-10-08 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Create config_files table
    op.create_table(
        "config_files",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("device_uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("content_hash", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), nullable=False),
        sa.Column("commit_message", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "device_uuid", "filename", "version", name="uq_device_filename_version"
        ),
    )
    op.create_index("idx_config_files_author", "config_files", ["author"], unique=False)
    op.create_index("idx_config_files_created_at", "config_files", ["created_at"], unique=False)
    op.create_index(
        "idx_config_files_device_filename",
        "config_files",
        ["device_uuid", "filename"],
        unique=False,
    )
    op.create_index("idx_config_files_device_uuid", "config_files", ["device_uuid"], unique=False)

    # Create devices table
    op.create_table(
        "devices",
        sa.Column("uuid", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("site", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("uuid"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("idx_devices_site", "devices", ["site"], unique=False)

    # Create config_audit_log table
    op.create_table(
        "config_audit_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("config_file_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("user_email", sa.Text(), nullable=True),
        sa.Column("ip_address", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_config_audit_log_config_file_id", "config_audit_log", ["config_file_id"], unique=False
    )
    op.create_index(
        "idx_config_audit_log_created_at", "config_audit_log", ["created_at"], unique=False
    )


def downgrade() -> None:
    op.drop_index("idx_config_audit_log_created_at", table_name="config_audit_log")
    op.drop_index("idx_config_audit_log_config_file_id", table_name="config_audit_log")
    op.drop_table("config_audit_log")

    op.drop_index("idx_devices_site", table_name="devices")
    op.drop_table("devices")

    op.drop_index("idx_config_files_device_uuid", table_name="config_files")
    op.drop_index("idx_config_files_device_filename", table_name="config_files")
    op.drop_index("idx_config_files_created_at", table_name="config_files")
    op.drop_index("idx_config_files_author", table_name="config_files")
    op.drop_table("config_files")
