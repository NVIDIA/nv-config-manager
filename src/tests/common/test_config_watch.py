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
"""Tests for restarting a service when its configuration file changes."""

import os
import signal
import threading
import time
from collections.abc import Callable
from pathlib import Path
from unittest.mock import patch

import pytest

from nv_config_manager.common import config_watch
from nv_config_manager.common.config_watch import _watch, changed_keys
from nv_config_manager.common.ini import file_digest

ORIGINAL = """[nats]
server = nats://nats:4222
queue = nv-config-manager
password = original
"""

ROTATED = """[nats]
server = nats://nats:4222
queue = nv-config-manager
password = rotated
"""

RENAMED_STREAM = """[nats]
server = nats://nats:4222
queue = nv-config-manager
password = original
config_manager_stream = renamed
"""

POLL_INTERVAL = 0.01


@pytest.fixture
def ini(tmp_path: Path) -> Path:
    """Write a starting INI file and return its path."""
    path = tmp_path / "nv-config-manager.ini"
    path.write_text(ORIGINAL)
    return path


def _watch_while(
    path: Path,
    change: Callable[[], None] | None = None,
    max_jitter: float = 0.0,
) -> list[tuple[int, int]]:
    """Start a watch, apply a change to the file, and report any signal sent.

    The watch reads its baseline as it starts, the way a service does, so the
    change has to land after it is already running.

    Args:
        path: INI file being watched
        change: Applied once the watch has taken its baseline
        max_jitter: Upper bound on the delay before signalling

    Returns:
        The (pid, signal) pairs the watch sent
    """
    signals: list[tuple[int, int]] = []
    stop = threading.Event()
    baseline_taken = threading.Event()
    read_file = config_watch._read

    def record_baseline(target: str) -> str:
        """Report that the watch has finished reading the file it starts from."""
        contents = read_file(target)
        baseline_taken.set()
        return contents

    with (
        patch(
            "nv_config_manager.common.config_watch.os.kill",
            side_effect=lambda pid, sig: signals.append((pid, sig)),
        ),
        patch("nv_config_manager.common.config_watch._read", side_effect=record_baseline),
    ):
        watcher = threading.Thread(
            target=_watch,
            args=(str(path), POLL_INTERVAL, max_jitter, stop),
            daemon=True,
        )
        watcher.start()

        # Changing the file before the watch has read it would make the new
        # contents its baseline, and the change would go unnoticed.
        assert baseline_taken.wait(timeout=5.0)
        if change is not None:
            change()

        # A watch with nothing to act on never returns, so give it a bounded
        # chance to react and then take it down.
        deadline = time.monotonic() + 1.0
        while not signals and time.monotonic() < deadline:
            time.sleep(POLL_INTERVAL)
        stop.set()
        watcher.join(timeout=5.0)

    return signals


def test_a_rotated_password_stops_the_process(ini: Path) -> None:
    """A new credential only reaches an open connection by way of a restart."""
    signals = _watch_while(ini, change=lambda: ini.write_text(ROTATED))

    assert signals == [(os.getpid(), signal.SIGTERM)]


def test_a_renamed_stream_stops_the_process(ini: Path) -> None:
    """Consumers bind their stream at startup, so a rename needs a restart too."""
    signals = _watch_while(ini, change=lambda: ini.write_text(RENAMED_STREAM))

    assert signals == [(os.getpid(), signal.SIGTERM)]


def test_an_unchanged_file_leaves_the_process_alone(ini: Path) -> None:
    """Nothing changed, so nothing should be disturbed."""
    assert _watch_while(ini) == []


def test_an_identical_rewrite_is_not_a_change(ini: Path, tmp_path: Path) -> None:
    """Kubernetes and Vault Agent rewrite these files on their own schedules.

    The replacement arrives with a new inode and new timestamps, so watching
    file metadata would restart a service that has nothing new to read.
    """

    def rewrite_with_the_same_contents() -> None:
        replacement = tmp_path / "replacement.ini"
        replacement.write_text(ORIGINAL)
        os.replace(replacement, ini)

    before = file_digest(str(ini))
    signals = _watch_while(ini, change=rewrite_with_the_same_contents)

    assert file_digest(str(ini)) == before
    assert signals == []


def test_an_unreadable_file_is_not_a_change(ini: Path) -> None:
    """Losing sight of the file is a mount problem, not a reason to restart."""
    assert _watch_while(ini, change=ini.unlink) == []


def test_the_restart_is_spread_across_replicas(ini: Path) -> None:
    """Every replica sees the change at once, so they must not all exit at once."""
    with patch("nv_config_manager.common.config_watch.random.uniform", return_value=0.0) as uniform:
        _watch_while(ini, change=lambda: ini.write_text(ROTATED), max_jitter=20.0)

    uniform.assert_called_once_with(0, 20.0)


def test_changed_keys_names_the_settings_that_moved() -> None:
    """An operator needs to know why a service restarted."""
    assert changed_keys(ORIGINAL, RENAMED_STREAM) == ["nats.config_manager_stream"]
    assert changed_keys(ORIGINAL, ROTATED) == ["nats.password"]
    assert changed_keys(ORIGINAL, ORIGINAL) == []


def test_changed_keys_does_not_leak_the_values() -> None:
    """The file holds credentials, so only names may be logged."""
    reported = " ".join(changed_keys(ORIGINAL, ROTATED))

    assert "rotated" not in reported
    assert "original" not in reported
