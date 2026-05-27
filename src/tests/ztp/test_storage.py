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
"""Unit tests for storage factory."""

import pytest

from nv_config_manager.common.config import get_storage_client
from nv_config_manager.ztp.filestore import FileStoreClient
from nv_config_manager.ztp.s3 import S3Client


def test_get_storage_client_default_s3(monkeypatch):
    """Test that S3Client is returned by default."""
    monkeypatch.delenv("STORAGE_TYPE", raising=False)
    monkeypatch.delenv("FILE_STORE_PATH", raising=False)

    client = get_storage_client()
    assert isinstance(client, S3Client)


def test_get_storage_client_explicit_s3(monkeypatch):
    """Test that S3Client is returned when STORAGE_TYPE=s3."""
    monkeypatch.setenv("STORAGE_TYPE", "s3")
    monkeypatch.delenv("FILE_STORE_PATH", raising=False)

    client = get_storage_client()
    assert isinstance(client, S3Client)


def test_get_storage_client_file_storage_success(monkeypatch, tmp_path):
    """Test that FileStoreClient is returned when STORAGE_TYPE=file."""
    monkeypatch.setenv("STORAGE_TYPE", "file")
    monkeypatch.setenv("FILE_STORE_PATH", str(tmp_path))

    # Create a minimal manifest
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text('{"images": []}')

    client = get_storage_client()
    assert isinstance(client, FileStoreClient)


def test_get_storage_client_file_storage_missing_path(monkeypatch):
    """Test that ValueError is raised when STORAGE_TYPE=file but FILE_STORE_PATH not set."""
    monkeypatch.setenv("STORAGE_TYPE", "file")
    monkeypatch.delenv("FILE_STORE_PATH", raising=False)

    with pytest.raises(ValueError, match="STORAGE_TYPE is 'file' but FILE_STORE_PATH is not set"):
        get_storage_client()


def test_get_storage_client_case_insensitive(monkeypatch, tmp_path):
    """Test that STORAGE_TYPE is case insensitive."""
    monkeypatch.setenv("STORAGE_TYPE", "FILE")
    monkeypatch.setenv("FILE_STORE_PATH", str(tmp_path))

    # Create a minimal manifest
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text('{"images": []}')

    client = get_storage_client()
    assert isinstance(client, FileStoreClient)

    # Test S3 case insensitivity
    monkeypatch.setenv("STORAGE_TYPE", "S3")
    client = get_storage_client()
    assert isinstance(client, S3Client)
