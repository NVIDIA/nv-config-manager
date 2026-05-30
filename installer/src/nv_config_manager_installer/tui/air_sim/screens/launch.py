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
"""Launch screen - step progress and log output for simulation bringup."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import IO

from textual import events, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.reactive import reactive
from textual.widgets import Button, DataTable, Label, RichLog, Static
from textual.worker import Worker, WorkerState

from nv_config_manager_installer.air_sim.constants import NVCM_BOX_PASSWORD, NVCM_BOX_USER
from nv_config_manager_installer.air_sim.orchestrator import (
    STEPS,
    OrchestratorCallback,
    SimOrchestrator,
    StepStatus,
)
from nv_config_manager_installer.air_sim.proxy import ProxyInfo
from nv_config_manager_installer.air_sim.sim_config import SimConfig
from nv_config_manager_installer.air_sim.sim_manager import AirSimulationManager

_STATUS_ICON = {
    StepStatus.PENDING: "[ ]",
    StepStatus.RUNNING: "[>]",
    StepStatus.SUCCESS: "[*]",
    StepStatus.FAILED: "[!]",
    StepStatus.SKIPPED: "[-]",
}

_COPY_ICON = "⧉"
_COPIED_ICON = "✓"


def _copy_button(
    button_id: str,
    tooltip: str,
    *,
    classes: str = "copy-icon-btn",
    variant: str = "default",
) -> Button:
    button = Button(_COPY_ICON, id=button_id, variant=variant, classes=classes)
    button.tooltip = tooltip
    return button


def _clean_dhcp_line(line: str) -> str:
    """Trim a kea-dhcp4 log line to start at the DHCP4 message identifier."""
    idx = line.find("DHCP4")
    return line[idx:] if idx >= 0 else line


def _clean_ztp_line(line: str) -> str:
    """Extract the msg/message field from a JSON-structured ZTP log line."""
    idx = line.find("{")
    if idx >= 0:
        try:
            data = json.loads(line[idx:])
            return str(data.get("msg") or data.get("message") or line)
        except json.JSONDecodeError:
            pass
    return line


# Rough typical durations shown as hints for pending/running steps.
_TYPICAL: dict[str, str] = {
    "parse-topology": "~5s",
    "create-sim": "~10s",
    "attach-cloud-init": "~5s",
    "start-sim": "4-6m",
    "create-ssh": "~15s",
    "wait-setup": "3-5m",
    "upload-files": "~5s",
    "run-deploy": "~20m",
    "post-deploy": "~1m",
}


def _fmt_duration(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


# ── Messages ──────────────────────────────────────────────────────────────────


class _StepUpdated(Message):
    def __init__(self, step_id: str, status: StepStatus, message: str) -> None:
        super().__init__()
        self.step_id = step_id
        self.status = status
        self.message = message


class _LogLine(Message):
    def __init__(self, line: str, stream: str = "deploy") -> None:
        super().__init__()
        self.line = line
        self.stream = stream


class _SshReady(Message):
    def __init__(self, host: str, port: int) -> None:
        super().__init__()
        self.host = host
        self.port = port


class _DeployStarted(Message):
    def __init__(self, host: str, port: int) -> None:
        super().__init__()
        self.host = host
        self.port = port


class _BringupComplete(Message):
    def __init__(self, success: bool, host: str, port: int) -> None:
        super().__init__()
        self.success = success
        self.host = host
        self.port = port


# ── Callback bridge ───────────────────────────────────────────────────────────


class _TuiCallback(OrchestratorCallback):
    def __init__(self, screen: LaunchScreen, log_file: IO[str] | None = None) -> None:
        self._screen = screen
        self._log_file = log_file

    def on_step(self, step_id: str, status: StepStatus, message: str = "") -> None:
        self._screen.post_message(_StepUpdated(step_id, status, message))

    def on_log(self, line: str) -> None:
        stream = "deploy"
        if line.startswith("[DHCP]"):
            stream = "dhcp"
        elif line.startswith("[ZTP]"):
            stream = "ztp"
        self._screen.post_message(_LogLine(line, stream))
        if self._log_file:
            self._log_file.write(line + "\n")
            self._log_file.flush()

    def on_ssh_ready(self, host: str, port: int) -> None:
        self._screen.post_message(_SshReady(host, port))

    def on_deploy_started(self, host: str, port: int) -> None:
        self._screen.post_message(_DeployStarted(host, port))

    def on_complete(self, success: bool, host: str = "", port: int = 0) -> None:
        self._screen.post_message(_BringupComplete(success, host, port))


# ── Step list widget ──────────────────────────────────────────────────────────


class _StepListWidget(Vertical):
    """Left panel: deployment steps with live status icons and elapsed timing."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._labels: dict[str, Static] = {}
        self._statuses: dict[str, StepStatus] = {}
        self._start_times: dict[str, float] = {}
        self._durations: dict[str, float] = {}
        self._running_step: str | None = None

    def compose(self) -> ComposeResult:
        yield Label("Steps", classes="section-title")
        yield Label("─" * 24, classes="section-divider")
        for step_id, _label in STEPS:
            w = Static(self._render_text(step_id, StepStatus.PENDING), id=f"step-{step_id}")
            self._labels[step_id] = w
            self._statuses[step_id] = StepStatus.PENDING
            yield w

    def on_mount(self) -> None:
        self.set_interval(1.0, self._tick)

    def _tick(self) -> None:
        if self._running_step:
            self._refresh(self._running_step)

    def update_step(self, step_id: str, status: StepStatus) -> None:
        self._statuses[step_id] = status
        if status == StepStatus.RUNNING:
            self._start_times[step_id] = time.monotonic()
            self._running_step = step_id
        else:
            if step_id in self._start_times and step_id not in self._durations:
                self._durations[step_id] = time.monotonic() - self._start_times[step_id]
            if self._running_step == step_id:
                self._running_step = None
        self._refresh(step_id)

    def _refresh(self, step_id: str) -> None:
        widget = self._labels.get(step_id)
        if widget:
            status = self._statuses.get(step_id, StepStatus.PENDING)
            widget.update(self._render_text(step_id, status))

    def _render_text(self, step_id: str, status: StepStatus) -> str:
        label = dict(STEPS).get(step_id, step_id)
        icon = _STATUS_ICON[status]

        timing = ""
        if status == StepStatus.RUNNING and step_id in self._start_times:
            elapsed = time.monotonic() - self._start_times[step_id]
            timing = f"  {_fmt_duration(elapsed)}"
        elif step_id in self._durations:
            timing = f"  {_fmt_duration(self._durations[step_id])}"

        hint = ""
        if status in (StepStatus.PENDING, StepStatus.RUNNING) and step_id in _TYPICAL:
            hint = f"  [dim](~{_TYPICAL[step_id]})[/dim]"

        return f"{icon}  {label}{timing}{hint}"


