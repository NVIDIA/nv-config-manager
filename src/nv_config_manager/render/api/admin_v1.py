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
"""V1 Admin API Endpoints for NATS Consumer Management."""

import json
from enum import StrEnum
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from nats.aio.client import Client
from nats.errors import NoRespondersError
from nats.errors import TimeoutError as NatsTimeoutError
from nats.js import JetStreamContext
from nats.js.errors import NotFoundError
from pydantic import BaseModel

from nv_config_manager.common.config import (
    DEFAULT_NATS_API_PREFIX,
    load_config,
    nats_config_manager_api_prefix,
    nats_connection,
    nats_nautobot_api_prefix,
    nats_nautobot_change_config,
    nats_render_change_config,
)
from nv_config_manager.common.log import LogCategory, get_logger


class ConsumerType(StrEnum):
    """Valid consumer types for NATS consumer management."""

    nautobot = "nautobot"
    device = "device"
    template = "template"


responses: dict[int | str, dict[str, Any]] = {
    200: {"description": "Operation successful"},
    404: {"description": "Consumer not found"},
    500: {"description": "Internal server error"},
}

router = APIRouter(prefix="/admin", responses=responses)
logger = get_logger(__name__, category=LogCategory.RENDER_API)

# Reset is a single server-side cursor move, so it needs only a normal request timeout
# rather than a budget scaled to the size of the backlog.
CONSUMER_RESET_TIMEOUT_SECONDS = 10.0


class ConsumerInfo(BaseModel):
    """Consumer information model."""

    name: str
    stream: str
    subject: str
    num_pending: int
    num_ack_pending: int
    num_delivered: int


class ConsumerResetResponse(BaseModel):
    """Consumer reset response model."""

    consumer_name: str
    stream: str
    status: str
    message: str
    skipped: int = 0
    remaining_pending: int = 0
    reset_seq: int = 0


class ConsumerListResponse(BaseModel):
    """Consumer list response model."""

    consumers: list[ConsumerInfo]


def get_consumer_configs() -> dict[str, dict[str, str]]:
    """Get the consumer configurations mapped by consumer type."""
    config = load_config()
    queue_prefix = config["nats"]["queue"]

    nautobot_stream, nautobot_subject = nats_nautobot_change_config(config)
    nautobot_api_prefix = nats_nautobot_api_prefix(config)
    render_stream, render_subject = nats_render_change_config(config)
    render_api_prefix = nats_config_manager_api_prefix(config)

    return {
        "nautobot": {
            "durable_name": f"{queue_prefix}-nautobot",
            "stream": nautobot_stream,
            "subject": nautobot_subject,
            "api_prefix": nautobot_api_prefix,
        },
        "device": {
            "durable_name": f"{queue_prefix}-device",
            "stream": render_stream,
            "subject": render_subject,
            "api_prefix": render_api_prefix,
        },
    }


def jetstream_for_consumer(nats_conn: Client, consumer_config: dict[str, str]) -> JetStreamContext:
    """Return a JetStream context for this consumer's configured stream account."""
    return nats_conn.jetstream(prefix=consumer_config.get("api_prefix", DEFAULT_NATS_API_PREFIX))


class ConsumerResetRejected(Exception):
    """The server refused a $JS.API.CONSUMER.RESET request."""

    def __init__(self, description: str, err_code: int | None = None) -> None:
        super().__init__(description)
        self.description = description
        self.err_code = err_code


