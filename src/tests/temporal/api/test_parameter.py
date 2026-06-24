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
from aioresponses import aioresponses
from fastapi.testclient import TestClient

from nv_config_manager.temporal.api.main import app

V2_SITES = {
    "data": {"locations": [{"id": "ddadde54-cbdd-4fa5-94ce-ca649b7e2aa8", "name": "SITEA"}]}
}

DEVICES = {
    "data": {
        "devices": [
            {
                "id": "aa6ef75b-00fe-45e6-8adb-62609509cb4f",
                "name": "core1-cg1-cp1-tan1-sitea",
                "platform": {"name": "Cumulus Linux"},
            }
        ]
    }
}

# config_manager_devices response for tenant endpoint (managed_only)
NV_CONFIG_MANAGER_DEVICES_TENANTS = {
    "data": {
        "config_manager_devices": [
            {"device": {"tenant": {"id": "tenant-uuid-1", "name": "TenantA"}}},
            {"device": {"tenant": {"id": "tenant-uuid-2", "name": "TenantB"}}},
            {"device": {"tenant": {"id": "tenant-uuid-3", "name": "Example Cloud"}}},
        ]
    }
}

# config_manager_devices response for role endpoint (managed_only)
NV_CONFIG_MANAGER_DEVICES_ROLES = {
    "data": {
        "config_manager_devices": [
            {"device": {"role": {"id": "role-uuid-1", "name": "leaf"}}},
            {"device": {"role": {"id": "role-uuid-2", "name": "spine"}}},
            {"device": {"role": {"id": "role-uuid-1", "name": "leaf"}}},
        ]
    }
}

# All tenants (default)
TENANTS = {
    "data": {
        "tenants": [
            {"id": "tenant-uuid-1", "name": "TenantA"},
            {"id": "tenant-uuid-2", "name": "TenantB"},
            {"id": "tenant-uuid-3", "name": "Example Cloud"},
        ]
    }
}

# All roles (default)
ROLES = {
    "data": {
        "roles": [
            {"id": "role-uuid-1", "name": "leaf"},
            {"id": "role-uuid-2", "name": "spine"},
        ]
    }
}

STATUSES = {
    "data": {
        "statuses": [
            {"id": "status-uuid-1", "name": "Active"},
            {"id": "status-uuid-2", "name": "Provisioned"},
            {"id": "status-uuid-3", "name": "Decommissioned"},
        ]
    }
}

NAMESPACE_TAGS = {
    "data": {
        "namespaces": [
            {"tags": [{"name": "spectrumx"}, {"name": "tenant-a"}]},
            {"tags": [{"name": "spectrumx"}]},
            {"tags": []},
        ]
    }
}


def test_site_v2():
    with aioresponses() as m:
        # Mock the graphql endpoint to return V2_SITES data
        # URL comes from conftest.py mock config
        m.post("https://nautobot.example.com/api/graphql/", payload=V2_SITES)

        client = TestClient(app)
        rsp = client.get("/v1/parameter/site")
        assert rsp.json() == [{"id": "ddadde54-cbdd-4fa5-94ce-ca649b7e2aa8", "name": "SITEA"}]

    with aioresponses() as m:
        m.post("https://nautobot.example.com/api/graphql/", payload=V2_SITES)

        client = TestClient(app)
        rsp = client.get("/v1/parameter/site?location_type=Site")
        assert rsp.json() == [{"id": "ddadde54-cbdd-4fa5-94ce-ca649b7e2aa8", "name": "SITEA"}]


def test_device_v2():
    with aioresponses() as m:
        # Mock the graphql endpoint to return DEVICES data for all calls
        # URL comes from conftest.py mock config
        m.post("https://nautobot.example.com/api/graphql/", payload=DEVICES, repeat=True)

        client = TestClient(app)
        rsp = client.get("/v1/parameter/device?site=SITEA&status=Active&tenant=TenantA")
        assert rsp.json() == [
            {
                "id": "aa6ef75b-00fe-45e6-8adb-62609509cb4f",
                "name": "core1-cg1-cp1-tan1-sitea",
                "platform": "cumulus-linux",
            }
        ]

        # Test with custom platform
        rsp = client.get(
            "/v1/parameter/device?site=SITEA&status=Active&tenant=TenantA&platform=UFM"
        )
        assert rsp.json() == [
            {
                "id": "aa6ef75b-00fe-45e6-8adb-62609509cb4f",
                "name": "core1-cg1-cp1-tan1-sitea",
                "platform": "cumulus-linux",
            }
        ]


UFM_DEVICES = {
    "data": {
        "devices": [
            {
                "id": "ufm-uuid-1",
                "name": "ufm-test-device",
                "platform": {"name": "UFM"},
            }
        ]
    }
}


def test_ufm_device():
    """The dedicated UFM endpoint filters by role=UFM + primary IP, with no platform allow-list."""
    with aioresponses() as m:
        m.post("https://nautobot.example.com/api/graphql/", payload=UFM_DEVICES)

        client = TestClient(app)
        rsp = client.get("/v1/parameter/ufm-device?site=SITEA")
        assert rsp.json() == [{"id": "ufm-uuid-1", "name": "ufm-test-device", "platform": "ufm"}]

        sent = next(iter(m.requests.values()))[0]
        variables = sent.kwargs["json"]["variables"]
        assert variables["role"] == ["UFM"]
        assert variables["site"] == ["SITEA"]
        assert "platform" not in variables


