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
"""Test device data."""

# flake8: noqa

ARISTA_MAC_TABLE = [
    {
        "command": "show mac address-table",
        "result": {
            "multicastTable": {"tableEntries": []},
            "unicastTable": {
                "tableEntries": [
                    {
                        "macAddress": "b8:3f:d2:bf:3e:22",
                        "lastMove": 1709197358.909267,
                        "interface": "Ethernet1",
                        "moves": 1,
                        "entryType": "dynamic",
                        "vlanId": 13,
                    },
                    {
                        "macAddress": "cc:48:3a:1e:c5:4c",
                        "lastMove": 1716671524.569158,
                        "interface": "Ethernet3",
                        "moves": 1,
                        "entryType": "dynamic",
                        "vlanId": 13,
                    },
                    {
                        "macAddress": "cc:48:3a:1f:79:44",
                        "lastMove": 1722124624.08915,
                        "interface": "Ethernet2",
                        "moves": 1,
                        "entryType": "dynamic",
                        "vlanId": 13,
                    },
                ]
            },
        },
        "encoding": "json",
    }
]


ARISTA_INTERFACE_STATUS = [
    {
        "command": "show interface status",
        "result": {
            "interfaceStatuses": {
                "Ethernet1": {
                    "vlanInformation": {
                        "interfaceMode": "bridged",
                        "vlanId": 677,
                        "interfaceForwardingModel": "bridged",
                    },
                    "bandwidth": 1000000000,
                    "interfaceType": "1000BASE-T",
                    "description": "rno1-m04-C10-server1.lab1 dpu2",
                    "autoNegotiateActive": True,
                    "duplex": "duplexFull",
                    "autoNegotigateActive": True,
                    "linkStatus": "connected",
                    "lineProtocolStatus": "up",
                },
                "Ethernet2": {
                    "vlanInformation": {
                        "interfaceMode": "bridged",
                        "vlanId": 677,
                        "interfaceForwardingModel": "bridged",
                    },
                    "bandwidth": 1000000000,
                    "interfaceType": "1000BASE-T",
                    "description": "rno1-m04-C10-server1.lab1",
                    "autoNegotiateActive": True,
                    "duplex": "duplexFull",
                    "autoNegotigateActive": True,
                    "linkStatus": "connected",
                    "lineProtocolStatus": "up",
                },
                "Ethernet3": {
                    "vlanInformation": {
                        "interfaceMode": "bridged",
                        "vlanId": 677,
                        "interfaceForwardingModel": "bridged",
                    },
                    "bandwidth": 1000000000,
                    "interfaceType": "1000BASE-T",
                    "description": "rno1-m04-C10-core1-cg1.tan.lab1",
                    "autoNegotiateActive": True,
                    "duplex": "duplexFull",
                    "autoNegotigateActive": True,
                    "linkStatus": "connected",
                    "lineProtocolStatus": "up",
                },
                "Ethernet4": {
                    "vlanInformation": {
                        "interfaceMode": "bridged",
                        "vlanId": 677,
                        "interfaceForwardingModel": "bridged",
                    },
                    "bandwidth": 1000000000,
                    "interfaceType": "1000BASE-T",
                    "description": "rno1-m04-C10-spine1-hss.tan.lab1",
                    "autoNegotiateActive": True,
                    "duplex": "duplexFull",
                    "autoNegotigateActive": True,
                    "linkStatus": "connected",
                    "lineProtocolStatus": "up",
                },
            }
        },
    }
]


ARISTA_ARP_TABLE = [
    {
        "command": "show ip arp",
        "result": {
            "dynamicEntries": 25,
            "ipV4Neighbors": [
                {
                    "hwAddress": "e023.ffd1.8695",
                    "address": "10.180.166.1",
                    "interface": "Vlan677, Ethernet52",
                    "age": 0,
                },
                {
                    "hwAddress": "9c63.c009.25f2",
                    "address": "10.180.166.11",
                    "interface": "Vlan677, Ethernet2",
                    "age": 13314,
                },
                {
                    "hwAddress": "7483.ef20.f558",
                    "address": "10.180.166.12",
                    "interface": "Vlan677, Ethernet1",
                    "age": 3234,
                },
            ],
            "notLearnedEntries": 11,
            "totalEntries": 25,
            "staticEntries": 0,
        },
    }
]


