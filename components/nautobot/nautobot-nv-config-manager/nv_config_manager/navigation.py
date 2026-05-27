#  SPDX-FileCopyrightText: Copyright (c) "2025" NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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
"""Navigation."""

from nautobot.core.apps import (
    NavMenuAddButton,
    NavMenuGroup,
    NavMenuItem,
    NavMenuTab,
)

items_overview = [
    NavMenuItem(
        link="plugins:nv_config_manager:configmanagerdevicestatus_list",
        name="Config Manager Devices",
        permissions=["nv_config_manager.view_configmanagerdevicestatus"],
        buttons=[
            NavMenuAddButton(
                link="plugins:nv_config_manager:configmanagerdevicestatus_add",
                permissions=["nv_config_manager.add_configmanagerdevicestatus"],
            ),
        ],
    ),
]

# NavMenuTab.name MUST stay "NVIDIA" -- nautobot-app-nvdatamodels registers
# the same tab and Nautobot merges by exact name match.
menu_items = (
    NavMenuTab(
        name="NVIDIA",
        groups=(
            NavMenuGroup(
                name="Config Manager",
                weight=100,
                items=tuple(items_overview),
            ),
        ),
    ),
)
