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
"""Pytest fixtures to use across component tests."""

from __future__ import annotations

import configparser
import json
from pathlib import Path

import pytest

RESOURCES_DIR = Path(__file__).resolve().parents[1] / "resources"
NAUTOBOT_MOCK_DIR = RESOURCES_DIR / "nautobot"


def _load_nautobot_fixture(name: str) -> dict:
    with (NAUTOBOT_MOCK_DIR / f"{name}.json").open(encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def amend_config_read(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch ConfigParser.read with deterministic test secret content."""

    def mock_read(self: configparser.ConfigParser, filenames, *args, **kwargs) -> list[str]:
        ini = """
[region.amer]
root_password_r1: DUMMY
hash_salt: H0QFj2rx
hash_salt_t7: 0

[site.test-site]
bgp_password_r1: DUMMY
root_password_r1: DUMMY
hash_salt: H0QFj2rx
hash_salt_t7: 0
"""
        self.read_string(ini)
        return []

    monkeypatch.setattr(configparser.ConfigParser, "read", mock_read)


@pytest.fixture
def public_tor_data() -> dict:
    """Load representative OOB leaf data."""
    return _load_nautobot_fixture("a04-u44-p01-tor-01")


@pytest.fixture
def public_leaf_data() -> dict:
    """Load representative in-band leaf data."""
    return _load_nautobot_fixture("a08-u32-p01-cleaf-01")


@pytest.fixture
def public_border_leaf_data() -> dict:
    """Load representative border leaf data."""
    return _load_nautobot_fixture("a09-u28-p01-bleaf-01")


@pytest.fixture
def public_spine_data() -> dict:
    """Load representative converged spine data."""
    return _load_nautobot_fixture("a09-u36-p01-spine-01")


@pytest.fixture
def public_location_data() -> dict:
    """Load representative site data."""
    return _load_nautobot_fixture("TEST-SITE")
