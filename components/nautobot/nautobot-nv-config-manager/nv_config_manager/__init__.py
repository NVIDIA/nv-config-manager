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
"""App declaration for nv_config_manager."""

from importlib import metadata

from nautobot.extras.plugins import NautobotAppConfig

_DIST_NAME = "nautobot-nv-config-manager"

try:
    __version__ = metadata.version(_DIST_NAME)
    _DIST_METADATA = metadata.metadata(_DIST_NAME)
except metadata.PackageNotFoundError:
    __version__ = "0.0.0"
    _DIST_METADATA = {}


class NvConfigManagerConfig(NautobotAppConfig):
    """App configuration for nv_config_manager."""

    name: str = "nv_config_manager"
    verbose_name: str = "NVIDIA Config Manager"
    version: str = __version__
    author: str = _DIST_METADATA.get("Author", "NVIDIA Corporation")
    author_email: str = _DIST_METADATA.get("Author-email", "support@nvidia.com")
    description: str = _DIST_METADATA.get("Summary", "NVIDIA Config Manager Nautobot app.")
    base_url: str = "nv-config-manager"
    required_settings: list[str] = []
    min_version: str = "2.0.0"
    max_version: str = "2.9999"
    default_settings: dict[str, str | dict[str, str]] = {}
    caching_config: dict[str, str | dict[str, str]] = {}
    middleware: list[str] = []


config = NvConfigManagerConfig  # pylint: disable=invalid-name
