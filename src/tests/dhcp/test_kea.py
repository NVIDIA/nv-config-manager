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

import pytest
from aiohttp import ClientResponseError
from aioresponses import aioresponses
from yarl import URL

from nv_config_manager.dhcp.kea import KeaClient


@pytest.mark.parametrize(
    ("method_name", "operation"),
    [("get_lease", "get"), ("delete_lease", "del")],
)
async def test_lease_methods_wrap_kea_requests(method_name: str, operation: str) -> None:
    """Verify domain lease methods hide KEA's control-agent envelope."""
    response = [{"result": 0, "text": "success"}]

    with aioresponses() as mocked:
        mocked.post("http://kea.example.com:8000/", payload=response)
        async with KeaClient(host="kea.example.com", port=8000) as client:
            method = getattr(client, method_name)
            result = await method("2001:db8::5", version=6)

        request = mocked.requests[("POST", URL("http://kea.example.com:8000/"))][0]

    assert result == response
    assert request.kwargs["json"] == {
        "command": f"lease6-{operation}",
        "service": ["dhcp6"],
        "arguments": {
            "ip-address": "2001:db8::5",
            **({"type": "IA_NA"} if operation == "get" else {}),
        },
    }


async def test_get_lease_raises_for_kea_http_error() -> None:
    """Verify non-success KEA transport responses are not silently returned."""
    with aioresponses() as mocked:
        mocked.post("http://kea.example.com:8000/", status=503)
        async with KeaClient(host="kea.example.com", port=8000) as client:
            with pytest.raises(ClientResponseError) as exc_info:
                await client.get_lease("7.245.196.5")

    assert exc_info.value.status == 503


async def test_get_lease_page_forwards_bounded_request() -> None:
    """Verify lease inventory uses KEA pagination rather than get-all."""
    response = [{"result": 0, "arguments": {"leases": []}}]

    with aioresponses() as mocked:
        mocked.post("http://kea.example.com:8000/", payload=response)
        async with KeaClient(host="kea.example.com", port=8000) as client:
            result = await client.get_lease_page(
                limit=75,
                version=6,
                from_address="2001:db8::5",
            )

        request = mocked.requests[("POST", URL("http://kea.example.com:8000/"))][0]

    assert result == response
    assert request.kwargs["json"] == {
        "command": "lease6-get-page",
        "service": ["dhcp6"],
        "arguments": {"from": "2001:db8::5", "limit": 75},
    }


async def test_get_statistics_forwards_service_version() -> None:
    """Verify dashboard statistics target the requested KEA service."""
    response = [{"result": 0, "arguments": {"assigned-addresses": [[2, "timestamp"]]}}]

    with aioresponses() as mocked:
        mocked.post("http://kea.example.com:8000/", payload=response)
        async with KeaClient(host="kea.example.com", port=8000) as client:
            result = await client.get_statistics(version=4)

        request = mocked.requests[("POST", URL("http://kea.example.com:8000/"))][0]

    assert result == response
    assert request.kwargs["json"] == {
        "command": "statistic-get-all",
        "service": ["dhcp4"],
        "arguments": {},
    }
