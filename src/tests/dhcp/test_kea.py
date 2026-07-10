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

from nv_config_manager.dhcp.kea import KeaClient, LeaseCommand


@pytest.mark.parametrize("command", ["lease4-get", "lease4-del"])
async def test_lease_command_forwards_restricted_kea_request(command: LeaseCommand) -> None:
    """Verify lease commands are sent to KEA using its control-agent envelope."""
    response = [{"result": 0, "text": "success"}]

    with aioresponses() as mocked:
        mocked.post("http://kea.example.com:8000/", payload=response)
        async with KeaClient(host="kea.example.com", port=8000) as client:
            result = await client.lease_command(command, "7.245.196.5")

        request = mocked.requests[("POST", URL("http://kea.example.com:8000/"))][0]

    assert result == response
    assert request.kwargs["json"] == {
        "command": command,
        "service": ["dhcp4"],
        "arguments": {"ip-address": "7.245.196.5"},
    }


async def test_lease_command_raises_for_kea_http_error() -> None:
    """Verify non-success KEA transport responses are not silently returned."""
    with aioresponses() as mocked:
        mocked.post("http://kea.example.com:8000/", status=503)
        async with KeaClient(host="kea.example.com", port=8000) as client:
            with pytest.raises(ClientResponseError) as exc_info:
                await client.lease_command("lease4-get", "7.245.196.5")

    assert exc_info.value.status == 503
