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
"""Mock device API server.

Runs a FastAPI server that emulates either Arista EAPI or Cumulus NVUE
depending on the configured platform.
"""

from __future__ import annotations

import logging
import os

import uvicorn
from fastapi import FastAPI

from mock_device.config import DeviceConfig
from mock_device.device_api import eapi, nvue

logger = logging.getLogger(__name__)

TLS_CERT_PATH = "/app/tls.crt"
TLS_KEY_PATH = "/app/tls.key"


def create_app(device: DeviceConfig) -> FastAPI:
    """Create a FastAPI app configured for the given device platform."""
    app = FastAPI(
        title=f"Mock Device API - {device.name}",
        description=f"Mock {device.platform} API for {device.name}",
    )

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        """Return a simple liveness probe response."""
        return {"status": "ok", "device": device.name, "platform": device.platform}

    if device.platform in ("arista", "arista_eos"):
        eapi.configure(device)
        app.include_router(eapi.router)
        logger.info("Configured Arista EAPI mock for %s", device.name)
    elif device.platform in ("cumulus", "cumulus_linux", "nvos", "nv_os"):
        nvue.configure(device)
        app.include_router(nvue.router)
        logger.info("Configured Cumulus/NVOS NVUE mock for %s", device.name)
    else:
        nvue.configure(device)
        app.include_router(nvue.router)
        logger.warning(
            "Unknown platform %s for %s, defaulting to NVUE", device.platform, device.name
        )

    return app


def run_server(device: DeviceConfig) -> None:
    """Run the mock device API server."""
    port = device.api_port
    if port == 0:
        port = 443 if device.platform in ("arista", "arista_eos", "nvos", "nv_os") else 8765

    app = create_app(device)

    ssl_certfile = os.environ.get("TLS_CERTFILE", TLS_CERT_PATH)
    ssl_keyfile = os.environ.get("TLS_KEYFILE", TLS_KEY_PATH)
    use_tls = os.path.exists(ssl_certfile) and os.path.exists(ssl_keyfile)

    logger.info(
        "Starting mock %s API for %s on port %d (TLS=%s)",
        device.platform,
        device.name,
        port,
        use_tls,
    )

    kwargs: dict = {"host": "0.0.0.0", "port": port, "log_level": "info"}
    if use_tls:
        kwargs["ssl_certfile"] = ssl_certfile
        kwargs["ssl_keyfile"] = ssl_keyfile

    uvicorn.run(app, **kwargs)
