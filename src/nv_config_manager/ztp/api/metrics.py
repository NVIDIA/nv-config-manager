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
"""Custom FastAPI metrics."""

from collections.abc import Callable

from prometheus_client import Counter
from prometheus_fastapi_instrumentator.metrics import Info


def device_http_requests(
    metric_namespace: str = "",
    metric_subsystem: str = "",
) -> Callable[[Info], None]:
    """Record metric for device clients."""
    metric_name = "device_http_requests"
    if metric_subsystem:
        metric_name = f"{metric_subsystem}_{metric_name}"
    if metric_namespace:
        metric_name = f"{metric_namespace}_{metric_name}"
    METRIC = Counter(  # pylint: disable=invalid-name
        metric_name,
        "Count of HTTP requests initiated from a network device",
        labelnames=["client_ip", "base_url", "device_uuid"],
    )

    def instrumentation(info: Info) -> None:
        """Increment the metric for network device initiated requests."""
        if info.request.client is None:
            # No client info available, ignore
            return
        if info.request.client.host == "127.0.0.1":
            # HTTPS request from nvproxy, ignore
            return
        device_uuid = info.request.path_params.get("device_uuid")
        if not device_uuid:
            # Not a ZTP start/end related request, ignore
            return
        METRIC.labels(info.request.client.host, info.request.base_url, device_uuid)

    return instrumentation
