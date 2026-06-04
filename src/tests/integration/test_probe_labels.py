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
"""Live-cluster integration test for probe SLO customLabels.

Every blackbox ``Probe`` the chart renders must carry ``global.customLabels``
under ``spec.targets.staticConfig.labels`` so Prometheus attaches them to every
probe sample. The Probe CR's ``metadata.labels`` are NOT propagated onto
samples by Prometheus Operator, so ``staticConfig.labels`` is the only way to
surface labels like ``include_in_slo`` on probe metrics (see the
``nv-config-manager.probeStaticConfigLabels`` helper in
``deploy/helm/templates/_helpers.tpl``).

These assertions only apply when the observability stack is deployed — i.e. the
prometheus-operator CRDs are registered and ``monitoring.probes`` is enabled.
The kind integration job turns that on via its ``observability`` workflow input,
which flips ``infrastructure.monitoring.observability_enabled``, layers
``deploy/helm/values-observability.yaml`` (where the customLabels are set), and
exports ``OBSERVABILITY=true`` to the test step.

Following the pattern in ``test_diagnostics.py`` (Jira), the whole module is
gated behind a ``skipif`` keyed on that ``OBSERVABILITY`` env var rather than
probing the cluster: when the flag is off the module is skipped at collection
(no cluster calls); when it is on the test runs and a missing Probe CRD / no
Probe CRs is a *failure*, not a silent skip — that means the observability
install is broken.
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

# Must match global.customLabels in deploy/helm/values-observability.yaml.
EXPECTED_PROBE_LABELS = {"include_in_slo": "true"}

PROBE_RESOURCE = "probes.monitoring.coreos.com"


def _kubectl_get_json(*args: str) -> dict | None:
    """Run ``kubectl get ... -o json`` and parse stdout.

    Returns ``None`` when the command fails (e.g. the CRD isn't registered).
    The module is already gated on OBSERVABILITY=true, so the fixture treats
    ``None`` as a failure (broken observability install), not a skip.
    """
    result = subprocess.run(
        # --request-timeout caps the wait so an unreachable/stale API server
        # fails fast instead of hanging until the pytest timeout.
        ["kubectl", "get", *args, "-o", "json", "--request-timeout=15s"],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


@pytest.fixture(scope="module")
def probes(config_manager_namespace: str) -> list[dict]:
    """Return the Probe CRs in the namespace.

    Reached only when OBSERVABILITY=true (module-level skipif), so a missing
    CRD or empty list is a real failure of the observability deploy.
    """
    data = _kubectl_get_json(PROBE_RESOURCE, "-n", config_manager_namespace)
    assert data is not None, (
        f"{PROBE_RESOURCE} CRD not registered though {OBSERVABILITY_ENV}=true — "
        "the observability stack (prometheus-operator CRDs) failed to install"
    )
    items = data.get("items", [])
    assert items, (
        f"No {PROBE_RESOURCE} in namespace '{config_manager_namespace}' though "
        f"{OBSERVABILITY_ENV}=true — monitoring.probes rendered no Probe CRs"
    )
    return items


def _static_config_labels(probe: dict) -> dict | None:
    return probe.get("spec", {}).get("targets", {}).get("staticConfig", {}).get("labels")


def test_probes_carry_static_config_labels(probes: list[dict]) -> None:
    """Every Probe must surface global.customLabels under staticConfig.labels."""
    problems: list[str] = []
    for probe in probes:
        name = probe.get("metadata", {}).get("name", "<unknown>")
        labels = _static_config_labels(probe)
        if labels is None:
            problems.append(f"{name}: missing spec.targets.staticConfig.labels")
            continue
        for key, value in EXPECTED_PROBE_LABELS.items():
            if labels.get(key) != value:
                problems.append(f"{name}: expected {key}={value!r}, got {labels.get(key)!r}")

    assert not problems, "Probe staticConfig labels missing/incorrect:\n" + "\n".join(problems)
