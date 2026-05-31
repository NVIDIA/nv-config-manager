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
"""Tests for AIR simulation cloud-init generation."""

from __future__ import annotations

from pathlib import Path

from nv_config_manager_installer.air_sim.cloud_init import generate_server_cloud_init

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_generated_minimal_server_cloud_init_matches_golden_output() -> None:
    user_data = generate_server_cloud_init(
        internal_mac="44:38:39:00:00:01",
        internal_ip="10.100.1.2/25",
        site_name="SPO01",
        oob_gateway="10.100.1.1",
    )

    assert user_data == (FIXTURES_DIR / "minimal_server_cloud_init.yaml").read_text()
