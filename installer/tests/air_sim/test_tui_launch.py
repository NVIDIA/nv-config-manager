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
"""Textual tests for the AIR simulation launch screen."""

from __future__ import annotations

import pytest

from nv_config_manager_installer.air_sim.sim_config import SimConfig
from nv_config_manager_installer.tui.air_sim.app import NVCMAirSimApp
from nv_config_manager_installer.tui.air_sim.screens.launch import LaunchScreen


class ClipboardAirSimApp(NVCMAirSimApp):
    """Test app that records clipboard writes."""

    copied_text: str | None = None

    def copy_to_clipboard(self, text: str) -> None:
        self.copied_text = text


@pytest.mark.asyncio
async def test_ssh_copy_button_and_command_bar_copy_command() -> None:
    app = ClipboardAirSimApp(config=SimConfig(ngc_api_key="nvapi-test"))
    command = "sshpass -p NVCMDemo1! ssh -p 17117 nvcm@example.air"

    async with app.run_test(size=(180, 70)) as pilot:
        app.switch_section("launch")
        await pilot.pause(0.1)

        launch = app.query_one("#screen-launch", LaunchScreen)
        launch._show_ssh_command(command)
        await pilot.pause(0.1)

        await pilot.click("#copy-ssh")
        await pilot.pause(0.1)
        assert app.copied_text == command

        app.copied_text = None
        await pilot.click("#ssh-cmd")
        await pilot.pause(0.1)
        assert app.copied_text == command


@pytest.mark.asyncio
async def test_access_panel_copy_button_and_panel_body_copy_command() -> None:
    app = ClipboardAirSimApp(config=SimConfig(ngc_api_key="nvapi-test"))

    async with app.run_test(size=(180, 70)) as pilot:
        app.switch_section("launch")
        await pilot.pause(0.1)

        launch = app.query_one("#screen-launch", LaunchScreen)
        launch._show_proxy_panel("ngc-worker55.air-inside.nvidia.com", 17117)
        await pilot.pause(0.1)

        await pilot.click("#copy-ssh-unix")
        await pilot.pause(0.1)
        assert app.copied_text is not None
        assert "sshpass -p NVCMDemo1!" in app.copied_text
        assert "ngc-worker55.air-inside.nvidia.com" in app.copied_text

        app.copied_text = None
        await pilot.click("#cmd-ssh-unix")
        await pilot.pause(0.1)
        assert app.copied_text is not None
        assert "sshpass -p NVCMDemo1!" in app.copied_text
        assert "ngc-worker55.air-inside.nvidia.com" in app.copied_text
