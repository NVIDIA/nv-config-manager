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
"""Tests for AIR simulation manager helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

import pytest

import nv_config_manager_installer.air_sim.sim_manager as sim_manager_module
from nv_config_manager_installer.air_sim.sim_manager import AirSimulationManager


def _image(name: str, modified: datetime, version: str = "") -> SimpleNamespace:
    return SimpleNamespace(
        name=name,
        version=version,
        modified=modified,
        created=modified,
    )


def _manager_with_images(images: list[SimpleNamespace]) -> AirSimulationManager:
    manager = AirSimulationManager.__new__(AirSimulationManager)
    manager.client = SimpleNamespace(
        images=SimpleNamespace(list=lambda: iter(images)),
    )
    return manager


def test_resolve_cumulus_vx_images_prefers_exact_name() -> None:
    manager = _manager_with_images(
        [
            _image(
                "cumulus-linux-vx-amd64-5.16.1.0008.qcow2",
                datetime(2026, 1, 2, tzinfo=UTC),
            ),
            _image("cumulus-vx-5.16.1", datetime(2026, 1, 1, tzinfo=UTC)),
        ]
    )

    assert manager.resolve_cumulus_vx_images(["5.16.1"]) == {"5.16.1": "cumulus-vx-5.16.1"}


def test_resolve_cumulus_vx_images_uses_newest_close_match() -> None:
    manager = _manager_with_images(
        [
            _image(
                "cumulus-linux-vx-amd64-5.16.1.0007.qcow2",
                datetime(2026, 1, 1, tzinfo=UTC),
            ),
            _image(
                "cumulus-linux-vx-amd64-5.16.1.0008.qcow2",
                datetime(2026, 1, 2, tzinfo=UTC),
            ),
        ]
    )

    assert manager.resolve_cumulus_vx_images(["5.16.1"]) == {
        "5.16.1": "cumulus-linux-vx-amd64-5.16.1.0008.qcow2"
    }


def test_resolve_cumulus_vx_images_requires_match() -> None:
    manager = _manager_with_images([_image("generic/ubuntu2404", datetime(2026, 1, 1, tzinfo=UTC))])

    with pytest.raises(RuntimeError, match="cumulus-vx-5.16.1"):
        manager.resolve_cumulus_vx_images(["5.16.1"])


def test_configure_nat_rules_enables_dhcp_relay(monkeypatch: pytest.MonkeyPatch) -> None:
    manager = AirSimulationManager.__new__(AirSimulationManager)
    commands: list[str] = []

    def fake_ssh_cmd(host: str, port: int) -> list[str]:
        assert host == "worker.example"
        assert port == 17117
        return ["ssh", "nvcm@worker.example"]

    def fake_run(
        cmd: list[str],
        *,
        capture_output: bool,
        text: bool,
        timeout: int,
    ) -> SimpleNamespace:
        assert capture_output is True
        assert text is True
        remote_command = cmd[-1]
        commands.append(remote_command)
        if "nv-config-manager-dhcp-service" in remote_command:
            return SimpleNamespace(returncode=0, stdout="172.18.255.202\n", stderr="")
        if "nv-config-manager-ztp-service" in remote_command:
            return SimpleNamespace(returncode=0, stdout="172.18.255.201\n", stderr="")
        if "docker network inspect kind" in remote_command:
            return SimpleNamespace(returncode=0, stdout="a0016a226683\n", stderr="")
        if "docker ps" in remote_command:
            return SimpleNamespace(returncode=0, stdout="nvcm-control-plane\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(manager, "_ssh_cmd", fake_ssh_cmd)
    monkeypatch.setattr(sim_manager_module.subprocess, "run", fake_run)

    assert manager.configure_nat_rules(
        "worker.example",
        17117,
        oob_gateway="10.100.0.1",
        relay_return_networks=["10.100.0.0/16"],
        internal_iface="eth1",
    )

    relay_config = next(command for command in commands if "/etc/default/isc-dhcp-relay" in command)
    assert 'SERVERS="172.18.255.202"' in relay_config
    assert 'INTERFACES="eth1 br-a0016a226683"' in relay_config
    assert "sudo systemctl enable isc-dhcp-relay" in commands
    assert "sudo systemctl restart isc-dhcp-relay" in commands
    assert not any("disable --now isc-dhcp-relay" in command for command in commands)
