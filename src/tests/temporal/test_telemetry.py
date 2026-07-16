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
"""Tests for the Temporal OpenTelemetry bootstrap."""

from unittest import mock

import pytest

from nv_config_manager.temporal import telemetry

OTLP_ENV = "OTEL_EXPORTER_OTLP_ENDPOINT"
SERVICE_ENV = "OTEL_SERVICE_NAME"
ENVIRONMENT_ENV = "ENVIRONMENT"


@pytest.fixture(autouse=True)
def _reset_runtime():
    """Reset the module-level cached runtime around every test."""
    telemetry._runtime = None
    yield
    telemetry._runtime = None


@pytest.fixture
def _clean_env(monkeypatch):
    """Remove telemetry env vars so each test controls them explicitly."""
    for name in (OTLP_ENV, SERVICE_ENV, ENVIRONMENT_ENV):
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.fixture
def otel_mocks():
    """Patch the OTel/Temporal constructors used by setup_telemetry()."""
    with (
        mock.patch.object(telemetry, "TracerProvider") as provider_cls,
        mock.patch.object(telemetry, "BatchSpanProcessor") as span_processor_cls,
        mock.patch.object(telemetry, "OTLPSpanExporter") as exporter_cls,
        mock.patch.object(telemetry, "Resource") as resource_cls,
        # Patch the real function on opentelemetry.trace (not the whole module) so a
        # wrong attribute name fails at patch time instead of silently auto-mocking.
        mock.patch.object(telemetry.trace, "set_tracer_provider") as set_tracer_provider,
        mock.patch.object(telemetry, "Runtime") as runtime_cls,
        mock.patch.object(telemetry, "TelemetryConfig") as telemetry_config_cls,
        mock.patch.object(telemetry, "OpenTelemetryConfig") as otel_config_cls,
    ):
        yield {
            "provider_cls": provider_cls,
            "span_processor_cls": span_processor_cls,
            "exporter_cls": exporter_cls,
            "resource_cls": resource_cls,
            "set_tracer_provider": set_tracer_provider,
            "runtime_cls": runtime_cls,
            "telemetry_config_cls": telemetry_config_cls,
            "otel_config_cls": otel_config_cls,
        }


class TestSetupTelemetryDisabled:
    """setup_telemetry() must no-op when no endpoint is configured."""

    def test_no_endpoint_returns_plain_runtime(self, _clean_env, otel_mocks):
        """Missing endpoint skips exporter wiring and returns a plain Runtime."""
        result = telemetry.setup_telemetry("svc")

        otel_mocks["exporter_cls"].assert_not_called()
        otel_mocks["provider_cls"].assert_not_called()
        otel_mocks["set_tracer_provider"].assert_not_called()
        otel_mocks["otel_config_cls"].assert_not_called()
        otel_mocks["telemetry_config_cls"].assert_called_once_with()
        assert result is otel_mocks["runtime_cls"].return_value
        assert telemetry._runtime is result

    @pytest.mark.parametrize("value", ["", "   ", "\t\n"])
    def test_blank_endpoint_is_disabled(self, _clean_env, otel_mocks, value):
        """Empty or whitespace endpoint is treated as disabled."""
        _clean_env.setenv(OTLP_ENV, value)

        telemetry.setup_telemetry("svc")

        otel_mocks["exporter_cls"].assert_not_called()
        otel_mocks["otel_config_cls"].assert_not_called()


class TestSetupTelemetryEnabled:
    """setup_telemetry() wires exporters when an endpoint is configured."""

    def test_endpoint_configures_tracing_and_metrics(self, _clean_env, otel_mocks):
        """A configured endpoint builds the span exporter and metrics runtime."""
        _clean_env.setenv(OTLP_ENV, "http://collector:4317")

        result = telemetry.setup_telemetry("svc")

        otel_mocks["exporter_cls"].assert_called_once_with(endpoint="http://collector:4317")
        otel_mocks["provider_cls"].assert_called_once_with(
            resource=otel_mocks["resource_cls"].create.return_value
        )
        otel_mocks["provider_cls"].return_value.add_span_processor.assert_called_once_with(
            otel_mocks["span_processor_cls"].return_value
        )
        otel_mocks["set_tracer_provider"].assert_called_once_with(
            otel_mocks["provider_cls"].return_value
        )
        otel_mocks["otel_config_cls"].assert_called_once_with(url="http://collector:4317")
        assert result is otel_mocks["runtime_cls"].return_value
        assert telemetry._runtime is result

    def test_endpoint_is_stripped(self, _clean_env, otel_mocks):
        """Surrounding whitespace on the endpoint is trimmed before use."""
        _clean_env.setenv(OTLP_ENV, "  http://collector:4317  ")

        telemetry.setup_telemetry("svc")

        otel_mocks["exporter_cls"].assert_called_once_with(endpoint="http://collector:4317")

    def test_service_name_argument_used_as_default(self, _clean_env, otel_mocks):
        """The service_name argument seeds the service.name resource attribute."""
        _clean_env.setenv(OTLP_ENV, "http://collector:4317")

        telemetry.setup_telemetry("worker-svc")

        attrs = otel_mocks["resource_cls"].create.call_args.args[0]
        assert attrs["service.name"] == "worker-svc"
        assert attrs["deployment.environment"] == "unknown"

    def test_env_overrides_service_name_and_environment(self, _clean_env, otel_mocks):
        """OTEL_SERVICE_NAME and ENVIRONMENT override defaults."""
        _clean_env.setenv(OTLP_ENV, "http://collector:4317")
        _clean_env.setenv(SERVICE_ENV, "override-svc")
        _clean_env.setenv(ENVIRONMENT_ENV, "staging")

        telemetry.setup_telemetry("worker-svc")

        attrs = otel_mocks["resource_cls"].create.call_args.args[0]
        assert attrs["service.name"] == "override-svc"
        assert attrs["deployment.environment"] == "staging"


class TestGetRuntime:
    """get_runtime() returns the cached runtime or a safe fallback."""

    def test_returns_cached_runtime_after_setup(self, _clean_env, otel_mocks):
        """get_runtime() returns the runtime built by setup_telemetry()."""
        created = telemetry.setup_telemetry("svc")
        assert telemetry.get_runtime() is created

    def test_fallback_runtime_when_not_initialized(self, otel_mocks):
        """get_runtime() builds a no-telemetry Runtime when setup was skipped."""
        telemetry._runtime = None

        result = telemetry.get_runtime()

        otel_mocks["telemetry_config_cls"].assert_called_once_with()
        assert result is otel_mocks["runtime_cls"].return_value
