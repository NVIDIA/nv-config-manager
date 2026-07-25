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
"""Main FastAPI application."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator import metrics as instrumentator_metrics

from nv_config_manager.common.auth import install_identity_probe
from nv_config_manager.common.log import LogCategory, configure_logging, get_logger
from nv_config_manager.common.telemetry import instrument_fastapi_app, setup_tracing
from nv_config_manager.config_store.api.admin_v1 import router as admin_router
from nv_config_manager.config_store.api.config_v1 import router as config_router
from nv_config_manager.config_store.config import settings

configure_logging(service="config-store")
setup_tracing("config-store")
logger = get_logger(__name__, category=LogCategory.CONFIG_STORE_API)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Handle application lifespan (startup and shutdown)."""
    from nv_config_manager.config_store.core.device_cache_redis import DeviceCacheService

    # Startup
    cache_service = None
    if settings.nautobot_token:
        try:
            logger.info("Initializing Redis-based Nautobot cache service (read-only)")
            cache_service = await DeviceCacheService.from_config(settings.config)
            app.state.cache_service = cache_service
            logger.info(
                "Redis-based Nautobot cache service initialized "
                "(cache refresh runs in separate container)"
            )
        except Exception as e:
            logger.error("Failed to initialize Nautobot cache service: %s", e)
            app.state.cache_service = None
    else:
        logger.info("Nautobot cache service disabled")
        app.state.cache_service = None

    yield

    # Shutdown
    logger.info("API service shutting down")
    if cache_service:
        await cache_service.nautobot_client.close()
        logger.info("Closed Nautobot client")
        await cache_service.redis_client.close()
        logger.info("Closed Redis connection")


# Create FastAPI app
app = FastAPI(
    title="NVIDIA Config Manager Config Store Service",
    description="PostgreSQL-backed configuration storage service",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

instrument_fastapi_app(app)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,  # type: ignore[arg-type]
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(config_router, prefix="/v1/config", tags=["config"])
app.include_router(admin_router, prefix="/v1/admin", tags=["admin"])

# Setup Prometheus metrics
if settings.enable_metrics:
    instrumentator = Instrumentator(excluded_handlers=["/healthcheck", "/metrics"])
    instrumentator.add(
        instrumentator_metrics.default(
            metric_namespace="nv-config-manager",
            metric_subsystem="config_store",
        )
    )
    instrumentator.instrument(app)
    instrumentator.expose(app, include_in_schema=False)


@app.get("/healthcheck", include_in_schema=False)
async def healthcheck() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


install_identity_probe(app)


def main() -> None:
    """CLI entrypoint for Config Store API."""

    uvicorn.run(
        "nv_config_manager.config_store.api.main:app",
        host="0.0.0.0",
        port=9000,
        log_config=None,
    )