ARISTA_LLDP_NEIGHBORS = [
    {
        "command": "show lldp neighbors detail",
        "result": {
            "lldpNeighbors": {
                "Ethernet1": {
                    "lldpNeighborInfo": [
                        {
                            "chassisIdType": "macAddress",
                            "chassisId": "2899.3aee.669e",
                            "systemName": "PDX01-M01-G29-IPMITOR-01",
                            "systemDescription": "Arista Networks EOS version 4.28.9M running on an Arista Networks DCS-7010T-48",
                            "systemCapabilities": {"bridge": True, "router": True},
                            "lastContactTime": 1718403557.5882056,
                            "neighborDiscoveryTime": 1709191327.1552835,
                            "lastChangeTime": 1709191327.1552835,
                            "ttl": 120,
                            "managementAddresses": [
                                {
                                    "addressType": "ipv4",
                                    "address": "10.217.194.220",
                                    "interfaceNumType": "ifIndex",
                                    "interfaceNum": 5000000,
                                    "oidString": "",
                                }
                            ],
                            "neighborInterfaceInfo": {
                                "interfaceIdType": "interfaceName",
                                "interfaceId": '"Ethernet51"',
                                "interfaceId_v2": "Ethernet51",
                                "interfaceDescription": "Uplink to IPMISPINE-01:Eth1",
                                "linkAggregation8023Status": "capableAndDisabled",
                                "linkAggregation8023InterfaceId": 0,
                                "maxFrameSize": 9416,
                                "portVlanId": 0,
                                "vlanNames": {},
                                "unknownOrgDefinedTlvs": [],
                                "ztpBootVlan": 0,
                                "portAndProtocolVlanSupported": {},
                                "portAndProtocolVlanEnabled": {},
                                "protocolIdentityInfo": [],
                                "autoNegAdvertisedCapabilities": [],
                                "unknownTlvs": [],
                            },
                        }
                    ]
                },
                "Ethernet2": {
                    "lldpNeighborInfo": [
                        {
                            "chassisIdType": "macAddress",
                            "chassisId": "2899.3aec.4c84",
                            "systemName": "PDX01-M01-H29-IPMITOR-01",
                            "systemDescription": "Arista Networks EOS version 4.28.9M running on an Arista Networks DCS-7010T-48",
                            "systemCapabilities": {"bridge": True, "router": True},
                            "lastContactTime": 1718403544.9843848,
                            "neighborDiscoveryTime": 1709188118.1678758,
                            "lastChangeTime": 1709188118.1678758,
                            "ttl": 120,
                            "managementAddresses": [
                                {
                                    "addressType": "ipv4",
                                    "address": "10.217.194.249",
                                    "interfaceNumType": "ifIndex",
                                    "interfaceNum": 5000000,
                                    "oidString": "",
                                }
                            ],
                            "neighborInterfaceInfo": {
                                "interfaceIdType": "interfaceName",
                                "interfaceId": '"Ethernet51"',
                                "interfaceId_v2": "Ethernet51",
                                "interfaceDescription": "Uplink to IPMISPINE-01:Eth1",
                                "linkAggregation8023Status": "capableAndDisabled",
                                "linkAggregation8023InterfaceId": 0,
                                "maxFrameSize": 9416,
                                "portVlanId": 0,
                                "vlanNames": {},
                                "unknownOrgDefinedTlvs": [],
                                "ztpBootVlan": 0,
                                "portAndProtocolVlanSupported": {},
                                "portAndProtocolVlanEnabled": {},
                                "protocolIdentityInfo": [],
                                "autoNegAdvertisedCapabilities": [],
                                "unknownTlvs": [],
                            },
                        }
                    ]
                },
                "Ethernet3": {
                    "lldpNeighborInfo": [
                        {
                            "chassisIdType": "macAddress",
                            "chassisId": "1070.fd55.2646",
                            "systemName": "PDX01-M01-D36-IPMIFAB-01",
                            "systemDescription": "Cumulus Linux version 5.2.0 running on Mellanox Technologies Ltd. MSN3420",
                            "systemCapabilities": {"bridge": False, "router": True},
                            "lastContactTime": 1718403563.0636237,
                            "neighborDiscoveryTime": 1707459875.8630328,
                            "lastChangeTime": 1707459875.8630328,
                            "ttl": 120,
                            "managementAddresses": [
                                {
                                    "addressType": "ipv4",
                                    "address": "10.217.194.11",
                                    "interfaceNumType": "ifIndex",
                                    "interfaceNum": 1,
                                    "oidString": "",
                                },
                                {
                                    "addressType": "ipv6",
                                    "address": "fe80::1270:fdff:fe55:2646",
                                    "interfaceNumType": "ifIndex",
                                    "interfaceNum": 2,
                                    "oidString": "",
                                },
                            ],
                            "neighborInterfaceInfo": {
                                "interfaceIdType": "interfaceName",
                                "interfaceId": '"swp52"',
                                "interfaceId_v2": "swp52",
                                "interfaceDescription": "PDX01-M01-G29-IPMISPINE-01:Et3",
                                "linkAggregation8023Status": "capableAndDisabled",
                                "linkAggregation8023InterfaceId": 0,
                                "maxFrameSize": 9214,
                                "vlanNames": {},
                                "medInfo": {
                                    "capabilities": {
                                        "capabilities": True,
                                        "networkPolicy": True,
                                        "location": True,
                                        "extendedPse": True,
                                        "extendedPd": True,
                                        "inventory": True,
                                        "deviceType": "networkConnectivity",
                                    },
                                    "networkPolicies": [],
                                    "firmwareRevisionTlvInfo": "5.11",
                                    "softwareRevisionTlvInfo": "5.2.0",
                                    "serialNumberTlvInfo": "MT2213J12202",
                                    "manufacturerNameTlvInfo": "Mellanox Technologies Ltd.",
                                    "modelNameTlvInfo": "MSN3420",
                                },
                                "unknownOrgDefinedTlvs": [],
                                "ztpBootVlan": 0,
                                "portAndProtocolVlanSupported": {},
                                "portAndProtocolVlanEnabled": {},
                                "protocolIdentityInfo": [],
                                "autoNegCapability": "capableAndEnabled",
                                "autoNegAdvertisedCapabilities": ["Other"],
                                "operMauType": "10GBASE-LR",
                                "unknownTlvs": [],
                            },
                        }
                    ]
                },
                "Ethernet4": {
                    "lldpNeighborInfo": [
                        {
                            "chassisIdType": "macAddress",
                            "chassisId": "b8ce.f6e7.3386",
                            "systemName": "PDX01-M01-C36-IPMIFAB-01",
                            "systemDescription": "Cumulus Linux version 5.2.0 running on Mellanox Technologies Ltd. MSN3420",
                            "systemCapabilities": {"bridge": False, "router": True},
                            "lastContactTime": 1718403561.5472672,
                            "neighborDiscoveryTime": 1707459875.783456,
                            "lastChangeTime": 1707459875.783456,
                            "ttl": 120,
                            "managementAddresses": [
                                {
                                    "addressType": "ipv4",
                                    "address": "10.217.194.10",
                                    "interfaceNumType": "ifIndex",
                                    "interfaceNum": 1,
                                    "oidString": "",
                                },
                                {
                                    "addressType": "ipv6",
                                    "address": "fe80::bace:f6ff:fee7:3386",
                                    "interfaceNumType": "ifIndex",
                                    "interfaceNum": 2,
                                    "oidString": "",
                                },
                            ],
                            "neighborInterfaceInfo": {
                                "interfaceIdType": "interfaceName",
                                "interfaceId": '"swp52"',
                                "interfaceId_v2": "swp52",
                                "interfaceDescription": "PDX01-M01-G29-IPMISPINE-01:Et4",
                                "linkAggregation8023Status": "capableAndDisabled",
                                "linkAggregation8023InterfaceId": 0,
                                "maxFrameSize": 9214,
                                "vlanNames": {},
                                "medInfo": {
                                    "capabilities": {
                                        "capabilities": True,
                                        "networkPolicy": True,
                                        "location": True,
                                        "extendedPse": True,
                                        "extendedPd": True,
                                        "inventory": True,
                                        "deviceType": "networkConnectivity",
                                    },
                                    "networkPolicies": [],
                                    "firmwareRevisionTlvInfo": "5.11",
                                    "softwareRevisionTlvInfo": "5.2.0",
                                    "serialNumberTlvInfo": "MT2128X09595",
                                    "manufacturerNameTlvInfo": "Mellanox Technologies Ltd.",
                                    "modelNameTlvInfo": "MSN3420",
                                },
                                "unknownOrgDefinedTlvs": [],
                                "ztpBootVlan": 0,
                                "portAndProtocolVlanSupported": {},
                                "portAndProtocolVlanEnabled": {},
                                "protocolIdentityInfo": [],
                                "autoNegCapability": "capableAndEnabled",
                                "autoNegAdvertisedCapabilities": ["Other"],
                                "operMauType": "10GBASE-LR",
                                "unknownTlvs": [],
                            },
                        }
                    ]
                },
            }
        },
    }
]