# ── Log widget with scroll-to-follow tracking ─────────────────────────────────


class _FollowLog(RichLog):
    """Log widget that pauses auto-scroll when the user scrolls up."""

    following: reactive[bool] = reactive(True)

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._line_count = 0

    @property
    def line_count(self) -> int:
        return self._line_count

    def clear(self) -> None:
        self._line_count = 0
        super().clear()

    def write(self, content: object, *args: object, **kwargs: object) -> object:
        if isinstance(content, str):
            for line in content.splitlines():
                self.write_line(line)
            return self
        self._line_count += 1
        return super().write(content, *args, **kwargs)

    def write_line(self, line: str) -> None:
        self._line_count += 1
        super().write(line)

    def replace_lines(self, lines: list[str]) -> None:
        self._line_count = len(lines)
        super().clear()
        if lines:
            super().write("\n".join(lines))

    def watch_scroll_y(self, old: float, new: float) -> None:
        at_bottom = self.max_scroll_y <= 0 or new >= self.max_scroll_y - 1
        if at_bottom and not self.auto_scroll:
            self.auto_scroll = True
            self.following = True
        elif not at_bottom and new < old - 0.5 and self.auto_scroll:
            self.auto_scroll = False
            self.following = False


# ── Tabbed log viewer ─────────────────────────────────────────────────────────


