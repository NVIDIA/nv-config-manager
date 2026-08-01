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
"""Pull-based Nautobot NATS Consumer."""

import asyncio
import asyncio.log
import json
import logging
import os
import signal
import ssl
from asyncio import AbstractEventLoop
from datetime import UTC, datetime

import nats
import nats.errors
from nats.aio.client import Client
from nats.aio.msg import Msg
from nats.js import JetStreamContext
from nats.js.api import ConsumerConfig, ConsumerInfo, DeliverPolicy
from nats.js.errors import FetchTimeoutError, NotFoundError, ServiceUnavailableError
from prometheus_client import start_http_server

from nv_config_manager.common.config import (
    DEFAULT_NATS_API_PREFIX,
    LogCategory,
    NATSConnectionManager,
    NautobotConnectionManager,
    configure_logging,
    get_logger,
    load_config,
    nats_config_manager_api_prefix,
    nats_connection,
    nats_nautobot_api_prefix,
    nats_nautobot_change_config,
    nats_render_change_config,
)
from nv_config_manager.render.dispatch import EventDispatcher
from nv_config_manager.render.events.util import DeviceNotEnabledError, clear_queued
from nv_config_manager.render.exceptions import RenderException
from nv_config_manager.render.lock import create_lock

configure_logging(service="render")

# $JS.API.CONSUMER.RESET only accepts these, so a consumer outside the set can never be
# fast-forwarded by the admin API. See ADR-60.
RESETTABLE_DELIVER_POLICIES = frozenset(
    {
        DeliverPolicy.ALL,
        DeliverPolicy.BY_START_SEQUENCE,
        DeliverPolicy.BY_START_TIME,
    }
)