CUMULUS_INTERFACES = {
    "eth0": {
        "ifindex": 2,
        "ip": {"address": {"10.180.166.11/26": {}, "fe80::9e63:c0ff:fe09:25f2/64": {}}},
        "link": {
            "auto-negotiate": "on",
            "duplex": "full",
            "mac": "9c:63:c0:09:25:f2",
            "mtu": 1500,
            "speed": "1G",
            "state": {"up": {}},
            "stats": {
                "carrier-transitions": 2,
                "in-bytes": 93128486,
                "in-drops": 0,
                "in-errors": 0,
                "in-pkts": 512136,
                "out-bytes": 7782751,
                "out-drops": 0,
                "out-errors": 0,
                "out-pkts": 39159,
            },
            "troubleshooting-info": None,
        },
        "lldp": {
            "dcbx-ets-config-tlv": "off",
            "dcbx-ets-recomm-tlv": "off",
            "dcbx-pfc-tlv": "off",
            "neighbor": {
                "rno1-m04-C10-leaf1.smn.lab1": {
                    "age": "698044",
                    "bridge": {"untagged": 677, "vlan": {}},
                    "chassis": {
                        "capability": {"is-bridge": {}, "is-router": {}},
                        "chassis-id": "fc:59:c0:3d:4c:cb",
                        "management-address-ipv4": "10.180.166.2",
                        "system-description": (
                            "Arista Networks EOS version 4.26.0F running on an Arista"
                            " Networks DCS-7010TX-48"
                        ),
                        "system-name": "rno1-m04-C10-leaf1.smn.lab1",
                    },
                    "lldp-med": {
                        "capability": {"capabilities": {}},
                        "device-type": "Network Connectivity Device",
                        "inventory": {},
                    },
                    "port": {
                        "description": "",
                        "name": "Ethernet2",
                        "pmd-autoneg": {},
                        "ttl": 120,
                        "type": "ifname",
                    },
                }
            },
        },
        "type": "eth",
    },
    "lo": {
        "ifindex": 1,
        "ip": {"address": {"10.180.166.129/32": {}, "127.0.0.1/8": {}, "::1/128": {}}},
        "link": {
            "mac": "00:00:00:00:00:00",
            "mtu": 65536,
            "state": {"up": {}},
            "stats": {
                "carrier-transitions": 0,
                "in-bytes": 50544494,
                "in-drops": 0,
                "in-errors": 0,
                "in-pkts": 774798,
                "out-bytes": 50544494,
                "out-drops": 0,
                "out-errors": 0,
                "out-pkts": 774798,
            },
        },
        "type": "loopback",
    },
    "mgmt": {
        "ifindex": 70,
        "ip": {"address": {"127.0.0.1/8": {}, "::1/128": {}}},
        "link": {
            "mac": "b2:ff:14:dc:8a:04",
            "mtu": 65575,
            "state": {"up": {}},
            "stats": {
                "carrier-transitions": 0,
                "in-bytes": 43080930,
                "in-drops": 0,
                "in-errors": 0,
                "in-pkts": 137257,
                "out-bytes": 986776,
                "out-drops": 5201,
                "out-errors": 0,
                "out-pkts": 6857,
            },
        },
        "type": "vrf",
    },
    "swp1": {
        "ifindex": 4,
        "ip": {"address": {}},
        "link": {
            "auto-negotiate": "on",
            "mac": "9c:05:91:a2:e6:f0",
            "mtu": 9216,
            "state": {"down": {}},
            "stats": {
                "carrier-transitions": 1,
                "in-bytes": 0,
                "in-drops": 0,
                "in-errors": 0,
                "in-pkts": 0,
                "out-bytes": 0,
                "out-drops": 0,
                "out-errors": 0,
                "out-pkts": 0,
            },
            "troubleshooting-info": "Cable is unplugged.",
        },
        "port-security": {"enable": "off"},
        "type": "swp",
    },
    "swp10": {
        "ifindex": 13,
        "ip": {"address": {}},
        "link": {
            "auto-negotiate": "on",
            "mac": "9c:05:91:a2:e6:d4",
            "mtu": 9216,
            "state": {"down": {}},
            "stats": {
                "carrier-transitions": 1,
                "in-bytes": 0,
                "in-drops": 0,
                "in-errors": 0,
                "in-pkts": 0,
                "out-bytes": 0,
                "out-drops": 0,
                "out-errors": 0,
                "out-pkts": 0,
            },
            "troubleshooting-info": "Cable is unplugged.",
        },
        "port-security": {"enable": "off"},
        "type": "swp",
    },
    "swp11": {
        "ifindex": 14,
        "ip": {"address": {}},
        "link": {
            "auto-negotiate": "on",
            "mac": "9c:05:91:a2:e6:dc",
            "mtu": 9216,
            "state": {"down": {}},
            "stats": {
                "carrier-transitions": 1,
                "in-bytes": 0,
                "in-drops": 0,
                "in-errors": 0,
                "in-pkts": 0,
                "out-bytes": 0,
                "out-drops": 0,
                "out-errors": 0,
                "out-pkts": 0,
            },
            "troubleshooting-info": "Cable is unplugged.",
        },
        "port-security": {"enable": "off"},
        "type": "swp",
    },
    "swp12": {
        "ifindex": 15,
        "ip": {"address": {}},
        "link": {
            "auto-negotiate": "on",
            "mac": "9c:05:91:a2:e6:d8",
            "mtu": 9216,
            "state": {"down": {}},
            "stats": {
                "carrier-transitions": 1,
                "in-bytes": 0,
                "in-drops": 0,
                "in-errors": 0,
                "in-pkts": 0,
                "out-bytes": 0,
                "out-drops": 0,
                "out-errors": 0,
                "out-pkts": 0,
            },
            "troubleshooting-info": "Cable is unplugged.",
        },
        "port-security": {"enable": "off"},
        "type": "swp",
    },
    "br_default": {
        "ifindex": 58,
        "ip": {"address": {"fe80::fe6a:1cff:fe05:83bf/64": {}}},
        "link": {
            "mac": "fc:6a:1c:05:83:bf",
            "mtu": 9216,
            "state": {"up": {}},
            "stats": {
                "carrier-transitions": 2,
                "in-bytes": 718359214,
                "in-drops": 0,
                "in-errors": 0,
                "in-pkts": 9202673,
                "out-bytes": 841301123,
                "out-drops": 0,
                "out-errors": 0,
                "out-pkts": 8404708,
            },
        },
        "type": "bridge",
    },
}