async def fast_forward_consumer(
    nats_conn: Client, jetstream: JetStreamContext, consumer_config: dict[str, str]
) -> tuple[int, int, int]:
    """Fast-forward a consumer past its backlog using $JS.API.CONSUMER.RESET.

    Reset moves the delivery cursor server-side in one call, so unlike deleting and
    recreating the consumer it needs no consumer management rights on the stream, and
    unlike draining it costs no round trip per message. Requires nats-server 2.14.0+
    and a consumer whose deliver_policy is not `new` -- see ADR-60.

    Returns the backlog skipped, the backlog still outstanding, and the stream sequence
    the consumer was reset to.
    """
    durable = consumer_config["durable_name"]
    stream = consumer_config["stream"]
    api_prefix = consumer_config.get("api_prefix", DEFAULT_NATS_API_PREFIX)

    # Raises NotFoundError for an absent consumer, which callers turn into a 404 before
    # any reset is attempted.
    backlog = (await jetstream.consumer_info(stream=stream, consumer=durable)).num_pending

    # Reset leaves the consumer so the next message it delivers has a stream sequence
    # >= seq, so one past the last stored sequence puts it at the head of the stream.
    target_seq = (await jetstream.stream_info(stream)).state.last_seq + 1

    subject = f"{api_prefix}.CONSUMER.RESET.{stream}.{durable}"
    try:
        response = await nats_conn.request(
            subject,
            json.dumps({"seq": target_seq}).encode(),
            timeout=CONSUMER_RESET_TIMEOUT_SECONDS,
        )
    except (NoRespondersError, NatsTimeoutError) as exc:
        raise ConsumerResetRejected(
            f"No response on {subject}. Reset requires nats-server 2.14.0+, and on a"
            " stream imported from another account an export covering the subject."
        ) from exc

    payload = json.loads(response.data)
    if error := payload.get("error"):
        raise ConsumerResetRejected(
            error.get("description", "consumer reset rejected"), error.get("err_code")
        )

    remaining = (await jetstream.consumer_info(stream=stream, consumer=durable)).num_pending
    return backlog, remaining, int(payload.get("reset_seq", target_seq))


@router.get("/consumers", response_model=ConsumerListResponse)
async def list_consumers(request: Request) -> ConsumerListResponse:
    """List all consumers and their current status."""
    try:
        nats_conn = await nats_connection()
        consumer_configs = get_consumer_configs()
        consumers = []

        for config in consumer_configs.values():
            jetstream = jetstream_for_consumer(nats_conn, config)
            try:
                consumer_info = await jetstream.consumer_info(
                    stream=config["stream"], consumer=config["durable_name"]
                )

                consumers.append(
                    ConsumerInfo(
                        name=config["durable_name"],
                        stream=config["stream"],
                        subject=config["subject"],
                        num_pending=consumer_info.num_pending,
                        num_ack_pending=consumer_info.num_ack_pending,
                        num_delivered=consumer_info.delivered.consumer_seq,
                    )
                )

            except Exception as e:
                logger.warning(f"Could not get info for consumer {config['durable_name']}: {e}")
                # Add consumer with unknown status
                consumers.append(
                    ConsumerInfo(
                        name=config["durable_name"],
                        stream=config["stream"],
                        subject=config["subject"],
                        num_pending=-1,
                        num_ack_pending=-1,
                        num_delivered=-1,
                    )
                )

        await nats_conn.close()
        return ConsumerListResponse(consumers=consumers)

    except Exception as exc:
        logger.exception("Error listing consumers")
        raise HTTPException(status_code=500, detail="Failed to list consumers") from exc


def _reset_message(consumer_config: dict[str, str], skipped: int, remaining: int) -> str:
    """Describe the outcome of a reset for the given consumer."""
    message = (
        f"Consumer '{consumer_config['durable_name']}' fast-forwarded past {skipped} message(s)."
    )
    if remaining:
        # The reset itself is atomic, so a backlog now means new arrivals rather than
        # progress left to make. Saying so avoids reading it as a failed reset.
        message += f" {remaining} message(s) have arrived since."
    return message