class _LogViewerWidget(Vertical):
    """Log panel with phase-aware log tabs plus an access-details tab."""

    DEFAULT_CSS = """
    _LogViewerWidget { height: 1fr; }
    _LogViewerWidget #log-pane { height: 1fr; }
    _LogViewerWidget #access-pane {
        display: none;
        height: 1fr;
        overflow-y: auto;
    }
    _LogViewerWidget #log-output { height: 1fr; }
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._buffers: dict[str, list[str]] = {}
        self._active_tab = "deploy"

    def compose(self) -> ComposeResult:
        yield Label("Output", classes="section-title")
        with Horizontal(id="log-tabs"):
            yield Button("Deploy Log", id="log-tab-deploy", variant="primary")
            yield _copy_button("log-copy", "Copy active log")
            yield Button("↓ Follow", id="log-follow", variant="warning", classes="log-follow-btn")
        with Container(id="log-pane"):
            yield _FollowLog(id="log-output", highlight=False, auto_scroll=True)
        with VerticalScroll(id="access-pane"):
            yield Static("Access details will appear after deployment completes.")

    def on_mount(self) -> None:
        log = self.query_one("#log-output", _FollowLog)
        self.watch(log, "following", self._on_following_changed)
        self.query_one("#log-pane").display = True
        self.query_one("#access-pane").display = False

    def _on_following_changed(self, following: bool) -> None:
        self.query_one("#log-follow", Button).display = (
            self._active_tab != "access" and not following
        )

    def add_tab(self, tab_id: str, tab_label: str) -> None:
        """Add a new log tab if it doesn't already exist."""
        tab_bar = self.query_one("#log-tabs", Horizontal)
        btn_id = f"log-tab-{tab_id}"
        if tab_bar.query(f"#{btn_id}"):
            return
        copy_btn = tab_bar.query_one("#log-copy", Button)
        tab_bar.mount(Button(tab_label, id=btn_id, variant="default"), before=copy_btn)

    def _activate_tab(self, tab_id: str) -> None:
        self._active_tab = tab_id
        for btn in self.query("#log-tabs Button"):
            if isinstance(btn, Button) and btn.id not in {"log-copy", "log-follow"}:
                btn.variant = "primary" if btn.id == f"log-tab-{tab_id}" else "default"
        self.query_one("#log-pane").display = tab_id != "access"
        self.query_one("#access-pane").display = tab_id == "access"
        self.query_one("#log-copy", Button).display = tab_id != "access"
        follow = self.query_one("#log-output", _FollowLog).following
        self.query_one("#log-follow", Button).display = tab_id != "access" and not follow
        if tab_id == "access":
            return
        self._flush_buffer(self._buffers.get(tab_id, []))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid == "log-copy":
            self._copy_log()
            event.stop()
            return
        if bid == "log-follow":
            log = self.query_one("#log-output", _FollowLog)
            log.auto_scroll = True
            log.following = True
            log.scroll_end(animate=False)
            event.stop()
            return
        if not bid.startswith("log-tab-"):
            return
        tab_id = bid.removeprefix("log-tab-")
        self._activate_tab(tab_id)
        event.stop()

    def _flush_buffer(self, buf: list[str]) -> None:
        log = self.query_one("#log-output", _FollowLog)
        _MAX = 500
        lines = buf[-_MAX:]
        if len(buf) > _MAX:
            hidden = len(buf) - _MAX
            note = f"... {hidden} earlier lines not shown - use log clipboard for full content ..."
            lines = [note, *lines]
        log.replace_lines(lines)
        log.auto_scroll = True
        log.following = True
        log.scroll_end(animate=False)

    def append_line(self, line: str, stream: str = "deploy") -> None:
        """Buffer a line and write it to the Log widget if its tab is active."""
        if stream not in self._buffers:
            self._buffers[stream] = []
        self._buffers[stream].append(line)
        if stream == self._active_tab:
            self.query_one("#log-output", _FollowLog).write_line(line)

    def _copy_log(self) -> None:
        button = self.query_one("#log-copy", Button)
        text = "\n".join(self._buffers.get(self._active_tab, []))
        self.app.copy_to_clipboard(text)
        button.label = _COPIED_ICON
        self.app.notify("Copied to clipboard")
        self.set_timer(1.0, self._restore_copy_button)

    def _restore_copy_button(self) -> None:
        button = self.query_one("#log-copy", Button)
        if str(button.label) == _COPIED_ICON:
            button.label = _COPY_ICON

    def set_access_widget(self, widget: _ProxyAccessWidget) -> None:
        """Install access details and expose them as a first-class tab."""
        pane = self.query_one("#access-pane", VerticalScroll)
        pane.remove_children()
        pane.mount(widget)
        self.add_tab("access", "Access")
        self._activate_tab("access")


