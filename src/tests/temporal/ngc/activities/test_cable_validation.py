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
"""Test suite for cable validation activities."""

from typing import Any

import pytest
from aioresponses import aioresponses

from nv_config_manager.temporal.client.device import InterfaceNeighborData
from nv_config_manager.temporal.ngc.activities.cable_validation import (
    CableValidationResultData,
    DecorateResultActivityInput,
    DecorateResultActivityOutput,
    InvalidCable,
    decorate_result,
)
from tests.temporal.ngc.activities.test_cable_validation_activity_data import (
    NAUTOBOT_INTERFACE_RESPONSE,
    VALIDATION_RESULTS,
)


def construct_input(json: Any) -> DecorateResultActivityInput:
    return DecorateResultActivityInput(
        devices={device: CableValidationResultData(**data) for device, data in json.items()}
    )


@pytest.mark.asyncio
async def test_decorate_results():
    with aioresponses() as m:
        m.post(
            "https://nautobot.example.com/api/graphql/",
            payload=NAUTOBOT_INTERFACE_RESPONSE,
        )

        result = await decorate_result(construct_input(VALIDATION_RESULTS))

    assert result == DecorateResultActivityOutput(
        devices={
            "AZ50-AG422-GW-02": CableValidationResultData(
                interfaces={
                    "swp31": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet17/1",
                            macs=[],
                            device_name="TYO27-0101-0801-01T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp32": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet18/1",
                            macs=[],
                            device_name="TYO27-0101-0801-01T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp33": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet19/1",
                            macs=[],
                            device_name="TYO27-0101-0801-01T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp34": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet20/1",
                            macs=[],
                            device_name="TYO27-0101-0801-01T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp35": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet21/1",
                            macs=[],
                            device_name="TYO27-0101-0801-01T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp36": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet22/1",
                            macs=[],
                            device_name="TYO27-0101-0801-01T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp37": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet23/1",
                            macs=[],
                            device_name="TYO27-0101-0801-01T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp38": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet24/1",
                            macs=[],
                            device_name="TYO27-0101-0801-01T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp39": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet25/1",
                            macs=[],
                            device_name="TYO27-0101-0801-01T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp40": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet26/1",
                            macs=[],
                            device_name="TYO27-0101-0801-01T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp41": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet27/1",
                            macs=[],
                            device_name="TYO27-0101-0801-01T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp42": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet28/1",
                            macs=[],
                            device_name="TYO27-0101-0801-01T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp43": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet29/1",
                            macs=[],
                            device_name="TYO27-0101-0801-01T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp44": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet30/1",
                            macs=[],
                            device_name="TYO27-0101-0801-01T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp45": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet31/1",
                            macs=[],
                            device_name="TYO27-0101-0801-01T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp46": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet32/1",
                            macs=[],
                            device_name="TYO27-0101-0801-01T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp47": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet17/1",
                            macs=[],
                            device_name="TYO27-0101-0801-02T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp48": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet18/1",
                            macs=[],
                            device_name="TYO27-0101-0801-02T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp49": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet19/1",
                            macs=[],
                            device_name="TYO27-0101-0801-02T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp50": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet20/1",
                            macs=[],
                            device_name="TYO27-0101-0801-02T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp51": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet21/1",
                            macs=[],
                            device_name="TYO27-0101-0801-02T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp52": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet22/1",
                            macs=[],
                            device_name="TYO27-0101-0801-02T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp53": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet23/1",
                            macs=[],
                            device_name="TYO27-0101-0801-02T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp54": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet24/1",
                            macs=[],
                            device_name="TYO27-0101-0801-02T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp55": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet25/1",
                            macs=[],
                            device_name="TYO27-0101-0801-02T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp56": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet26/1",
                            macs=[],
                            device_name="TYO27-0101-0801-02T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp57": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet27/1",
                            macs=[],
                            device_name="TYO27-0101-0801-02T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp58": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet28/1",
                            macs=[],
                            device_name="TYO27-0101-0801-02T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp59": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet29/1",
                            macs=[],
                            device_name="TYO27-0101-0801-02T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp60": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet30/1",
                            macs=[],
                            device_name="TYO27-0101-0801-02T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp61": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet31/1",
                            macs=[],
                            device_name="TYO27-0101-0801-02T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                    "swp62": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="Ethernet32/1",
                            macs=[],
                            device_name="TYO27-0101-0801-02T0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                    ),
                },
                device=None,
            ),
            "AZ50-AG422-LEAF-01": CableValidationResultData(interfaces={}, device=None),
            "AZ50-AN422-IPMITOR-03": CableValidationResultData(
                interfaces={
                    "swp34": InvalidCable(
                        intended=InterfaceNeighborData(
                            name="Server BMC",
                            macs=["08-8F-C3-A6-35-F5"],
                            device_name="AZ50-AT422-OVX-Server-01",
                            device_serial="J701C0T7",
                            device_role="tenant-a-device",
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                        actual=InterfaceNeighborData(
                            name="DPU BMC",
                            macs=[
                                "B8-3F-D2-E9-B1-48",
                                "B8-3F-D2-E9-B1-54",
                                "FC-6A-1C-05-BD-41",
                            ],
                            device_name="AZ50-AT422-OVX-Server-01-dpu0",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=True,
                            ts_info=None,
                        ),
                    ),
                    "swp35": InvalidCable(
                        intended=None,
                        actual=InterfaceNeighborData(
                            name="p1",
                            macs=[],
                            device_name="gpu56-gp1-cin1-sitea-dpu39",
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=True,
                            ts_info=None,
                        ),
                    ),
                },
                device=None,
            ),
            "AZ50-AO425-IPMITOR-03": CableValidationResultData(
                interfaces={
                    "swp19": InvalidCable(
                        intended=InterfaceNeighborData(
                            name="DPU BMC",
                            macs=["A0-88-C2-9B-22-60"],
                            device_name="AZ50-AZ431-OVX-Server-02-dpu0",
                            device_serial="0",
                            device_role="tenant-a-device",
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                        actual=InterfaceNeighborData(
                            name="FC-6A-1C-05-8A-6E",
                            macs=["FC-6A-1C-05-8A-6E"],
                            device_name=None,
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=False,
                            ts_info=None,
                        ),
                    ),
                    "swp23": InvalidCable(
                        intended=InterfaceNeighborData(
                            name="DPU BMC",
                            macs=[],
                            device_name="AZ50-AJ434-OVX-Server-02-dpu0",
                            device_serial="0",
                            device_role="tenant-a-device",
                            device_rack=None,
                            device_position=None,
                            link_up=None,
                            ts_info=None,
                        ),
                        actual=InterfaceNeighborData(
                            name="A0-88-C2-00-B5-F2",
                            macs=[
                                "A0-88-C2-00-B5-F2",
                                "A0-88-C2-00-B5-FE",
                                "FC-6A-1C-05-8A-6A",
                            ],
                            device_name=None,
                            device_serial=None,
                            device_role=None,
                            device_rack=None,
                            device_position=None,
                            link_up=True,
                            ts_info=None,
                        ),
                    ),
                },
                device=None,
            ),
        }
    )