@router.delete("/consumers/{consumer_type}/reset", response_model=ConsumerResetResponse)
async def reset_consumer(consumer_type: ConsumerType, request: Request) -> ConsumerResetResponse:
    """Fast-forward a consumer past its backlog with the JetStream consumer reset API.

    The consumer is moved in place rather than deleted, so this works identically on
    locally owned streams and on streams imported from another NATS account.
    """

    try:
        consumer_configs = get_consumer_configs()
        config = consumer_configs[consumer_type]

        nats_conn = await nats_connection()
        try:
            jetstream = jetstream_for_consumer(nats_conn, config)

            try:
                skipped, remaining, reset_seq = await fast_forward_consumer(
                    nats_conn, jetstream, config
                )
            except NotFoundError as exc:
                raise HTTPException(
                    status_code=404,
                    detail=f"Consumer '{config['durable_name']}' not found",
                ) from exc
            except ConsumerResetRejected as exc:
                raise HTTPException(status_code=503, detail=str(exc)) from exc

            logger.info(
                "Reset consumer %s to sequence %d: skipped %d, %d pending",
                config["durable_name"],
                reset_seq,
                skipped,
                remaining,
            )

            return ConsumerResetResponse(
                consumer_name=config["durable_name"],
                stream=config["stream"],
                status="success",
                message=_reset_message(config, skipped, remaining),
                skipped=skipped,
                remaining_pending=remaining,
                reset_seq=reset_seq,
            )
        finally:
            await nats_conn.close()

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error resetting consumer %s", consumer_type)
        raise HTTPException(status_code=500, detail="Failed to reset consumer") from exc


@router.delete("/consumers/reset-all", response_model=list[ConsumerResetResponse])
async def reset_all_consumers(request: Request) -> list[ConsumerResetResponse]:
    """Fast-forward every consumer past its backlog with the JetStream consumer reset API."""
    try:
        results = []
        consumer_configs = get_consumer_configs()

        nats_conn = await nats_connection()
        try:
            for consumer_type, config in consumer_configs.items():
                jetstream = jetstream_for_consumer(nats_conn, config)
                skipped = 0
                remaining = 0
                reset_seq = 0
                try:
                    skipped, remaining, reset_seq = await fast_forward_consumer(
                        nats_conn, jetstream, config
                    )
                    status = "success"
                    message = _reset_message(config, skipped, remaining)
                    logger.info(
                        "Reset consumer %s to sequence %d: skipped %d, %d pending",
                        config["durable_name"],
                        reset_seq,
                        skipped,
                        remaining,
                    )

                # Mirrors the 404 from the single-consumer endpoint: an absent consumer
                # was not fast-forwarded, so reporting success would misrepresent it.
                except NotFoundError:
                    status = "not_found"
                    message = f"Consumer '{config['durable_name']}' does not exist."
                    logger.info(f"Consumer {config['durable_name']} not found")

                except Exception as e:
                    status = "error"
                    message = f"Failed to reset consumer '{config['durable_name']}': {str(e)}"
                    logger.error(f"Error processing consumer {consumer_type}: {e}")

                results.append(
                    ConsumerResetResponse(
                        consumer_name=config["durable_name"],
                        stream=config["stream"],
                        status=status,
                        message=message,
                        skipped=skipped,
                        remaining_pending=remaining,
                        reset_seq=reset_seq,
                    )
                )

            return results
        finally:
            await nats_conn.close()

    except Exception as exc:
        logger.exception("Error resetting all consumers")
        raise HTTPException(status_code=500, detail="Failed to reset consumers") from exc


@router.get("/consumers/{consumer_type}", response_model=ConsumerInfo)
async def get_consumer_info(consumer_type: ConsumerType, request: Request) -> ConsumerInfo:
    """Get detailed information about a specific consumer."""

    try:
        consumer_configs = get_consumer_configs()
        config = consumer_configs[consumer_type]

        nats_conn = await nats_connection()
        jetstream = jetstream_for_consumer(nats_conn, config)

        try:
            consumer_info = await jetstream.consumer_info(
                stream=config["stream"], consumer=config["durable_name"]
            )

            result = ConsumerInfo(
                name=config["durable_name"],
                stream=config["stream"],
                subject=config["subject"],
                num_pending=consumer_info.num_pending,
                num_ack_pending=consumer_info.num_ack_pending,
                num_delivered=consumer_info.delivered.consumer_seq,
            )

        except NotFoundError as e:
            raise HTTPException(
                status_code=404,
                detail=f"Consumer '{config['durable_name']}' not found",
            ) from e

        await nats_conn.close()
        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error getting consumer info for %s", consumer_type)
        raise HTTPException(status_code=500, detail="Failed to get consumer info") from exc
