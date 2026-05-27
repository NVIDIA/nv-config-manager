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
"""Temporal Codec Server HTTP endpoints for Web UI payload decoding.

Implements the Temporal Codec Server protocol so the Temporal Web UI can
display decoded (decompressed) payloads instead of raw compressed data.
"""

from __future__ import annotations

import gzip
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from google.protobuf import json_format, message
from temporalio.api.common.v1 import Payloads

from nv_config_manager.common.log import LogCategory, get_logger
from nv_config_manager.temporal.converter import CompressionPayloadCodec

logger = get_logger(__name__, category=LogCategory.TEMPORAL_API)

router = APIRouter(prefix="/codec", tags=["codec"])
_codec = CompressionPayloadCodec()


async def _parse_payloads(request: Request) -> Payloads:
    """Parse a Protobuf Payloads message from the request body."""
    try:
        body = await request.body()
        return json_format.Parse(body, Payloads())
    except json_format.ParseError as exc:
        logger.exception("Codec server failed to parse request body")
        raise HTTPException(status_code=400, detail="Invalid payloads JSON") from exc
    except (TypeError, ValueError) as exc:
        logger.exception("Codec server received invalid payloads structure")
        raise HTTPException(status_code=400, detail="Invalid payloads structure") from exc


async def _decode_handler(request: Request) -> dict[str, Any]:
    """Parse JSON Payloads from body, decode via codec, return JSON Payloads."""
    payloads_msg = await _parse_payloads(request)
    try:
        decoded = await _codec.decode(list(payloads_msg.payloads))
    except gzip.BadGzipFile as exc:
        logger.exception("Codec server decode failed: invalid gzip data")
        raise HTTPException(status_code=500, detail="Invalid gzip data") from exc
    except (UnicodeDecodeError, message.DecodeError) as exc:
        logger.exception("Codec server decode failed: invalid protobuf data")
        raise HTTPException(status_code=500, detail="Invalid protobuf data") from exc
    result = Payloads(payloads=decoded)
    return json_format.MessageToDict(result)


async def _encode_handler(request: Request) -> dict[str, Any]:
    """Parse JSON Payloads from body, encode via codec, return JSON Payloads."""
    payloads_msg = await _parse_payloads(request)
    try:
        encoded = await _codec.encode(list(payloads_msg.payloads))
    except gzip.BadGzipFile as exc:
        logger.exception("Codec server encode failed: invalid gzip data")
        raise HTTPException(status_code=500, detail="Invalid gzip data") from exc
    except (UnicodeDecodeError, message.DecodeError) as exc:
        logger.exception("Codec server encode failed: invalid protobuf data")
        raise HTTPException(status_code=500, detail="Invalid protobuf data") from exc
    result = Payloads(payloads=encoded)
    return json_format.MessageToDict(result)


@router.post(
    "/decode",
    summary="Decode payloads",
)
async def decode(request: Request) -> dict[str, Any]:
    """Decode (decompress) payloads for Temporal Web UI display."""
    return await _decode_handler(request)


@router.post(
    "/encode",
    summary="Encode payloads",
)
async def encode(request: Request) -> dict[str, Any]:
    """Encode (compress) payloads for Temporal Web UI when editing."""
    return await _encode_handler(request)
