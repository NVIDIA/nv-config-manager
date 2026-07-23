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
"""Live-cluster integration test for the nautobot NATS metrics exporter.

When the observability path is enabled, the chart must deploy a
``prometheus-nats-exporter`` sidecar on the nautobot NATS pod and a matching
``PodMonitor`` so Prometheus can scrape the JetStream metrics that KEDA render
autoscaling consumes (``nats_consumer_num_pending``). This exercises the two
opt-in knobs added to the chart:

* ``nautobotNats.metrics.enabled`` -> the ``prom-exporter`` sidecar (with the
  ``prom-metrics`` port and ``-jsz=all`` so JetStream consumer stats are
  emitted), and
* the NATS ``PodMonitor`` (gated on that + ``monitoring.podMonitors.enabled``).

Both default to ``false`` in ``values.yaml``; the observability overlay
(``deploy/helm/values-observability.yaml``) flips
``nautobotNats.metrics.enabled`` on, and the installer flips
``monitoring.podMonitors.enabled`` on when ``observability_enabled`` is set.

Like ``test_probe_labels.py``, the module is gated behind ``OBSERVABILITY=true``
rather than probing the cluster: when the flag is off the module is skipped at
collection (no cluster calls); when it is on, a missing PodMonitor CRD / no NATS
PodMonitor / a NATS pod without the exporter sidecar is a *failure*, not a silent
skip — that means the observability install (or the chart wiring) is broken.
"""

from __future__ import annotations

import json
import os
import subprocess

import pytest

OBSERVABILITY_ENV = "OBSERVABILITY"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get(OBSERVABILITY_ENV, "").lower() != "true",
        reason=f"{OBSERVABILITY_ENV} != true — observability stack not deployed",
    ),
]

PODMONITOR_RESOURCE = "podmonitors.monitoring.coreos.com"

# Set by templates/monitoring.yaml on the NATS PodMonitor and by the
# nautobot-nats labels helper on the NATS pod/deployment.
NATS_COMPONENT_SELECTOR = "app.kubernetes.io/component=nautobot-nats"

# Contract asserted below — must match templates/nautobot.yaml (sidecar) and
# templates/monitoring.yaml (PodMonitor endpoint).
EXPORTER_CONTAINER = "prom-exporter"
EXPORTER_PORT = "prom-metrics"
EXPORTER_JSZ_ARG = "-jsz=all"
# Every arg the sidecar must carry for the metrics KEDA/PromQL rely on:
# -connz/-varz select the connection + server endpoints, -jsz=all emits the
# JetStream consumer series, and -prefix=nats yields the nats_* metric names.
EXPORTER_REQUIRED_ARGS = ("-connz", "-varz", EXPORTER_JSZ_ARG, "-prefix=nats")
# The exporter image, regardless of registry. Pinned upstream to
# docker.io/natsio/prometheus-nats-exporter, but air-gapped installs legitimately
# mirror it under another registry (e.g. nvcr.io/...), so match by repo suffix
# rather than an exact string.
EXPORTER_IMAGE_REPO = "prometheus-nats-exporter"


