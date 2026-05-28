#  SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#  SPDX-License-Identifier: Apache-2.0
#
#  Licensed under the Apache License, Version 2.0 (the "License")
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""App declaration for nautobot_app_overlays."""

from importlib import metadata

from nautobot.apps import NautobotAppConfig

__version__ = metadata.version("nautobot-app-overlays")


class NautobotAppOverlaysConfig(NautobotAppConfig):
    """App configuration for the nautobot_app_overlays app."""

    name = "nautobot_app_overlays"
    verbose_name = "Overlays"
    version = __version__
    author = "Network Automation Team"
    author_email = "network-automation@nvidia.com"
    description = "A Nautobot app that provides data models and UI for network overlay segregation and multi-tenancy."
    base_url = "overlays"
    required_settings = []
    min_version = "2.0.0"
    max_version = "2.9999"
    default_settings = {}
    caching_config = {}
    docs_view_name = "plugins:nautobot_app_overlays:docs"

    def ready(self):
        """Import GraphQL types and register post_migrate signal handlers."""
        super().ready()

        from nautobot_app_overlays import (  # noqa: F401
            graphql,
            signals,
        )


config = NautobotAppOverlaysConfig  # pylint:disable=invalid-name
