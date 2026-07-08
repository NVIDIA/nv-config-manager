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
"""Tests for nv_config_manager.common.log."""

import pytest

from nv_config_manager.common.log import escape_log_newlines


@pytest.mark.parametrize(
    ("separator", "escaped"),
    [
        ("\n", r"\n"),
        ("\r", r"\r"),
        ("\v", r"\v"),
        ("\f", r"\f"),
        ("\x1c", r"\x1c"),
        ("\x1d", r"\x1d"),
        ("\x1e", r"\x1e"),
        ("\x85", r"\x85"),
        ("\u2028", r"\u2028"),
        ("\u2029", r"\u2029"),
    ],
)
def test_escape_log_newlines_escapes_line_separators(separator: str, escaped: str) -> None:
    assert escape_log_newlines(f"before{separator}after") == f"before{escaped}after"


def test_escape_log_newlines_stringifies_objects() -> None:
    assert escape_log_newlines(ValueError("before\nafter")) == r"before\nafter"


def test_escape_log_newlines_escapes_terminal_escape_character() -> None:
    assert escape_log_newlines("before\x1b[31mafter") == r"before\x1b[31mafter"


def test_escape_log_newlines_preserves_text_without_separators() -> None:
    assert escape_log_newlines("unchanged") == "unchanged"
