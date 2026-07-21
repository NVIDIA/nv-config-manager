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
"""ZTP test configuration - INI mocking handled by top-level conftest.py."""

import json
import os

import pytest

from nv_config_manager.ztp.api import clients, storage_clients

# Get the directory containing this conftest.py
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture(autouse=True)
def _reset_shared_ztp_clients():
    """Drop the process-wide ZTP backend clients between tests.

    The shared Nautobot client carries a cache, circuit-breaker, and concurrency
    limiter, and the shared storage/Config Store clients carry connection pools;
    resetting keeps those from leaking state across test cases.
    """
    clients.reset_nautobot_client()
    storage_clients.reset_storage_clients()
    yield
    clients.reset_nautobot_client()
    storage_clients.reset_storage_clients()


@pytest.fixture
def mock_device_data():
    with open(os.path.join(_THIS_DIR, "resources/device_data.json")) as f:
        return json.load(f)


@pytest.fixture
def mock_not_found_data():
    with open(os.path.join(_THIS_DIR, "resources/null.json")) as f:
        return json.load(f)


@pytest.fixture
def mock_no_render_data():
    with open(os.path.join(_THIS_DIR, "resources/device_data_no_render.json")) as f:
        return json.load(f)
