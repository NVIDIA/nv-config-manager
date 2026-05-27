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
"""Dynamic Event Dispatcher."""

from __future__ import annotations

import os
import re
from datetime import UTC, datetime
from inspect import getmembers, isfunction
from typing import Any

from prometheus_client import Counter, Histogram

import nv_config_manager.render.events
from nv_config_manager.common.client import ConfigStoreException
from nv_config_manager.common.log import LogCategory, get_logger
from nv_config_manager.render.events.exceptions import EventParseError
from nv_config_manager.render.events.util import DeviceNotEnabledError
from nv_config_manager.render.exceptions import NautobotException, RenderException
from nv_config_manager.render.render import execute_render

# Define custom bucket values for histograms (in seconds)
HISTOGRAM_BUCKETS = [
    0.1,
    0.5,
    1.0,
    2.5,
    5.0,
    7.5,
    10.0,
    15.0,
    30.0,
    60.0,
    120.0,
    300.0,
    600.0,
    float("inf"),
]

EVENT_PROCESSING_TIME = Histogram(
    "nv_config_manager_event_processing_time",
    "Time spent processing an event",
    ["model", "instance", "namespace"],
    buckets=HISTOGRAM_BUCKETS,
)
EVENT_RECEIVED_COUNTER = Counter(
    "nv_config_manager_events_received",
    "Events received via NATS",
    ["model", "instance", "namespace"],
)
EVENT_PROCESSED_COUNTER = Counter(
    "nv_config_manager_events_processed",
    "Events processed by the dispatcher",
    ["model", "instance", "namespace"],
)
EVENT_SKIPPED_COUNTER = Counter(
    "nv_config_manager_events_skipped",
    "Events skipped by the dispatcher",
    ["model", "instance", "namespace"],
)
EVENT_FAILED_COUNTER = Counter(
    "nv_config_manager_events_failed",
    "Events failed to process",
    ["model", "instance", "exception_class", "namespace"],
)

NAUTOBOT_CHANGE_PROCESSING_TIME = Histogram(
    "nv_config_manager_nautobot_change_message_processing_time",
    "Time spent processing a render for a nautobot change",
    ["instance", "namespace"],
    buckets=HISTOGRAM_BUCKETS,
)
NAUTOBOT_CHANGE_END_TO_END_TIME = Histogram(
    "nv_config_manager_nautobot_change_message_end_to_end_time",
    "End-to-end time from Nautobot message publish to config store persistence in seconds",
    ["instance", "namespace"],
    buckets=HISTOGRAM_BUCKETS,
)
NAUTOBOT_CHANGE_RECEIVED_COUNTER = Counter(
    "nv_config_manager_nautobot_change_messages_received",
    "Nautobot change messages received via NATS",
    ["instance", "namespace"],
)
NAUTOBOT_CHANGE_PROCESSED_COUNTER = Counter(
    "nv_config_manager_nautobot_change_messages_processed",
    "Nautobot change messages processed by the dispatcher",
    ["instance", "namespace"],
)
NAUTOBOT_CHANGE_FAILED_COUNTER = Counter(
    "nv_config_manager_nautobot_change_messages_failed",
    "Nautobot change messages that failed to process",
    ["instance", "exception_class", "namespace"],
)


class EventDispatcher:  # pylint: disable=too-few-public-methods
    """Nautobot NATS Event Dispatcher."""

    logger = get_logger(__name__, category=LogCategory.RENDER_EVENT)

    def __init__(self) -> None:
        """Initialize the dispatcher."""
        self.dispatch_table = {}
        self.instance = os.getenv("HOSTNAME", "unknown")
        self.namespace = os.getenv("NV_CONFIG_MANAGER_K8S_NAMESPACE", "unknown")

        # Dynamically load dispatch functions by module and method name
        # e.g. dcim.device will map to function nv_config_manager.render.events.dcim.device
        functions = getmembers(nv_config_manager.render.events, isfunction)
        for name, func in functions:
            module = re.sub("nv_config_manager.render.events.", "", func.__module__)
            if module == "util":
                continue
            self.dispatch_table[f"{module}.{name}"] = func

    async def nautobot_event_dispatch(self, data: dict[str, Any]) -> None:
        """Invoke the appropriate function for the given NATS message."""
        model = data["model"]

        EVENT_RECEIVED_COUNTER.labels(model, self.instance, self.namespace).inc()
        if data.get("record") is None:
            # Have seen instances of this occurring, could be an object that was deleted
            # after an update and therefore the change producer has no record to include
            # in the message.
            EVENT_SKIPPED_COUNTER.labels(model, self.instance, self.namespace).inc()
            return

        try:
            func = self.dispatch_table[model]
        except KeyError:
            self.logger.info("No event handler implemented for %s, ignoring message.", model)
            EVENT_SKIPPED_COUNTER.labels(model, self.instance, self.namespace).inc()
            return

        try:
            with EVENT_PROCESSING_TIME.labels(model, self.instance, self.namespace).time():
                await func(data)
                EVENT_PROCESSED_COUNTER.labels(model, self.instance, self.namespace).inc()
        except DeviceNotEnabledError as exc:
            self.logger.info(str(exc))
            EVENT_SKIPPED_COUNTER.labels(model, self.instance, self.namespace).inc()
        except EventParseError as exc:
            self.logger.exception(str(exc))
            EVENT_FAILED_COUNTER.labels(
                model, self.instance, exc.__class__.__name__, self.namespace
            ).inc()
        except NautobotException as exc:
            self.logger.exception("Error processing event: %s", data)
            EVENT_FAILED_COUNTER.labels(
                model, self.instance, exc.__class__.__name__, self.namespace
            ).inc()

    async def nautobot_change_dispatch(self, data: dict[str, Any]) -> None:
        """Invoke a device render for a nautobot change."""
        NAUTOBOT_CHANGE_RECEIVED_COUNTER.labels(self.instance, self.namespace).inc()
        try:
            with NAUTOBOT_CHANGE_PROCESSING_TIME.labels(self.instance, self.namespace).time():
                await execute_render(
                    data["device_id"],
                    data["commit_message"],
                    data["user"],
                )
                e2e_time = (
                    datetime.now(UTC) - datetime.fromisoformat(data["@timestamp"])
                ).total_seconds()
                NAUTOBOT_CHANGE_END_TO_END_TIME.labels(
                    self.instance,
                    self.namespace,
                ).observe(e2e_time)
                NAUTOBOT_CHANGE_PROCESSED_COUNTER.labels(self.instance, self.namespace).inc()

        except (RenderException, ConfigStoreException, NautobotException) as exc:
            self.logger.exception("Error processing nautobot device change event: %s", data)
            NAUTOBOT_CHANGE_FAILED_COUNTER.labels(
                self.instance, exc.__class__.__name__, self.namespace
            ).inc()
