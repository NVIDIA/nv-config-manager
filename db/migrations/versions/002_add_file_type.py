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
"""Add file_type column

Revision ID: 002
Revises: 001
Create Date: 2025-10-10 12:00:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Create the enum type
    file_type_enum = sa.Enum("intended", "backup", name="filetype")
    file_type_enum.create(op.get_bind())

    # Add the file_type column with default value 'intended'
    op.add_column(
        "config_files",
        sa.Column("file_type", file_type_enum, nullable=False, server_default="intended"),
    )

    # Drop old unique constraint
    op.drop_constraint("uq_device_filename_version", "config_files", type_="unique")

    # Create new unique constraint with file_type
    op.create_unique_constraint(
        "uq_device_filename_filetype_version",
        "config_files",
        ["device_uuid", "filename", "file_type", "version"],
    )

    # Create new index for device_uuid, filename, file_type
    op.create_index(
        "idx_config_files_device_filename_filetype",
        "config_files",
        ["device_uuid", "filename", "file_type"],
        unique=False,
    )

    # Create index for file_type
    op.create_index("idx_config_files_file_type", "config_files", ["file_type"], unique=False)


def downgrade() -> None:
    # Drop the new indexes
    op.drop_index("idx_config_files_file_type", table_name="config_files")
    op.drop_index("idx_config_files_device_filename_filetype", table_name="config_files")

    # Drop new unique constraint
    op.drop_constraint("uq_device_filename_filetype_version", "config_files", type_="unique")

    # Recreate old unique constraint
    op.create_unique_constraint(
        "uq_device_filename_version", "config_files", ["device_uuid", "filename", "version"]
    )

    # Drop the file_type column
    op.drop_column("config_files", "file_type")

    # Drop the enum type
    sa.Enum(name="filetype").drop(op.get_bind())
