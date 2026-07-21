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
"""FastAPI Main App."""

from __future__ import annotations

import argparse
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from prometheus_fastapi_instrumentator import Instrumentator, metrics

from nv_config_manager.common.auth import install_identity_probe
from nv_config_manager.common.log import configure_logging
from nv_config_manager.ztp.api import device_v1, files_v1, firmware_v1
from nv_config_manager.ztp.api.clients import close_nautobot_client, get_nautobot_client
from nv_config_manager.ztp.api.metrics import device_http_requests
from nv_config_manager.ztp.api.storage_clients import (
    StorageUnavailableError,
    close_storage_clients,
    warm_storage_clients,
)
from nv_config_manager.ztp.nautobot import NautobotUnavailableError

configure_logging(service="ztp")


def main() -> None:
    """CLI entrypoint for ZTP API."""
    parser = argparse.ArgumentParser(description="ZTP API Server")
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to bind to (default: 0.0.0.0)"
    )
    parser.add_argument("--port", type=int, default=9000, help="Port to listen on (default: 9000)")
    parser.add_argument(
        "--workers",
        type=int,
        default=int(os.environ.get("ZTP_API_WORKERS") or os.environ.get("WEB_CONCURRENCY") or "1"),
        help=(
            "Number of uvicorn worker processes (default: 1, or $ZTP_API_WORKERS / "
            "$WEB_CONCURRENCY). Each worker runs its own event loop and its own shared "
            "backend-client singletons, spreading per-pod device concurrency across loops "
            "so a single loop is less likely to stall (liveness kill) under a boot storm."
        ),
    )
    args = parser.parse_args()

    uvicorn.run(
        "nv_config_manager.ztp.api.main:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        proxy_headers=True,
        log_config=None,
        timeout_keep_alive=75,
        limit_concurrency=1000,
        backlog=2048,
    )


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Create shared backend clients on startup, close them on shutdown.

    The Nautobot, object storage, and Config Store clients are process-wide
    singletons so their connection pools / keepalive / backpressure are shared
    across requests instead of rebuilt per request.
    """
    get_nautobot_client()
    await warm_storage_clients()
    try:
        yield
    finally:
        await close_nautobot_client()
        await close_storage_clients()


app = FastAPI(lifespan=lifespan)


@app.exception_handler(NautobotUnavailableError)
async def _nautobot_unavailable_handler(
    _request: Request, exc: NautobotUnavailableError
) -> PlainTextResponse:
    """Surface Nautobot backpressure/circuit-breaker as a retryable 503.

    Devices (and ONIE) retry on transient failures, so shedding load here is
    far better than letting requests pile up on a struggling Nautobot.
    """
    return PlainTextResponse(
        str(exc) or "Nautobot temporarily unavailable.",
        status_code=503,
        headers={"Retry-After": "5"},
    )


@app.exception_handler(StorageUnavailableError)
async def _storage_unavailable_handler(
    _request: Request, exc: StorageUnavailableError
) -> PlainTextResponse:
    """Surface object-storage / Config Store backpressure as a retryable 503.

    Sheds load fast (rather than letting per-request S3/Config Store I/O pile up
    on the event loop) so a device/ONIE backs off and retries its boot.
    """
    return PlainTextResponse(
        str(exc) or "Storage temporarily unavailable.",
        status_code=503,
        headers={"Retry-After": "5"},
    )


# Include routers
app.include_router(device_v1.router, prefix="/v1")
app.include_router(firmware_v1.router, prefix="/v1")
app.include_router(files_v1.router, prefix="/v1")

instrumentator = Instrumentator(excluded_handlers=["/healthcheck", "/metrics"])
instrumentator.add(
    metrics.default(
        metric_namespace="nv-config-manager",
        metric_subsystem="ztp",
    )
)
instrumentator.add(
    device_http_requests(
        metric_namespace="nv-config-manager",
        metric_subsystem="ztp",
    )
)
instrumentator.instrument(app)
instrumentator.expose(app, include_in_schema=False)


@app.get("/healthcheck")
async def healthcheck() -> str:
    # Async so the liveness/readiness probe runs directly on the event loop
    # instead of the anyio threadpool. Under a boot storm the threadpool can be
    # saturated by blocking per-request I/O, which would otherwise starve a sync
    # probe handler and trigger spurious liveness-kill restarts of http-lb.
    """Execute healthcheck."""
    return "OK"


install_identity_probe(app, deferred_auth_prefixes=("/v1/device/",))