class _CopyCommandPanel(Container):
    """Copyable command panel with a large click target."""

    def __init__(
        self,
        title: str,
        command: str,
        button_id: str,
        tooltip: str,
        *,
        panel_id: str,
        command_id: str,
    ) -> None:
        super().__init__(id=panel_id, classes="copy-panel")
        self._title = title
        self._command = command
        self._button_id = button_id
        self._tooltip = tooltip
        self._command_id = command_id
        self.tooltip = tooltip

    def compose(self) -> ComposeResult:
        with Horizontal(classes="copy-panel-header"):
            yield Label(self._title, classes="copy-panel-title")
            yield _copy_button(self._button_id, self._tooltip)
        yield Static(self._command, id=self._command_id, classes="proxy-cmd")

    def on_click(self) -> None:
        self._copy_command()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == self._button_id:
            self._copy_command()
            event.stop()

    def _copy_command(self) -> None:
        self.app.copy_to_clipboard(self._command)
        button = self.query_one(f"#{self._button_id}", Button)
        button.label = _COPIED_ICON
        self.app.notify("Copied to clipboard")
        self.set_timer(1.0, lambda: self._restore_copy_button(button))

    def _restore_copy_button(self, button: Button) -> None:
        if str(button.label) == _COPIED_ICON:
            button.label = _COPY_ICON


