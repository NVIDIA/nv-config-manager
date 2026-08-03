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
"""Live-cluster integration test for KEDA render-consumer autoscaling.

``test_nats_exporter.py`` proves the metric is *produced* (exporter sidecar +
PodMonitor). This module proves it is *consumed*, closing the chain:
exporter -> PodMonitor -> Alloy -> Prometheus -> KEDA trigger -> HPA.

Why this is worth a live test: ``renderService.autoscaling.enabled`` defaults to
``false`` and nothing installs KEDA outside the observability path, so before
this the ScaledObject template was never rendered against real CRDs, let alone
reconciled. Two defects in particular could not be caught anywhere else:

* an empty ``serverAddress`` (the pre-existing default), which KEDA cannot query
  at all, and
* a trigger query whose labels don't match the series the exporter emits, which
  silently scales on nothing.

The assertions are deliberately layered because they buy different things, and
one of them is weaker than it looks:

* ``Ready=True`` means KEDA validated the ScaledObject and created its HPA. It
  does *not* mean the query returned data.
* KEDA's external-metrics endpoint returning a value means KEDA really reached
  Prometheus and executed the query without error.
* Neither of the above catches a label mismatch, because
  ``ignoreNullValues: "true"`` (values.yaml) makes a query matching *no* series
  resolve to 0 rather than fail. So the query is also run directly against
  Prometheus and required to match a live series.

Gated behind ``OBSERVABILITY=true`` like the rest of the observability suite:
when the flag is off the module is skipped at collection, and when it is on a
missing CRD or unready ScaledObject is a failure, not a silent skip.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from urllib.parse import quote

import pytest

OBSERVABILITY_ENV = "OBSERVABILITY"

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        os.environ.get(OBSERVABILITY_ENV, "").lower() != "true",
        reason=f"{OBSERVABILITY_ENV} != true — observability stack not deployed",
    ),
    # KEDA's default pollingInterval is 30s and the consumers must register their
    # JetStream durables first, so the waits below can legitimately take a couple
    # of minutes under CI load.
    pytest.mark.timeout(420),
]

SCALEDOBJECT_RESOURCE = "scaledobjects.keda.sh"

# templates/render-service-scaledobject.yaml names these
# <release>-render-consumer-<type>; only device and nautobot have entries under
# renderService.autoscaling.consumers in values.yaml (the template also iterates
# "template", which is skipped while unconfigured).
EXPECTED_CONSUMER_TYPES = ("device", "nautobot")
SCALEDOBJECT_NAME_SUFFIX = "-render-consumer-"

# Set by values-observability.yaml (prometheus.server.fullnameOverride) and
# resolved into the trigger by the ScaledObject template.
PROMETHEUS_SERVICE = "prometheus-server"
PROMETHEUS_PORT = 9090

# The series the exporter emits and the labels the trigger must filter on.
TRIGGER_METRIC = "nats_consumer_num_pending"
LEADER_LABEL = 'is_consumer_leader="true"'

# KEDA names the metric for a ScaledObject's first (index 0) trigger s0-<type>.
KEDA_EXTERNAL_METRIC = "s0-prometheus"

READY_TIMEOUT_SECONDS = 240
SERIES_TIMEOUT_SECONDS = 180
POLL_INTERVAL_SECONDS = 10


def _kubectl_json(*args: str) -> dict | None:
    """Run ``kubectl ... -o json`` and parse stdout, or return ``None``.

    Mirrors ``test_nats_exporter._kubectl_get_json``: the module is already gated
    on OBSERVABILITY=true, so callers treat ``None`` as a broken install rather
    than a reason to skip.
    """
    try:
        result = subprocess.run(
            [*args, "-o", "json", "--request-timeout=15s"],
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


def _kubectl_raw(path: str) -> dict | None:
    """GET an API-server path with ``kubectl get --raw`` and parse the JSON.

    Used for the aggregated external-metrics API and to reach Prometheus through
    the API server's service proxy, which avoids a port-forward (racy) or an
    extra curl pod (needs an image pull).
    """
    try:
        result = subprocess.run(
            ["kubectl", "get", "--raw", path, "--request-timeout=15s"],
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


def _prometheus_query(namespace: str, query: str) -> dict | None:
    """Run an instant PromQL query via the API server's service proxy."""
    path = (
        f"/api/v1/namespaces/{namespace}/services/"
        f"{PROMETHEUS_SERVICE}:{PROMETHEUS_PORT}/proxy/api/v1/query"
        f"?query={quote(query)}"
    )
    return _kubectl_raw(path)


