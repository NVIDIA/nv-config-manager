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
"""Temporal OpenTelemetry bootstrap (SDK Runtime + built-in metrics)."""

import os

from temporalio.runtime import OpenTelemetryConfig, Runtime, TelemetryConfig

from nv_config_manager.common.telemetry import setup_tracing

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
    setup_tracing(service_name)
    if not otlp_endpoint:
        _runtime = Runtime(telemetry=TelemetryConfig())
        return _runtime

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
