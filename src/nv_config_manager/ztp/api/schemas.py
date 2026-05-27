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
"""Shared Pydantic response models for ZTP API endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class ChecksumResponse(BaseModel):
    """Response containing a file checksum."""

    checksum: str


class FileInfo(BaseModel):
    """Metadata for a file in object storage."""

    file: str = Field(description="Filename")
    last_modified: datetime | float = Field(description="Last modification timestamp")
    size: int = Field(description="File size in bytes")


class ObjectInfo(BaseModel):
    """Metadata for an object in the storage backend."""

    key: str = Field(description="Object key/path")
    size: int = Field(description="Object size in bytes")
    last_modified: datetime | float = Field(description="Last modification timestamp")
    etag: str | None = Field(default=None, description="ETag hash")
    metadata: dict[str, str] | None = Field(default=None, description="Object metadata")
    tags: dict[str, str] | None = Field(default=None, description="Object tags")
