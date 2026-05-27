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
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

import pytest

from nv_config_manager.render.events.extras import configcontext


@pytest.mark.asyncio
@patch("nv_config_manager.render.events.extras.queue_render", new_callable=AsyncMock)
async def test_device(mock_enqueue: Mock):
    test_uuids = [uuid4() for i in range(10)]
    site_uuid = "7bebe881-aadd-446c-a9a3-8df264dcf35e"
    tenant_uuid = "66784853-f6ce-4477-8211-62a34948061e"

    message = {
        "@timestamp": "2025-03-10T20:22:41Z",
        "request": {"addr": "10.221.54.139", "user": "testuser"},
        "response": {"host": "nautobot-default-599f49fff9-kkhx2"},
        "event": "update",
        "model": "extras.configcontext",
        "record": {
            "id": "e347e3c7-e6c4-4e68-bda0-a0ad2439a8f9",
            "object_type": "extras.configcontext",
            "display": "rno1-network-management-services",
            "url": "https://nautobot.example.com/api/extras/config-contexts/e347e3c7-e6c4-4e68-bda0-a0ad2439a8f9/",
            "natural_slug": "rno1-network-management-services_e347",
            "owner_content_type": None,
            "owner": None,
            "name": "rno1-network-management-services",
            "owner_object_id": None,
            "weight": 1000,
            "description": "",
            "is_active": True,
            "data": {"ztp": {"ipv4": ["10.48.135.79"]}},
            "config_context_schema": None,
            "locations": [
                {
                    "id": "7bebe881-aadd-446c-a9a3-8df264dcf35e",
                    "object_type": "dcim.location",
                    "display": "NVIDIA \u2192 AMER \u2192 United States \u2192 Reno \u2192 RNO1",
                    "url": "https://nautobot.example.com/api/dcim/locations/7bebe881-aadd-446c-a9a3-8df264dcf35e/",
                    "natural_slug": "rno1_reno_united-states_amer_nvidia_7beb",
                    "time_zone": None,
                    "name": "RNO1",
                    "description": "",
                    "facility": "",
                    "asn": None,
                    "physical_address": "",
                    "shipping_address": "",
                    "latitude": None,
                    "longitude": None,
                    "contact_name": "",
                    "contact_phone": "",
                    "contact_email": "",
                    "comments": "",
                    "parent": {
                        "id": "0fd99ade-c2e2-4d5e-8e5e-7bcc7a12a544",
                        "object_type": "dcim.location",
                        "display": "NVIDIA \u2192 AMER \u2192 United States \u2192 Reno",
                        "url": "https://nautobot.example.com/api/dcim/locations/0fd99ade-c2e2-4d5e-8e5e-7bcc7a12a544/",
                        "natural_slug": "reno_united-states_amer_nvidia_0fd9",
                        "time_zone": None,
                        "name": "Reno",
                        "description": "",
                        "facility": "",
                        "asn": None,
                        "physical_address": "",
                        "shipping_address": "",
                        "latitude": None,
                        "longitude": None,
                        "contact_name": "",
                        "contact_phone": "",
                        "contact_email": "",
                        "comments": "",
                        "parent": {
                            "id": "da189958-30b8-4561-bf7e-0039f11e0081",
                            "object_type": "dcim.location",
                            "url": "https://nautobot.example.com/api/dcim/locations/da189958-30b8-4561-bf7e-0039f11e0081/",
                        },
                        "location_type": {
                            "id": "fee380e0-06ca-4c55-a79a-89362881dd26",
                            "object_type": "dcim.locationtype",
                            "url": "https://nautobot.example.com/api/dcim/location-types/fee380e0-06ca-4c55-a79a-89362881dd26/",
                        },
                        "status": {
                            "id": "19ec3633-8e5f-40cb-8851-57de84ce69e4",
                            "object_type": "extras.status",
                            "url": "https://nautobot.example.com/api/extras/statuses/19ec3633-8e5f-40cb-8851-57de84ce69e4/",
                        },
                        "tenant": None,
                        "created": "2025-01-24T18:25:13.660229Z",
                        "last_updated": "2025-01-24T18:25:13.660246Z",
                        "notes_url": "https://nautobot.example.com/api/dcim/locations/0fd99ade-c2e2-4d5e-8e5e-7bcc7a12a544/notes/",
                        "custom_fields": {
                            "site_account_number": "",
                            "cafm_building": "",
                            "floor": "",
                            "nw_discovery": None,
                            "office_manager": "",
                            "resource_id": "",
                            "resource_info": None,
                            "room": "",
                            "secondary_contact": "",
                            "secondary_contact_bu": "",
                            "security_officer": "",
                            "site_leader": "",
                            "site_type": "",
                        },
                    },
                    "location_type": {
                        "id": "1ccd5fdc-a7ac-4dce-9827-a1de15451773",
                        "object_type": "dcim.locationtype",
                        "display": "Provider \u2192 Region \u2192 Site",
                        "url": "https://nautobot.example.com/api/dcim/location-types/1ccd5fdc-a7ac-4dce-9827-a1de15451773/",
                        "natural_slug": "site_1ccd",
                        "name": "Site",
                        "description": "Physical site (e.g. datacenter, POP)",
                        "nestable": False,
                        "parent": {
                            "id": "fee380e0-06ca-4c55-a79a-89362881dd26",
                            "object_type": "dcim.locationtype",
                            "url": "https://nautobot.example.com/api/dcim/location-types/fee380e0-06ca-4c55-a79a-89362881dd26/",
                        },
                        "created": "2024-11-22T21:14:54.029675Z",
                        "last_updated": "2025-03-04T15:43:18.656230Z",
                        "notes_url": "https://nautobot.example.com/api/dcim/location-types/1ccd5fdc-a7ac-4dce-9827-a1de15451773/notes/",
                        "custom_fields": {},
                    },
                    "status": {
                        "id": "19ec3633-8e5f-40cb-8851-57de84ce69e4",
                        "object_type": "extras.status",
                        "display": "Active",
                        "url": "https://nautobot.example.com/api/extras/statuses/19ec3633-8e5f-40cb-8851-57de84ce69e4/",
                        "natural_slug": "active_19ec",
                        "name": "Active",
                        "color": "4caf50",
                        "description": "",
                        "created": "2024-11-20T00:00:00Z",
                        "last_updated": "2025-03-07T15:04:53.353064Z",
                        "notes_url": "https://nautobot.example.com/api/extras/statuses/19ec3633-8e5f-40cb-8851-57de84ce69e4/notes/",
                        "custom_fields": {},
                    },
                    "tenant": None,
                    "created": "2025-01-24T18:25:31.081485Z",
                    "last_updated": "2025-01-24T18:25:31.081499Z",
                    "notes_url": "https://nautobot.example.com/api/dcim/locations/7bebe881-aadd-446c-a9a3-8df264dcf35e/notes/",
                    "custom_fields": {
                        "site_account_number": "",
                        "cafm_building": "",
                        "floor": "",
                        "nw_discovery": None,
                        "office_manager": "",
                        "resource_id": "",
                        "resource_info": None,
                        "room": "",
                        "secondary_contact": "",
                        "secondary_contact_bu": "",
                        "security_officer": "",
                        "site_leader": "",
                        "site_type": "",
                    },
                }
            ],
            "roles": [],
            "device_types": [],
            "device_redundancy_groups": [],
            "platforms": [],
            "cluster_groups": [],
            "clusters": [],
            "tenant_groups": [],
            "tenants": [
                {
                    "id": "66784853-f6ce-4477-8211-62a34948061e",
                    "object_type": "tenancy.tenant",
                    "display": "TenantB",
                    "url": "https://nautobot.example.com/api/tenancy/tenants/66784853-f6ce-4477-8211-62a34948061e/",
                    "natural_slug": "ngc_6678",
                    "name": "TenantB",
                    "description": "Tenant for Resources Belonging to a Cerebro Site",
                    "comments": "",
                    "tenant_group": None,
                    "created": "2025-01-31T18:23:29.580823Z",
                    "last_updated": "2025-01-31T18:23:29.580835Z",
                    "notes_url": "https://nautobot.example.com/api/tenancy/tenants/66784853-f6ce-4477-8211-62a34948061e/notes/",
                    "custom_fields": {"aws_account_id": None},
                }
            ],
            "created": "2025-01-24T19:00:18.558233Z",
            "last_updated": "2025-03-10T20:22:40.793872Z",
            "notes_url": "https://nautobot.example.com/api/extras/config-contexts/e347e3c7-e6c4-4e68-bda0-a0ad2439a8f9/notes/",
            "tags": [],
        },
        "@url": "https://nautobot.example.com/api/extras/config-contexts/e347e3c7-e6c4-4e68-bda0-a0ad2439a8f9/",
        "detail": {
            "last_updated": [
                "2025-02-06T21:33:54.803901Z",
                "2025-03-10T20:22:40.793872Z",
            ]
        },
    }

    with patch(
        "nv_config_manager.render.events.extras.get_managed_device_uuids",
        return_value=test_uuids,
    ) as nb_mock:
        await configcontext(message)
        nb_mock.assert_called_with(locations=[site_uuid], tenants=[tenant_uuid])

    assert mock_enqueue.call_count == 10

    expected_message = "Triggered from nb extras.configcontext update on rno1-network-management-services by testuser at 2025-03-10T20:22:41Z"
    for test_uuid in test_uuids:
        mock_enqueue.assert_any_call(
            device_uuid=test_uuid,
            commit_message=expected_message,
            user="testuser",
            timestamp="2025-03-10T20:22:41Z",
        )
