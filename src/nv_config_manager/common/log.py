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
"""NVIDIA Config Manager structured logging."""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

from pythonjsonlogger import jsonlogger

# =============================================================================
# LOG CATEGORIES
# =============================================================================


class LogCategory:
    """Standard log category labels for structured logging."""

    RENDER = "render"
    RENDER_EVENT = "render.event"
    RENDER_API = "render.api"
    DHCP = "dhcp"
    DHCP_DATA = "dhcp.data"
    CONFIG_STORE = "config_store"
    CONFIG_STORE_API = "config_store.api"
    ZTP = "ztp"
    ZTP_API = "ztp.api"
    TEMPORAL = "temporal"
    TEMPORAL_WORKFLOW = "temporal.workflow"
    TEMPORAL_ACTIVITY = "temporal.activity"
    TEMPORAL_API = "temporal.api"
    NAUTOBOT = "nautobot"
    AUTH = "auth"
    API = "api"  # Deprecated: use per-service variants (RENDER_API, etc.)
    NATS = "nats"
    CACHE = "cache"


# =============================================================================
# INTERNALS
# =============================================================================

_logging_configured = False
_custom_labels: dict[str, str] = {}

_VALID_LABEL_KEY = re.compile(r"^\w+(\_\w+)?$")
_MAX_LABEL_VALUE_LEN = 63
_RESERVED_FIELDS = frozenset(
    {
        "message",
        "msg",
        "level",
        "levelname",
        "levelno",
        "name",
        "pathname",
        "filename",
        "module",
        "lineno",
        "funcName",
        "created",
        "asctime",
        "msecs",
        "relativeCreated",
        "thread",
        "threadName",
        "process",
        "processName",
        "exc_info",
        "exc_text",
        "stack_info",
        "service",
        "category",
    }
)


def _load_custom_labels() -> dict[str, str]:
    """Parse and validate NV_CONFIG_MANAGER_CUSTOM_LABELS env var.

    Keys must be valid Python/Prometheus identifiers (``[a-zA-Z_][a-zA-Z0-9_]*``),
    at most 63 characters, and must not collide with reserved LogRecord fields.
    Values are truncated to 63 characters to stay within the Kubernetes pod-label
    limit.  Invalid entries are skipped with a warning on stderr.
    """
    raw = os.getenv("NV_CONFIG_MANAGER_CUSTOM_LABELS", "")
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        print(  # noqa: T201
            f"WARNING: NV_CONFIG_MANAGER_CUSTOM_LABELS is not valid JSON, ignoring: {raw!r}",
        )
        return {}
    if not isinstance(parsed, dict):
        return {}

    labels: dict[str, str] = {}
    for k, v in parsed.items():
        key = str(k)
        if key in _RESERVED_FIELDS:
            print(f"WARNING: custom label key {key!r} is reserved, skipping")  # noqa: T201
            continue
        if not _VALID_LABEL_KEY.match(key) or len(key) > _MAX_LABEL_VALUE_LEN:
            print(  # noqa: T201
                f"WARNING: custom label key {key!r} is invalid "
                f"(must match {_VALID_LABEL_KEY.pattern} and be <= 63 chars), skipping",
            )
            continue
        value = str(v)[:_MAX_LABEL_VALUE_LEN]
        labels[key] = value
    return labels


def _get_log_level() -> int:
    """Resolve log level from LOG_LEVEL env var, falling back to DEBUG env var."""
    level_name = os.getenv("LOG_LEVEL", "").upper()
    if level_name:
        return getattr(logging, level_name, logging.INFO)
    return logging.DEBUG if os.getenv("DEBUG") else logging.INFO


def _use_json_format() -> bool:
    """Check LOG_FORMAT env var: 'text' for plain text, JSON otherwise."""
    return os.getenv("LOG_FORMAT", "json").lower() != "text"


def _build_formatter() -> logging.Formatter:
    """Build the appropriate formatter based on environment configuration."""
    if _use_json_format():
        format_str = "%(message)s%(levelname)s%(name)s%(asctime)s%(module)s%(lineno)d"
        return jsonlogger.JsonFormatter(format_str)
    return logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")


# =============================================================================
# PUBLIC API
# =============================================================================


def configure_logging(service: str | None = None) -> None:
    """Configure the root logger for the entire process.

    Call this once at service startup before any other logging calls.
    Sets up the root logger with JSON or text formatting so that all
    loggers (including third-party libraries) produce consistent output.

    Args:
        service: Service name to embed in every log record
                 (e.g., "render", "dhcp", "ztp").
    """
    global _logging_configured, _custom_labels  # noqa: PLW0603
    if _logging_configured:
        return
    _logging_configured = True

    _custom_labels = _load_custom_labels()

    root = logging.getLogger()
    root.setLevel(_get_log_level())

    for h in root.handlers[:]:
        root.removeHandler(h)

    handler = logging.StreamHandler()
    handler.setFormatter(_build_formatter())
    root.addHandler(handler)

    old_factory = logging.getLogRecordFactory()

    def _record_factory(*args: Any, **kwargs: Any) -> logging.LogRecord:
        record = old_factory(*args, **kwargs)
        record.level = record.levelname.lower()  # type: ignore[attr-defined]
        if service:
            record.service = service  # type: ignore[attr-defined]
        for key, value in _custom_labels.items():
            setattr(record, key, value)
        return record

    logging.setLogRecordFactory(_record_factory)


def get_logger(
    name: str,
    json_format: bool = True,
    category: str = "",
) -> logging.LoggerAdapter:
    """Get a configured logger with optional category label.

    If ``configure_logging()`` has already been called (recommended), this
    simply returns a ``LoggerAdapter`` wrapping the named logger with a
    ``category`` extra field.  Otherwise it attaches a handler to the named
    logger directly for backward compatibility.

    Args:
        name: Logger name (typically ``__name__``)
        json_format: Ignored when ``configure_logging()`` has been called;
                     kept for backward compatibility.
        category: Default log category for this logger (see ``LogCategory``).

    Returns:
        A ``LoggerAdapter`` with a ``category`` extra field.
    """
    logger = logging.getLogger(name)

    if not _logging_configured and not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(
            _build_formatter()
            if json_format
            else logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(handler)
        logger.setLevel(_get_log_level())

    return logging.LoggerAdapter(logger, extra={"category": category})