CUMULUS_BRIDGE_DOMAINS = {
    "br_default": {
        "ageing": 1800,
        "encap": "802.1Q",
        "mdb": {},
        "multicast": {"snooping": {"enable": "off", "querier": {"enable": "off"}}},
        "port": {
            "bond1": {
                "flags": "flood,learning,mcast_flood",
                "state": "forwarding",
                "vlan": {
                    "121": {"fwd-state": "forwarding", "tag-state": "tagged"},
                    "122": {"fwd-state": "forwarding", "tag-state": "untagged"},
                },
            },
            "bond2": {
                "flags": "flood,learning,mcast_flood",
                "state": "forwarding",
                "vlan": {
                    "121": {"fwd-state": "forwarding", "tag-state": "tagged"},
                    "122": {"fwd-state": "forwarding", "tag-state": "untagged"},
                },
            },
        },
    }
}


CUMULUS_MAC_TABLE = {
    "1": {
        "age": 21,
        "bridge-domain": "br_default",
        "interface": "swp30s0",
        "last-update": 1414,
        "mac": "48:b0:2d:6c:8d:6f",
        "vlan": 121,
    },
    "10": {
        "age": 1369,
        "bridge-domain": "br_default",
        "entry-type": "static",
        "interface": "bond5",
        "last-update": 1369,
        "mac": "48:b0:2d:38:15:db",
        "vlan": 122,
    },
    "11": {
        "age": 12,
        "bridge-domain": "br_default",
        "entry-type": "static",
        "interface": "bond5",
        "mac": "48:b0:2d:81:8c:85",
        "vlan": 122,
    },
    "12": {
        "age": 1468,
        "bridge-domain": "br_default",
        "entry-type": "permanent",
        "interface": "bond5",
        "last-update": 1468,
        "mac": "48:b0:2d:ec:3c:d4",
    },
    "13": {
        "age": 1468,
        "bridge-domain": "br_default",
        "entry-type": "permanent",
        "interface": "br_default",
        "last-update": 1468,
        "mac": "48:b0:2d:ec:3c:10",
    },
    "14": {
        "age": 1554,
        "bridge-domain": "br_default",
        "entry-type": "permanent",
        "interface": "br_default",
        "last-update": 1468,
        "mac": "48:b0:2d:ec:3c:10",
    },
}

