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
"""Render service activities."""

import asyncio
from datetime import datetime, timedelta

from pydantic import BaseModel
from temporalio import activity
from temporalio.exceptions import ApplicationError

from nv_config_manager.common.client.render import FileCommit
from nv_config_manager.common.config import ConfigStoreType, config_store_client, render_client
from nv_config_manager.temporal.common.mixins.device import NetworkDeviceData, Platform


class ExecuteRenderInput(BaseModel):
    """Input for executing a render operation."""

    device_id: str
    workflow_id: str


class ExecuteRenderOutput(BaseModel):
    """Output for render operation."""

    updated_files: list[FileCommit] = []

    def get_commit(self, filename: str) -> str | None:
        """Look up the commit ID for a given filename."""
        return next((fc.commit for fc in self.updated_files if fc.filename == filename), None)


@activity.defn
async def execute_render(
    activity_input: ExecuteRenderInput,
) -> ExecuteRenderOutput:
    """Execute a render operation for a device.

    Args:
        activity_input: Input containing the device ID

    Returns:
        ExecuteRenderOutput containing updated_files list
    """
    client = render_client()
    updated_files = await client.execute_render(
        activity_input.device_id, activity_input.workflow_id
    )
    return ExecuteRenderOutput(updated_files=updated_files)


class ValidateRenderedImageChangeInput(BaseModel):
    """Input for validating the rendered image change."""

    device_data: NetworkDeviceData
    desired_image: str


class ValidateRenderedPasswordChangeInput(BaseModel):
    """Input for validating the rendered password change."""

    device_data: NetworkDeviceData
    desired_password_string: str


# Temporary hack until we can get proper mTLS certificates issued
# for communication between the render service and the temporal service
@activity.defn
async def validate_rendered_image_change(
    activity_input: ValidateRenderedImageChangeInput,
) -> bool:
    """Validate the rendered image change.

    Polls the file content every 30 seconds for up to 5 minutes to check for the desired image version.
    Raises ApplicationError if the timeout is reached.
    """
    client = config_store_client(ConfigStoreType.INTENDED)
    boot_script = None
    if activity_input.device_data.platform == Platform.CUMULUS_LINUX:
        boot_script = "boot-script"

    if not boot_script:
        raise NotImplementedError(f"Platform {activity_input.device_data.platform} not supported")

    start_time = datetime.now()
    timeout = timedelta(minutes=5)
    poll_interval = 30  # seconds

    async with client:
        while datetime.now() - start_time < timeout:
            # Send heartbeat with progress information
            elapsed_minutes = (datetime.now() - start_time).total_seconds() / 60
            activity.heartbeat(f"Validating render ({elapsed_minutes:.0f}m)")

            config_file = await client.load_file(
                device_uuid=activity_input.device_data.id, filename=boot_script
            )
            if f"VERSION_ID={activity_input.desired_image}" in config_file.content:
                return True
            await asyncio.sleep(poll_interval)

    raise ApplicationError(
        f"Timeout waiting for image version {activity_input.desired_image} to be present in boot script"
    )


@activity.defn
async def validate_rendered_password_change(
    activity_input: ValidateRenderedPasswordChangeInput,
) -> bool:
    """Validate the rendered password change.

    Polls the file content every 30 seconds for up to 5 minutes to check for the desired password string.
    Raises ApplicationError if the timeout is reached.
    """
    client = config_store_client(ConfigStoreType.INTENDED)
    filename = activity_input.device_data.intended_config_file

    if not filename:
        raise ApplicationError(
            f"No intended config filename found for device {activity_input.device_data.name}"
        )

    start_time = datetime.now()
    timeout = timedelta(minutes=5)
    poll_interval = 30  # seconds

    async with client:
        while datetime.now() - start_time < timeout:
            # Send heartbeat with progress information
            elapsed_minutes = (datetime.now() - start_time).total_seconds() / 60
            activity.heartbeat(f"Validating password render ({elapsed_minutes:.0f}m)")

            config_file = await client.load_file(
                device_uuid=activity_input.device_data.id, filename=filename
            )
            if activity_input.desired_password_string in config_file.content:
                return True
            await asyncio.sleep(poll_interval)

    raise ApplicationError(
        f"Timeout waiting for password string {activity_input.desired_password_string} to be present in configuration"
    )
