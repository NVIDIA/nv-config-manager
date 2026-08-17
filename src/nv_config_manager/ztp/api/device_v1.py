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
"""V1 Device API Endpoints."""

import aiohttp
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from nv_config_manager.common.auth import auth_required, require_sso_or_device
from nv_config_manager.common.client import ConfigStoreException, ConfigStoreFileNotFound
from nv_config_manager.common.config import get_storage_client, temporal_client
from nv_config_manager.common.log import LogCategory, get_logger
from nv_config_manager.ztp.api.schemas import ChecksumResponse
from nv_config_manager.ztp.api.storage_clients import (
    StorageUnavailableError,
    get_object_storage_client,
    guarded_storage,
)
from nv_config_manager.ztp.api.streaming import create_object_storage_streaming_response
from nv_config_manager.ztp.nautobot import NautobotClient, NotFoundError
from nv_config_manager.ztp.storage import ObjectStorageNotFoundException

logger = get_logger(__name__, category=LogCategory.ZTP_API)

router = APIRouter(prefix="/device", tags=["device"], responses={404: {"description": "Not found"}})

# HTTP statuses the Config Store client itself retries; if one still surfaces it
# means the backend is transiently unhealthy, so treat it as retryable (503).
_CONFIG_STORE_RETRYABLE_STATUSES = {429, 500, 502, 503, 504}


def _config_store_error_is_transient(exc: ConfigStoreException) -> bool:
    """Return True if a ConfigStoreException stems from a transient backend blip.

    The Config Store client wraps the underlying failure as the ``__cause__``:
    a raw ``aiohttp.ClientError`` (connection reset/disconnect/timeout) is always
    transient, while a ``ClientResponseError`` is transient only for retryable
    5xx/429 statuses (a 4xx is a genuine client error and stays a 500).
    """
    cause = exc.__cause__
    if isinstance(cause, aiohttp.ClientResponseError):
        return cause.status in _CONFIG_STORE_RETRYABLE_STATUSES
    return isinstance(cause, aiohttp.ClientError)


async def _authorize_request(request: Request, device_uuid: str) -> None:
    # This endpoint has sensitive content, check if coming from the
    # device associated with this configuration

    if not auth_required():
        return

    identity = await require_sso_or_device(request)
    if identity is not None and identity.source != "anonymous":
        # Request came in through SSO, mTLS, SPIFFE, or JWT/OIDC — the
        # shared auth layer has validated it, so no further IP check needed.
        return

    try:
        nb_client = NautobotClient()
        async with nb_client:
            device_data = await nb_client.get_device_data(device_uuid)
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    allowed_addresses = device_data.addresses
    allowed_addresses.append("127.0.0.1")

    if request.client is None:
        raise HTTPException(status_code=403, detail="Unable to determine client IP address.")

    client_ip = request.client.host

    if client_ip not in allowed_addresses:
        logger.warning(
            "Unauthorized ZTP request for device %s from %s (allowed: %s)",
            device_uuid,
            client_ip,
            allowed_addresses,
        )
        raise HTTPException(
            status_code=403,
            detail=(
                f"Unauthorized: client IP {client_ip} is not associated with this device. "
                "Ensure the requesting IP is assigned to the device in Nautobot."
            ),
        )


@router.get("/{device_uuid}/boot-script", response_class=PlainTextResponse)
async def load_bootscript(device_uuid: str, request: Request) -> PlainTextResponse:
    """Load the bootscript for the given nautobot device UUID."""
    return await load_configuration(device_uuid, "boot-script", request)


