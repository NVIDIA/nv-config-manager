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
"""Tests for Temporal Codec Server API endpoints."""

import base64
import gzip

from fastapi.testclient import TestClient
from google.protobuf import json_format
from temporalio.api.common.v1 import Payload, Payloads

from nv_config_manager.temporal.api.main import app


def test_codec_server_decode_decompresses_payload():
    """POST /v1/codec/decode with compressed payload returns decoded payload."""
    # Build one compressed payload (as the UI would send it)
    inner = Payload(data=b'{"workflow": "input"}')
    compressed_data = gzip.compress(inner.SerializeToString())
    payload = Payload(
        metadata={"encoding": b"binary/gzip"},
        data=compressed_data,
    )
    payloads_msg = Payloads(payloads=[payload])
    body = json_format.MessageToJson(payloads_msg)

    client = TestClient(app)
    response = client.post("/v1/codec/decode", content=body)

    assert response.status_code == 200
    data = response.json()
    assert "payloads" in data
    assert len(data["payloads"]) == 1
    # Decoded payload data should be the original inner payload (base64 in JSON)
    decoded_b64 = data["payloads"][0].get("data")
    assert decoded_b64 is not None
    decoded_bytes = base64.b64decode(decoded_b64)
    assert b'"workflow": "input"' in decoded_bytes


def test_codec_server_decode_invalid_json_returns_400():
    """POST /v1/codec/decode with invalid JSON returns 400."""
    client = TestClient(app)
    response = client.post("/v1/codec/decode", content="not json")
    assert response.status_code == 400