class _SshCommandBar(Horizontal):
    """Copyable SSH command strip shown once the AIR worker is reachable."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._command = ""
        self.tooltip = "Copy SSH command"

    def compose(self) -> ComposeResult:
        yield Label("SSH", classes="ssh-badge")
        yield Static("", id="ssh-cmd", classes="ssh-cmd")
        yield _copy_button(
            "copy-ssh",
            "Copy SSH command",
            classes="copy-icon-btn ssh-copy-btn",
        )

    def set_command(self, command: str) -> None:
        self._command = command
        self.query_one("#ssh-cmd", Static).update(command)
        self.display = True

    def on_click(self, event: events.Click) -> None:
        self._copy_command()
        event.stop()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "copy-ssh":
            self._copy_command()
            event.stop()

    def _copy_command(self) -> None:
        if not self._command:
            return
        self.app.copy_to_clipboard(self._command)
        button = self.query_one("#copy-ssh", Button)
        button.label = _COPIED_ICON
        self.app.notify("Copied to clipboard")
        self.set_timer(1.0, lambda: self._restore_copy_button(button))

    def _restore_copy_button(self, button: Button) -> None:
        if str(button.label) == _COPIED_ICON:
            button.label = _COPY_ICON


# ── Proxy access widget ───────────────────────────────────────────────────────


class _ProxyAccessWidget(Container):
    """Shows per-platform SOCKS proxy commands and a Launch Browser button."""

    def __init__(self, proxy: ProxyInfo, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._proxy = proxy
        self._tunnel_proc: subprocess.Popen[bytes] | None = None

    def compose(self) -> ComposeResult:
        p = self._proxy

        yield Label("Proxy Access", classes="subsection-label")
        yield Label(
            "Start the SOCKS tunnel, then open the browser with the proxy.",
            classes="field-hint",
        )

        yield _CopyCommandPanel(
            "Linux / macOS - SOCKS tunnel",
            p.ssh_cmd_unix(),
            "copy-ssh-unix",
            "Copy Linux/macOS SOCKS tunnel",
            panel_id="panel-ssh-unix",
            command_id="cmd-ssh-unix",
        )
        yield _CopyCommandPanel(
            "Windows OpenSSH - SOCKS tunnel",
            p.ssh_cmd_windows(),
            "copy-ssh-win",
            "Copy Windows SOCKS tunnel",
            panel_id="panel-ssh-win",
            command_id="cmd-ssh-win",
        )
        yield _CopyCommandPanel(
            "Linux / macOS - browser",
            p.browser_cmd_unix(),
            "copy-browser-unix",
            "Copy Linux/macOS browser command",
            panel_id="panel-browser-unix",
            command_id="cmd-browser-unix",
        )
        yield _CopyCommandPanel(
            "Windows - browser",
            p.browser_cmd_windows(),
            "copy-browser-win",
            "Copy Windows browser command",
            panel_id="panel-browser-win",
            command_id="cmd-browser-win",
        )

        with Horizontal(id="proxy-controls"):
            yield Button("Launch Browser", id="btn-launch-browser", variant="primary")
        yield Static("", id="proxy-status")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        btn = event.button.id or ""
        if btn == "btn-launch-browser":
            self._launch_browser()
            event.stop()

    @work(thread=True)
    def _launch_browser(self) -> None:
        self.app.call_from_thread(
            self.query_one("#proxy-status", Static).update,
            "[yellow]Starting SOCKS tunnel...[/yellow]",
        )
        proc = self._proxy.start_tunnel()
        if proc is None:
            self.app.call_from_thread(
                self.query_one("#proxy-status", Static).update,
                "[red]Could not start tunnel — run the SSH command manually.[/red]",
            )
            return
        self._tunnel_proc = proc
        ok = self._proxy.launch_browser()
        if ok:
            self.app.call_from_thread(
                self.query_one("#proxy-status", Static).update,
                f"[green]Tunnel running (PID {proc.pid}). Browser launched.[/green]",
            )
        else:
            self.app.call_from_thread(
                self.query_one("#proxy-status", Static).update,
                f"[yellow]Tunnel running (PID {proc.pid}). "
                "No browser found — use the commands above.[/yellow]",
            )

    def on_unmount(self) -> None:
        if self._tunnel_proc and self._tunnel_proc.poll() is None:
            self._tunnel_proc.terminate()


# ── Pod status widget ─────────────────────────────────────────────────────────


class _PodStatusWidget(Vertical):
    """Polls `kubectl get pods -n nvcm` over SSH every 5 s and shows a DataTable."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._host = ""
        self._port = 0
        self._manager: object = None  # AirSimulationManager, set at start_polling
        self._stop = threading.Event()
        self._polling = False
        self._prov_polling = False

    def compose(self) -> ComposeResult:
        yield Label("Pod Status", classes="section-title")
        yield Label("─" * 30, classes="section-divider")
        yield Static("Provisioned: —", id="prov-count")
        yield Static("", id="prov-detail")
        yield Label("─" * 30, classes="section-divider")
        yield DataTable(id="pod-table", show_cursor=False)

    def on_mount(self) -> None:
        table = self.query_one("#pod-table", DataTable)
        table.add_columns("NAME", "READY", "STATUS", "RESTARTS", "AGE")

    def start_polling(self, host: str, port: int, manager: object) -> None:
        self._host = host
        self._port = port
        self._manager = manager
        self._stop.clear()
        self._polling = False
        self._prov_polling = False
        self.set_interval(5.0, self._tick)
        self._prov_tick()
        self.set_interval(30.0, self._prov_tick)

    def stop_polling(self) -> None:
        self._stop.set()

    def _tick(self) -> None:
        if self._stop.is_set() or self._manager is None or self._polling:
            return
        self._do_refresh()

    def _prov_tick(self) -> None:
        if self._stop.is_set() or self._manager is None or self._prov_polling:
            return
        self._do_prov_refresh()

    @work(thread=True, exclusive=False)
    def _do_refresh(self) -> None:
        self._polling = True
        try:
            assert isinstance(self._manager, AirSimulationManager)
            pods = self._manager.get_pod_status(self._host, self._port)
            self.app.call_from_thread(self._update_table, pods)
        finally:
            self._polling = False

    @work(thread=True, exclusive=False)
    def _do_prov_refresh(self) -> None:
        self._prov_polling = True
        try:
            assert isinstance(self._manager, AirSimulationManager)
            prov, total, remaining = self._manager.get_provisioning_status(self._host, self._port)
            self.app.call_from_thread(self._update_prov, prov, total, remaining)
        finally:
            self._prov_polling = False

    def _update_prov(self, prov: int, total: int, remaining: list[str]) -> None:
        try:
            self.query_one("#prov-count", Static).update(
                f"Provisioned: {prov}/{total}" if total else "Provisioned: —"
            )
            detail = ""
            if remaining and total and prov < total:
                detail = "Pending: " + ", ".join(remaining)
            self.query_one("#prov-detail", Static).update(detail)
        except Exception:
            pass

    def _update_table(self, pods: list[dict[str, str]]) -> None:
        try:
            table = self.query_one("#pod-table", DataTable)
        except Exception:
            return
        table.clear()
        for p in pods:
            name = p["name"]
            if len(name) > 42:
                name = name[:39] + "..."
            table.add_row(name, p["ready"], p["status"], p["restarts"], p["age"])


