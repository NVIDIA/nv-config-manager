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
"""Render test configuration - INI mocking handled by top-level conftest.py."""

import os
from typing import Any

import pytest

# Check if nv_config_manager_templates is available
try:
    import nv_config_manager_templates  # noqa: F401

    HAS_NV_CONFIG_MANAGER_TEMPLATES = True
except ImportError:
    HAS_NV_CONFIG_MANAGER_TEMPLATES = False


# List of test modules that require nv_config_manager_templates
REQUIRES_NV_CONFIG_MANAGER_TEMPLATES = [
    "test_render.py",
    "test_dispatch.py",
    "test_pull_consumer.py",
    "test_producer.py",
    "test_admin_v1.py",
    "test_main.py",
]


def pytest_ignore_collect(collection_path, config):
    """Ignore test modules that require nv_config_manager_templates when it's not installed."""
    if HAS_NV_CONFIG_MANAGER_TEMPLATES:
        return False

    # Get the filename from the path
    filename = os.path.basename(str(collection_path))
    if filename in REQUIRES_NV_CONFIG_MANAGER_TEMPLATES:
        return True
    return False


@pytest.fixture()
def base_message() -> dict[str, Any]:
    """Base message object to extend in tests."""
    return {
        "@timestamp": "2024-01-16T21:46:05Z",
        "request": {"addr": "10.126.195.140", "user": "testuser"},
        "response": {"host": "test-host-01"},
        "event": None,
        "model": None,
        "record": {"id": None, "name": None},
    }