def _kubectl_get_json(*args: str) -> dict | None:
    """Run ``kubectl get ... -o json`` and parse stdout.

    Returns ``None`` when the command fails (e.g. the CRD isn't registered).
    The module is already gated on OBSERVABILITY=true, so callers treat ``None``
    as a failure (broken observability install), not a skip.
    """
    try:
        result = subprocess.run(
            # --request-timeout caps the API request, but it does NOT bound a hung
            # exec auth plugin or client-side setup; timeout= gives a hard process
            # deadline so the test fails fast instead of hanging until the pytest
            # timeout. Keep it above --request-timeout so the request-level timeout
            # can surface its own error first.
            ["kubectl", "get", *args, "-o", "json", "--request-timeout=15s"],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return None
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


@pytest.fixture(scope="module")
def nats_podmonitor(config_manager_namespace: str) -> dict:
    """Return the single nautobot NATS PodMonitor CR in the namespace.

    Reached only when OBSERVABILITY=true (module-level skipif), so a missing CRD
    or empty list is a real failure of the observability deploy / chart wiring.
    """
    data = _kubectl_get_json(
        PODMONITOR_RESOURCE, "-n", config_manager_namespace, "-l", NATS_COMPONENT_SELECTOR
    )
    assert data is not None, (
        f"{PODMONITOR_RESOURCE} CRD not registered though {OBSERVABILITY_ENV}=true — "
        "the observability stack (prometheus-operator CRDs) failed to install"
    )
    items = data.get("items", [])
    assert items, (
        f"No NATS PodMonitor ({NATS_COMPONENT_SELECTOR}) in namespace "
        f"'{config_manager_namespace}' though {OBSERVABILITY_ENV}=true — "
        "nautobotNats.metrics.enabled + monitoring.podMonitors.enabled rendered nothing"
    )
    assert len(items) == 1, (
        f"Expected exactly one NATS PodMonitor, found {len(items)}: "
        f"{[i.get('metadata', {}).get('name') for i in items]}"
    )
    return items[0]


def _match_labels(podmonitor: dict) -> dict:
    return podmonitor.get("spec", {}).get("selector", {}).get("matchLabels", {})


def test_nats_podmonitor_scrapes_exporter_port(nats_podmonitor: dict) -> None:
    """The NATS PodMonitor must scrape the exporter's ``prom-metrics`` port.

    Guards against the PodMonitor pointing at a port the sidecar doesn't expose
    (which would silently yield zero NATS metrics in Prometheus).
    """
    endpoints = nats_podmonitor.get("spec", {}).get("podMetricsEndpoints", [])
    ports = [ep.get("port") for ep in endpoints]
    assert EXPORTER_PORT in ports, (
        f"NATS PodMonitor does not scrape port '{EXPORTER_PORT}'; "
        f"podMetricsEndpoints ports = {ports}"
    )


def test_nats_podmonitor_selects_nats_pod(nats_podmonitor: dict) -> None:
    """The PodMonitor selector must target the NATS pod (``*-nats``)."""
    labels = _match_labels(nats_podmonitor)
    name = labels.get("app.kubernetes.io/name", "")
    assert name.endswith("-nats"), (
        f"NATS PodMonitor selector.matchLabels app.kubernetes.io/name={name!r} "
        "does not look like the NATS pod (expected a '*-nats' value)"
    )


def test_nats_podmonitor_excludes_nats_box(nats_podmonitor: dict) -> None:
    """The selector must exclude the nats-box pod, which shares the name label.

    nats-box carries an ``app.kubernetes.io/component`` label the nats server
    pod does not; without a ``DoesNotExist`` exclusion the PodMonitor would also
    select nats-box (which has no ``prom-metrics`` port).
    """
    expressions = nats_podmonitor.get("spec", {}).get("selector", {}).get("matchExpressions", [])
    excludes_component = any(
        e.get("key") == "app.kubernetes.io/component" and e.get("operator") == "DoesNotExist"
        for e in expressions
    )
    assert excludes_component, (
        "NATS PodMonitor selector should exclude pods carrying "
        "app.kubernetes.io/component (to skip nats-box); matchExpressions="
        f"{expressions}"
    )


@pytest.fixture(scope="module")
def nats_deployment(config_manager_namespace: str, nats_podmonitor: dict) -> dict:
    """Return the nautobot NATS server Deployment.

    The chart names the PodMonitor and the NATS server Deployment identically
    (both ``$natsName``), so we resolve the Deployment by the PodMonitor's name
    rather than reconstructing a label selector — this pins the assertion to the
    server Deployment and sidesteps the nats-box pod sharing the name label.
    """
    name = nats_podmonitor.get("metadata", {}).get("name")
    assert name, "NATS PodMonitor has no metadata.name"
    data = _kubectl_get_json("deployment", name, "-n", config_manager_namespace)
    assert data is not None, (
        f"NATS server Deployment '{name}' not found in '{config_manager_namespace}' "
        f"though {OBSERVABILITY_ENV}=true"
    )
    return data


def _exporter_container(deployment: dict) -> dict | None:
    containers = (
        deployment.get("spec", {}).get("template", {}).get("spec", {}).get("containers", [])
    )
    for container in containers:
        if container.get("name") == EXPORTER_CONTAINER:
            return container
    return None


def test_nats_deployment_has_exporter_sidecar(nats_deployment: dict) -> None:
    """The NATS server Deployment must carry the fully-configured exporter sidecar.

    Asserts the container exists, runs the prometheus-nats-exporter image (any
    registry, so an air-gapped mirror is accepted), exposes the ``prom-metrics``
    port the PodMonitor scrapes, and carries every required arg — ``-connz``,
    ``-varz``, ``-jsz=all`` (JetStream ``nats_consumer_num_pending`` for KEDA),
    and ``-prefix=nats`` (so metrics are named ``nats_*``).
    """
    name = nats_deployment.get("metadata", {}).get("name", "<unknown>")
    container = _exporter_container(nats_deployment)
    assert container is not None, f"{name}: missing '{EXPORTER_CONTAINER}' sidecar container"

    problems: list[str] = []

    # Image: match by repo suffix so any registry (incl. air-gapped mirror) passes,
    # but a wrong image (e.g. a copy-paste of another sidecar) is rejected.
    image = container.get("image", "")
    repo = image.rsplit(":", 1)[0]  # strip tag; ignore version for the contract
    if not repo.endswith(EXPORTER_IMAGE_REPO):
        problems.append(
            f"'{EXPORTER_CONTAINER}' image {image!r} is not a '{EXPORTER_IMAGE_REPO}' image"
        )

    port_names = [p.get("name") for p in container.get("ports", [])]
    if EXPORTER_PORT not in port_names:
        problems.append(
            f"'{EXPORTER_CONTAINER}' does not expose port '{EXPORTER_PORT}' (ports={port_names})"
        )

    args = container.get("args", [])
    missing_args = [arg for arg in EXPORTER_REQUIRED_ARGS if arg not in args]
    if missing_args:
        problems.append(
            f"'{EXPORTER_CONTAINER}' missing required arg(s) {missing_args} "
            f"(metrics KEDA/PromQL rely on would be absent or misnamed); args={args}"
        )

    assert not problems, f"{name}: NATS exporter sidecar misconfigured:\n" + "\n".join(problems)
