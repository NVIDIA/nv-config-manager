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
"""Cable validation activity test data."""

NAUTOBOT_INTERFACE_RESPONSE = {
    "data": {
        "interfaces": [
            {
                "id": "734102e2-16d6-4bfe-a120-46d53109f7e8",
                "name": "ipmi0",
                "mac_address": "08:8F:C3:A6:37:85",
                "device": {"name": "AZ50-AK422-OVX-Server-03"},
            },
            {
                "id": "2fbb667c-6e91-484e-830e-6f1d23c79bea",
                "name": "ipmi0",
                "mac_address": "08:8F:C3:A6:0D:35",
                "device": {"name": "AZ50-AK431-OVX-Server-02"},
            },
            {
                "id": "11eaf20e-6538-45b6-a284-7dc25b694e74",
                "name": "Server BMC",
                "mac_address": "08:8F:C3:A6:35:F5",
                "device": {"name": "AZ50-AT422-OVX-Server-01"},
            },
            {
                "id": "c6f27d81-558f-4f44-a092-966c62f3897c",
                "name": "ipmi0",
                "mac_address": "08:8F:C3:A6:35:F5",
                "device": {"name": "AZ50-AT422-OVX-Server-01"},
            },
            {
                "id": "2827d873-1410-41b8-a646-738d0a4b60f4",
                "name": "DPU BMC",
                "mac_address": "B8:3F:D2:E9:B1:48",
                "device": {"name": "AZ50-AT422-OVX-Server-01-dpu0"},
            },
            {
                "id": "0830fd47-523c-4136-99f8-aafd4f93c4c8",
                "name": "p1",
                "mac_address": "58:A2:E1:D4:5C:E4",
                "device": {"name": "gpu56-gp1-cin1-sitea-dpu39"},
            },
        ]
    }
}


