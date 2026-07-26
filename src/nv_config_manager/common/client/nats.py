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
"""NATS Client.

Shared NATS client for all NVIDIA Config Manager services.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import ssl
from collections.abc import Awaitable, Callable
from configparser import ConfigParser
from typing import Any

import certifi
import nats
import nats.js.errors
from nats.aio.client import Client
from nats.aio.msg import Msg
from nats.js.api import DeliverPolicy, StreamInfo

from nv_config_manager.common.log import LogCategory, get_logger

logger = get_logger(__name__, category=LogCategory.NATS)

# Defined here rather than in common.config because that module imports this
# package; common.config re-exports it as the public name.
DEFAULT_NATS_API_PREFIX = "$JS.API"


class NatsClient:
    """Base client for NATS JetStream."""

    def __init__(
        self,
        server: str,
        queue: str = "nv-config-manager",
        local: bool = False,
        auth_method: str = "password",
        user: str | None = None,
        password: str | None = None,
        creds_path: str | None = None,
        default_stream_name: str = "nv-config-manager",
        default_stream_subjects: list[str] | None = None,
        api_prefix: str = DEFAULT_NATS_API_PREFIX,
    ) -> None:
        """Initialize the NATS client.

        Args:
            server: NATS server URL
            queue: Queue prefix for consumer groups
            local: Whether this is a local development environment
            auth_method: Authentication method ('password' or 'JWT')
            user: Username for password auth
            password: Password for password auth
            creds_path: Path to credentials file for JWT auth
            default_stream_name: Stream backing this client
            default_stream_subjects: Subjects to create the stream with when local
            api_prefix: JetStream API prefix. Use the exporting account's rewritten
                prefix when the stream is imported from another NATS account.
        """
        self.server = server
        self.queue = queue
        self.local = local
        self.auth_method = auth_method
        self.user = user
        self.password = password
        self.creds_path = creds_path
        self.default_stream_name = default_stream_name
        self.default_stream_subjects = default_stream_subjects or ["nv-config-manager.>"]
        self.api_prefix = api_prefix

        self.ssl_context = ssl.create_default_context()
        self.ssl_context.load_verify_locations(certifi.where())
        self.conn: Client | None = None
        self.stream_info: StreamInfo | None = None

    @classmethod
    def from_config(cls, config: ConfigParser) -> NatsClient:
        """Create NatsClient from configuration.

        Args:
            config: ConfigParser with 'nats' section

        Returns:
            Configured NatsClient instance
        """
        nats_config = config["nats"]

        stream_subjects = [
            subject.strip()
            for subject in nats_config.get("config_manager_subjects", "nv-config-manager.>").split(
                ","
            )
            if subject.strip()
        ]
        return cls(
            server=nats_config["server"],
            queue=nats_config.get("queue", "nv-config-manager"),
            local=nats_config.getboolean("local", fallback=False),
            auth_method=nats_config.get("auth_method", "password"),
            user=nats_config.get("user"),
            password=nats_config.get("password"),
            creds_path=nats_config.get("creds_path"),
            default_stream_name=nats_config.get("config_manager_stream", "nv-config-manager"),
            default_stream_subjects=stream_subjects,
            api_prefix=nats_config.get("config_manager_api_prefix", DEFAULT_NATS_API_PREFIX),
        )

    async def _disconnected_cb(self) -> None:
        logger.info("Disconnected from NATS")

    async def _reconnected_cb(self) -> None:
        logger.info("Reconnected to NATS")

    async def _closed_cb(self) -> None:
        logger.info("NATS connection closed")

    async def _error_cb(self, error: Exception) -> None:
        logger.error("NATS error: %s", error, exc_info=error)

    async def connect(self) -> Client:
        """Connect to the NATS server.

        Returns:
            Connected NATS client
        """
        logger.debug(
            "Connecting to NATS server=%s local=%s auth_method=%s",
            self.server,
            self.local,
            self.auth_method,
        )
        options: dict[str, Any] = {
            "connect_timeout": 30,
            "reconnected_cb": self._reconnected_cb,
            "disconnected_cb": self._disconnected_cb,
            "closed_cb": self._closed_cb,
            "error_cb": self._error_cb,
        }
        # Use TLS and auth the same way as nats_connection() (used by Render).
        # When local=True we used to skip TLS, but the server may still require TLS
        # for JetStream; skipping it caused "Connected" then JetStream timeouts.
        if self.auth_method == "JWT":
            options["user_credentials"] = self.creds_path
        else:
            options["user"] = self.user
            options["password"] = self.password
        options["tls"] = self.ssl_context

        try:
            self.conn = await nats.connect(self.server, **options)
            await self._ensure_stream()
        except Exception as err:
            logger.error(
                "NATS connection failed: server=%s error=%s",
                self.server,
                err,
                exc_info=True,
            )
            raise

        logger.info("Connected to NATS %s", self.conn.connected_url)
        return self.conn

    async def _ensure_stream(self) -> None:
        """Ensure the configured stream exists."""
        if not self.conn:
            return

        jetstream = self.conn.jetstream(prefix=self.api_prefix)
        try:
            self.stream_info = await jetstream.stream_info(self.default_stream_name)
        except nats.js.errors.NotFoundError:
            if self.local:
                logger.info("Configured stream %s not found, creating...", self.default_stream_name)
                await jetstream.add_stream(
                    name=self.default_stream_name,
                    subjects=self.default_stream_subjects,
                )
                self.stream_info = await jetstream.stream_info(self.default_stream_name)
            else:
                logger.error(
                    "Configured JetStream stream %s not found (publish will fail): server=%s",
                    self.default_stream_name,
                    self.server,
                )

    async def close(self) -> None:
        """Close the NATS connection."""
        if self.conn and not self.conn.is_closed:
            await self.conn.close()


class NatsProducer(NatsClient):
    """NATS JetStream producer for publishing messages."""

    async def publish(self, subject: str, message: str, stream: str | None = None) -> None:
        """Publish a message to NATS JetStream.

        Args:
            subject: Subject to publish to
            message: Message payload
            stream: Stream name. Defaults to the configured client stream.
        """
        stream_name = stream or self.default_stream_name
        async with await self.connect() as conn:
            await conn.jetstream(prefix=self.api_prefix).publish(
                subject=subject, payload=message.encode("utf-8"), stream=stream_name
            )
            logger.debug("Published NATS message on stream %s subject %s", stream_name, subject)


class NatsConsumer(NatsClient):
    """NATS JetStream consumer for subscribing to messages."""

    def __init__(
        self,
        stream: str,
        subject: str,
        queue_suffix: str,
        handler: Callable[[Msg], Awaitable[None]],
        **kwargs: Any,
    ) -> None:
        """Initialize the consumer.

        Args:
            stream: Stream name to consume from
            subject: Subject to subscribe to
            queue_suffix: Suffix for the queue group name
            handler: Async callback for handling messages
            **kwargs: Additional arguments passed to NatsClient
        """
        super().__init__(**kwargs)
        self.stream = stream
        self.subject = subject
        self.queue_suffix = queue_suffix
        self.handler = handler
        self._loop: asyncio.AbstractEventLoop | None = None

    @property
    def full_queue_name(self) -> str:
        """Get the full queue name."""
        return f"{self.queue}-{self.queue_suffix}"

    def run(self) -> None:
        """Run the consumer (blocking)."""
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()

        for sig in (signal.SIGHUP, signal.SIGTERM, signal.SIGINT):
            self._loop.add_signal_handler(sig, self._clean_exit)

        logger.info("Starting consumer event loop")
        self._loop.run_until_complete(self.main())
        self._loop.close()

    async def main(self) -> None:
        """Main consumer loop."""
        self.conn = await self.connect()
        jetstream = self.conn.jetstream(prefix=self.api_prefix)

        await jetstream.subscribe(
            subject=self.subject,
            stream=self.stream,
            deliver_policy=DeliverPolicy.NEW,
            queue=self.full_queue_name,
            cb=self.handler,
        )
        logger.info(
            "Subscribed to subject %s on stream %s with queue %s",
            self.subject,
            self.stream,
            self.full_queue_name,
        )

        while not self.conn.is_closed:
            await asyncio.sleep(1)

    def _clean_exit(self) -> None:
        """Cancel all running tasks and close the connection."""

        async def close_connection() -> None:
            asyncio_logger = logging.getLogger("asyncio")
            old_loglevel = asyncio_logger.level
            asyncio_logger.setLevel(logging.ERROR)
            try:
                if self.conn and not self.conn.is_closed:
                    await self.conn.close()
            except ssl.SSLError:
                pass
            asyncio_logger.setLevel(old_loglevel)

        if self._loop:
            self._loop.create_task(close_connection())
