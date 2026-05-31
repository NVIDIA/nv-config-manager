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
from textual.widgets import Input

from nv_config_manager_installer.air_sim.constants import NVCM_BOX_PASSWORD
from nv_config_manager_installer.air_sim.sim_config import SimConfig
from nv_config_manager_installer.tui.air_sim.app import NVCMAirSimApp
from nv_config_manager_installer.tui.air_sim.screens.launch import (
    LaunchScreen,
    _ActivityWidget,
    _DeployStarted,
    _PodStatusWidget,
    _TuiCallback,
)
from nv_config_manager_installer.tui.widgets import LabeledSwitch

PUBLIC_AIR_WORKER = "eb515e50.workers.ngc.air.nvidia.com"


class ClipboardAirSimApp(NVCMAirSimApp):
    """Test app that records clipboard writes."""

    copied_text: str | None = None

    def copy_to_clipboard(self, text: str) -> None:
        self.copied_text = text


class CallbackRecorder:
    """Small callback target used to verify callback filtering behavior."""

    def __init__(self) -> None:
        self.entries: list[tuple[str, str]] = []
        self.messages: list[object] = []

    def post_message(self, message: object) -> None:
        self.messages.append(message)

    def enqueue_log_line(self, line: str, stream: str = "deploy") -> None:
        self.entries.append((line, stream))


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
async def test_activity_feed_keeps_selected_progress_events() -> None:
    app = ClipboardAirSimApp(config=SimConfig(ngc_api_key="nvapi-test"))

    async with app.run_test(size=(180, 70)) as pilot:
        app.switch_section("launch")
        await pilot.pause(0.1)

        launch = app.query_one("#screen-launch", LaunchScreen)
        viewer = launch.query_one("#activity-viewer", _ActivityWidget)
        viewer.append_lines(
            [
                ("Simulation: demo-id", "deploy"),
                ("DHCP4_LEASE_ALLOC [hwtype=1 44:38:39:00:00:02], cid=[no info]", "dhcp"),
                ('10.120.1.10:12345 - "GET /v1/device/abc/boot-script HTTP/1.1" 200', "ztp"),
            ]
        )
        await pilot.pause(0.1)

        activity_text = str(viewer.query_one("#activity-lines").render())
        assert "[DEPLOY] Simulation: demo-id" in activity_text
        assert "[DHCP] DHCP4_LEASE_ALLOC" in activity_text
        assert "[ZTP] 10.120.1.10" in activity_text


def test_tui_callback_streams_unfiltered_deploy_log_lines() -> None:
    recorder = CallbackRecorder()
    callback = _TuiCallback(recorder)  # type: ignore[arg-type]

    callback.on_log("ordinary docker build output with no activity keyword")

    assert recorder.entries == [("ordinary docker build output with no activity keyword", "deploy")]


@pytest.mark.asyncio
async def test_pod_summary_prioritizes_nautobot_progress() -> None:
    app = ClipboardAirSimApp(config=SimConfig(ngc_api_key="nvapi-test"))

    async with app.run_test(size=(180, 70)) as pilot:
        app.switch_section("launch")
        await pilot.pause(0.1)

        panel = app.query_one("#pod-status-panel", _PodStatusWidget)
        panel._update_table(
            [
                {
                    "name": "nv-config-manager-dhcp-6f86b9f5b7-lm2xq",
                    "ready": "4/4",
                    "status": "Running",
                    "restarts": "0",
                    "age": "4m",
                },
                {
                    "name": "nv-config-manager-nautobot-7c6c5b566-2kqq2",
                    "ready": "1/2",
                    "status": "Running",
                    "restarts": "0",
                    "age": "3m",
                },
                {
                    "name": "nv-config-manager-render-api-5858dcb947-n257z",
                    "ready": "0/1",
                    "status": "Init:0/1",
                    "restarts": "0",
                    "age": "1m",
                },
                {
                    "name": "cluster-nautobot-1",
                    "ready": "1/1",
                    "status": "Running",
                    "restarts": "0",
                    "age": "5m",
                },
            ]
        )

        summary_text = str(panel.query_one("#pod-summary").render())
        detail_text = str(panel.query_one("#pod-detail").render())

        assert summary_text == "Nautobot: 1/2 Running"
        assert "Other pods ready: 2/3" in detail_text
        assert "nv-config-manager-render-api" in detail_text


@pytest.mark.asyncio
async def test_switch_provisioning_waiting_state_names_nautobot_dependency() -> None:
    app = ClipboardAirSimApp(config=SimConfig(ngc_api_key="nvapi-test"))

    async with app.run_test(size=(180, 70)) as pilot:
        app.switch_section("launch")
        await pilot.pause(0.1)

        panel = app.query_one("#pod-status-panel", _PodStatusWidget)
        panel._update_prov(0, 0, [])

        assert (
            str(panel.query_one("#prov-count").render())
            == "Switches Provisioned: waiting for Nautobot"
        )


