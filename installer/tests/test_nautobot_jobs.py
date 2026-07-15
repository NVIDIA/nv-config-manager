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
"""Tests for Nautobot job execution shared by deployment and PVC updates."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from nv_config_manager_installer.nautobot_jobs import NautobotJobRunner


@patch("nv_config_manager_installer.nautobot_jobs.ServiceProxy")
def test_runs_job_with_json_input_and_waits_for_completion(mock_proxy_class: MagicMock) -> None:
    k8s = MagicMock()
    k8s.read_secret_data.return_value = {"api_token": "api-token"}
    pod = MagicMock()
    pod.metadata.name = "nv-config-manager-nautobot-123"
    pod.status.phase = "Running"
    k8s.v1.list_namespaced_pod.return_value.items = [pod]
    proxy = mock_proxy_class.return_value
    proxy.request.side_effect = [
        "{}",
        json.dumps({"results": [{"id": "job-id", "enabled": True}]}),
        json.dumps({"id": "result-id"}),
        json.dumps({"status": {"value": "completed"}}),
        "[]",
    ]

    completed = NautobotJobRunner(
        k8s,
        "nv-config-manager",
        "nv-config-manager",
        poll_interval=0,
    ).run("custom_jobs.bootstrap.SiteBootstrap", {"site": "site-1"})

    assert completed is True
    assert proxy.request.call_args_list[2].kwargs == {
        "method": "POST",
        "headers": {"Authorization": "Token api-token", "Content-Type": "application/json"},
        "data": '{"data": {"site": "site-1"}}',
    }
    k8s.exec_command.assert_called_once_with(
        "nv-config-manager-nautobot-123",
        "nv-config-manager",
        [
            "nautobot-server",
            "shell",
            "--command",
            "from nautobot.extras.jobs import get_jobs; get_jobs(reload=True)",
        ],
        container="nautobot",
    )
    proxy.stop.assert_called_once()


def test_rejects_job_without_module_name() -> None:
    with pytest.raises(ValueError, match="MODULE.CLASS"):
        NautobotJobRunner(MagicMock(), "nv-config-manager", "nv-config-manager").run(
            "SiteBootstrap", {}
        )
