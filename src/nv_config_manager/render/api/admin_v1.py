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

from enum import StrEnum
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from nv_config_manager.common.config import (
    DEFAULT_NATS_API_PREFIX,
    load_config,
    nats_connection,
    nats_nautobot_api_prefix,
    nats_nautobot_change_config,
    nats_render_change_api_prefix,
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
    render_api_prefix = nats_render_change_api_prefix(config)

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


def jetstream_for_consumer(nats_conn: Any, consumer_config: dict[str, str]) -> Any:
    """Return a JetStream context for this consumer's configured stream account."""
    return nats_conn.jetstream(prefix=consumer_config.get("api_prefix", DEFAULT_NATS_API_PREFIX))


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


@router.delete("/consumers/{consumer_type}/reset", response_model=ConsumerResetResponse)
async def reset_consumer(consumer_type: ConsumerType, request: Request) -> ConsumerResetResponse:
    """Reset a consumer by deleting it. The consumer will be automatically recreated within seconds by the running service."""

    try:
        consumer_configs = get_consumer_configs()
        config = consumer_configs[consumer_type]

        nats_conn = await nats_connection()
        jetstream = jetstream_for_consumer(nats_conn, config)

        # Try to get consumer info first to check if it exists
        try:
            consumer_info = await jetstream.consumer_info(
                stream=config["stream"], consumer=config["durable_name"]
            )
            pending_msgs = consumer_info.num_pending
            logger.info(f"Consumer {config['durable_name']} has {pending_msgs} pending messages")
        except Exception:
            pending_msgs = 0
            logger.info(f"Consumer {config['durable_name']} not found or already deleted")

        # Delete the consumer
        try:
            await jetstream.delete_consumer(
                stream=config["stream"], consumer=config["durable_name"]
            )

            status = "success"
            message = f"Consumer '{config['durable_name']}' deleted successfully. Had {pending_msgs} pending messages. Consumer will be automatically recreated within seconds."
            logger.info(f"Successfully deleted consumer {config['durable_name']}")

        except Exception as delete_error:
            if "not found" in str(delete_error).lower():
                status = "success"
                message = (
                    f"Consumer '{config['durable_name']}' was already deleted or did not exist."
                )
                logger.info(f"Consumer {config['durable_name']} was already deleted")
            else:
                raise delete_error

        await nats_conn.close()

        return ConsumerResetResponse(
            consumer_name=config["durable_name"],
            stream=config["stream"],
            status=status,
            message=message,
        )

    except Exception as exc:
        logger.exception("Error resetting consumer %s", consumer_type)
        raise HTTPException(status_code=500, detail="Failed to reset consumer") from exc


@router.delete("/consumers/reset-all", response_model=list[ConsumerResetResponse])
async def reset_all_consumers(request: Request) -> list[ConsumerResetResponse]:
    """Reset all consumers by deleting them. Consumers will be automatically recreated within seconds by the running services."""
    try:
        results = []
        consumer_configs = get_consumer_configs()

        nats_conn = await nats_connection()

        for consumer_type, config in consumer_configs.items():
            jetstream = jetstream_for_consumer(nats_conn, config)
            try:
                # Try to get consumer info first
                try:
                    consumer_info = await jetstream.consumer_info(
                        stream=config["stream"], consumer=config["durable_name"]
                    )
                    pending_msgs = consumer_info.num_pending
                    logger.info(
                        f"Consumer {config['durable_name']} has {pending_msgs} pending messages"
                    )
                except Exception:
                    pending_msgs = 0
                    logger.info(f"Consumer {config['durable_name']} not found")

                # Delete the consumer
                try:
                    await jetstream.delete_consumer(
                        stream=config["stream"], consumer=config["durable_name"]
                    )

                    status = "success"
                    message = f"Consumer '{config['durable_name']}' deleted successfully. Had {pending_msgs} pending messages."
                    logger.info(f"Successfully deleted consumer {config['durable_name']}")

                except Exception as delete_error:
                    if "not found" in str(delete_error).lower():
                        status = "success"
                        message = f"Consumer '{config['durable_name']}' was already deleted or did not exist."
                        logger.info(f"Consumer {config['durable_name']} was already deleted")
                    else:
                        status = "error"
                        message = f"Failed to delete consumer '{config['durable_name']}': {str(delete_error)}"
                        logger.error(
                            f"Failed to delete consumer {config['durable_name']}: {delete_error}"
                        )

                results.append(
                    ConsumerResetResponse(
                        consumer_name=config["durable_name"],
                        stream=config["stream"],
                        status=status,
                        message=message,
                    )
                )

            except Exception as e:
                logger.error(f"Error processing consumer {consumer_type}: {e}")
                results.append(
                    ConsumerResetResponse(
                        consumer_name=config["durable_name"],
                        stream=config["stream"],
                        status="error",
                        message=f"Error processing consumer: {str(e)}",
                    )
                )

        await nats_conn.close()
        return results

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

        except Exception as e:
            if "not found" in str(e).lower():
                raise HTTPException(
                    status_code=404,
                    detail=f"Consumer '{config['durable_name']}' not found",
                ) from e
            else:
                raise e

        await nats_conn.close()
        return result

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Error getting consumer info for %s", consumer_type)
        raise HTTPException(status_code=500, detail="Failed to get consumer info") from exc