VALIDATION_RESULTS = {
    "AZ50-AG422-GW-02": {
        "interfaces": {
            "swp31": {
                "actual": {
                    "device_name": "TYO27-0101-0801-01T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet17/1",
                },
                "intended": None,
            },
            "swp32": {
                "actual": {
                    "device_name": "TYO27-0101-0801-01T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet18/1",
                },
                "intended": None,
            },
            "swp33": {
                "actual": {
                    "device_name": "TYO27-0101-0801-01T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet19/1",
                },
                "intended": None,
            },
            "swp34": {
                "actual": {
                    "device_name": "TYO27-0101-0801-01T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet20/1",
                },
                "intended": None,
            },
            "swp35": {
                "actual": {
                    "device_name": "TYO27-0101-0801-01T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet21/1",
                },
                "intended": None,
            },
            "swp36": {
                "actual": {
                    "device_name": "TYO27-0101-0801-01T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet22/1",
                },
                "intended": None,
            },
            "swp37": {
                "actual": {
                    "device_name": "TYO27-0101-0801-01T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet23/1",
                },
                "intended": None,
            },
            "swp38": {
                "actual": {
                    "device_name": "TYO27-0101-0801-01T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet24/1",
                },
                "intended": None,
            },
            "swp39": {
                "actual": {
                    "device_name": "TYO27-0101-0801-01T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet25/1",
                },
                "intended": None,
            },
            "swp40": {
                "actual": {
                    "device_name": "TYO27-0101-0801-01T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet26/1",
                },
                "intended": None,
            },
            "swp41": {
                "actual": {
                    "device_name": "TYO27-0101-0801-01T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet27/1",
                },
                "intended": None,
            },
            "swp42": {
                "actual": {
                    "device_name": "TYO27-0101-0801-01T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet28/1",
                },
                "intended": None,
            },
            "swp43": {
                "actual": {
                    "device_name": "TYO27-0101-0801-01T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet29/1",
                },
                "intended": None,
            },
            "swp44": {
                "actual": {
                    "device_name": "TYO27-0101-0801-01T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet30/1",
                },
                "intended": None,
            },
            "swp45": {
                "actual": {
                    "device_name": "TYO27-0101-0801-01T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet31/1",
                },
                "intended": None,
            },
            "swp46": {
                "actual": {
                    "device_name": "TYO27-0101-0801-01T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet32/1",
                },
                "intended": None,
            },
            "swp47": {
                "actual": {
                    "device_name": "TYO27-0101-0801-02T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet17/1",
                },
                "intended": None,
            },
            "swp48": {
                "actual": {
                    "device_name": "TYO27-0101-0801-02T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet18/1",
                },
                "intended": None,
            },
            "swp49": {
                "actual": {
                    "device_name": "TYO27-0101-0801-02T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet19/1",
                },
                "intended": None,
            },
            "swp50": {
                "actual": {
                    "device_name": "TYO27-0101-0801-02T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet20/1",
                },
                "intended": None,
            },
            "swp51": {
                "actual": {
                    "device_name": "TYO27-0101-0801-02T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet21/1",
                },
                "intended": None,
            },
            "swp52": {
                "actual": {
                    "device_name": "TYO27-0101-0801-02T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet22/1",
                },
                "intended": None,
            },
            "swp53": {
                "actual": {
                    "device_name": "TYO27-0101-0801-02T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet23/1",
                },
                "intended": None,
            },
            "swp54": {
                "actual": {
                    "device_name": "TYO27-0101-0801-02T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet24/1",
                },
                "intended": None,
            },
            "swp55": {
                "actual": {
                    "device_name": "TYO27-0101-0801-02T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet25/1",
                },
                "intended": None,
            },
            "swp56": {
                "actual": {
                    "device_name": "TYO27-0101-0801-02T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet26/1",
                },
                "intended": None,
            },
            "swp57": {
                "actual": {
                    "device_name": "TYO27-0101-0801-02T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet27/1",
                },
                "intended": None,
            },
            "swp58": {
                "actual": {
                    "device_name": "TYO27-0101-0801-02T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet28/1",
                },
                "intended": None,
            },
            "swp59": {
                "actual": {
                    "device_name": "TYO27-0101-0801-02T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet29/1",
                },
                "intended": None,
            },
            "swp60": {
                "actual": {
                    "device_name": "TYO27-0101-0801-02T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet30/1",
                },
                "intended": None,
            },
            "swp61": {
                "actual": {
                    "device_name": "TYO27-0101-0801-02T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet31/1",
                },
                "intended": None,
            },
            "swp62": {
                "actual": {
                    "device_name": "TYO27-0101-0801-02T0",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": None,
                    "macs": [],
                    "name": "Ethernet32/1",
                },
                "intended": None,
            },
        }
    },
    "AZ50-AG422-LEAF-01": {"interfaces": {}},
    "AZ50-AN422-IPMITOR-03": {
        "interfaces": {
            "swp34": {
                "actual": {
                    "device_name": None,
                    "device_role": None,
                    "device_serial": None,
                    "link_up": True,
                    "macs": [
                        "B8-3F-D2-E9-B1-48",
                        "B8-3F-D2-E9-B1-54",
                        "FC-6A-1C-05-BD-41",
                    ],
                    "name": None,
                },
                "intended": {
                    "device_name": "AZ50-AT422-OVX-Server-01",
                    "device_role": "tenant-a-device",
                    "device_serial": "J701C0T7",
                    "link_up": None,
                    "macs": ["08-8F-C3-A6-35-F5"],
                    "name": "Server BMC",
                },
            },
            "swp35": {
                "actual": {
                    "device_name": "host-203-0-113-43",
                    "device_role": None,
                    "device_serial": None,
                    "link_up": True,
                    "macs": [],
                    "name": "58-A2-E1-D4-5C-E4",
                },
                "intended": None,
            },
        }
    },
    "AZ50-AO425-IPMITOR-03": {
        "interfaces": {
            "swp19": {
                "actual": {
                    "device_name": None,
                    "device_role": None,
                    "device_serial": None,
                    "link_up": False,
                    "macs": ["FC-6A-1C-05-8A-6E"],
                    "name": None,
                },
                "intended": {
                    "device_name": "AZ50-AZ431-OVX-Server-02-dpu0",
                    "device_role": "tenant-a-device",
                    "device_serial": "0",
                    "link_up": None,
                    "macs": ["A0-88-C2-9B-22-60"],
                    "name": "DPU BMC",
                },
            },
            "swp23": {
                "actual": {
                    "device_name": None,
                    "device_role": None,
                    "device_serial": None,
                    "link_up": True,
                    "macs": [
                        "A0-88-C2-00-B5-F2",
                        "A0-88-C2-00-B5-FE",
                        "FC-6A-1C-05-8A-6A",
                    ],
                    "name": None,
                },
                "intended": {
                    "device_name": "AZ50-AJ434-OVX-Server-02-dpu0",
                    "device_role": "tenant-a-device",
                    "device_serial": "0",
                    "link_up": None,
                    "macs": [],
                    "name": "DPU BMC",
                },
            },
        }
    },
}
