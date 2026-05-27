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
"""NB NATS extras.* Event Handlers."""

from typing import Any

from nv_config_manager.common.log import LogCategory, get_logger
from nv_config_manager.render.events.util import (
    DeviceNotEnabledError,
    build_commit_message,
    extract_user,
    get_managed_device_uuids,
    queue_render,
)

FILTER_FIELDS = [
    "locations",
    "roles",
    "device_types",
    "platforms",
    "tenant_groups",
    "tenants",
    "device_redundancy_groups",
    "tags",
]

logger = get_logger(__name__, category=LogCategory.RENDER_EVENT)


async def configcontext(data: dict[str, Any]) -> None:
    """extras.configcontext event handler."""
    filter_kwargs = {}
    record = data["record"]
    for field in FILTER_FIELDS:
        if not record[field]:
            # Skip empty lists
            continue
        filter_kwargs[field] = [entry["id"] for entry in record[field] if "id" in entry]

    affected_devices = get_managed_device_uuids(**filter_kwargs)
    if affected_devices:
        logger.info(
            "Identified %s affected managed devices for config-context update %s",
            len(affected_devices),
            record["name"],
        )
        try:
            commit_message = build_commit_message(data)
            user = extract_user(data)
            timestamp = data["@timestamp"]
            # Removing concurrent execution to address issues
            # with NATS connections
            # await asyncio.gather(
            #     *[
            #         queue_render(
            #             device_uuid=device_uuid,
            #             commit_message=commit_message,
            #             user=user,
            #             timestamp=timestamp,
            #         )
            #         for device_uuid in affected_devices
            #     ]
            # )
            for device_uuid in affected_devices:
                try:
                    await queue_render(
                        device_uuid=device_uuid,
                        commit_message=commit_message,
                        user=user,
                        timestamp=timestamp,
                    )
                except DeviceNotEnabledError:
                    logger.info(
                        "Device %s is not enabled for configuration renders, skipping",
                        device_uuid,
                    )
        except Exception:
            logger.exception(
                "Error queuing render jobs for config-context update %s", record["name"]
            )
        logger.info(
            "Queued %s render jobs for config-context update %s",
            len(affected_devices),
            record["name"],
        )
    else:
        logger.info(
            "No affected managed devices found for config-context update %s",
            record["name"],
        )
