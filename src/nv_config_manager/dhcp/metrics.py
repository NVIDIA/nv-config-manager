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
"""Prometheus metrics for the DHCP service."""

from prometheus_client import Counter, Histogram

DHCP_CONFIG_GENERATION_ERRORS = Counter(
    "nv_config_manager_dhcp_config_generation_errors_total",
    "Total DHCP configuration generation errors",
    ["error_type", "ip_version"],
)

DHCP_QUERY_ERRORS = Counter(
    "nv_config_manager_dhcp_query_errors_total",
    "Total DHCP Nautobot query/data validation errors",
    ["error_type"],
)

DHCP_CONFIG_GENERATION_DURATION = Histogram(
    "nv_config_manager_dhcp_config_generation_duration_seconds",
    "Time taken to generate DHCP configuration",
    ["ip_version"],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, float("inf")],
)

DHCP_CACHE_REFRESH_ERRORS = Counter(
    "nv_config_manager_dhcp_cache_refresh_errors_total",
    "Total DHCP cache refresh failures",
    ["ip_version"],
)
