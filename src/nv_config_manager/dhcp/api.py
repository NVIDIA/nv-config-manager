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
"""Simple HealthCheck API for DHCP Server."""

import argparse
import asyncio
from ipaddress import IPv4Address
from typing import Any, Literal

import uvicorn
from aiohttp import ClientError, ClientResponseError
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator
from prometheus_fastapi_instrumentator import metrics as instrumentator_metrics
from pydantic import BaseModel, ConfigDict, Field

from nv_config_manager.common.auth import install_identity_probe
from nv_config_manager.common.config import load_config
from nv_config_manager.common.log import configure_logging
from nv_config_manager.dhcp.kea import KeaClient, KeaException, LeaseCommand
from nv_config_manager.dhcp.lease_dashboard import (
    LeaseDashboardResponse,
    build_lease_dashboard,
)
from nv_config_manager.dhcp.redis import RedisClient

configure_logging(service="dhcp")

app = FastAPI()

CACHE_LAST_REFRESH = Gauge(
    "cache_last_refresh_timestamp_seconds",
    "Unix timestamp of last successful DHCP cache refresh",
    ["ip_version"],
    namespace="nv-config-manager",
    subsystem="dhcp",
)

instrumentator = Instrumentator(excluded_handlers=["/healthcheck", "/metrics"])
instrumentator.add(
    instrumentator_metrics.default(
        metric_namespace="nv-config-manager",
        metric_subsystem="dhcp",
    )
)
instrumentator.instrument(app)


class LeaseArguments(BaseModel):
    """Arguments accepted by the supported KEA lease commands."""

    model_config = ConfigDict(extra="forbid")

    ip_address: IPv4Address = Field(alias="ip-address")


class LeaseRequest(BaseModel):
    """Restricted KEA command envelope for IPv4 lease operations."""

    model_config = ConfigDict(extra="forbid")

    command: LeaseCommand
    service: list[Literal["dhcp4"]] = Field(min_length=1, max_length=1)
    arguments: LeaseArguments


def main() -> None:
    """CLI entrypoint for DHCP API."""

    parser = argparse.ArgumentParser(description="DHCP API Server")
    parser.add_argument("--port", type=int, default=9000, help="Port to listen on")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host to bind to")
    args = parser.parse_args()

    uvicorn.run(
        "nv_config_manager.dhcp.api:app",
        host=args.host,
        port=args.port,
        proxy_headers=True,
        log_config=None,
    )


def sanitize_config(config: Any) -> None:
    """Recursively remove user and password keys from the config dictionary."""
    if isinstance(config, dict):
        config.pop("user", None)
        config.pop("password", None)
        for value in config.values():
            sanitize_config(value)
    elif isinstance(config, list):
        for item in config:
            sanitize_config(item)


@app.get("/config")
async def get_config(request: Request, ip_version: int = 4) -> Any:
    """Get the running KEA DHCP Configuration."""
    client = KeaClient.from_config()
    try:
        raw_config = await client.get_config(ip_version)
        sanitize_config(raw_config)
        return raw_config
    except TimeoutError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ClientResponseError as exc:
        raise HTTPException(status_code=500, detail=str(exc.message)) from exc
    finally:
        await client.close()


@app.post("/lease")
async def proxy_lease_command(request: Request, lease_request: LeaseRequest) -> Any:
    """Proxy a supported IPv4 lease command to KEA."""
    client = KeaClient.from_config()
    try:
        return await client.lease_command(
            lease_request.command,
            str(lease_request.arguments.ip_address),
        )
    except TimeoutError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ClientResponseError as exc:
        raise HTTPException(status_code=500, detail=str(exc.message)) from exc
    except ClientError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        await client.close()


@app.get("/lease-dashboard", response_model=LeaseDashboardResponse)
async def get_lease_dashboard(
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
) -> LeaseDashboardResponse:
    """Return bounded lease, reservation, and pool data for operators."""
    client = KeaClient.from_config()
    try:
        config, leases, statistics = await asyncio.gather(
            client.get_config(4),
            client.get_lease_page(limit),
            client.get_statistics(4),
        )
        return build_lease_dashboard(config, leases, statistics, limit=limit)
    except TimeoutError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ClientResponseError as exc:
        raise HTTPException(status_code=500, detail=str(exc.message)) from exc
    except ClientError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except KeaException as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        await client.close()


@app.delete("/admin/cache")
async def flush_cache(request: Request, ip_version: int = 4) -> dict[str, str]:
    """Flush the cached KEA DHCP configuration from Redis."""
    app_config = load_config()
    redis_client = RedisClient.from_config(app_config)
    try:
        deleted = await redis_client.flush_kea_config(ip_version)
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"No cached configuration found for DHCPv{ip_version}",
            )
        return {"detail": f"DHCPv{ip_version} cached configuration flushed"}
    finally:
        await redis_client.close()


@app.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    """Expose Prometheus metrics for cache observability.

    We handle this endpoint ourselves rather than via instrumentator.expose()
    because we need async Redis reads to update the cache refresh gauge before
    generating the response.
    """
    app_config = load_config()
    redis_client = RedisClient.from_config(app_config)
    try:
        for ip_version in (4, 6):
            timestamp = await redis_client.load_refresh_timestamp(ip_version)
            if timestamp is not None:
                CACHE_LAST_REFRESH.labels(ip_version=str(ip_version)).set(timestamp)
    finally:
        await redis_client.close()
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/healthcheck")
async def healthcheck() -> str:
    """Execute healthcheck."""
    client = KeaClient.from_config(attached=True)
    app_config = load_config()
    try:
        status = await client.status()
        for process in status:
            if process["result"] != 0:
                raise HTTPException(status_code=500, detail=status)
        # Load the config and validate that the lease-db is present to validate
        # that initial config sync has occurred
        remote_lease_db = not app_config["dhcp.lease_db"].getboolean("local")
        config = await client.get_config(4)
        # KEA returns a list of responses, we want the first one
        config_list = config if isinstance(config, list) else [config]

        # Some error conditions don't return result or argument keys
        if config_list[0].get("result", 0) != 0 or "arguments" not in config_list[0]:
            error_msg = config_list[0].get("text", "No message provided")
            raise HTTPException(status_code=500, detail=f"Failed to get KEA config: {error_msg}")

        dhcp4_config = config_list[0]["arguments"]["Dhcp4"]
        lease_db_type = dhcp4_config.get("lease-database", {}).get("type", "memfile")
        if remote_lease_db and lease_db_type != "postgresql":
            # This check is only valid after the very first config sync has occurred,
            # if there is no data at all in Redis, we must not fail the healthcheck
            # or the config-refresh process will never be able to validate the config
            redis_client = RedisClient.from_config(app_config)
            if await redis_client.load_kea_config(4) is None:
                await redis_client.close()
                return "OK"
            await redis_client.close()
            raise HTTPException(
                status_code=500, detail="Lease database not present in Dhcp4 config"
            )
        return "OK"
    except TimeoutError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except ClientResponseError as exc:
        raise HTTPException(status_code=500, detail=str(exc.message)) from exc
    finally:
        await client.close()


install_identity_probe(app)