# ── Launch screen ─────────────────────────────────────────────────────────────


class LaunchScreen(Container):
    """Launch panel: summary, launch button, step list, and log stream."""

    def __init__(self, config: SimConfig, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._config = config
        self._bringup_running = False
        self._host = ""
        self._port = 0
        self._ssh_cmd_text = ""
        self._monitor_stop = threading.Event()
        self._deploy_log_path: Path | None = None

    def compose(self) -> ComposeResult:
        yield Label("Launch", classes="section-title")
        yield Label("─" * 40, classes="section-divider")

        with Horizontal(id="launch-controls"):
            yield Button("Launch Simulation", id="btn-launch", variant="success")
        yield Static("", id="launch-status")

        yield Label("─" * 40, classes="section-divider")

        yield _SshCommandBar(id="ssh-info-bar", classes="ssh-info-bar")

        with Vertical(id="launch-dashboard"):
            with Horizontal(id="dashboard-top"):
                with VerticalScroll(id="step-panel"):
                    yield _StepListWidget(id="step-list")
                yield _PodStatusWidget(id="pod-status-panel")
            yield _LogViewerWidget(id="log-viewer")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-launch" and not self._bringup_running:
            self._start_bringup()
            event.stop()

    def _set_status(self, markup: str) -> None:
        self.query_one("#launch-status", Static).update(markup)

    def _show_ssh_command(self, ssh_cmd: str) -> None:
        self._ssh_cmd_text = ssh_cmd
        self.query_one("#ssh-info-bar", _SshCommandBar).set_command(ssh_cmd)

    def _start_bringup(self) -> None:
        if self._config.run_mock_topology_job:
            if not self._config.mock_blueprint:
                self._set_status(
                    "[bold red][!] Mock blueprint required — set it on the Topology screen.[/bold red]"
                )
                return
            if not self._config.deployment_name:
                self._set_status(
                    "[bold red][!] Deployment name required — set it on the Topology screen.[/bold red]"
                )
                return
            if not self._config.mock_topology_path:
                self._set_status(
                    "[bold red][!] Mock topology path required — set it on the Topology screen.[/bold red]"
                )
                return
        elif not self._config.topology_path:
            self._set_status(
                "[bold red][!] No topology file — set one on the Topology screen.[/bold red]"
            )
            return
        if not self._config.ngc_api_key:
            self._set_status(
                "[bold red][!] NGC API key required — set it on the Options screen.[/bold red]"
            )
            return

        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self._deploy_log_path = Path(tempfile.gettempdir()) / f"nvcm-deploy-{stamp}.log"
        self._bringup_running = True
        self._monitor_stop.clear()
        self.query_one("#btn-launch", Button).disabled = True
        self._set_status(f"[yellow]Running...  log → {self._deploy_log_path}[/yellow]")
        self._run_orchestrator()

    @work(thread=True, exclusive=False)
    def _run_orchestrator(self) -> None:
        log_path = self._deploy_log_path
        with open(log_path, "w") if log_path else open(os.devnull, "w") as lf:
            cb = _TuiCallback(self, log_file=lf)
            orchestrator = SimOrchestrator(self._config, cb)
            orchestrator.run()

    @work(thread=True, exclusive=False)
    def _run_monitoring(self, host: str, port: int) -> None:
        manager = AirSimulationManager(
            ngc_api_key=self._config.ngc_api_key,
            use_internal=self._config.use_internal,
            org_id=self._config.org_id,
        )

        class _Fwd(logging.Handler):
            def __init__(self, screen: LaunchScreen) -> None:
                super().__init__()
                self._s = screen

            def emit(self, record: logging.LogRecord) -> None:
                line = self.format(record)
                stream = "deploy"
                if "[DHCP]" in line:
                    stream = "dhcp"
                    line = _clean_dhcp_line(line)
                elif "[ZTP]" in line:
                    stream = "ztp"
                    line = _clean_ztp_line(line)
                self._s.app.call_from_thread(self._s.post_message, _LogLine(line, stream))

        pkg_logger = logging.getLogger("nv_config_manager_installer.air_sim")
        prev_level = pkg_logger.level
        fwd = _Fwd(self)
        fwd.setFormatter(logging.Formatter("%(asctime)s  %(message)s", datefmt="%H:%M:%S"))
        pkg_logger.addHandler(fwd)
        pkg_logger.setLevel(logging.DEBUG)
        try:
            manager.monitor_services(host, port, stop_event=self._monitor_stop)
        finally:
            pkg_logger.removeHandler(fwd)
            pkg_logger.setLevel(prev_level)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker.name == "_run_orchestrator" and event.state == WorkerState.ERROR:
            self._bringup_running = False
            self.query_one("#btn-launch", Button).disabled = False
            self._set_status(
                "[bold red][!] Worker crashed — check the Textual log for details.[/bold red]"
            )

    def on__step_updated(self, event: _StepUpdated) -> None:
        self.query_one("#step-list", _StepListWidget).update_step(event.step_id, event.status)

    def on__log_line(self, event: _LogLine) -> None:
        self.query_one("#log-viewer", _LogViewerWidget).append_line(event.line, event.stream)

    def on__ssh_ready(self, event: _SshReady) -> None:
        self._host = event.host
        self._port = event.port
        ssh_cmd = (
            f"sshpass -p {NVCM_BOX_PASSWORD} ssh"
            f" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
            f" -o PreferredAuthentications=password"
            f" -p {event.port} {NVCM_BOX_USER}@{event.host}"
        )
        self._show_ssh_command(ssh_cmd)
        manager = AirSimulationManager(
            ngc_api_key=self._config.ngc_api_key,
            use_internal=self._config.use_internal,
            org_id=self._config.org_id,
        )
        self.query_one("#pod-status-panel", _PodStatusWidget).start_polling(
            event.host, event.port, manager
        )

    def on__deploy_started(self, event: _DeployStarted) -> None:
        pass

    def on__bringup_complete(self, event: _BringupComplete) -> None:
        self._bringup_running = False
        self.query_one("#btn-launch", Button).disabled = False
        if event.success:
            self._host = event.host
            self._port = event.port
            self._set_status("[bold green][*] Bringup complete![/bold green]")
            self.app.notify("Simulation bringup complete!", severity="information")
            viewer = self.query_one("#log-viewer", _LogViewerWidget)
            viewer.add_tab("dhcp", "DHCP")
            viewer.add_tab("ztp", "ZTP")
            if event.host:
                self._show_proxy_panel(event.host, event.port)
                self._run_monitoring(event.host, event.port)
        else:
            self._set_status("[bold red][!] Bringup failed — check the log above[/bold red]")
            self.app.notify("Bringup failed. See log for details.", severity="error")

    def _show_proxy_panel(self, host: str, port: int) -> None:
        proxy = ProxyInfo(host=host, port=port)
        widget = _ProxyAccessWidget(proxy, id="proxy-access")
        self.query_one("#log-viewer", _LogViewerWidget).set_access_widget(widget)

    def on_unmount(self) -> None:
        self._monitor_stop.set()
        try:
            self.query_one("#pod-status-panel", _PodStatusWidget).stop_polling()
        except Exception:
            pass

    def get_status(self, config: SimConfig) -> str:
        if self._bringup_running:
            return "[>]"
        if self._host:
            return "[*]"
        return "[ ]"