def _conditions(scaled_object: dict) -> dict[str, str]:
    return {
        condition.get("type", ""): condition.get("status", "")
        for condition in scaled_object.get("status", {}).get("conditions", [])
    }


@pytest.fixture(scope="module")
def scaled_objects(config_manager_namespace: str) -> dict[str, dict]:
    """Return the render-consumer ScaledObjects keyed by consumer type."""
    data = _kubectl_json("kubectl", "get", SCALEDOBJECT_RESOURCE, "-n", config_manager_namespace)
    assert data is not None, (
        f"{SCALEDOBJECT_RESOURCE} CRD not registered though {OBSERVABILITY_ENV}=true — "
        "the KEDA release (installed by Deployer._install_crds when "
        "observability_enabled is set) failed to install"
    )
    items = data.get("items", [])
    assert items, (
        f"No ScaledObjects in namespace '{config_manager_namespace}' though "
        f"{OBSERVABILITY_ENV}=true — renderService.autoscaling.enabled "
        "(values-observability.yaml) rendered nothing"
    )
    by_type: dict[str, dict] = {}
    for item in items:
        name = item.get("metadata", {}).get("name", "")
        if SCALEDOBJECT_NAME_SUFFIX in name:
            by_type[name.rsplit(SCALEDOBJECT_NAME_SUFFIX, 1)[1]] = item
    return by_type


def test_scaledobjects_exist_for_each_configured_consumer(
    scaled_objects: dict[str, dict],
) -> None:
    """Every consumer configured for autoscaling must get a ScaledObject.

    Catches the template's consumer loop silently skipping an entry (e.g. a
    renamed key under renderService.autoscaling.consumers), which would leave
    that consumer pinned at its static replica count with no indication.
    """
    missing = [t for t in EXPECTED_CONSUMER_TYPES if t not in scaled_objects]
    assert not missing, (
        f"No ScaledObject for consumer type(s) {missing}; found {sorted(scaled_objects)}"
    )


@pytest.mark.parametrize("consumer_type", EXPECTED_CONSUMER_TYPES)
def test_trigger_prometheus_address_is_resolved(
    scaled_objects: dict[str, dict], consumer_type: str, config_manager_namespace: str
) -> None:
    """The trigger must carry a usable Prometheus address.

    ``renderService.autoscaling.prometheus.serverAddress`` defaults to ``""``, so
    before the template's fallback an enabled ScaledObject shipped with no
    address and KEDA could never query it. Asserting the resolved value (rather
    than just non-empty) also pins the FQDN form, which matters because KEDA
    resolves it from its own namespace, not the release's.
    """
    triggers = scaled_objects[consumer_type].get("spec", {}).get("triggers", [])
    addresses = [t.get("metadata", {}).get("serverAddress", "") for t in triggers]
    expected = f"http://{PROMETHEUS_SERVICE}.{config_manager_namespace}.svc.cluster.local:{PROMETHEUS_PORT}"
    assert expected in addresses, (
        f"{consumer_type} ScaledObject trigger serverAddress = {addresses}, "
        f"expected {expected!r}. An empty value means KEDA has nothing to query; "
        "a short name would not resolve from KEDA's own namespace."
    )


@pytest.mark.parametrize("consumer_type", EXPECTED_CONSUMER_TYPES)
def test_trigger_query_filters_the_exporter_series(
    scaled_objects: dict[str, dict], consumer_type: str
) -> None:
    """The trigger query must select the exporter's metric for this consumer.

    A cheap shape check (no cluster round-trip) for the parts a template edit is
    most likely to break: the metric name, the leader filter that prevents
    double-counting under HA, and the ``{queue}-{type}`` consumer name that ties
    the query to this specific ScaledObject.
    """
    triggers = scaled_objects[consumer_type].get("spec", {}).get("triggers", [])
    queries = [t.get("metadata", {}).get("query", "") for t in triggers]
    assert queries, f"{consumer_type} ScaledObject has no triggers"
    query = queries[0]
    assert TRIGGER_METRIC in query, (
        f"{consumer_type} trigger query does not use {TRIGGER_METRIC}: {query}"
    )
    assert LEADER_LABEL in query, (
        f"{consumer_type} trigger query is missing {LEADER_LABEL}, so replicas of "
        f"the same consumer would be double-counted: {query}"
    )
    assert f'-{consumer_type}"' in query, (
        f"{consumer_type} trigger query does not filter on a consumer_name ending "
        f"in '-{consumer_type}': {query}"
    )


