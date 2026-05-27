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
from unittest.mock import patch

from ruamel.yaml import YAML

from nv_config_manager.temporal.client.air import AirDevice
from nv_config_manager.temporal.ngc.activities.air import (
    ConfigTestInput,
    validate_configuration_against_air_device,
)


def test_test_configuration_against_air_device():
    config = """
- set:
    system:
        aaa:
            tacacs:
                server:
                    '1':
                        host: 1.1.1.1
                        secret: tacacs-secret
            user:
                cumulus:
                    hashed-password: cumulus
                    role: system-admin
                svc-ngc-cfa-nv-config-manager:
                    hashed-password: svc-ngc-cfa-nv-config-manager
                    role: system-admin
    vrf:
        default:
            router:
                bgp:
                    peer-group:
                        PEERGROUP:
                            password: bgppassword
"""

    expected_sanitized_config = """
- set:
    system:
        aaa:
            tacacs:
                server:
                    '1':
                        host: 1.1.1.1
                        secret: DuMMyP4SSW0RD!
            user:
                nv-config-manager-air-integration:
                    password: nv-config-manager-air-integration-password
                    role: system-admin
    vrf:
        default:
            router:
                bgp:
                    peer-group:
                        PEERGROUP:
                            password: DuMMyP4SSW0RD!
"""

    with (
        patch("nv_config_manager.temporal.ngc.activities.air.CumulusConnection") as mock_connection,
        patch("nv_config_manager.temporal.ngc.activities.air.AirClient") as mock_air_client,
    ):
        # Mock the AirClient configuration
        mock_client_instance = mock_air_client.return_value
        mock_client_instance.cfg = {
            "temporal.air": {
                "air_node_user": "nv-config-manager-air-integration",
                "air_node_password": "nv-config-manager-air-integration-password",
            }
        }

        mock_connection.return_value.perform_candidate_diff.return_value = None
        result = validate_configuration_against_air_device(
            ConfigTestInput(
                node=AirDevice(id="1", name="test", worker_ip="192.168.1.1", api_port=8000),
                config=config,
            )
        )
        assert result.error is None

        mock_connection.return_value.perform_candidate_diff.assert_called_once()
        actual_config = mock_connection.return_value.perform_candidate_diff.call_args[0][0]
        expected_obj = YAML().load(expected_sanitized_config)
        actual_obj = YAML().load(actual_config)
        assert actual_obj == expected_obj, (
            f"Config mismatch:\nExpected: {expected_obj}\nActual: {actual_obj}"
        )
