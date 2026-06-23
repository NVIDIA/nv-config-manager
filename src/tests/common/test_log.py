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
"""Tests for structured logging trace/span correlation."""

import logging
import sys
from unittest import mock

import pytest

from nv_config_manager.common import log

# W3C trace-context example IDs.
_TRACE_ID = 0x4BF92F3577B34DA6A3CE929D0E0E4736
_SPAN_ID = 0x00F067AA0BA902B7
_TRACE_ID_HEX = "4bf92f3577b34da6a3ce929d0e0e4736"
_SPAN_ID_HEX = "00f067aa0ba902b7"


def _mock_span(*, trace_id: int, span_id: int, is_valid: bool):
    """Build a mock OTel span with the given span context."""
    span = mock.MagicMock()
    ctx = span.get_span_context.return_value
    ctx.is_valid = is_valid
    ctx.trace_id = trace_id
    ctx.span_id = span_id
    return span


class TestOtelTraceFields:
    """_otel_trace_fields() reads the active span context."""

    def test_valid_span_returns_zero_padded_hex(self):
        """A valid span yields 32-char trace_id and 16-char span_id."""
        span = _mock_span(trace_id=_TRACE_ID, span_id=_SPAN_ID, is_valid=True)
        with mock.patch("opentelemetry.trace.get_current_span", return_value=span):
            assert log._otel_trace_fields() == {
                "trace_id": _TRACE_ID_HEX,
                "span_id": _SPAN_ID_HEX,
            }

    def test_small_ids_are_left_padded(self):
        """Small integer IDs are padded to the full hex width."""
        span = _mock_span(trace_id=0x1, span_id=0x1, is_valid=True)
        with mock.patch("opentelemetry.trace.get_current_span", return_value=span):
            fields = log._otel_trace_fields()
        assert fields["trace_id"] == "0" * 31 + "1"
        assert fields["span_id"] == "0" * 15 + "1"

    def test_invalid_span_context_returns_empty(self):
        """No active/valid span yields no fields."""
        span = _mock_span(trace_id=0, span_id=0, is_valid=False)
        with mock.patch("opentelemetry.trace.get_current_span", return_value=span):
            assert log._otel_trace_fields() == {}

    def test_missing_opentelemetry_returns_empty(self):
        """When opentelemetry is not importable, no fields are emitted."""
        with mock.patch.dict(sys.modules, {"opentelemetry": None}):
            assert log._otel_trace_fields() == {}


@pytest.fixture
def _restore_logging():
    """Restore the global record factory and config flag after the test."""
    original_factory = logging.getLogRecordFactory()
    original_configured = log._logging_configured
    yield
    logging.setLogRecordFactory(original_factory)
    log._logging_configured = original_configured


class TestRecordFactoryIntegration:
    """configure_logging() wires trace fields onto every record."""

    def test_factory_stamps_trace_fields_when_span_active(self, _restore_logging):
        """Records carry trace_id/span_id when a valid span is in context."""
        log._logging_configured = False
        span = _mock_span(trace_id=_TRACE_ID, span_id=_SPAN_ID, is_valid=True)
        with mock.patch("opentelemetry.trace.get_current_span", return_value=span):
            log.configure_logging(service="test-svc")
            record = logging.getLogRecordFactory()("n", logging.INFO, "p", 1, "m", None, None)
        assert record.trace_id == _TRACE_ID_HEX
        assert record.span_id == _SPAN_ID_HEX
        assert record.service == "test-svc"

    def test_factory_omits_trace_fields_without_span(self, _restore_logging):
        """Records have no trace fields when no span is active."""
        log._logging_configured = False
        span = _mock_span(trace_id=0, span_id=0, is_valid=False)
        with mock.patch("opentelemetry.trace.get_current_span", return_value=span):
            log.configure_logging(service="test-svc")
            record = logging.getLogRecordFactory()("n", logging.INFO, "p", 1, "m", None, None)
        assert not hasattr(record, "trace_id")
        assert not hasattr(record, "span_id")