@pytest.mark.parametrize("consumer_type", EXPECTED_CONSUMER_TYPES)
def test_scaledobject_becomes_ready(
    scaled_objects: dict[str, dict], consumer_type: str, config_manager_namespace: str
) -> None:
    """KEDA must accept the ScaledObject and create its HPA.

    ``Ready=True`` is KEDA's signal that the spec validated and the underlying
    HPA exists — it catches a malformed trigger, an unknown scaler type, or a
    scale target that doesn't resolve. It does not imply the query returned
    data; that is covered by the two tests below.
    """
    name = scaled_objects[consumer_type].get("metadata", {}).get("name", "")
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    conditions: dict[str, str] = {}
    while time.monotonic() < deadline:
        current = _kubectl_json(
            "kubectl", "get", SCALEDOBJECT_RESOURCE, name, "-n", config_manager_namespace
        )
        if current is not None:
            conditions = _conditions(current)
            if conditions.get("Ready") == "True":
                return
        time.sleep(POLL_INTERVAL_SECONDS)
    pytest.fail(
        f"ScaledObject '{name}' did not reach Ready=True within "
        f"{READY_TIMEOUT_SECONDS}s; conditions = {conditions or '<none reported>'}"
    )


@pytest.mark.parametrize("consumer_type", EXPECTED_CONSUMER_TYPES)
def test_keda_serves_the_trigger_metric(
    scaled_objects: dict[str, dict], consumer_type: str, config_manager_namespace: str
) -> None:
    """KEDA must be able to execute the query and serve a metric value.

    Reading KEDA's aggregated external-metrics API makes it run the trigger on
    demand, so this fails if the resolved ``serverAddress`` is unreachable, the
    PromQL is malformed, or the metrics-apiserver isn't registered. Note it does
    *not* fail on a query that matches nothing (ignoreNullValues yields 0) —
    that gap is what the next test covers.
    """
    name = scaled_objects[consumer_type].get("metadata", {}).get("name", "")
    path = (
        f"/apis/external.metrics.k8s.io/v1beta1/namespaces/{config_manager_namespace}/"
        f"{KEDA_EXTERNAL_METRIC}?labelSelector=scaledobject.keda.sh%2Fname%3D{name}"
    )
    deadline = time.monotonic() + READY_TIMEOUT_SECONDS
    payload: dict | None = None
    while time.monotonic() < deadline:
        payload = _kubectl_raw(path)
        if payload is not None and payload.get("items"):
            return
        time.sleep(POLL_INTERVAL_SECONDS)
    pytest.fail(
        f"KEDA served no external metric '{KEDA_EXTERNAL_METRIC}' for ScaledObject "
        f"'{name}' within {READY_TIMEOUT_SECONDS}s (response: {payload}). KEDA could "
        "not query Prometheus at the trigger's serverAddress, or its "
        "metrics-apiserver is not registered."
    )


@pytest.mark.parametrize("consumer_type", EXPECTED_CONSUMER_TYPES)
def test_trigger_query_matches_a_live_series(
    scaled_objects: dict[str, dict], consumer_type: str, config_manager_namespace: str
) -> None:
    """The rendered query must match a real series in Prometheus.

    This is the assertion that catches a label mismatch — a wrong
    ``stream_name``, a queue/consumer naming change, or a PodMonitor that drops
    a label the query filters on. KEDA itself cannot catch those: with
    ``ignoreNullValues: "true"`` a query matching no series resolves to 0, so
    autoscaling would look healthy while never scaling. Running the exact
    rendered PromQL and requiring a non-empty result closes that hole.

    Polled, because the render consumers must register their JetStream durables
    and Prometheus must scrape them before the series exists.
    """
    query = (
        scaled_objects[consumer_type]
        .get("spec", {})
        .get("triggers", [{}])[0]
        .get("metadata", {})
        .get("query", "")
    )
    assert query, f"{consumer_type} ScaledObject trigger has no query"
    deadline = time.monotonic() + SERIES_TIMEOUT_SECONDS
    payload: dict | None = None
    while time.monotonic() < deadline:
        payload = _prometheus_query(config_manager_namespace, query)
        if payload is not None and payload.get("data", {}).get("result"):
            return
        time.sleep(POLL_INTERVAL_SECONDS)
    pytest.fail(
        f"The {consumer_type} trigger query matched no series in Prometheus within "
        f"{SERIES_TIMEOUT_SECONDS}s.\n  query: {query}\n  response: {payload}\n"
        "Either the exporter is not emitting nats_consumer_num_pending for this "
        "consumer, or the query's labels (stream_name / consumer_name / "
        "is_consumer_leader) no longer match what it emits — in which case KEDA "
        "would silently scale on 0 forever."
    )