CUMULUS_MAC_TABLE_DUPS = {
    "1": {
        "age": 21,
        "bridge-domain": "br_default",
        "interface": "swp30s0",
        "last-update": 1414,
        "mac": "48:b0:2d:6c:8d:6f",
        "vlan": 121,
    },
    "2": {
        "age": 1369,
        "bridge-domain": "br_default",
        "entry-type": "static",
        "interface": "swp30s0",
        "last-update": 1369,
        "mac": "48:b0:2d:6c:8d:6f",
        "vlan": 122,
    },
}

CUMULUS_INTERFACES_MINIMAL = {
    "br_default": {"ifindex": 58},
    "STBOND1": {"ifindex": 70},
    "STBOND1.19": {"ifindex": 74},
    "eth0": {"ifindex": 2, "type": "eth"},
    "swp1": {"ifindex": 4, "type": "swp"},
    "swp2": {"ifindex": 13, "type": "swp"},
}

CUMULUS_ARP_TABLE = [
    {"ipv4": {}, "ipv6": {}},
    {
        "ipv4": {
            "10.91.144.10": {
                "flag": {},
                "lladdr": "c0:69:11:9f:f7:b1",
                "state": {"reachable": {}},
            }
        },
        "ipv6": {
            "fe80::c269:11ff:fe9f:f7b1": {
                "flag": {},
                "lladdr": "c0:69:11:9f:f7:b1",
                "state": {"stale": {}},
            }
        },
    },
    {
        "ipv4": {
            "10.91.144.14": {
                "flag": {},
                "lladdr": "c0:69:11:9f:ee:69",
                "state": {"reachable": {}},
            }
        },
        "ipv6": {
            "fe80::c269:11ff:fe9f:ee69": {
                "flag": {},
                "lladdr": "c0:69:11:9f:ee:69",
                "state": {"stale": {}},
            }
        },
    },
    {
        "ipv4": {
            "169.254.0.1": {
                "flag": {},
                "lladdr": "9c:05:91:ba:34:68",
                "state": {"permanent": {}},
            }
        },
        "ipv6": {
            "fe80::9e05:91ff:feba:3468": {
                "flag": {"is-router": {}},
                "lladdr": "9c:05:91:ba:34:68",
                "state": {"reachable": {}},
            }
        },
    },
    {
        "ipv4": {
            "169.254.0.1": {
                "flag": {},
                "lladdr": "9c:05:91:ba:34:6a",
                "state": {"permanent": {}},
            }
        },
        "ipv6": {
            "fe80::9e05:91ff:feba:346a": {
                "flag": {"is-router": {}},
                "lladdr": "9c:05:91:ba:34:6a",
                "state": {"reachable": {}},
            }
        },
    },
]


