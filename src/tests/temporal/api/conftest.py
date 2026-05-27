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
"""Temporal API test configuration."""

from __future__ import annotations

import pytest

from nv_config_manager.common.auth import AuthConfig


@pytest.fixture(autouse=True)
def disable_app_auth_for_temporal_api_unit_tests(mocker):
    """Keep Temporal API unit tests focused on workflow behavior."""
    mocker.patch(
        "nv_config_manager.common.auth._auth_config",
        AuthConfig(required=False, accept_request_headers=True),
    )
