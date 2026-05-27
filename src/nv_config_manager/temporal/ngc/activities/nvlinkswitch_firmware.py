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
"""NVLinkSwitch Firmware related activities."""

import asyncio
from datetime import datetime, timedelta
from typing import Any, cast

from pydantic import BaseModel
from temporalio import activity
from temporalio.exceptions import ApplicationError

from nv_config_manager.common.config import ConfigStoreType, config_store_client, ztp_client
from nv_config_manager.temporal.client.device import NetworkConnection, NetworkDeviceData
from nv_config_manager.temporal.client.nautobot import NautobotClient


class GetRunningFirmwareInput(BaseModel):
    """Input for getting running firmware versions."""

    device_data: NetworkDeviceData


class GetRunningFirmwareOutput(BaseModel):
    """Output for getting running firmware versions."""

    running_firmware: dict[str, str]


class CompareRunningDesiredInput(BaseModel):
    """Input for comparing running vs desired versions."""

    device_data: NetworkDeviceData
    running_os: str
    running_firmware: dict[str, str]
    bundle_version: str


class CompareRunningDesiredOutput(BaseModel):
    """Output for comparing running vs desired versions."""

    upgrade_needed: bool
    desired_os: str
    desired_firmware: dict[str, str]
    differences: dict[str, dict[str, str]]


class UpdateDeviceContextInput(BaseModel):
    """Input for updating device context."""

    device_data: NetworkDeviceData
    bundle_version: str


class ValidateRenderTargetsInput(BaseModel):
    """Input for validating render targets."""

    device_data: NetworkDeviceData
    desired_firmware: dict[str, str]


class ValidateTargetFilesInput(BaseModel):
    """Input for validating target files on ZTP server."""

    device_data: NetworkDeviceData
    desired_firmware: dict[str, str]


class RebootDeviceInput(BaseModel):
    """Input for rebooting device."""

    device_data: NetworkDeviceData


class RebootDeviceOutput(BaseModel):
    """Output for rebooting device."""

    start_time: str  # ISO format string


@activity.defn
def get_running_firmware(
    activity_input: GetRunningFirmwareInput,
) -> GetRunningFirmwareOutput:
    """Get the running firmware versions from the device."""
    device = NetworkConnection.from_device_data(activity_input.device_data)

    try:
        running_firmware = device.get_firmware_versions()

        # Transform to expected format (component -> version mapping)
        firmware_dict = {}
        for component, data in running_firmware.items():
            if isinstance(data, dict) and "actual-firmware" in data:
                firmware_dict[component.lower()] = data["actual-firmware"]
            else:
                firmware_dict[component.lower()] = str(data)

        return GetRunningFirmwareOutput(running_firmware=firmware_dict)
    except Exception as e:
        raise ApplicationError(f"Failed to get running firmware: {str(e)}") from e


@activity.defn
async def compare_running_desired(
    activity_input: CompareRunningDesiredInput,
) -> CompareRunningDesiredOutput:
    """Compare running vs desired firmware versions."""
    try:
        # Get desired firmware and OS from device config context with single API call
        desired_firmware, desired_os = await _get_desired_firmware_and_os_from_context(
            activity_input.device_data, activity_input.bundle_version
        )

        # Compare OS versions
        os_upgrade_needed = activity_input.running_os != desired_os

        # Compare firmware versions
        differences = {}
        for component, desired_version in desired_firmware.items():
            # Special handling for CPLD: NVLink switches report CPLD firmware as 'CPLD1'
            # but our config uses 'cpld', so we map desired 'cpld' to running 'cpld1'
            if component == "cpld":
                running_version = activity_input.running_firmware.get("cpld1", "")
            else:
                running_version = activity_input.running_firmware.get(component, "")

            if running_version != desired_version:
                differences[component] = {
                    "actual": running_version,
                    "expected": desired_version,
                }

        upgrade_needed = os_upgrade_needed or bool(differences)

        return CompareRunningDesiredOutput(
            upgrade_needed=upgrade_needed,
            desired_os=desired_os,
            desired_firmware=desired_firmware,
            differences=differences,
        )
    except Exception as e:
        raise ApplicationError(f"Failed to compare versions: {str(e)}") from e