ARISTA_HOSTNAME = [
    {
        "command": "show hostname",
        "result": {
            "fqdn": "rno1-m04-C10-leaf1.smn.lab1",
            "hostname": "rno1-m04-C10-leaf1.smn.lab1",
        },
    }
]


CUMULUS_SYSTEM = {
    "build": "Cumulus Linux 5.6.0",
    "hostname": "rno1-m04-c10-leaf2-hss-tan-lab1",
    "timezone": "Etc/UTC",
    "uptime": 8282449,
}


CUMULUS_DIFF = {
    "added": {
        "interface": {
            "lo": {"description": None},
            "swp1": {"description": "test description"},
        },
        "service": {"syslog": {"mgmt": None}},
    },
    "removed": {
        "interface": {"lo": {"description": "test123"}, "swp1": {"description": None}},
        "service": {
            "syslog": {"mgmt": {"server": {"1.1.1.1": {"port": 32365, "protocol": "udp"}}}}
        },
    },
}

CUMULUS_DHCP_DIFF = {
    "added": {
        "service": {
            "dhcp-relay": {
                "default": {
                    "interface": {
                        "swp49": {},
                        "swp50": {},
                        "vlan112": {},
                        "vlan12": {},
                    },
                    "server": {"10.91.208.128": {}},
                }
            }
        }
    },
    "removed": {"service": {"dhcp-relay": None}},
}


