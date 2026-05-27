# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
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
