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
"""Tests for the Redfish client."""

from nv_config_manager.temporal.client.redfish import (
    RedfishConnection,
    RedfishHost,
    RedfishVendor,
)


def test_redfish_session_verifies_server_certificate() -> None:
    host = RedfishHost(address="bmc.example.com", vendor=RedfishVendor.DELL)
    connection = RedfishConnection(host, username="admin", password="secret")

    session = connection.get_session()

    assert session.verify is True