CUMULUS_INVALID_CONFIG = {
    "state": "invalid",
    "transition": {
        "issue": {
            "00000": {
                "code": "generic",
                "data": {
                    "msg": "User cumulus already exists in the system. NVUE will not take over the user"
                },
                "message": "User cumulus already exists in the system. NVUE will not take over the user",
                "severity": "error",
            },
            "00001": {
                "code": "generic",
                "data": {
                    "msg": "User svc-ngc-cfa-nv-config-manager already exists in the system. NVUE will not take over the user"
                },
                "message": "User svc-ngc-cfa-nv-config-manager already exists in the system. NVUE will not take over the user",
                "severity": "error",
            },
        },
        "progress": "Invalid config",
    },
}

# Used to exercise ConfigApplyFailureException and format_nvue_apply_error
CUMULUS_IGNORE_FAIL_CONFIG = {
    "state": "ignore_fail",
    "transition": {
        "progress": "Failure during apply. Ignore?",
        "issue": {
            "00000": {
                "code": "systemctl",
                "message": "Unable to reload-or-restart services (frr): Job for frr.service failed.",
                "severity": "error",
            },
        },
    },
}

# ignore_fail with no transition (covers branch that uses default error message)
CUMULUS_IGNORE_FAIL_NO_TRANSITION = {
    "state": "ignore_fail",
}


INTENDED_NEIGHBORS_V2 = {
    "data": {
        "interfaces": [
            {
                "name": "swp27",
                "tags": [],
                "connected_interface": {
                    "name": "swp27",
                    "mac_address": None,
                    "module": {
                        "device": {
                            "name": "AZ51-AD505-IPMISPINE-02",
                            "serial": "M2NJ33L000C",
                            "role": {"name": "Azure-Ipmispine"},
                            "rack": {"name": "AD505"},
                            "position": 1,
                        }
                    },
                    "device": None,
                },
            },
            {
                "name": "swp28",
                "tags": [{"name": "cable-validation-ignore"}],
                "connected_interface": {
                    "name": "swp28",
                    "mac_address": None,
                    "device": {
                        "name": "AZ51-AD505-IPMISPINE-02",
                        "serial": "M2NJ33L000C",
                        "role": {"name": "Azure-Ipmispine"},
                        "rack": {"name": "AD505"},
                        "position": 1,
                    },
                    "module": None,
                },
            },
        ]
    }
}
