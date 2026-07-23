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

from __future__ import annotations

import io
import tarfile
from pathlib import Path

import pytest

from nv_config_manager_installer.content import _extract_tarball


def test_extract_tarball_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive, "w:gz") as contents:
        info = tarfile.TarInfo("../outside")
        info.size = 0
        contents.addfile(info)

    with pytest.raises(ValueError, match="unsafe path"):
        _extract_tarball(archive, tmp_path / "staging")


def test_extract_tarball_rejects_absolute_paths(tmp_path: Path) -> None:
    archive = tmp_path / "absolute.tar.gz"
    with tarfile.open(archive, "w:gz") as contents:
        info = tarfile.TarInfo("/outside")
        info.size = 0
        contents.addfile(info)

    with pytest.raises(ValueError, match="unsafe path"):
        _extract_tarball(archive, tmp_path / "staging")


def test_extract_tarball_rejects_links(tmp_path: Path) -> None:
    archive = tmp_path / "link.tar.gz"
    with tarfile.open(archive, "w:gz") as contents:
        info = tarfile.TarInfo("link")
        info.type = tarfile.SYMTYPE
        info.linkname = "/tmp/outside"
        contents.addfile(info)

    with pytest.raises(ValueError, match="unsupported entry"):
        _extract_tarball(archive, tmp_path / "staging")


def test_extract_tarball_rejects_hardlinks(tmp_path: Path) -> None:
    archive = tmp_path / "hardlink.tar.gz"
    with tarfile.open(archive, "w:gz") as contents:
        info = tarfile.TarInfo("hardlink")
        info.type = tarfile.LNKTYPE
        info.linkname = "target"
        contents.addfile(info)

    with pytest.raises(ValueError, match="unsupported entry"):
        _extract_tarball(archive, tmp_path / "staging")


def test_extract_tarball_rejects_special_entries(tmp_path: Path) -> None:
    archive = tmp_path / "fifo.tar.gz"
    with tarfile.open(archive, "w:gz") as contents:
        info = tarfile.TarInfo("fifo")
        info.type = tarfile.FIFOTYPE
        contents.addfile(info)

    with pytest.raises(ValueError, match="unsupported entry"):
        _extract_tarball(archive, tmp_path / "staging")


def test_extract_tarball_extracts_valid_file_and_directory(tmp_path: Path) -> None:
    archive = tmp_path / "valid.tar.gz"
    file_contents = b"hello from archive\n"

    with tarfile.open(archive, "w:gz") as contents:
        directory = tarfile.TarInfo("plugin")
        directory.type = tarfile.DIRTYPE
        directory.mode = 0o755
        contents.addfile(directory)

        file_info = tarfile.TarInfo("plugin/job.py")
        file_info.mode = 0o644
        file_info.size = len(file_contents)
        contents.addfile(file_info, io.BytesIO(file_contents))

    staging = tmp_path / "staging"
    _extract_tarball(archive, staging)

    assert (staging / "plugin").is_dir()
    assert (staging / "plugin/job.py").read_bytes() == file_contents
