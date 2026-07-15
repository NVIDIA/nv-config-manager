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
"""Run Nautobot jobs through the API exposed by an NVCM deployment."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

from nv_config_manager_installer.k8s import K8sClient, ServiceProxy


class NautobotJobRunner:
    """Run a named Nautobot job and wait for its result."""

    _COMPLETED_STATUSES = frozenset({"completed", "success"})
    _FAILED_STATUSES = frozenset({"failed", "failure", "errored", "error"})
    _PENDING_STATUSES = frozenset({"pending", "running", "started", ""})

    def __init__(
        self,
        k8s: K8sClient,
        namespace: str,
        release_name: str,
        *,
        on_log: Callable[[str], None] | None = None,
        poll_interval: float = 3,
    ) -> None:
        self._k8s = k8s
        self._namespace = namespace
        self._release_name = release_name
        self._on_log = on_log or (lambda _message: None)
        self._poll_interval = poll_interval

    def run(self, job_class: str, job_input: dict[str, Any], *, timeout: int = 1_800) -> bool:
        """Run *job_class* with *job_input*, returning whether it succeeded."""
        module_name, job_class_name = self._split_job_class(job_class)
        token = self._get_api_token()
        if not token:
            raise RuntimeError("Could not retrieve Nautobot API token from the cluster secret")

        proxy = ServiceProxy(self._k8s, f"{self._release_name}-nautobot", self._namespace)
        try:
            proxy.start()
            self._on_log("Nautobot port-forward established")
            self._on_log("Waiting for Nautobot API...")
            self._wait_for_api(proxy)
            self._reload_jobs()
            headers = {"Authorization": f"Token {token}", "Content-Type": "application/json"}
            return self._run_job(
                proxy,
                module_name,
                job_class_name,
                job_class,
                job_input,
                headers,
                timeout,
            )
        finally:
            proxy.stop()

    @staticmethod
    def _split_job_class(job_class: str) -> tuple[str, str]:
        try:
            module_name, class_name = job_class.rsplit(".", 1)
        except ValueError as exc:
            raise ValueError("Nautobot job must use the fully qualified MODULE.CLASS name") from exc
        if not module_name or not class_name:
            raise ValueError("Nautobot job must use the fully qualified MODULE.CLASS name")
        return module_name, class_name

    def _get_api_token(self) -> str:
        data = self._k8s.read_secret_data("nautobot-admin", self._namespace)
        if "api_token" in data:
            return data["api_token"]
        data = self._k8s.read_secret_data("nautobot-token", self._namespace)
        return data.get("token", "")

    def _wait_for_api(self, proxy: ServiceProxy, timeout: int = 300) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                proxy.request("health")
                return
            except Exception:
                time.sleep(self._poll_interval)
        raise TimeoutError("Nautobot API did not become healthy within timeout")

    def _reload_jobs(self) -> None:
        """Reload JOBS_ROOT in Nautobot so freshly mounted custom jobs are registered."""
        pods = self._k8s.v1.list_namespaced_pod(
            self._namespace,
            label_selector=(
                f"app.kubernetes.io/name={self._release_name}-nautobot,"
                f"app.kubernetes.io/instance={self._release_name}"
            ),
        )
        running_pods = [
            pod
            for pod in pods.items
            if pod.status and pod.status.phase == "Running" and pod.metadata and pod.metadata.name
        ]
        if not running_pods:
            raise RuntimeError("Could not find a running Nautobot pod to reload custom jobs")

        pod_name = running_pods[0].metadata.name
        self._on_log("Reloading Nautobot job registry...")
        self._k8s.exec_command(
            pod_name,
            self._namespace,
            [
                "nautobot-server",
                "shell",
                "--command",
                "from nautobot.extras.jobs import get_jobs; get_jobs(reload=True)",
            ],
            container="nautobot",
        )

    def _run_job(
        self,
        proxy: ServiceProxy,
        module_name: str,
        job_class_name: str,
        job_class: str,
        job_input: dict[str, Any],
        headers: dict[str, str],
        timeout: int,
    ) -> bool:
        self._on_log(f"Running Nautobot job: {job_class}")
        jobs_data = json.loads(
            proxy.request(
                f"api/extras/jobs/?module_name={module_name}&job_class_name={job_class_name}",
                headers=headers,
            )
        )
        if not jobs_data.get("results"):
            self._on_log(f"Job not found: {job_class}")
            return False

        job_record = jobs_data["results"][0]
        job_id = job_record["id"]
        self._on_log(f"Found job ID: {job_id}")
        self._enable_job(proxy, job_id, job_record, headers)

        self._on_log("Starting job execution...")
        run_data = json.loads(
            proxy.request(
                f"api/extras/jobs/{job_id}/run/",
                method="POST",
                headers=headers,
                data=json.dumps({"data": job_input}),
            )
        )
        job_result_id = (
            run_data.get("id")
            or run_data.get("job_result", {}).get("id")
            or run_data.get("result", {}).get("id")
            or ""
        )
        if not job_result_id:
            self._on_log(f"Run API response keys: {list(run_data.keys())}")
            return False

        self._on_log(f"Job started, result ID: {job_result_id}")
        return self._poll_job_result(proxy, job_result_id, headers, timeout)

    def _enable_job(
        self,
        proxy: ServiceProxy,
        job_id: str,
        job_data: dict[str, Any],
        headers: dict[str, str],
    ) -> None:
        if job_data.get("enabled"):
            return

        self._on_log("Enabling job...")
        try:
            proxy.request(
                f"api/extras/jobs/{job_id}/",
                method="PATCH",
                headers=headers,
                data=json.dumps({"enabled": True}),
            )
        except Exception:
            self._on_log("API PATCH failed, enabling through nautobot-server shell...")
            pods = self._k8s.v1.list_namespaced_pod(
                self._namespace,
                label_selector=(
                    f"app.kubernetes.io/name={self._release_name}-nautobot,"
                    f"app.kubernetes.io/instance={self._release_name}"
                ),
            )
            if not pods.items:
                raise RuntimeError("Could not find a Nautobot pod to enable the job") from None
            pod_name = pods.items[0].metadata.name
            self._k8s.exec_command(
                pod_name,
                self._namespace,
                [
                    "nautobot-server",
                    "shell",
                    "--command",
                    (
                        "from nautobot.extras.models import Job; "
                        f"j=Job.objects.get(id='{job_id}'); "
                        "j.enabled=True; j.save()"
                    ),
                ],
                container="nautobot",
            )

    def _poll_job_result(
        self,
        proxy: ServiceProxy,
        job_result_id: str,
        headers: dict[str, str],
        timeout: int,
    ) -> bool:
        deadline = time.monotonic() + timeout
        last_log_line = 0
        while time.monotonic() < deadline:
            try:
                result_data = json.loads(
                    proxy.request(f"api/extras/job-results/{job_result_id}/", headers=headers)
                )
            except Exception:
                time.sleep(self._poll_interval)
                continue

            last_log_line = self._stream_job_logs(proxy, job_result_id, headers, last_log_line)
            status_obj = result_data.get("status", {})
            status = (
                status_obj.get("value", "") if isinstance(status_obj, dict) else str(status_obj)
            ).lower()
            if status in self._COMPLETED_STATUSES:
                return True
            if status in self._FAILED_STATUSES:
                self._on_log(f"Job failed (status: {status})")
                return False
            if status not in self._PENDING_STATUSES:
                self._on_log(f"Unknown job status: {status}")
            time.sleep(self._poll_interval)

        self._on_log(f"Job timed out after {timeout}s")
        return False

    def _stream_job_logs(
        self,
        proxy: ServiceProxy,
        job_result_id: str,
        headers: dict[str, str],
        last_line: int,
    ) -> int:
        try:
            logs_data = json.loads(
                proxy.request(f"api/extras/job-results/{job_result_id}/logs/", headers=headers)
            )
        except Exception:
            return last_line
        if not isinstance(logs_data, list) or len(logs_data) <= last_line:
            return last_line
        for entry in logs_data[last_line:]:
            self._on_log(
                "[{}] [{}] {}".format(
                    entry.get("log_level", "").upper(),
                    entry.get("grouping", ""),
                    entry.get("message", ""),
                )
            )
        return len(logs_data)
