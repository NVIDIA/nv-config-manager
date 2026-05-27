#  SPDX-FileCopyrightText: Copyright (c) "2025" NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#  SPDX-License-Identifier: Apache-2.0
#
#  Licensed under the Apache License, Version 2.0 (the "License")
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Shared mock data aligned with the mock topology and render tests."""

CONFIG_STORE_UI_URL = "https://config-manager.example.com/"
CONFIG_STORE_HTTP_URL = "http://config-manager.example.com/"
CONFIG_STORE_API_URL = "https://api.config-store.config-manager.example.com/"
TEST_HTTP_HOST = "config-manager.local"

TEMPLATE_VERSION = "engine=nv-config-manager-templates:0.0.1;plugins=none"

CONFIG_PATH = "startup.yaml"
BACKUP_CONFIG_PATH = "startup.yaml"

REGION_NAME = "Region-A"
SITE_NAME = "DC01"
SECOND_SITE_NAME = "TEST-SITE"
MODULE_NAME = "DC01 Module 1"
SECOND_MODULE_NAME = "TEST-SITE SUPERPOD 1 - test"
BUILDING_NAME = "DC01 Building 1"
FLOOR_NAME = "DC01 Building 1 Floor 1"
ROOM_NAME = "DC01 Building 1 Room 101"
EMPTY_LOCATION_NAME = "DC01 Empty Location"

TENANT_NAME = "Example Cloud"
SECOND_TENANT_NAME = "SuperPod"

MANUFACTURER_NAME = "NVIDIA"
MELLANOX_MANUFACTURER_NAME = "Mellanox"
SECOND_MANUFACTURER_NAME = "Arista"
DEVICE_TYPE_MODEL = "SN5600"
SECOND_DEVICE_TYPE_MODEL = "MSN4700-WS2RC"
THIRD_DEVICE_TYPE_MODEL = "MSN3700-CS2RC"
ARISTA_DEVICE_TYPE_MODEL = "DCS-7804R3-BND"
PLATFORM_NAME = "Cumulus Linux"
SECOND_PLATFORM_NAME = "MLNX-OS"
ARISTA_PLATFORM_NAME = "Arista EOS"

SPINE_ROLE_NAME = "TAN-Spine"
CORE_ROLE_NAME = "TAN-Core"
LEAF_ROLE_NAME = "TAN-Leaf"
ARISTA_LEAF_ROLE_NAME = "TAN-BBR"
AGGREGATE_ROLE_NAME = "SMN-Leaf"

DEVICE_NAME = "leaf1-hss1-cp1-tan1-dc01"
SECOND_DEVICE_NAME = "leaf2-hss1-cp1-tan1-dc01"
THIRD_DEVICE_NAME = "spine4-hss1-cp1-tan1-dc01"
FOURTH_DEVICE_NAME = "core1-cg1-cp1-tan1-dc01"
FIFTH_DEVICE_NAME = "core2-cg1-cp1-tan1-dc01"
ARISTA_DEVICE_NAME = "bbr1-cp1-tan1-dc01"
SECOND_ARISTA_DEVICE_NAME = "bbr2-cp1-tan1-dc01"
NON_MANAGED_DEVICE_NAME = "leaf2-cno1-cp1-tan1-dc01"
OVERDUE_DEVICE_NAME = "spine3-cno1-cp1-tan1-dc01"
CONFIG_STORE_DEVICE_NAME = "leaf1-cno1-cp1-tan1-dc01"
AGGREGATE_DEVICE_NAME = "leaf2-cp1-smn1-dc01"

RACK_1_NAME = "DC01-RACK-02"
RACK_2_NAME = "DC01-RACK-01"

TEST_RENDER_USER = "test user"
TEST_EVENT_USER = "testuser"
TEST_COMMIT_MESSAGE = "test commit message"
TEST_BACKUP_COMMIT_MESSAGE = "Device backup"
TEST_WORKFLOW_ID = "workflow-id"
TEST_BACKUP_WORKFLOW_ID = "backup-workflow-id"

TEST_INTENDED_COMMIT_ID = 12345
TEST_BACKUP_COMMIT_ID = 3
TEST_PREVIOUS_COMMIT_ID = 42
TEST_DEPLOYABLE_COMMIT_ID = 20
TEST_PENDING_DEPLOYED_COMMIT_ID = 7
TEST_MATCHING_COMMIT_ID = 99
TEST_UPDATED_COMMIT_ID = 456
TEST_UPDATED_DEPLOYED_COMMIT_ID = 789

TEST_RENDER_TIMESTAMP = "2024-04-04T15:41:22.083507"
TEST_API_TIMESTAMP = "2024-07-15T18:30:00+00:00"