@router.get("/{device_uuid}/config/{configlet}", response_class=PlainTextResponse)
async def load_configuration(
    device_uuid: str, configlet: str, request: Request
) -> PlainTextResponse:
    """Load the specified configuration file for the given nautobot device UUID."""
    await _authorize_request(request, device_uuid)
    try:
        nb_client = NautobotClient()
        async with nb_client:
            device_data = await nb_client.get_device_data(device_uuid)
        content = await device_data.load_file(configlet)
        return PlainTextResponse(content)
    except (NotFoundError, ConfigStoreFileNotFound) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ConfigStoreException as exc:
        # A transient Config Store blip (connection reset/disconnect, or a 5xx/429
        # that outlived the client's own retries) should shed as a retryable 503
        # so the device retries, not masquerade as a hard 500. Genuine errors
        # (e.g. a 4xx) stay 500.
        if _config_store_error_is_transient(exc):
            raise StorageUnavailableError(str(exc)) from exc
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# ONIE process pulls image first, then looks for $url.ztp to load the ZTP script
# where $url is whats supplied by DHCP in boot-file-name
# Add some onie shortcuts so that image and boot script can be selected from the
# same DHCP boot-file-name option
@router.get("/{device_uuid}/onie", response_class=PlainTextResponse)
@router.get("/{device_uuid}/firmware", response_class=StreamingResponse)
async def load_firmware(device_uuid: str, request: Request) -> StreamingResponse:
    """Load the firmware for the given device."""
    await _authorize_request(request, device_uuid)
    try:
        nb_client = NautobotClient()
        async with nb_client:
            device_data = await nb_client.get_device_data(device_uuid)
        if device_data.platform is None or device_data.version is None:
            raise HTTPException(status_code=404, detail="Device firware data not found")
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    storage_client = get_storage_client()
    try:
        return await create_object_storage_streaming_response(
            storage_client,
            storage_client.get_firmware_object,
            device_data.platform,
            device_data.version,
            request=request,
        )
    except ObjectStorageNotFoundException as exc:
        raise HTTPException(status_code=404, detail="Firmware image not found in S3.") from exc


@router.get("/{device_uuid}/firmware/checksum")
async def load_firmware_checksum(device_uuid: str, request: Request) -> ChecksumResponse:
    """Load the firmware checksum for the given device."""
    await _authorize_request(request, device_uuid)
    try:
        nb_client = NautobotClient()
        async with nb_client:
            device_data = await nb_client.get_device_data(device_uuid)
        if device_data.platform is None or device_data.version is None:
            raise HTTPException(status_code=404, detail="Device firware data not found")
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    storage_client = await get_object_storage_client()
    try:
        checksum = await guarded_storage(
            lambda: storage_client.get_firmware_checksum(device_data.platform, device_data.version)
        )
        return ChecksumResponse(checksum=checksum)
    except ObjectStorageNotFoundException as exc:
        raise HTTPException(status_code=404, detail="Firmware image not found in S3.") from exc


@router.post("/{device_uuid}/provisioned")
async def mark_provisioned(device_uuid: str, request: Request) -> str:
    """Mark the ZTP process complete for the given device."""
    await _authorize_request(request, device_uuid)
    nb_client = NautobotClient()
    async with nb_client:
        await nb_client.set_status_provisioned(device_uuid)
    # Trigger a backup workflow
    try:
        client = temporal_client()
        async with client:
            await client.invoke_backup_workflow(device_uuid)
    except Exception as e:
        logger.error("Error invoking backup workflow: %s", e)
    return "OK"


class ValidateSerialBody(BaseModel):
    """Request body for serial number validation."""

    serial: str


def _compare_serials(expected: str, observed: str) -> bool:
    # Some devices may report part number and serial in the CID field
    # in the DHCP request in which case we'll have to update nautobot
    # with the extended serial data for DHCP to work
    # We've also seen some devices that may be reporting the serial
    # as the part number + serial within the OS but not in the CID field
    # so we'll allow comparisons both directions to avoid conflicts
    if observed.lower().endswith(expected.lower()):
        return True
    if expected.lower().endswith(observed.lower()):
        return True
    return False


@router.post("/{device_uuid}/validate_serial")
async def validate_serial(device_uuid: str, body: ValidateSerialBody, request: Request) -> str:
    """Validate the device serial number matches nautobot."""
    await _authorize_request(request, device_uuid)
    nb_client = NautobotClient()
    try:
        async with nb_client:
            expected_serial = await nb_client.get_device_serial(device_uuid)
        if not _compare_serials(expected_serial, body.serial):
            logger.error(
                "Serial number mismatch observed on device %s, expected: %s, observed: %s.",
                device_uuid,
                expected_serial,
                body.serial,
            )
            raise HTTPException(
                status_code=400,
                detail="Serial number does not match device in Nautobot.",
            )
        return "OK"
    except NotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
