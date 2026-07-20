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
"""Helpers for detecting changes to mounted INI files."""

from __future__ import annotations

import os

type FileFingerprint = tuple[int, int, int, int, int]


def file_fingerprint(path: str | None) -> FileFingerprint | None:
    """Return metadata that changes for direct writes and atomic symlink swaps.

    Kubernetes updates Secret volumes by atomically changing the symlink target.
    Following the symlink and including the target inode detects that update even
    when the replacement has the same size and timestamps as the previous file.
    """
    if not path:
        return None

    try:
        stat_result = os.stat(path)
    except OSError:
        return None

    return (
        stat_result.st_dev,
        stat_result.st_ino,
        stat_result.st_size,
        stat_result.st_mtime_ns,
        stat_result.st_ctime_ns,
    )