@activity.defn
async def update_device_context(activity_input: UpdateDeviceContextInput) -> None:
    """Update local device context with firmware targets."""
    try:
        # Get the desired OS version from the firmware bundle
        _, desired_os = await _get_desired_firmware_and_os_from_context(
            activity_input.device_data, activity_input.bundle_version
        )

        client = NautobotClient()

        # Update both firmware bundle version and intended firmware context
        # This ensures templates have access to both the bundle config and the OS version
        context_update = {
            "firmware_bundle_version": activity_input.bundle_version,
            "intended-firmware": {"version": desired_os},
        }

        async with client:
            await client.merge_config_context(
                activity_input.device_data.id,
                context_update,
            )
    except Exception as e:
        raise ApplicationError(f"Failed to update device context: {str(e)}") from e


@activity.defn
async def validate_render_targets(activity_input: ValidateRenderTargetsInput) -> None:
    """Validate that render contains new firmware targets.

    Polls the rendered firmware commands file every 10 seconds for up to 3 minutes
    to check that all expected firmware file names from the bundle configuration
    are present in the rendered fwupdate-commands.txt file.
    """
    try:
        # Get device context once and extract all expected filenames
        config_context = await _get_device_config_context(activity_input.device_data)
        bundle_version = config_context.get("firmware_bundle_version")
        firmware_bundles = config_context.get("firmware_bundles", {})

        if bundle_version not in firmware_bundles:
            raise ApplicationError(f"Firmware bundle {bundle_version} not found")

        bundle = firmware_bundles[bundle_version]
        firmware_section = bundle.get("firmware", {})

        # Extract expected filenames for each component
        expected_files = {}
        for component in activity_input.desired_firmware.keys():
            component_info = firmware_section.get(component, {})
            if isinstance(component_info, dict) and "file" in component_info:
                expected_files[component] = component_info["file"]
            else:
                expected_files[component] = None

        # Validate that the firmware update commands template is rendered correctly
        config_client = config_store_client(ConfigStoreType.INTENDED)

        # Check for firmware update commands file
        fw_commands_filename = "fwupdate-commands.txt"

        start_time = datetime.now()
        timeout = timedelta(minutes=3)
        poll_interval = 10  # seconds
        missing_files: list[str] = []
        last_exception = None

        async with config_client:
            while datetime.now() - start_time < timeout:
                # Send heartbeat with progress information
                elapsed_minutes = (datetime.now() - start_time).total_seconds() / 60
                activity.heartbeat(f"Validating targets ({elapsed_minutes:.0f}m)")

                try:
                    fw_commands_file = await config_client.load_file(
                        device_uuid=activity_input.device_data.id,
                        filename=fw_commands_filename,
                    )
                    missing_files = []  # Reset for this iteration

                    for component, expected_filename in expected_files.items():
                        if expected_filename:
                            # Check if this filename appears in the rendered commands
                            if expected_filename not in fw_commands_file.content:
                                missing_files.append(f"{component}: {expected_filename}")
                        else:
                            missing_files.append(f"{component}: no file info found")

                    if not missing_files:
                        return  # All firmware files found in rendered config

                except Exception as e:
                    # File might not exist yet, continue polling
                    last_exception = e
                    pass

                await asyncio.sleep(poll_interval)

        # Build detailed error message
        error_msg = "Timeout waiting for firmware commands to be rendered with new targets. "
        if missing_files:
            error_msg += f"Last check showed missing files: {missing_files}"
        elif last_exception:
            error_msg += f"Unable to load file (path: {fw_commands_file}). Last exception: {str(last_exception)}"
        else:
            error_msg += "No successful file loads occurred."

        raise ApplicationError(error_msg)
    except Exception as e:
        raise ApplicationError(f"Failed to validate render targets: {str(e)}") from e


