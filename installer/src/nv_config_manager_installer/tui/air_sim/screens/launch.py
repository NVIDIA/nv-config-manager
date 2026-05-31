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
import os
import subprocess
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from queue import Empty, SimpleQueue
from typing import IO

from rich.text import Text
from textual import events, work
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Button, Label, Static
from textual.worker import Worker, WorkerState

from nv_config_manager_installer.air_sim.constants import (
    CONFIG_MANAGER_NAUTOBOT_DEPLOYMENT,
    DEFAULT_AIR_FRONTEND_URL,
    DEFAULT_AIR_INTERNAL_FRONTEND_URL,
    NVCM_BOX_PASSWORD,
    NVCM_BOX_USER,
)
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
_VISIBLE_ACTIVITY_LINES = 80
_LOG_FLUSH_INTERVAL = 0.5
_MAX_LOG_DRAIN_PER_FLUSH = 250
_MAX_SERVICE_EVENTS_PER_POLL = 25
_SERVICE_POLL_INTERVAL = 10.0
_POD_READY_STATES = {"Running", "Completed", "Succeeded"}
_DHCP_ACTIVITY_KEYWORDS = (
    "DHCPDISCOVER",
    "DHCPOFFER",
    "DHCPREQUEST",
    "DHCPACK",
    "DHCPNAK",
    "DHCP4_LEASE",
    "DHCP4_PACKET",
    "DHCPSRV_CFGMGR_NEW_SUBNET4",
    "DHCP4_CONFIG_COMPLETE",
    "Generating configuration from nautobot data",
    "Validating configuration against KEA API",
    "Persisting configuration to Redis",
    "KEA DHCP4 Configuration Refresh Complete",
    "error",
    "failed",
    "warning",
)
_ZTP_SKIP_KEYWORDS = ("health", "metrics", "readiness", "livez")
_NAUTOBOT_DEPENDENT_PREFIXES = (
    "nv-config-manager-nautobot-celery",
    "nv-config-manager-nautobot-celery-beat",
    "nv-config-manager-render-",
    "nv-config-manager-temporal-",
    "nv-config-manager-ztp",
    "nv-config-manager-dhcp",
)


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
    """Extract the useful DHCP event text from Kea or refresh logs."""
    message = _json_log_message(line)
    if message:
        return message
    for marker in ("DHCP4", "DHCPSRV"):
        idx = line.find(marker)
        if idx >= 0:
            return line[idx:]
    return line


def _clean_ztp_line(line: str) -> str:
    """Extract the msg/message field from a JSON-structured ZTP log line."""
    message = _json_log_message(line)
    if message:
        return message
    return line


def _json_log_message(line: str) -> str | None:
    """Extract msg/message from a JSON-structured service log line."""
    idx = line.find("{")
    if idx >= 0:
        try:
            data = json.loads(line[idx:])
            message = data.get("msg") or data.get("message")
            return str(message) if message else None
        except json.JSONDecodeError:
            return None
    return None


def _is_interesting_dhcp_line(line: str) -> bool:
    """Return true for DHCP lines that help explain provisioning progress."""
    lowered = line.lower()
    return any(keyword in line or keyword.lower() in lowered for keyword in _DHCP_ACTIVITY_KEYWORDS)


def _is_interesting_ztp_line(line: str) -> bool:
    """Return true for ZTP access/API lines, excluding health/readiness noise."""
    lowered = line.lower()
    if any(keyword in lowered for keyword in _ZTP_SKIP_KEYWORDS):
        return False
    return " /v1/" in line or "/v1/" in line or "error" in lowered or "failed" in lowered


def _activity_prefix(stream: str) -> str:
    if stream == "dhcp":
        return "[DHCP]"
    if stream == "ztp":
        return "[ZTP]"
    return "[DEPLOY]"


def _is_ready_pod(pod: dict[str, str]) -> bool:
    ready_count, _, ready_total = pod.get("ready", "").partition("/")
    return (
        bool(ready_count)
        and bool(ready_total)
        and ready_count == ready_total
        and pod.get("status") in _POD_READY_STATES
    )