@pytest.mark.asyncio
async def test_activity_feed_is_bounded() -> None:
    app = ClipboardAirSimApp(config=SimConfig(ngc_api_key="nvapi-test"))

    async with app.run_test(size=(180, 70)) as pilot:
        app.switch_section("launch")
        await pilot.pause(0.1)

        launch = app.query_one("#screen-launch", LaunchScreen)
        viewer = launch.query_one("#activity-viewer", _ActivityWidget)
        for i in range(120):
            viewer.append_lines([(f"deploy milestone {i:03d}", "deploy")])
        await pilot.pause(0.1)

        assert len(viewer._lines) == 80
        assert viewer._lines[0].endswith("deploy milestone 040")
        assert viewer._lines[-1].endswith("deploy milestone 119")


@pytest.mark.asyncio
async def test_log_flood_does_not_block_copy_or_save_key(tmp_path) -> None:
    app = ClipboardAirSimApp(
        config=SimConfig(ngc_api_key="nvapi-test"),
        config_path=tmp_path / "air-sim.yaml",
    )

    async with app.run_test(size=(180, 70)) as pilot:
        app.switch_section("launch")
        await pilot.pause(0.1)

        launch = app.query_one("#screen-launch", LaunchScreen)
        ssh_command = f"sshpass -p {NVCM_BOX_PASSWORD} ssh -p 17117 nvcm@{PUBLIC_AIR_WORKER}"
        launch._show_ssh_command(ssh_command)
        launch._show_proxy_panel(PUBLIC_AIR_WORKER, 17117)
        await pilot.pause(0.1)

        for i in range(2000):
            launch.enqueue_log_line(f"ztp line {i:04d}", "ztp")

        await pilot.click("#copy-ssh")
        await pilot.press("f2")
        await pilot.pause(0.2)

        assert app.copied_text == ssh_command
        assert app.config_path.exists()


@pytest.mark.asyncio
async def test_deploy_started_does_not_start_service_log_polling() -> None:
    app = ClipboardAirSimApp(config=SimConfig(ngc_api_key="nvapi-test"))

    async with app.run_test(size=(180, 70)) as pilot:
        app.switch_section("launch")
        await pilot.pause(0.1)

        launch = app.query_one("#screen-launch", LaunchScreen)
        launch.on__deploy_started(_DeployStarted(PUBLIC_AIR_WORKER, 17117))

        assert launch._host == PUBLIC_AIR_WORKER
        assert launch._port == 17117
        assert launch._service_polling is False


@pytest.mark.asyncio
async def test_launch_status_keeps_deploy_log_and_air_bar_on_completion(tmp_path) -> None:
    app = ClipboardAirSimApp(config=SimConfig(ngc_api_key="nvapi-test", use_internal=True))

    async with app.run_test(size=(180, 70)) as pilot:
        app.switch_section("launch")
        await pilot.pause(0.1)

        launch = app.query_one("#screen-launch", LaunchScreen)
        launch._deploy_log_path = tmp_path / "nvcm-deploy.log"
        launch.set_simulation_id("7dfde74b-ce46-4a29-97dc-58294ee39390")
        launch._set_status(launch._status_text("[bold green][*] Bringup complete![/bold green]"))
        await pilot.pause(0.1)

        status_text = str(launch.query_one("#launch-status").render())
        air_url = (
            "https://ngc.air-inside.nvidia.com/simulations/7dfde74b-ce46-4a29-97dc-58294ee39390"
        )
        assert str(tmp_path / "nvcm-deploy.log") in status_text
        assert air_url not in status_text

        await pilot.click("#copy-air-link")
        await pilot.pause(0.1)
        assert app.copied_text == air_url


@pytest.mark.asyncio
async def test_options_page_saves_visible_fields_without_resetting_hidden_flags(tmp_path) -> None:
    config = SimConfig(
        ngc_api_key="nvapi-test",
        auto_configure=False,
        deploy=False,
        no_aggressive_dhcp=True,
        no_reset_before_dhcp=True,
        size="medium",
    )
    app = ClipboardAirSimApp(config=config, config_path=tmp_path / "air-sim.yaml")

    async with app.run_test(size=(180, 70)) as pilot:
        app.switch_section("options")
        await pilot.pause(0.1)

        options = app.query_one("#screen-options")
        options.query_one("#use-public-air", LabeledSwitch).value = False
        options.query_one("#config-manager-ref", Input).value = "feature/air-demo"
        await pilot.click("#size-large")
        await pilot.pause(0.1)

        app.collect_config()

    assert config.use_internal is True
    assert config.config_manager_ref == "feature/air-demo"
    assert config.auto_configure is False
    assert config.deploy is False
    assert config.no_aggressive_dhcp is True
    assert config.no_reset_before_dhcp is True
    assert config.size == "large"
