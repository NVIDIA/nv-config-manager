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
from __future__ import annotations

import json
from typing import Any

from nv_config_manager.common.client.dhcp import _response_payload


class InvalidJSONResponse:
    async def json(self) -> Any:
        raise json.JSONDecodeError("invalid", "not-json", 0)

    async def text(self) -> str:
        return "not-json"


async def test_response_payload_falls_back_to_text_for_invalid_json() -> None:
    assert await _response_payload(InvalidJSONResponse()) == "not-json"  # type: ignore[arg-type]
