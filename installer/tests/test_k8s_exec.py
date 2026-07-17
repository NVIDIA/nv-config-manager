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
"""Focused tests for Kubernetes loader pod and exec behavior."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from nv_config_manager_installer.k8s import K8sClient


def _client() -> K8sClient:
    k8s = object.__new__(K8sClient)
    k8s.v1 = MagicMock()
    k8s.apps_v1 = MagicMock()
    return k8s


def test_exec_command_returns_output_after_zero_exit() -> None:
    k8s = _client()
    websocket = MagicMock()
    websocket.is_open.side_effect = [True, False]
    websocket.returncode = 0
    websocket.read_all.return_value = "done\n"

    with patch("nv_config_manager_installer.k8s.k8s_stream", return_value=websocket) as stream:
        output = k8s.exec_command("loader", "nv-config-manager", ["true"], timeout=30)

    assert output == "done\n"
    assert stream.call_args.kwargs["_request_timeout"] == 30
    websocket.close.assert_called_once()


def test_exec_command_raises_for_remote_nonzero_exit() -> None:
    k8s = _client()
    websocket = MagicMock()
    websocket.is_open.return_value = False
    websocket.returncode = 17
    websocket.read_all.return_value = "permission denied"

    with (
        patch("nv_config_manager_installer.k8s.k8s_stream", return_value=websocket),
        pytest.raises(RuntimeError, match="failed with exit 17: permission denied"),
    ):
        k8s.exec_command("loader", "nv-config-manager", ["false"])

    websocket.close.assert_called_once()


def test_create_loader_pod_stays_alive_and_targets_node() -> None:
    k8s = _client()

    k8s.create_loader_pod(
        "loader",
        "nv-config-manager",
        "jobs",
        "/jobs",
        node_name="worker-a",
    )

    body = k8s.v1.create_namespaced_pod.call_args.args[1]
    assert body.spec.node_name == "worker-a"
    assert body.spec.containers[0].command == [
        "sh",
        "-c",
        "while true; do sleep 3600; done",
    ]


def test_get_pvc_mounted_node_uses_a_running_consumer() -> None:
    k8s = _client()
    pending = SimpleNamespace(
        status=SimpleNamespace(phase="Pending"),
        spec=SimpleNamespace(
            node_name="worker-pending",
            volumes=[SimpleNamespace(persistent_volume_claim=SimpleNamespace(claim_name="jobs"))],
        ),
    )
    running = SimpleNamespace(
        status=SimpleNamespace(phase="Running"),
        spec=SimpleNamespace(
            node_name="worker-a",
            volumes=[SimpleNamespace(persistent_volume_claim=SimpleNamespace(claim_name="jobs"))],
        ),
    )
    k8s.v1.list_namespaced_pod.return_value.items = [pending, running]

    assert k8s.get_pvc_mounted_node("jobs", "nv-config-manager") == "worker-a"


def test_deployment_scale_helpers_preserve_replica_counts() -> None:
    k8s = _client()
    k8s.apps_v1.read_namespaced_deployment.return_value.spec.replicas = 3
    k8s.apps_v1.patch_namespaced_deployment.return_value.metadata.generation = 9

    assert k8s.get_deployment_replicas("render", "nv-config-manager") == 3
    k8s.apps_v1.read_namespaced_deployment.return_value.spec.replicas = None
    assert k8s.get_deployment_replicas("render", "nv-config-manager") == 1
    assert k8s.scale_deployment("render", "nv-config-manager", 0) == 9
    k8s.apps_v1.patch_namespaced_deployment.assert_called_once_with(
        "render",
        "nv-config-manager",
        {"spec": {"replicas": 0}},
    )


def test_rollout_completion_waits_for_scaled_down_pods_to_exit() -> None:
    deployment = SimpleNamespace(
        metadata=SimpleNamespace(generation=4),
        spec=SimpleNamespace(replicas=0),
        status=SimpleNamespace(observed_generation=4, replicas=1),
    )

    assert K8sClient._rollout_complete(deployment) is False

    deployment.status.replicas = 0
    assert K8sClient._rollout_complete(deployment) is True
