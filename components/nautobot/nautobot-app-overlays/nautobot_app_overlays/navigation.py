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

"""Navigation menu items for Overlays app."""

from nautobot.apps.ui import NavMenuAddButton, NavMenuGroup, NavMenuItem, NavMenuTab

menu_items = (
    NavMenuTab(
        name="Multi-Tenancy",
        groups=(
            NavMenuGroup(
                name="Overlays",
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_app_overlays:vxlanoverlay_list",
                        name="VXLAN",
                        permissions=["nautobot_app_overlays.view_overlay"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_app_overlays:vxlanoverlay_add",
                                permissions=["nautobot_app_overlays.add_overlay"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_app_overlays:spectrumxoverlay_list",
                        name="Spectrum X",
                        permissions=["nautobot_app_overlays.view_overlay"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_app_overlays:spectrumxoverlay_add",
                                permissions=["nautobot_app_overlays.add_overlay"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_app_overlays:nvlinkpartitionoverlay_list",
                        name="NVLink Partition",
                        permissions=["nautobot_app_overlays.view_overlay"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_app_overlays:nvlinkpartitionoverlay_add",
                                permissions=["nautobot_app_overlays.add_overlay"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_app_overlays:ibmkeyoverlay_list",
                        name="IB MKey",
                        permissions=["nautobot_app_overlays.view_overlay"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_app_overlays:ibmkeyoverlay_add",
                                permissions=["nautobot_app_overlays.add_overlay"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_app_overlays:ibpkeyoverlay_list",
                        name="IB PKey",
                        permissions=["nautobot_app_overlays.view_overlay"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_app_overlays:ibpkeyoverlay_add",
                                permissions=["nautobot_app_overlays.add_overlay"],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="Fabric Records",
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_app_overlays:vxlan_list",
                        name="VXLANs",
                        permissions=["nautobot_app_overlays.view_vxlan"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_app_overlays:vxlan_add",
                                permissions=["nautobot_app_overlays.add_vxlan"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_app_overlays:infinibandpkey_list",
                        name="IB PKeys",
                        permissions=["nautobot_app_overlays.view_infinibandpkey"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_app_overlays:infinibandpkey_add",
                                permissions=["nautobot_app_overlays.add_infinibandpkey"],
                            ),
                        ),
                    ),
                    NavMenuItem(
                        link="plugins:nautobot_app_overlays:infinibandmkey_list",
                        name="IB MKeys",
                        permissions=["nautobot_app_overlays.view_infinibandmkey"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_app_overlays:infinibandmkey_add",
                                permissions=["nautobot_app_overlays.add_infinibandmkey"],
                            ),
                        ),
                    ),
                ),
            ),
            NavMenuGroup(
                name="Assignments",
                items=(
                    NavMenuItem(
                        link="plugins:nautobot_app_overlays:overlayassignment_list",
                        name="Overlay Assignments",
                        permissions=["nautobot_app_overlays.view_overlayassignment"],
                        buttons=(
                            NavMenuAddButton(
                                link="plugins:nautobot_app_overlays:overlayassignment_add",
                                permissions=["nautobot_app_overlays.add_overlayassignment"],
                            ),
                        ),
                    ),
                ),
            ),
        ),
    ),
)