def _is_nautobot_web_pod(pod: dict[str, str]) -> bool:
    name = pod.get("name", "")
    return name.startswith(f"{CONFIG_MANAGER_NAUTOBOT_DEPLOYMENT}-") and not name.startswith(
        f"{CONFIG_MANAGER_NAUTOBOT_DEPLOYMENT}-celery"
    )


def _pod_state_text(pod: dict[str, str]) -> str:
    return f"{pod.get('ready', '—')} {pod.get('status', 'Unknown')}"


def _pod_attention_text(pod: dict[str, str]) -> str:
    return f"{pod.get('name', 'unknown')} ({_pod_state_text(pod)})"


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


class _SimulationCreated(Message):
    def __init__(self, simulation_id: str) -> None:
        super().__init__()
        self.simulation_id = simulation_id


# ── Callback bridge ───────────────────────────────────────────────────────────


class _TuiCallback(OrchestratorCallback):
    def __init__(self, screen: LaunchScreen, log_file: IO[str] | None = None) -> None:
        self._screen = screen
        self._log_file = log_file

    def on_step(self, step_id: str, status: StepStatus, message: str = "") -> None:
        self._screen.post_message(_StepUpdated(step_id, status, message))
        label = dict(STEPS).get(step_id, step_id)
        suffix = f" - {message}" if message else ""
        self._screen.enqueue_log_line(f"{_STATUS_ICON[status]} {label}{suffix}", "deploy")

    def on_log(self, line: str) -> None:
        stream = "deploy"
        if line.startswith("[DHCP]"):
            stream = "dhcp"
        elif line.startswith("[ZTP]"):
            stream = "ztp"
        ui_line = line
        if stream == "dhcp":
            ui_line = _clean_dhcp_line(line)
            show_line = _is_interesting_dhcp_line(ui_line)
        elif stream == "ztp":
            ui_line = _clean_ztp_line(line)
            show_line = _is_interesting_ztp_line(ui_line)
        else:
            show_line = True
            if line.startswith("Simulation: "):
                self._screen.post_message(
                    _SimulationCreated(line.removeprefix("Simulation: ").strip())
                )
        if show_line:
            self._screen.enqueue_log_line(ui_line, stream)
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