def test_ufm_device_without_site():
    """Site is optional; role=UFM is always applied and no platform allow-list leaks in."""
    with aioresponses() as m:
        m.post("https://nautobot.example.com/api/graphql/", payload=UFM_DEVICES)

        client = TestClient(app)
        rsp = client.get("/v1/parameter/ufm-device")
        assert rsp.status_code == 200

        sent = next(iter(m.requests.values()))[0]
        variables = sent.kwargs["json"]["variables"]
        assert variables["role"] == ["UFM"]
        assert "site" not in variables
        assert "platform" not in variables


def test_ufm_device_graphql_error_returns_400():
    """A GraphQL error is translated to HTTP 400 instead of an unhandled 500."""
    with aioresponses() as m:
        m.post(
            "https://nautobot.example.com/api/graphql/",
            payload={"errors": [{"message": "invalid query"}]},
        )

        client = TestClient(app)
        rsp = client.get("/v1/parameter/ufm-device?site=SITEA")
        assert rsp.status_code == 400


def test_tenant_default():
    """Test the tenant parameter endpoint (default: all tenants)."""
    with aioresponses() as m:
        m.post("https://nautobot.example.com/api/graphql/", payload=TENANTS)

        client = TestClient(app)
        rsp = client.get("/v1/parameter/tenant")
        assert rsp.json() == [
            {"id": "tenant-uuid-1", "name": "TenantA"},
            {"id": "tenant-uuid-2", "name": "TenantB"},
            {"id": "tenant-uuid-3", "name": "Example Cloud"},
        ]


def test_tenant_managed_only():
    """Test the tenant parameter endpoint (managed_only: from nv_config_manager_devices)."""
    with aioresponses() as m:
        m.post(
            "https://nautobot.example.com/api/graphql/",
            payload=NV_CONFIG_MANAGER_DEVICES_TENANTS,
        )

        client = TestClient(app)
        rsp = client.get("/v1/parameter/tenant?managed_only=true")
        result = rsp.json()
        assert len(result) == 3
        names = {t["name"] for t in result}
        assert names == {"TenantA", "TenantB", "Example Cloud"}


def test_role_default():
    """Test the role parameter endpoint (default: all roles)."""
    with aioresponses() as m:
        m.post("https://nautobot.example.com/api/graphql/", payload=ROLES)

        client = TestClient(app)
        rsp = client.get("/v1/parameter/role")
        assert rsp.json() == [
            {"id": "role-uuid-1", "name": "leaf"},
            {"id": "role-uuid-2", "name": "spine"},
        ]


def test_role_managed_only():
    """Test the role parameter endpoint (managed_only: from nv_config_manager_devices)."""
    with aioresponses() as m:
        m.post(
            "https://nautobot.example.com/api/graphql/",
            payload=NV_CONFIG_MANAGER_DEVICES_ROLES,
        )

        client = TestClient(app)
        rsp = client.get("/v1/parameter/role?managed_only=true")
        result = rsp.json()
        assert len(result) == 2
        names = {r["name"] for r in result}
        assert names == {"leaf", "spine"}


def test_namespace_tag():
    """Test the namespace tag parameter endpoint."""
    with aioresponses() as m:
        m.post("https://nautobot.example.com/api/graphql/", payload=NAMESPACE_TAGS)

        client = TestClient(app)
        rsp = client.get("/v1/parameter/namespace-tag?location=RNO1")
        assert rsp.json() == [
            {"id": "spectrumx", "name": "spectrumx"},
            {"id": "tenant-a", "name": "tenant-a"},
        ]


def test_namespace_tag_graphql_error():
    """Test the namespace tag endpoint handles Nautobot GraphQL errors."""
    with aioresponses() as m:
        m.post(
            "https://nautobot.example.com/api/graphql/",
            payload={"errors": [{"message": "boom"}]},
        )

        client = TestClient(app)
        rsp = client.get("/v1/parameter/namespace-tag")
        assert rsp.status_code == 500
        assert rsp.json() == {"detail": "Failed to query Nautobot namespace tags."}


def test_namespace_tag_malformed_response():
    """Test the namespace tag endpoint handles malformed Nautobot responses."""
    with aioresponses() as m:
        m.post(
            "https://nautobot.example.com/api/graphql/",
            payload={"data": {"namespaces": {}}},
        )

        client = TestClient(app)
        rsp = client.get("/v1/parameter/namespace-tag")
        assert rsp.status_code == 500
        assert rsp.json() == {"detail": "Malformed Nautobot namespace tag response."}


def test_status_with_content_type():
    """Test the status parameter endpoint with content_type filter."""
    with aioresponses() as m:
        m.post("https://nautobot.example.com/api/graphql/", payload=STATUSES)

        client = TestClient(app)
        rsp = client.get("/v1/parameter/status?content_type=dcim.device")
        assert rsp.json() == [
            {"id": "status-uuid-1", "name": "Active"},
            {"id": "status-uuid-2", "name": "Provisioned"},
            {"id": "status-uuid-3", "name": "Decommissioned"},
        ]


def test_status_without_content_type():
    """Test the status parameter endpoint without filter (all statuses)."""
    with aioresponses() as m:
        m.post("https://nautobot.example.com/api/graphql/", payload=STATUSES)

        client = TestClient(app)
        rsp = client.get("/v1/parameter/status")
        assert rsp.json() == [
            {"id": "status-uuid-1", "name": "Active"},
            {"id": "status-uuid-2", "name": "Provisioned"},
            {"id": "status-uuid-3", "name": "Decommissioned"},
        ]
