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

from unittest.mock import MagicMock

import pytest

from nv_config_manager.temporal.client.device import (
    AristaConnection,
    DiffChangedException,
    NetworkDeviceException,
)


def _arista_connection() -> AristaConnection:
    conn = AristaConnection.__new__(AristaConnection)
    conn._session_id = "sess-1"
    conn._host = "192.0.2.1"
    conn._abort = MagicMock()
    conn._load_candidate_config = MagicMock()
    conn._diff = MagicMock(return_value="new-diff")
    return conn


def test_commit_preserves_diff_changed_exception():
    """A mismatched approved diff raises DiffChangedException, not a wrapped failure."""
    conn = _arista_connection()
    conn._diff_eq = MagicMock(return_value=False)

    with pytest.raises(DiffChangedException, match="changed since approval"):
        conn.commit_candidate_config("config", "old-diff")

    conn._abort.assert_called_once()


def test_commit_wraps_other_failures_as_network_device_exception():
    """Unexpected commit errors stay wrapped as NetworkDeviceException."""
    conn = _arista_connection()
    conn._diff_eq = MagicMock(return_value=True)
    conn._node = MagicMock()
    conn._node.enable.side_effect = RuntimeError("eAPI down")

    with pytest.raises(NetworkDeviceException, match="Failed to commit session sess-1"):
        conn.commit_candidate_config("config", "new-diff", commit_confirm=False)
