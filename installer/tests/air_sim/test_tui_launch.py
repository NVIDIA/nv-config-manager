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
from textual.widgets import Tabs

from nv_config_manager_installer.air_sim.constants import NVCM_BOX_PASSWORD
from nv_config_manager_installer.air_sim.sim_config import SimConfig
from nv_config_manager_installer.tui.air_sim.app import NVCMAirSimApp
from nv_config_manager_installer.tui.air_sim.screens.launch import (
    LaunchScreen,
    _FollowLog,
    _LogViewerWidget,
)

PUBLIC_AIR_WORKER = "eb515e50.workers.ngc.air.nvidia.com"


class ClipboardAirSimApp(NVCMAirSimApp):
    """Test app that records clipboard writes."""

    copied_text: str | None = None

    def copy_to_clipboard(self, text: str) -> None:
        self.copied_text = text


@pytest.mark.asyncio
async def test_ssh_copy_button_and_command_bar_copy_command() -> None:
    app = ClipboardAirSimApp(config=SimConfig(ngc_api_key="nvapi-test"))
    command = f"sshpass -p {NVCM_BOX_PASSWORD} ssh -p 17117 nvcm@example.air"

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
        launch._show_proxy_panel(PUBLIC_AIR_WORKER, 17117)
        await pilot.pause(0.1)

        await pilot.click("#copy-ssh-unix")
        await pilot.pause(0.1)
        assert app.copied_text is not None
        assert f"sshpass -p {NVCM_BOX_PASSWORD}" in app.copied_text
        assert PUBLIC_AIR_WORKER in app.copied_text

        app.copied_text = None
        await pilot.click("#cmd-ssh-unix")
        await pilot.pause(0.1)
        assert app.copied_text is not None
        assert f"sshpass -p {NVCM_BOX_PASSWORD}" in app.copied_text
        assert PUBLIC_AIR_WORKER in app.copied_text


@pytest.mark.asyncio
async def test_log_tabs_keep_independent_log_widgets() -> None:
    app = ClipboardAirSimApp(config=SimConfig(ngc_api_key="nvapi-test"))

    async with app.run_test(size=(180, 70)) as pilot:
        app.switch_section("launch")
        await pilot.pause(0.1)

        launch = app.query_one("#screen-launch", LaunchScreen)
        viewer = launch.query_one("#log-viewer", _LogViewerWidget)
        viewer.append_line("deploy line 1", "deploy")
        viewer.append_line("deploy line 2", "deploy")
        viewer.add_tab("dhcp", "DHCP")
        viewer.append_line("dhcp line 1", "dhcp")
        await pilot.pause(0.1)

        await pilot.click("#log-tab-dhcp")
        await pilot.pause(0.1)

        deploy_log = viewer._logs["deploy"]
        dhcp_log = viewer._logs["dhcp"]
        assert deploy_log is not dhcp_log
        assert deploy_log.display is False
        assert dhcp_log.display is True
        assert dhcp_log.line_count == 1

        await pilot.click("#log-tab-deploy")
        await pilot.pause(0.1)

        assert deploy_log.display is True
        assert dhcp_log.display is False
        assert deploy_log.line_count == 2


@pytest.mark.asyncio
async def test_deploy_log_scrollback_pauses_following() -> None:
    app = ClipboardAirSimApp(config=SimConfig(ngc_api_key="nvapi-test"))

    async with app.run_test(size=(180, 70)) as pilot:
        app.switch_section("launch")
        await pilot.pause(0.1)

        launch = app.query_one("#screen-launch", LaunchScreen)
        viewer = launch.query_one("#log-viewer", _LogViewerWidget)
        for i in range(120):
            viewer.append_line(f"deploy line {i:03d} " + ("x" * 120), "deploy")
        await pilot.pause(0.2)

        log = viewer.query_one("#log-output", _FollowLog)
        assert log.max_scroll_y > 0
        log.scroll_end(animate=False, immediate=True, x_axis=False)
        await pilot.pause(0.1)

        bottom = log.scroll_y
        log.scroll_to(y=max(0, bottom - 8), animate=False, force=True, immediate=True)
        await pilot.pause(0.1)
        scrolled_y = log.scroll_y
        assert scrolled_y < bottom
        assert log.following is False

        viewer.append_line("deploy line after manual scroll", "deploy")
        await pilot.pause(0.1)

        assert log.scroll_y == scrolled_y
        assert log.following is False


@pytest.mark.asyncio
async def test_log_flood_does_not_block_tabs_or_save_key(tmp_path) -> None:
    app = ClipboardAirSimApp(
        config=SimConfig(ngc_api_key="nvapi-test"),
        config_path=tmp_path / "air-sim.yaml",
    )

    async with app.run_test(size=(180, 70)) as pilot:
        app.switch_section("launch")
        await pilot.pause(0.1)

        launch = app.query_one("#screen-launch", LaunchScreen)
        viewer = launch.query_one("#log-viewer", _LogViewerWidget)
        viewer.add_tab("dhcp", "DHCP")
        viewer.add_tab("ztp", "ZTP")
        ssh_command = f"sshpass -p {NVCM_BOX_PASSWORD} ssh -p 17117 nvcm@{PUBLIC_AIR_WORKER}"
        launch._show_ssh_command(ssh_command)
        launch._show_proxy_panel(PUBLIC_AIR_WORKER, 17117)
        await pilot.pause(0.1)

        await pilot.click("#log-tab-ztp")
        await pilot.pause(0.1)
        assert viewer._active_tab == "ztp"

        for i in range(2000):
            launch.enqueue_log_line(f"ztp line {i:04d}", "ztp")

        await pilot.click("#log-tab-access")
        await pilot.click("#copy-ssh")
        await pilot.press("f2")
        await pilot.pause(0.2)

        assert viewer._active_tab == "access"
        assert app.copied_text == ssh_command
        assert app.config_path.exists()
        assert app.query_one("#log-tabs", Tabs).active == "log-tab-access"
