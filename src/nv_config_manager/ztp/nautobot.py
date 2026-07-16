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
"""Nautobot Client for ZTP service.

Extends the base NautobotClient with ZTP-specific methods for device
bootstrapping and provisioning, plus resilience so a slow or flapping Nautobot
degrades gracefully instead of taking ZTP down with it.

Resilience features (all tunable via the ``[nautobot]`` INI section, with safe
defaults so no config change is required):

* Short request timeout so a stuck call releases its slot quickly
  (``request_timeout``, default 8s).
* A bounded concurrency semaphore so ZTP applies backpressure toward Nautobot
  instead of opening unbounded connections during a boot storm. Callers that
  cannot get a slot within ``acquire_timeout`` (default 3s) get a fast
  :class:`NautobotUnavailableError` (surfaced as HTTP 503) rather than piling
  up (``max_concurrency``, default 40).
* A short-TTL device-data cache with single-flight coalescing so a burst of
  requests for the same device collapses to a single GraphQL query
  (``cache_ttl``, default 5s).
* A circuit breaker that fails fast for a cooldown once Nautobot starts
  erroring/timing out, protecting both ZTP's event loop and a struggling
  Nautobot (``breaker_failure_threshold`` default 8, ``breaker_cooldown``
  default 10s).

Because these features carry per-instance state (semaphore, cache, breaker),
the client is meant to be created once and shared across requests — see
``nv_config_manager.ztp.api.clients.get_nautobot_client``.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from configparser import SectionProxy
from typing import Any, TypeVar

import aiohttp

from nv_config_manager.common.client import NautobotClient as BaseNautobotClient
from nv_config_manager.common.client import NautobotException
from nv_config_manager.common.config import load_config, parse_verify_param
from nv_config_manager.common.log import LogCategory, get_logger
from nv_config_manager.ztp.device import DeviceData

logger = get_logger(__name__, category=LogCategory.NAUTOBOT)

_T = TypeVar("_T")

DEVICE_QUERY = """
query ($id: ID!) {
  config_manager_device(id: $id) {
    intended_config {
      config_store_instance
      path
    }
    device {
      id
      name
      platform {
        name
      }
      config_context
      interfaces: interfaces(has_ip_addresses: true) {
        ip_addresses {
          host
        }
      }
    }
  }
}
"""


class NotFoundError(Exception):
    """No device data found in GraphQL."""


class NautobotUnavailableError(Exception):
    """Nautobot is overloaded or unhealthy; the caller should back off.

    Raised when the concurrency limiter is saturated or the circuit breaker is
    open. Surfaced to clients as HTTP 503 so devices retry rather than the
    request piling up on a struggling Nautobot.
    """


# Errors that indicate Nautobot itself is unhealthy (slow/down) and should count
# toward the circuit breaker. Logical/not-found errors are intentionally excluded.
_TRANSIENT_ERRORS = (
    TimeoutError,
    aiohttp.ClientError,
    NautobotException,
)


class NautobotClient(BaseNautobotClient):
    """Async, resilient Nautobot client for the ZTP service.

    Extends the base client with a bounded-concurrency limiter, a short-TTL
    device-data cache with single-flight coalescing, and a circuit breaker.
    Designed to be instantiated once and shared across requests.
    """

    def __init__(
        self,
        nautobot_url: str | None = None,
        token: str | None = None,
    ) -> None:
        """Initialize the ZTP Nautobot client from the unified INI config."""
        config = load_config()
        nb_config: SectionProxy = config["nautobot"]

        self._request_timeout = nb_config.getint("request_timeout", fallback=8)
        self._acquire_timeout = nb_config.getfloat("acquire_timeout", fallback=3.0)
        self._cache_ttl = nb_config.getfloat("cache_ttl", fallback=5.0)
        self._breaker_threshold = nb_config.getint("breaker_failure_threshold", fallback=8)
        self._breaker_cooldown = nb_config.getfloat("breaker_cooldown", fallback=10.0)
        max_concurrency = nb_config.getint("max_concurrency", fallback=40)

        super().__init__(
            nautobot_url=nautobot_url or nb_config["server"],
            token=token or nb_config["token"],
            verify=parse_verify_param(nb_config),
            timeout=self._request_timeout,
            # Give the pool a little headroom over the in-flight cap.
            connection_limit=nb_config.getint("connection_limit", fallback=max_concurrency + 10),
        )

        self._semaphore = asyncio.Semaphore(max_concurrency)

        # Device-data cache: device_id -> (expiry_monotonic, DeviceData).
        self._cache: dict[str, tuple[float, DeviceData]] = {}
        # In-flight single-flight tasks: device_id -> Task, so concurrent
        # requests for the same device share one GraphQL round-trip.
        self._inflight: dict[str, asyncio.Task[DeviceData]] = {}

        # Circuit breaker state.
        self._consecutive_failures = 0
        self._breaker_open_until = 0.0

    # ------------------------------------------------------------------
    # Test / lifecycle helpers
    # ------------------------------------------------------------------
    def reset_resilience_state(self) -> None:
        """Clear cache, in-flight tasks, and breaker state.

        Intended for test isolation between cases that share a singleton client.
        """
        self._cache.clear()
        self._inflight.clear()
        self._consecutive_failures = 0
        self._breaker_open_until = 0.0

    # ------------------------------------------------------------------
    # Circuit breaker
    # ------------------------------------------------------------------
    def _breaker_check(self) -> None:
        if self._breaker_open_until and time.monotonic() < self._breaker_open_until:
            raise NautobotUnavailableError(
                "Nautobot circuit breaker is open; refusing request to allow recovery."
            )

    def _record_success(self) -> None:
        self._consecutive_failures = 0
        self._breaker_open_until = 0.0

    def _record_failure(self) -> None:
        self._consecutive_failures += 1
        if self._consecutive_failures >= self._breaker_threshold:
            self._breaker_open_until = time.monotonic() + self._breaker_cooldown
            logger.warning(
                "Nautobot circuit breaker opened after %d consecutive failures; "
                "failing fast for %.0fs.",
                self._consecutive_failures,
                self._breaker_cooldown,
            )

    # ------------------------------------------------------------------
    # Concurrency limiter
    # ------------------------------------------------------------------
    async def _acquire_slot(self) -> None:
        try:
            await asyncio.wait_for(self._semaphore.acquire(), timeout=self._acquire_timeout)
        except TimeoutError as exc:
            raise NautobotUnavailableError(
                "Nautobot concurrency limit reached; try again shortly."
            ) from exc

    async def _guarded(self, make_coro: Callable[[], Awaitable[_T]]) -> _T:
        """Run a coroutine behind the breaker + concurrency limiter.

        Takes a factory (not a coroutine) so the underlying request is only
        created after the breaker and limiter admit it — no orphaned, never
        awaited coroutines when we fail fast.

        Only genuine Nautobot health failures (timeouts, connection errors,
        5xx) count toward the breaker; logical errors (e.g. NotFoundError)
        propagate without tripping it.
        """
        self._breaker_check()
        await self._acquire_slot()
        try:
            result = await make_coro()
        except _TRANSIENT_ERRORS:
            self._record_failure()
            raise
        except Exception:
            # Non-transient (e.g. NotFoundError): a healthy Nautobot answered.
            self._record_success()
            raise
        else:
            self._record_success()
            return result
        finally:
            self._semaphore.release()

    # ------------------------------------------------------------------
    # Cache
    # ------------------------------------------------------------------
    def _cache_get(self, device_id: str) -> DeviceData | None:
        entry = self._cache.get(device_id)
        if entry is None:
            return None
        expiry, data = entry
        if time.monotonic() >= expiry:
            self._cache.pop(device_id, None)
            return None
        return data

    def _cache_put(self, device_id: str, data: DeviceData) -> None:
        if self._cache_ttl > 0:
            self._cache[device_id] = (time.monotonic() + self._cache_ttl, data)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def get_device_data(self, device_id: str) -> DeviceData:
        """Load device data from GraphQL, with caching + single-flight.

        Concurrent requests for the same device share a single GraphQL query,
        and successful results are cached for a short TTL. This collapses the
        read amplification of a boot storm (many configlet fetches per device,
        plus the authorization lookup) down to roughly one query per device per
        TTL window.
        """
        cached = self._cache_get(device_id)
        if cached is not None:
            return cached

        task = self._inflight.get(device_id)
        if task is None:
            task = asyncio.ensure_future(self._load_device_data(device_id))
            self._inflight[device_id] = task

            def _discard(_task: asyncio.Task[DeviceData], key: str = device_id) -> None:
                self._inflight.pop(key, None)

            task.add_done_callback(_discard)
        return await task

    async def _load_device_data(self, device_id: str) -> DeviceData:
        data = await self._guarded(
            lambda: self.graphql_query(DEVICE_QUERY, variables={"id": device_id})
        )
        device_data = DeviceData.from_graphql(data)
        if not device_data:
            raise NotFoundError(f"No data found in NB for {device_id}.")
        self._cache_put(device_id, device_data)
        return device_data

    async def get_device_serial(self, device_id: str) -> str:
        """Return the serial number for the device from Nautobot."""
        query = """
query ($id: ID!) {
    device(id: $id) {
        serial
    }
}
"""
        data: dict[str, Any] = await self._guarded(
            lambda: self.graphql_query(query, variables={"id": device_id})
        )
        if "errors" in data:
            raise NotFoundError(f"No serial found in NB for {device_id}.")
        serial: str = data["data"]["device"]["serial"]
        return serial

    async def set_status_provisioned(self, device_id: str) -> None:
        """Update the device status to Provisioned."""
        await self._guarded(
            lambda: self.patch(f"dcim/devices/{device_id}/", {"status": "Provisioned"})
        )
        # Provisioning mutates device state; drop any stale cached copy.
        self._cache.pop(device_id, None)
