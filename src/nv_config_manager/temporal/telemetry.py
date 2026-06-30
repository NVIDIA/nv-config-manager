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
"""OpenTelemetry bootstrap shared by the Temporal worker and API.

Call setup_telemetry() once at process startup. When an OTLP endpoint is
configured (OTEL_EXPORTER_OTLP_ENDPOINT, injected by the Helm chart only when
temporal.observability.enabled), it:
  1. Configures the global Python OTel TracerProvider to export spans via
     OTLP/gRPC to the configured collector (in-cluster Grafana Alloy by
     default, or a managed/external collector when otlpEndpoint is set).
  2. Returns a Temporal Runtime whose SDK core pushes built-in Temporal
     metrics (workflow_completed, activity_execution_latency, etc.) via
     OTLP to the same endpoint.

When no endpoint is configured, observability is disabled: no exporters are
created and a plain Runtime is returned, so deployments without a collector
do not attempt to export to a nonexistent endpoint.

After setup_telemetry() returns, call get_runtime() to retrieve the
Runtime for passing to Client.connect(runtime=...).
"""

import os

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from temporalio.runtime import OpenTelemetryConfig, Runtime, TelemetryConfig

_runtime: Runtime | None = None


def setup_telemetry(service_name: str) -> Runtime:
    """Initialize OTel tracing and build a Temporal Runtime with OTel metrics.

    Reads:
      OTEL_EXPORTER_OTLP_ENDPOINT  — OTLP gRPC endpoint; observability is
                                     disabled (no exporters) when unset/empty
      OTEL_SERVICE_NAME            — overrides service_name argument when set
      ENVIRONMENT                  — used as deployment.environment resource attribute
    """
    global _runtime
    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not otlp_endpoint:
        _runtime = Runtime(telemetry=TelemetryConfig())
        return _runtime

    resolved_name = os.getenv("OTEL_SERVICE_NAME", service_name)
    resource = Resource.create(
        {
            "service.name": resolved_name,
            "deployment.environment": os.getenv("ENVIRONMENT", "unknown"),
        }
    )
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=otlp_endpoint)))
    trace.set_tracer_provider(provider)

    _runtime = Runtime(telemetry=TelemetryConfig(metrics=OpenTelemetryConfig(url=otlp_endpoint)))
    return _runtime


def get_runtime() -> Runtime:
    """Return the process-level Temporal Runtime initialized by setup_telemetry().

    Falls back to a no-telemetry Runtime when setup_telemetry() was not called
    (e.g. in unit tests that don't boot the full stack).
    """
    if _runtime is not None:
        return _runtime
    return Runtime(telemetry=TelemetryConfig())
