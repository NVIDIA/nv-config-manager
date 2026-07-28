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
"""Tests for DSX Air sim orchestrator topology resolution."""

from __future__ import annotations

import pytest

from nv_config_manager_installer.air_sim.orchestrator import (
    SimOrchestrator,
    _monitor_setup_command,
)
from nv_config_manager_installer.air_sim.sim_config import SimConfig


class _Callback:
    def on_step(self, step_id, status, message=""):
        pass

    def on_log(self, line):
        pass

    def on_ssh_ready(self, host, port):
        pass

    def on_deploy_started(self, host, port):
        pass

    def on_complete(self, success, host="", port=0):
        pass


def test_resolve_topology_prefers_direct_path() -> None:
    cfg = SimConfig(topology_path="/tmp/direct.yaml", run_mock_topology_job=True)
    orchestrator = SimOrchestrator(cfg, _Callback())

    assert orchestrator._resolve_topology_path(cfg) == "/tmp/direct.yaml"


def test_resolve_topology_generates_from_mock_context(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def fake_write_site_design_from_mock_context(blueprint: str, deployment_name: str) -> str:
        calls.append((blueprint, deployment_name))
        return "/tmp/generated.yaml"

    monkeypatch.setattr(
        "nv_config_manager_installer.air_sim.orchestrator.write_site_design_from_mock_context",
        fake_write_site_design_from_mock_context,
    )
    cfg = SimConfig(
        topology_path="",
        run_mock_topology_job=True,
        mock_blueprint="air_trial",
        deployment_name="demo",
    )
    orchestrator = SimOrchestrator(cfg, _Callback())

    assert orchestrator._resolve_topology_path(cfg) == "/tmp/generated.yaml"
    assert calls == [("air_trial", "demo")]


def test_resolve_topology_requires_direct_path_for_custom_flows() -> None:
    cfg = SimConfig(topology_path="", run_mock_topology_job=False)
    orchestrator = SimOrchestrator(cfg, _Callback())

    with pytest.raises(RuntimeError, match="topology_path is required"):
        orchestrator._resolve_topology_path(cfg)


def test_monitor_setup_command_uses_password_placeholder() -> None:
    command = _monitor_setup_command("worker.example", 17117)

    assert command.startswith("sshpass -p '<password>'")
    assert "worker.example" in command
    assert "17117" in command