class PullConsumer:
    """Pull-based Nautobot NATS Event Consumer."""

    logger = get_logger(__name__, category=LogCategory.RENDER_EVENT)

    def __init__(
        self,
        stream: str,
        subject: str,
        queue_suffix: str,
        api_prefix: str = DEFAULT_NATS_API_PREFIX,
    ) -> None:
        """Initialize the consumer."""
        config = load_config()
        self.loop: AbstractEventLoop | None = None
        self.nats_conn: Client | None = None
        self.jetstream: JetStreamContext | None = None
        queue_prefix = config["nats"]["queue"]
        self.queue = f"{queue_prefix}-{queue_suffix}"
        self.stream = stream
        self.subject = subject
        self.api_prefix = api_prefix
        self.dispatcher = EventDispatcher()
        self.running = False

        # Flow control settings
        self.idle_wait = 1.0  # Wait time when no messages available
        self.error_backoff = 2.0  # Wait time after errors
        # Heartbeat interval for consumer health detection
        # Must be < FetchMaxWait/2 (default FetchMaxWait=5s, so heartbeat must be < 2.5s)
        self.heartbeat_interval = 1.0

    def run(self) -> None:
        """Run the consumer."""
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        for sig in (signal.SIGHUP, signal.SIGTERM, signal.SIGINT):
            self.loop.add_signal_handler(sig, self._clean_exit)

        try:
            self.loop.run_until_complete(self.main())
        finally:
            # Clean up any remaining tasks before closing the loop
            try:
                # Only get pending tasks if the loop is still running
                if not self.loop.is_closed():
                    pending_tasks = [
                        task for task in asyncio.all_tasks(self.loop) if not task.done()
                    ]
                    for task in pending_tasks:
                        task.cancel()
                    # Wait for them to complete cancellation
                    self.loop.run_until_complete(
                        asyncio.gather(*pending_tasks, return_exceptions=True)
                    )
            except Exception as e:
                self.logger.warning("Error during task cleanup: %s", str(e))
            finally:
                # Close the loop if it's not already closed
                if not self.loop.is_closed():
                    self.loop.close()

    async def message_handler(self, msg: Msg) -> None:
        """Callback to process NATS message."""
        raise NotImplementedError("Consumer classes must implement message_handler.")

    async def can_process_message(self) -> bool:
        """Check if the consumer is ready to process another message.

        Override this in subclasses to implement custom flow control logic.
        """
        return True

    async def ack(self, msg: Msg) -> None:
        """Acknowledge a message with resilient error handling."""
        try:
            await msg.ack()
        except nats.errors.NoRespondersError:
            self.logger.warning(
                "No responders available for ack (likely during shutdown), treating as success"
            )
        except Exception as e:
            self.logger.error("Error acknowledging message: %s", str(e))
            raise

    async def nak(self, msg: Msg, delay: int | None = None) -> None:
        """Negative acknowledge a message with resilient error handling."""
        try:
            await msg.nak(delay=delay)
        except nats.errors.NoRespondersError:
            self.logger.warning(
                "No responders available for nak (likely during shutdown), ignoring"
            )
        except Exception as e:
            self.logger.error("Error nacking message: %s", str(e))
            raise

    async def main(self) -> None:
        """Connect to NATS and start the pull consumer loop."""

        async def closed_cb() -> None:
            self.logger.info("NATS connection is closed.")

        async def error_cb(exc: Exception) -> None:
            self.logger.error("Unhandled NATS error", exc_info=exc)

        async def disconnected_cb() -> None:
            self.logger.warning("NATS connection disconnected.")

        async def reconnected_cb() -> None:
            self.logger.warning("NATS connection reconnected.")

        self.nats_conn = await nats_connection(
            closed_cb=closed_cb,
            error_cb=error_cb,
            disconnected_cb=disconnected_cb,
            reconnected_cb=reconnected_cb,
        )
        self.logger.info("Consumer %s connected to NATS.", self.queue)

        # Register connection with manager for sharing with publishers
        connection_manager = NATSConnectionManager()
        connection_manager.set_connection(self.nats_conn)

        self.jetstream = self.nats_conn.jetstream(prefix=self.api_prefix)

        # Run the pull consumer loop
        await self._run_pull_consumer()

    async def _run_pull_consumer(self) -> None:
        """Run the pull consumer with automatic recreation if needed."""
        if self.nats_conn is None or self.jetstream is None:
            self.logger.error("NATS connection or JetStream is None, cannot run consumer")
            return

        self.running = True

        while self.running and not self.nats_conn.is_closed:
            try:
                await self._run_consumer_cycle()
            except asyncio.CancelledError:
                self.logger.info("Pull consumer cancelled, shutting down")
                break
            except Exception as e:
                # Any exception bubbling up from fetch indicates we need to recreate
                self.logger.warning("Consumer %s cycle failed, recreating: %s", self.queue, str(e))
                await asyncio.sleep(self.error_backoff)

        self.running = False

    async def _run_consumer_cycle(self) -> None:
        """Run a single consumer lifecycle: create, subscribe, and process messages."""
        # Ensure consumer exists and create subscription
        await self._ensure_consumer_exists()

        if self.jetstream is None:
            raise RuntimeError("JetStream context is None")

        # Pass the stream explicitly; omitting it makes nats-py resolve the name via
        # $JS.API.STREAM.NAMES, which is not exported across NATS account boundaries.
        pull_subscription = await self.jetstream.pull_subscribe(
            subject=self.subject, durable=self.queue, stream=self.stream
        )

        self.logger.info("Pull subscription created for consumer %s", self.queue)

        try:
            # Message processing loop
            while self.running and self.nats_conn and not self.nats_conn.is_closed:
                if not await self.can_process_message():
                    await asyncio.sleep(self.idle_wait)
                    continue

                try:
                    # Use heartbeat to detect consumer deletion automatically.
                    # If consumer is deleted, heartbeats will stop and fetch will
                    # raise an exception after missing heartbeats. Any exception
                    # during fetch indicates we should recreate the consumer.
                    msgs = await pull_subscription.fetch(batch=1, heartbeat=self.heartbeat_interval)
                    if msgs:
                        await self._resilient_message_handler(msgs[0])
                    else:
                        await asyncio.sleep(self.idle_wait)
                except FetchTimeoutError:
                    # Heartbeats were fine, but no messages were received
                    await asyncio.sleep(self.idle_wait)
                except Exception as e:
                    # Any exception during fetch (timeouts, heartbeat failures,
                    # consumer deletions, etc.) should trigger consumer recreation
                    self.logger.warning(
                        "Fetch error for consumer %s, recreating: %s",
                        self.queue,
                        str(e),
                    )
                    raise  # Bubble up to trigger recreation
        finally:
            try:
                await pull_subscription.unsubscribe()
            except Exception as e:
                self.logger.warning("Error unsubscribing: %s", str(e))

    async def _ensure_consumer_exists(self) -> None:
        """Ensure the JetStream consumer exists with proper configuration."""
        if self.jetstream is None:
            raise RuntimeError("JetStream context is None")

        try:
            # by_start_time rather than new: $JS.API.CONSUMER.RESET refuses to move a
            # consumer whose deliver_policy is new (ADR-60), and reset is how the admin
            # API fast-forwards past a backlog. Starting at creation time reproduces
            # what new gives us, so a freshly created consumer still ignores history.
            config = ConsumerConfig(
                deliver_policy=DeliverPolicy.BY_START_TIME,
                opt_start_time=datetime.now(UTC),
                ack_wait=360,
                durable_name=self.queue,
                filter_subject=self.subject,
            )

            self.logger.info("Creating/ensuring consumer exists: %s", self.queue)

            # Only a genuinely absent consumer should trigger creation. Treating any
            # failure as absence turns transient errors into spurious create attempts.
            try:
                existing = await self.jetstream.consumer_info(self.stream, self.queue)
                self.logger.info("Consumer %s already exists", self.queue)
                await self._migrate_deliver_policy(existing)
            except NotFoundError:
                try:
                    await self.jetstream.add_consumer(
                        stream=self.stream,
                        config=config,
                    )
                except ServiceUnavailableError as e:
                    raise RuntimeError(
                        f"Consumer {self.queue} is absent from stream {self.stream} and cannot be "
                        f"created through API prefix {self.api_prefix}. A stream imported from "
                        f"another NATS account does not export consumer creation, so the owning "
                        f"account must provision this consumer."
                    ) from e
                self.logger.info("Consumer %s created successfully", self.queue)

        except Exception as e:
            self.logger.error("Failed to ensure consumer exists: %s", str(e))
            raise

    async def _migrate_deliver_policy(self, existing: ConsumerInfo) -> None:
        """Recreate a pre-existing consumer whose deliver_policy forbids reset.

        deliver_policy is immutable, so a consumer created before this policy change
        keeps a value $JS.API.CONSUMER.RESET rejects (ADR-60) and can never be
        fast-forwarded. Recreating at the current ack floor rather than at the current
        time makes it reset-eligible without abandoning an in-flight backlog.
        """
        if self.jetstream is None:
            raise RuntimeError("JetStream context is None")

        policy = existing.config.deliver_policy
        if policy in RESETTABLE_DELIVER_POLICIES:
            return

        # Recreating means deleting first, which an imported stream does not export.
        if self.api_prefix != DEFAULT_NATS_API_PREFIX:
            self.logger.warning(
                "Consumer %s on imported stream %s has deliver_policy=%s, which blocks "
                "consumer reset. The account owning %s must recreate it with one of %s.",
                self.queue,
                self.stream,
                policy,
                self.api_prefix,
                sorted(p.value for p in RESETTABLE_DELIVER_POLICIES),
            )
            return

        # Resume from the first message this consumer has not acked, so nothing pending
        # is skipped and nothing already acked is replayed.
        resume_from = (existing.ack_floor.stream_seq if existing.ack_floor else 0) + 1
        self.logger.info(
            "Migrating consumer %s from deliver_policy=%s to by_start_sequence at %d",
            self.queue,
            policy,
            resume_from,
        )

        await self.jetstream.delete_consumer(stream=self.stream, consumer=self.queue)
        await self.jetstream.add_consumer(
            stream=self.stream,
            config=ConsumerConfig(
                deliver_policy=DeliverPolicy.BY_START_SEQUENCE,
                opt_start_seq=resume_from,
                ack_wait=360,
                durable_name=self.queue,
                filter_subject=self.subject,
            ),
        )
        self.logger.info("Consumer %s migrated successfully", self.queue)

    async def _resilient_message_handler(self, msg: Msg) -> None:
        """Wrapper around message_handler with additional error handling."""
        try:
            await self.message_handler(msg)
        except Exception as e:
            self.logger.error("Error in message handler: %s", str(e), exc_info=e)
            # For message handler errors, try to nak the message
            # Don't bubble up since these are processing errors, not consumer errors
            try:
                await self.nak(msg)
            except Exception as nak_error:
                self.logger.error("Failed to nak message after handler error: %s", str(nak_error))

    def _clean_exit(self) -> None:
        """Cancel all running tasks and close the connection to NATS."""
        self.logger.info("Received shutdown signal, initiating clean exit...")
        self.running = False

        async def close_connection() -> None:
            #
            # This quells "returning true from eof_received() has no"
            # effect when using ssl". Ref: asyncio/sslproto.py:_call_eof_received()
            old_asyncio_loglevel = asyncio.log.logger.level
            asyncio.log.logger.setLevel(logging.ERROR)

            try:
                if self.nats_conn and not self.nats_conn.is_closed:
                    # Clear the shared connections before closing
                    nats_manager = NATSConnectionManager()
                    nats_manager.clear_connection()

                    # Also clear the Nautobot connection to ensure clean shutdown
                    nautobot_manager = NautobotConnectionManager()
                    nautobot_manager.clear_connection()

                    await self.nats_conn.close()
                    self.logger.info("NATS connection closed successfully")
            except ssl.SSLError:
                # This has been occasionally seen during shutdown.
                self.logger.debug(
                    "SSL error during NATS connection close (expected during shutdown)"
                )
            except Exception as e:
                self.logger.warning("Error closing NATS connection: %s", str(e))

            #
            # This is almost certainly pointless since we've closed the NATS connection
            # at this point, but it can't hurt.
            asyncio.log.logger.setLevel(old_asyncio_loglevel)

        # Closing the NATS connection will stop the subscriber task
        if self.loop and not self.loop.is_closed():
            try:
                self.loop.create_task(close_connection())
            except RuntimeError as e:
                self.logger.warning("Could not schedule close_connection task: %s", str(e))


