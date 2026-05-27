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
"""Tests for Temporal payload compression codec."""

import pytest
from temporalio.api.common.v1 import Payload

from nv_config_manager.temporal.converter import (
    COMPRESSION_ENCODING,
    CompressionPayloadCodec,
    get_data_converter,
)


@pytest.mark.asyncio
async def test_compression_codec_encodes_with_gzip_metadata():
    """Encode sets binary/gzip encoding metadata on payloads."""
    codec = CompressionPayloadCodec()
    payload = Payload(data=b'{"key": "value"}')
    encoded = await codec.encode([payload])
    assert len(encoded) == 1
    assert encoded[0].metadata.get("encoding", b"").decode() == COMPRESSION_ENCODING
    assert len(encoded[0].data) > 0


@pytest.mark.asyncio
async def test_compression_codec_reduces_size_for_compressible_data():
    """Encode produces smaller payload for repetitive/compressible content."""
    codec = CompressionPayloadCodec()
    # Repetitive content compresses well
    raw = b'{"config": "' + (b"line with repeated text " * 100) + b'"}'
    payload = Payload(data=raw)
    original_size = len(payload.SerializeToString())
    encoded = await codec.encode([payload])
    assert len(encoded) == 1
    # Compressed serialized form should be smaller than original
    assert len(encoded[0].data) < original_size


@pytest.mark.asyncio
async def test_compression_codec_round_trip():
    """Encode then decode returns the original payload."""
    codec = CompressionPayloadCodec()
    payload = Payload(data=b'{"workflow": "input", "large": "payload"}')
    encoded = await codec.encode([payload])
    decoded = await codec.decode(encoded)
    assert len(decoded) == 1
    assert decoded[0].data == payload.data
    assert decoded[0].metadata == payload.metadata


@pytest.mark.asyncio
async def test_compression_codec_passes_through_unknown_encoding():
    """Decode leaves payloads without our encoding unchanged."""
    codec = CompressionPayloadCodec()
    # Payload that was not compressed by us (e.g. from before codec was enabled)
    payload = Payload(
        data=b'{"legacy": true}',
        metadata={"encoding": b"json/plain"},
    )
    decoded = await codec.decode([payload])
    assert len(decoded) == 1
    assert decoded[0].data == payload.data
    assert decoded[0].metadata == payload.metadata


@pytest.mark.asyncio
async def test_get_data_converter_returns_converter_with_codec():
    """get_data_converter() returns a converter that uses our codec."""
    converter = get_data_converter()
    assert converter.payload_codec is not None
    assert isinstance(converter.payload_codec, CompressionPayloadCodec)