@activity.defn
async def validate_target_files(activity_input: ValidateTargetFilesInput) -> None:
    """Validate that target firmware files exist on ZTP server."""
    try:
        # Get device context once and extract all firmware file info and ZTP servers
        config_context = await _get_device_config_context(activity_input.device_data)

        # Extract firmware file paths for each component
        bundle_version = config_context.get("firmware_bundle_version", "1.2.2")
        firmware_bundles = config_context.get("firmware_bundles", {})

        if bundle_version not in firmware_bundles:
            raise ApplicationError(f"Firmware bundle {bundle_version} not found")

        bundle = firmware_bundles[bundle_version]
        firmware_section = bundle.get("firmware", {})

        # Extract s3_path for each component
        component_s3_paths = {}
        for component in activity_input.desired_firmware.keys():
            component_info = firmware_section.get(component, {})
            if isinstance(component_info, dict) and "s3_path" in component_info:
                component_s3_paths[component] = component_info["s3_path"]
            else:
                component_s3_paths[component] = None

        ztp = ztp_client()
        missing_files = []

        for component, s3_path in component_s3_paths.items():
            if s3_path:
                file_exists = await ztp.check_file_exists(s3_path)
                if not file_exists:
                    missing_files.append(f"{component}: {s3_path}")
            else:
                missing_files.append(f"{component}: no s3_path found in firmware info")

        if missing_files:
            raise ApplicationError(f"Firmware files not found on ZTP server: {missing_files}")

    except Exception as e:
        raise ApplicationError(f"Failed to validate target files: {str(e)}") from e


@activity.defn
def reboot_device(activity_input: RebootDeviceInput) -> RebootDeviceOutput:
    """Reboot device via NVUE API."""
    device = NetworkConnection.from_device_data(activity_input.device_data)

    try:
        # Reboot the switch (similar to audit_firmware.py logic)
        device.reboot()
        return RebootDeviceOutput(start_time=datetime.now().isoformat())
    except Exception as e:
        raise ApplicationError(f"Failed to initiate reboot: {str(e)}") from e


async def _get_device_config_context(device_data: NetworkDeviceData) -> dict[str, Any]:
    """Get device config context with single Nautobot call."""
    try:
        client = NautobotClient()
        query = """
        query ($id: ID!) {
          device(id: $id) {
            config_context
          }
        }
        """
        async with client:
            result = await client.graphql_query(query, {"id": device_data.id})
            return cast(dict[str, Any], result["data"]["device"]["config_context"])
    except Exception as e:
        raise ApplicationError(f"Failed to get device config context: {str(e)}") from e


async def _get_desired_firmware_and_os_from_context(
    device_data: NetworkDeviceData, bundle_version: str
) -> tuple[dict[str, str], str]:
    """Extract desired firmware versions and OS version from device config context with single API call."""
    try:
        config_context = await _get_device_config_context(device_data)

        # Extract firmware component versions from bundle
        firmware_bundles = config_context.get("firmware_bundles", {})
        if bundle_version not in firmware_bundles:
            raise ApplicationError(f"Firmware bundle {bundle_version} not found")

        bundle = firmware_bundles[bundle_version]
        firmware_section = bundle.get("firmware", {})

        # Build desired firmware mapping
        desired_firmware = {}
        for component, component_data in firmware_section.items():
            if isinstance(component_data, dict):
                # Get the reported_version from the component configuration
                reported_version = component_data.get("reported_version", "")
                if not reported_version:
                    raise ApplicationError(
                        f"No 'reported_version' found for {component} in bundle {bundle_version}. "
                        "Please ensure each firmware component includes a 'reported_version' field "
                        "with the actual version string that devices report after upgrade."
                    )
                desired_firmware[component.lower()] = reported_version

        # Get desired OS version
        nv_os = bundle.get("nv_os", {})
        desired_os = nv_os.get("version", "")

        return desired_firmware, desired_os
    except Exception as e:
        raise ApplicationError(f"Failed to get desired firmware and OS: {str(e)}") from e