class PullNautobotConsumer(PullConsumer):
    """Pull-based consumer for configured Nautobot changelog events."""

    def __init__(self) -> None:
        """Initialize a Nautobot changelog consumer."""
        stream, subject = nats_nautobot_change_config()
        api_prefix = nats_nautobot_api_prefix()
        super().__init__(
            stream=stream,
            subject=subject,
            queue_suffix="nautobot",
            api_prefix=api_prefix,
        )

    async def message_handler(self, msg: Msg) -> None:
        """Process a nautobot changelog message."""
        try:
            data = json.loads(msg.data.decode())
            await self.dispatcher.nautobot_event_dispatch(data)
            # Only acknowledge if processing succeeded
            await self.ack(msg)
        except DeviceNotEnabledError:
            # No need to redeliver render exceptions, they won't succeed on retry
            await self.ack(msg)
        except Exception as e:
            self.logger.error("Error processing nautobot message", exc_info=e)
            await self.nak(msg)


class PullDeviceChangeConsumer(PullConsumer):
    """Pull-based consumer for configured render-triggering changes."""

    def __init__(self) -> None:
        """Initialize a render-triggering change consumer."""
        stream, subject = nats_render_change_config()
        api_prefix = nats_config_manager_api_prefix()
        super().__init__(
            stream=stream,
            subject=subject,
            queue_suffix="device",
            api_prefix=api_prefix,
        )

    async def message_handler(self, msg: Msg) -> None:
        """Process a device change triggered render."""
        data = json.loads(msg.data.decode())
        device_id = data["device_id"]

        lock = await create_lock(device_id, blocking=False)
        acquired = await lock.acquire()
        if not acquired:
            self.logger.info("Another process owns the lock for %s, nacking.", device_id)
            await self.nak(msg, delay=5)
            return
        try:
            # Clear the queued flag only after successfully acquiring the lock
            await clear_queued(device_id)
            # Dispatch is now async, so we can await it directly
            await self.dispatcher.nautobot_change_dispatch(data)
            await self.ack(msg)
        except RenderException:
            # No need to redeliver render exceptions, they won't succeed on retry
            await self.ack(msg)
        except Exception as e:
            self.logger.error("Error processing device change message: %s", data, exc_info=e)
            await self.nak(msg)
        finally:
            try:
                await lock.release()
            except Exception as e:
                self.logger.error("Error releasing lock for %s", device_id, exc_info=e)


def main() -> None:
    """Entry point for the pull consumer."""
    # Start Prometheus Server
    start_http_server(8000)

    consumer: PullConsumer
    consumer_name = os.getenv("NATS_CONSUMER")
    if consumer_name == "nautobot":
        consumer = PullNautobotConsumer()
    elif consumer_name == "device":
        consumer = PullDeviceChangeConsumer()
    else:
        raise NotImplementedError(f"No consumer implemented for {consumer_name}.")

    consumer.run()
    get_logger(__name__, category=LogCategory.RENDER_EVENT).info("Exiting...")


if __name__ == "__main__":
    main()
