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
"""Live-cluster integration test for the Envoy Gateway proxy PodMonitor.

Envoy Gateway exposes Prometheus metrics on each managed proxy pod's named
``metrics`` port at ``/stats/prometheus`` but ships no PodMonitor, so the
bundled Alloy stack (which discovers PodMonitor CRs, not ``prometheus.io/scrape``
annotations) would collect nothing. The installer therefore applies a single
cluster-scoped PodMonitor in the Envoy Gateway namespace so one CR covers every
per-release gateway proxy. It is created only when the installer both installs
Envoy Gateway AND the observability stack is enabled (see
``Deployer._install_crds``).

The kind integration job turns observability on via its ``observability``
workflow input, which flips ``infrastructure.monitoring.observability_enabled``
and exports ``OBSERVABILITY=true`` to the test step. ``make kind-up`` always
passes ``--install-envoy-gateway``, so both gate conditions hold on that run.

Following the pattern in ``test_probe_labels.py``, the whole module is gated
behind a ``skipif`` keyed on that ``OBSERVABILITY`` env var: when the flag is
off the module is skipped at collection (no cluster calls); when it is on, a
missing PodMonitor CRD / absent PodMonitor is a *failure*, not a silent skip —
that means the installer's envoy-gateway + observability path is broken.
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

# Must match Deployer._ENVOY_GATEWAY_NAMESPACE / _ENVOY_PROXY_PODMONITOR_NAME and
# the manifest built by Deployer._envoy_proxy_podmonitor_manifest().
ENVOY_GATEWAY_NAMESPACE = "envoy-gateway-system"
PODMONITOR_NAME = "envoy-proxy"
PODMONITOR_RESOURCE = "podmonitors.monitoring.coreos.com"

# Envoy Gateway labels every managed proxy pod with these (data-plane proxies).
EXPECTED_PROXY_SELECTOR = {
    "app.kubernetes.io/component": "proxy",
    "app.kubernetes.io/managed-by": "envoy-gateway",
}


def _kubectl_get_json(*args: str) -> dict | None:
    """Run ``kubectl get ... -o json`` and parse stdout.

    Returns ``None`` when the command fails (e.g. the CRD isn't registered or
    the PodMonitor is absent). The module is already gated on OBSERVABILITY=true,
    so the fixture treats ``None`` as a failure (broken install), not a skip.
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
def envoy_proxy_podmonitor() -> dict:
    """Return the installer-managed Envoy proxy PodMonitor.

    Reached only when OBSERVABILITY=true (module-level skipif), so a missing CRD
    or absent PodMonitor is a real failure of the installer's envoy-gateway +
    observability path.
    """
    data = _kubectl_get_json(PODMONITOR_RESOURCE, PODMONITOR_NAME, "-n", ENVOY_GATEWAY_NAMESPACE)
    assert data is not None, (
        f"{PODMONITOR_RESOURCE}/{PODMONITOR_NAME} not found in "
        f"'{ENVOY_GATEWAY_NAMESPACE}' though {OBSERVABILITY_ENV}=true — the installer "
        "should apply it when Envoy Gateway and observability are both installed "
        "(Deployer._install_crds)"
    )
    return data


def test_envoy_proxy_podmonitor_scrapes_gateway_proxies(envoy_proxy_podmonitor: dict) -> None:
    """The PodMonitor must select every gateway proxy and scrape its metrics port."""
    spec = envoy_proxy_podmonitor.get("spec", {})

    # Cluster-scoped: one PodMonitor covers proxies in any namespace, so a single
    # CR scrapes every per-release gateway rather than one PodMonitor per release.
    assert spec.get("namespaceSelector") == {"any": True}, (
        f"expected namespaceSelector any:true, got {spec.get('namespaceSelector')!r}"
    )

    assert spec.get("selector", {}).get("matchLabels") == EXPECTED_PROXY_SELECTOR, (
        f"unexpected proxy selector: {spec.get('selector')!r}"
    )

    endpoints = spec.get("podMetricsEndpoints", [])
    assert any(
        endpoint.get("port") == "metrics" and endpoint.get("path") == "/stats/prometheus"
        for endpoint in endpoints
    ), f"no metrics /stats/prometheus endpoint in podMetricsEndpoints: {endpoints!r}"