class _ActivityWidget(Vertical):
    """Compact bounded activity feed for deploy, DHCP, and ZTP progress."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._lines: list[str] = []
        self._seen: set[str] = set()

    def compose(self) -> ComposeResult:
        yield Label("Activity", classes="section-title")
        yield Static(
            "Showing deploy output. DHCP/ZTP events appear here after install completes.",
            classes="field-hint",
        )
        yield Static(
            "Waiting for activity...",
            id="activity-lines",
            classes="activity-lines",
            markup=False,
        )

    def append_lines(self, entries: list[tuple[str, str]]) -> None:
        changed = False
        for raw_line, stream in entries:
            line = raw_line.strip()
            if not line:
                continue
            display_line = f"{_activity_prefix(stream)} {line}"
            if stream != "deploy" and display_line in self._seen:
                continue
            if stream != "deploy":
                self._seen.add(display_line)
            self._lines.append(display_line)
            changed = True
        if not changed:
            return
        if len(self._lines) > _VISIBLE_ACTIVITY_LINES:
            self._lines = self._lines[-_VISIBLE_ACTIVITY_LINES:]
            self._seen = set(self._lines)
        self.query_one("#activity-lines", Static).update("\n".join(self._lines))


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


class _AirLinkBar(Horizontal):
    """Copyable AIR simulation URL shown once the simulation exists."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._url = ""
        self.tooltip = "Copy AIR simulation link"

    def compose(self) -> ComposeResult:
        yield Label("AIR", classes="ssh-badge")
        yield Static("", id="air-link", classes="ssh-cmd")
        yield _copy_button(
            "copy-air-link",
            "Copy AIR simulation link",
            classes="copy-icon-btn ssh-copy-btn",
        )

    def set_url(self, url: str) -> None:
        self._url = url
        self.query_one("#air-link", Static).update(Text(url, style=f"link {url}"))
        self.display = True

    def on_click(self, event: events.Click) -> None:
        self._copy_url()
        event.stop()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "copy-air-link":
            self._copy_url()
            event.stop()

    def _copy_url(self) -> None:
        if not self._url:
            return
        self.app.copy_to_clipboard(self._url)
        button = self.query_one("#copy-air-link", Button)
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

        yield Label("Access", classes="subsection-label")
        yield Label(
            "Start the SOCKS tunnel, then open the browser with the proxy after deploy is ready.",
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
    """Polls lightweight deployment health and provisioning status over SSH."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._host = ""
        self._port = 0
        self._manager: object = None  # AirSimulationManager, set at start_polling
        self._stop = threading.Event()
        self._polling = False
        self._prov_polling = False
        self._last_pod_summary = ""
        self._last_prov: tuple[int, int, tuple[str, ...]] | None = None

    def compose(self) -> ComposeResult:
        yield Label("Progress", classes="section-title")
        yield Label("─" * 30, classes="section-divider")
        yield Static("Switches Provisioned: —", id="prov-count")
        yield Static("", id="prov-detail")
        yield Label("─" * 30, classes="section-divider")
        yield Static("Pods: waiting for cluster", id="pod-summary")
        yield Static("", id="pod-detail")

    def start_polling(self, host: str, port: int, manager: object) -> None:
        self._host = host
        self._port = port
        self._manager = manager
        self._stop.clear()
        self._polling = False
        self._prov_polling = False
        self.query_one("#prov-count", Static).update("Switches Provisioned: waiting for Nautobot")
        self._tick()
        self.set_interval(15.0, self._tick)
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
            if not isinstance(self._manager, AirSimulationManager):
                raise TypeError("expected AirSimulationManager for self._manager")
            pods = self._manager.get_pod_status(self._host, self._port)
            self.app.call_from_thread(self._update_table, pods)
        finally:
            self._polling = False

    @work(thread=True, exclusive=False)
    def _do_prov_refresh(self) -> None:
        self._prov_polling = True
        try:
            if not isinstance(self._manager, AirSimulationManager):
                raise TypeError("expected AirSimulationManager for self._manager")
            prov, total, remaining = self._manager.get_provisioning_status(self._host, self._port)
            self.app.call_from_thread(self._update_prov, prov, total, remaining)
        finally:
            self._prov_polling = False

    def _update_prov(self, prov: int, total: int, remaining: list[str]) -> None:
        next_state = (prov, total, tuple(remaining))
        if next_state == self._last_prov:
            return
        self._last_prov = next_state
        try:
            self.query_one("#prov-count", Static).update(
                f"Switches Provisioned: {prov}/{total}"
                if total
                else "Switches Provisioned: waiting for Nautobot"
            )
            detail = ""
            if remaining and total and prov < total:
                detail = "Pending: " + ", ".join(remaining)
            self.query_one("#prov-detail", Static).update(detail)
        except Exception:
            pass

    def _update_table(self, pods: list[dict[str, str]]) -> None:
        total = len(pods)
        if not total:
            summary = "Pods: waiting for cluster"
            detail = ""
        else:
            nautobot = next((pod for pod in pods if _is_nautobot_web_pod(pod)), None)
            if nautobot is None:
                summary = "Nautobot: waiting for pod"
            elif _is_ready_pod(nautobot):
                summary = f"Nautobot: ready ({_pod_state_text(nautobot)})"
            else:
                summary = f"Nautobot: {_pod_state_text(nautobot)}"

            remaining = [pod for pod in pods if pod is not nautobot]
            remaining_not_ready = [pod for pod in remaining if not _is_ready_pod(pod)]
            dependent_not_ready = [
                pod
                for pod in remaining_not_ready
                if pod.get("name", "").startswith(_NAUTOBOT_DEPENDENT_PREFIXES)
            ]
            other_not_ready = [pod for pod in remaining_not_ready if pod not in dependent_not_ready]
            ready_remaining = len(remaining) - len(remaining_not_ready)
            detail = f"Other pods ready: {ready_remaining}/{len(remaining)}"

            attention = [*dependent_not_ready, *other_not_ready]
            if attention:
                detail += " | Remaining: " + ", ".join(
                    _pod_attention_text(pod) for pod in attention[:4]
                )
                if len(attention) > 4:
                    detail += f", +{len(attention) - 4} more"

        next_summary = f"{summary}\n{detail}"
        if next_summary == self._last_pod_summary:
            return
        self._last_pod_summary = next_summary
        self.query_one("#pod-summary", Static).update(summary)
        self.query_one("#pod-detail", Static).update(detail)


# ── Launch screen ─────────────────────────────────────────────────────────────


class LaunchScreen(Container):
    """Launch panel: summary, launch button, step list, and log stream."""

    def __init__(self, config: SimConfig, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._config = config
        self._bringup_running = False
        self._host = ""
        self._port = 0
        self._simulation_id = ""
        self._simulation_url = ""
        self._ssh_cmd_text = ""
        self._monitor_stop = threading.Event()
        self._deploy_log_path: Path | None = None
        self._pending_log_lines: SimpleQueue[tuple[str, str]] = SimpleQueue()
        self._log_flush_lock = threading.Lock()
        self._log_flush_scheduled = False
        self._service_polling = False
        self._seen_service_events: set[str] = set()
        self._proxy_access_target: tuple[str, int] | None = None

    def compose(self) -> ComposeResult:
        yield Label("Launch", classes="section-title")
        yield Label("─" * 40, classes="section-divider")

        with Horizontal(id="launch-controls"):
            yield Button("Launch Simulation", id="btn-launch", variant="success")
        yield Static("", id="launch-status")

        yield Label("─" * 40, classes="section-divider")

        yield _AirLinkBar(id="air-link-bar", classes="ssh-info-bar")
        yield _SshCommandBar(id="ssh-info-bar", classes="ssh-info-bar")
        with VerticalScroll(id="access-pane"):
            yield Static("Access details will appear after SSH is ready.")

        with Vertical(id="launch-dashboard"):
            with Horizontal(id="dashboard-top"):
                with VerticalScroll(id="step-panel"):
                    yield _StepListWidget(id="step-list")
                yield _PodStatusWidget(id="pod-status-panel")
            yield _ActivityWidget(id="activity-viewer")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-launch" and not self._bringup_running:
            self._start_bringup()
            event.stop()

    def _set_status(self, markup: str) -> None:
        self.query_one("#launch-status", Static).update(markup)

    def _status_text(self, state: str) -> str:
        parts = [state]
        if self._deploy_log_path:
            parts.append(f"log -> {self._deploy_log_path}")
        return "\n".join(parts)

    def _air_frontend_url(self) -> str:
        return (
            DEFAULT_AIR_INTERNAL_FRONTEND_URL
            if self._config.use_internal
            else DEFAULT_AIR_FRONTEND_URL
        ).rstrip("/")

    def set_simulation_id(self, simulation_id: str) -> None:
        if not simulation_id or simulation_id == self._simulation_id:
            return
        self._simulation_id = simulation_id
        self._simulation_url = f"{self._air_frontend_url()}/simulations/{simulation_id}"
        self.query_one("#air-link-bar", _AirLinkBar).set_url(self._simulation_url)
        self._set_status(self._status_text("[yellow]Running...[/yellow]"))

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
        self._set_status(self._status_text("[yellow]Running...[/yellow]"))
        self._run_orchestrator()

    @work(thread=True, exclusive=False)
    def _run_orchestrator(self) -> None:
        log_path = self._deploy_log_path
        with open(log_path if log_path else os.devnull, "w") as lf:
            cb = _TuiCallback(self, log_file=lf)
            orchestrator = SimOrchestrator(self._config, cb)
            orchestrator.run()

    @work(thread=True, exclusive=False)
    def _run_monitoring(self, host: str, port: int) -> None:
        try:
            manager = AirSimulationManager(
                ngc_api_key=self._config.ngc_api_key,
                use_internal=self._config.use_internal,
                org_id=self._config.org_id,
            )
            while not self._monitor_stop.is_set():
                snapshots = manager.get_service_log_snapshots(host, port)
                entries: list[tuple[str, str]] = []
                for stream, lines in snapshots.items():
                    for line in lines:
                        if stream == "dhcp":
                            clean = _clean_dhcp_line(line)
                            interesting = _is_interesting_dhcp_line(clean)
                        else:
                            clean = _clean_ztp_line(line)
                            interesting = _is_interesting_ztp_line(clean)
                        key = f"{stream}:{clean}"
                        if not interesting or key in self._seen_service_events:
                            continue
                        self._seen_service_events.add(key)
                        entries.append((clean, stream))
                for line, stream in entries[-_MAX_SERVICE_EVENTS_PER_POLL:]:
                    self.enqueue_log_line(line, stream)
                self._monitor_stop.wait(_SERVICE_POLL_INTERVAL)
        finally:
            self._service_polling = False

    def _start_monitoring(self, host: str, port: int) -> None:
        if self._service_polling:
            return
        self._service_polling = True
        self._run_monitoring(host, port)

    def on_worker_state_changed(self, event: Worker.StateChanged) -> None:
        if event.worker.name == "_run_orchestrator" and event.state == WorkerState.ERROR:
            self._bringup_running = False
            self.query_one("#btn-launch", Button).disabled = False
            self._set_status(
                self._status_text(
                    "[bold red][!] Worker crashed - check the Textual log for details.[/bold red]"
                )
            )

    def on__step_updated(self, event: _StepUpdated) -> None:
        self.query_one("#step-list", _StepListWidget).update_step(event.step_id, event.status)

    def on__log_line(self, event: _LogLine) -> None:
        self.enqueue_log_line(event.line, event.stream)

    def enqueue_log_line(self, line: str, stream: str = "deploy") -> None:
        """Queue a log line from any thread and batch UI refresh work."""
        self._pending_log_lines.put((line, stream))
        self._schedule_log_flush()

    def _schedule_log_flush(self) -> None:
        with self._log_flush_lock:
            if self._log_flush_scheduled:
                return
            self._log_flush_scheduled = True

        def schedule() -> None:
            self.set_timer(_LOG_FLUSH_INTERVAL, self._flush_log_lines)

        if threading.current_thread() is threading.main_thread():
            schedule()
        else:
            self.app.call_from_thread(schedule)

    def _flush_log_lines(self) -> None:
        with self._log_flush_lock:
            self._log_flush_scheduled = False

        try:
            viewer = self.query_one("#activity-viewer", _ActivityWidget)
        except Exception:
            return

        batch: list[tuple[str, str]] = []
        processed = 0
        while processed < _MAX_LOG_DRAIN_PER_FLUSH:
            try:
                line, stream = self._pending_log_lines.get_nowait()
            except Empty:
                break
            batch.append((line, stream))
            processed += 1

        if batch:
            viewer.append_lines(batch)

        if not self._pending_log_lines.empty():
            self._schedule_log_flush()

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
        self._show_proxy_panel(event.host, event.port)
        manager = AirSimulationManager(
            ngc_api_key=self._config.ngc_api_key,
            use_internal=self._config.use_internal,
            org_id=self._config.org_id,
        )
        self.query_one("#pod-status-panel", _PodStatusWidget).start_polling(
            event.host, event.port, manager
        )

    def on__deploy_started(self, event: _DeployStarted) -> None:
        self._host = event.host
        self._port = event.port

    def on__bringup_complete(self, event: _BringupComplete) -> None:
        self._bringup_running = False
        self.query_one("#btn-launch", Button).disabled = False
        if event.success:
            self._host = event.host
            self._port = event.port
            self.enqueue_log_line(
                "Bringup complete - monitoring DHCP and ZTP events.",
                "deploy",
            )
            self._set_status(self._status_text("[bold green][*] Bringup complete![/bold green]"))
            self.app.notify("Simulation bringup complete!", severity="information")
            if event.host:
                self._show_proxy_panel(event.host, event.port)
                self._start_monitoring(event.host, event.port)
        else:
            self.enqueue_log_line(
                "Bringup failed - check the deploy log for details.",
                "deploy",
            )
            self._set_status(
                self._status_text("[bold red][!] Bringup failed - check the deploy log[/bold red]")
            )
            self.app.notify("Bringup failed. See log for details.", severity="error")

    def on__simulation_created(self, event: _SimulationCreated) -> None:
        self.set_simulation_id(event.simulation_id)

    def _show_proxy_panel(self, host: str, port: int) -> None:
        if self._proxy_access_target == (host, port):
            return
        proxy = ProxyInfo(host=host, port=port)
        widget = _ProxyAccessWidget(proxy, id="proxy-access")
        pane = self.query_one("#access-pane", VerticalScroll)
        pane.remove_children()
        pane.mount(widget)
        pane.display = True
        self._proxy_access_target = (host, port)

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
