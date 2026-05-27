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
"""Tests for UFM client."""

from configparser import ConfigParser
from unittest.mock import patch

import pytest
from aioresponses import aioresponses

from nv_config_manager.temporal.client.ufm import UFMAuthError, UFMClient, UFMClientError
from nv_config_manager.temporal.common.secrets import clear_secrets_cache


def _create_config(sections: dict[str, dict[str, str]]) -> ConfigParser:
    """Create a ConfigParser from a dict of sections."""
    config = ConfigParser()
    for section, values in sections.items():
        config.add_section(section)
        for key, value in values.items():
            config.set(section, key, value)
    return config


@pytest.fixture(autouse=True)
def reset_secrets_cache():
    """Clear the secrets config cache before and after each test."""
    clear_secrets_cache()
    yield
    clear_secrets_cache()


@patch("nv_config_manager.temporal.client.ufm.load_config")
def test_loads_credentials_from_global_ufm_section(mock_load_config):
    """Test that credentials are loaded from global [ufm] section."""
    mock_load_config.return_value = _create_config(
        {"ufm": {"ufm_api_user": "admin", "ufm_api_token_r1": "password1"}}
    )

    client = UFMClient(host="ufm.example.com")

    assert client._username == "admin"
    assert client._passwords == ["password1"]


@patch("nv_config_manager.temporal.client.ufm.load_config")
def test_uses_rotation_passwords_sorted_by_revision(mock_load_config):
    """Test that rotation passwords are sorted by revision (newest first)."""
    mock_load_config.return_value = _create_config(
        {
            "ufm": {
                "ufm_api_user": "admin",
                "ufm_api_token_r1": "old_pw",
                "ufm_api_token_r2": "new_pw",
            }
        }
    )

    client = UFMClient(host="ufm.example.com")

    assert client._passwords == ["new_pw", "old_pw"]


@patch("nv_config_manager.temporal.client.ufm.load_config")
def test_respects_max_passwords_limit(mock_load_config):
    """Test that max_passwords limits the number of passwords returned."""
    mock_load_config.return_value = _create_config(
        {
            "ufm": {
                "ufm_api_user": "admin",
                "ufm_api_token_r1": "pw1",
                "ufm_api_token_r2": "pw2",
                "ufm_api_token_r3": "pw3",
            }
        }
    )

    client = UFMClient(host="ufm.example.com", max_passwords=2)

    assert client._passwords == ["pw3", "pw2"]


@patch("nv_config_manager.temporal.client.ufm.load_config")
def test_uses_secrets_config_for_site_credentials(mock_load_config, tmp_path):
    """Test that secrets config is used for site-specific credentials."""
    mock_load_config.return_value = _create_config(
        {"ufm": {"ufm_api_user": "global_user", "ufm_api_token_r1": "global_pw"}}
    )

    secrets_file = tmp_path / "config-secrets.ini"
    secrets_file.write_text("[site.site-a]\nufm_api_user = site_user\nufm_api_token_r1 = site_pw\n")

    with patch.dict("os.environ", {"NV_CONFIG_MANAGER_CONFIG_SECRET_PATH": str(secrets_file)}):
        client = UFMClient(host="ufm.example.com", site="Site A")

        assert client._username == "site_user"
        assert client._passwords == ["site_pw"]


@patch("nv_config_manager.temporal.client.ufm.load_config")
def test_falls_back_to_global_when_no_secrets_file(mock_load_config):
    """Test fallback to global [ufm] when secrets file doesn't exist."""
    mock_load_config.return_value = _create_config(
        {"ufm": {"ufm_api_user": "global_user", "ufm_api_token_r1": "global_pw"}}
    )

    with patch.dict(
        "os.environ", {"NV_CONFIG_MANAGER_CONFIG_SECRET_PATH": "/nonexistent/file.ini"}
    ):
        client = UFMClient(host="ufm.example.com", site="Site A")

        assert client._username == "global_user"
        assert client._passwords == ["global_pw"]


@patch("nv_config_manager.temporal.client.ufm.load_config")
def test_falls_back_to_global_when_site_not_in_secrets(mock_load_config, tmp_path):
    """Test fallback to global [ufm] when site section missing in secrets."""
    mock_load_config.return_value = _create_config(
        {"ufm": {"ufm_api_user": "global_user", "ufm_api_token_r1": "global_pw"}}
    )

    secrets_file = tmp_path / "config-secrets.ini"
    secrets_file.write_text("[site.other-site]\nufm_api_token_r1 = other_pw\n")

    with patch.dict("os.environ", {"NV_CONFIG_MANAGER_CONFIG_SECRET_PATH": str(secrets_file)}):
        client = UFMClient(host="ufm.example.com", site="Site A")

        assert client._username == "global_user"
        assert client._passwords == ["global_pw"]


@patch("nv_config_manager.temporal.client.ufm.load_config")
def test_working_password_tried_first(mock_load_config):
    """Test that cached working password is tried first."""
    mock_load_config.return_value = _create_config(
        {
            "ufm": {
                "ufm_api_user": "admin",
                "ufm_api_token_r1": "pw1",
                "ufm_api_token_r2": "pw2",
            }
        }
    )

    client = UFMClient(host="ufm.example.com")
    # Simulate pw1 was previously successful
    client._working_password = "pw1"

    passwords = client._get_passwords_to_try()

    # Working password should be first, followed by others
    assert passwords == ["pw1", "pw2"]


@patch("nv_config_manager.temporal.client.ufm.load_config")
def test_working_password_not_duplicated(mock_load_config):
    """Test that working password isn't duplicated in the list."""
    mock_load_config.return_value = _create_config(
        {
            "ufm": {
                "ufm_api_user": "admin",
                "ufm_api_token_r1": "pw1",
                "ufm_api_token_r2": "pw2",
            }
        }
    )

    client = UFMClient(host="ufm.example.com")
    client._working_password = "pw2"

    passwords = client._get_passwords_to_try()

    assert passwords == ["pw2", "pw1"]
    assert len(passwords) == 2


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.client.ufm.load_config")
async def test_successful_request(mock_load_config):
    """Test successful API request."""
    mock_load_config.return_value = _create_config(
        {"ufm": {"ufm_api_user": "admin", "ufm_api_token_r1": "password"}}
    )

    async with UFMClient(host="ufm.example.com") as client:
        with aioresponses() as m:
            m.get(
                "https://ufm.example.com/ufmRest/resources/ports",
                status=200,
                payload=[{"port": 1}],
            )

            result = await client.request("GET", "/resources/ports")

            assert result == [{"port": 1}]


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.client.ufm.load_config")
async def test_caches_working_password_on_success(mock_load_config):
    """Test that successful password is cached."""
    mock_load_config.return_value = _create_config(
        {"ufm": {"ufm_api_user": "admin", "ufm_api_token_r1": "password"}}
    )

    async with UFMClient(host="ufm.example.com") as client:
        with aioresponses() as m:
            m.get(
                "https://ufm.example.com/ufmRest/resources/ports",
                status=200,
                payload=[],
            )

            await client.request("GET", "/resources/ports")

            assert client._working_password == "password"


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.client.ufm.load_config")
async def test_tries_next_password_on_401(mock_load_config):
    """Test that next password is tried after 401."""
    mock_load_config.return_value = _create_config(
        {
            "ufm": {
                "ufm_api_user": "admin",
                "ufm_api_token_r1": "old_pw",
                "ufm_api_token_r2": "new_pw",
            }
        }
    )

    async with UFMClient(host="ufm.example.com") as client:
        with aioresponses() as m:
            # First password (new_pw) fails
            m.get(
                "https://ufm.example.com/ufmRest/resources/ports",
                status=401,
            )
            # Second password (old_pw) succeeds
            m.get(
                "https://ufm.example.com/ufmRest/resources/ports",
                status=200,
                payload=[{"port": 1}],
            )

            result = await client.request("GET", "/resources/ports")

            assert result == [{"port": 1}]
            assert client._working_password == "old_pw"


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.client.ufm.load_config")
async def test_raises_auth_error_when_all_passwords_fail(mock_load_config):
    """Test UFMAuthError is raised when all passwords fail."""
    mock_load_config.return_value = _create_config(
        {
            "ufm": {
                "ufm_api_user": "admin",
                "ufm_api_token_r1": "pw1",
                "ufm_api_token_r2": "pw2",
            }
        }
    )

    async with UFMClient(host="ufm.example.com") as client:
        with aioresponses() as m:
            m.get("https://ufm.example.com/ufmRest/test", status=401)
            m.get("https://ufm.example.com/ufmRest/test", status=401)

            with pytest.raises(UFMAuthError) as exc_info:
                await client.request("GET", "/test")

            assert "2 password attempts failed" in str(exc_info.value)


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.client.ufm.load_config")
async def test_raises_auth_error_when_no_passwords_configured(mock_load_config):
    """Test UFMAuthError is raised when no passwords are configured."""
    mock_load_config.return_value = _create_config({"ufm": {"ufm_api_user": "admin"}})

    async with UFMClient(host="ufm.example.com") as client:
        with pytest.raises(UFMAuthError) as exc_info:
            await client.request("GET", "/test")

        assert "No UFM passwords configured" in str(exc_info.value)


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.client.ufm.load_config")
async def test_raises_client_error_on_http_500(mock_load_config):
    """Test UFMClientError is raised for server errors."""
    mock_load_config.return_value = _create_config(
        {"ufm": {"ufm_api_user": "admin", "ufm_api_token_r1": "password"}}
    )

    async with UFMClient(host="ufm.example.com") as client:
        with aioresponses() as m:
            m.get(
                "https://ufm.example.com/ufmRest/test",
                status=500,
                body="Internal Server Error",
            )

            with pytest.raises(UFMClientError) as exc_info:
                await client.request("GET", "/test")

            assert "500" in str(exc_info.value)


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.client.ufm.load_config")
async def test_invalidates_cached_password_on_auth_failure(mock_load_config):
    """Test that cached working password is invalidated on auth failure."""
    mock_load_config.return_value = _create_config(
        {
            "ufm": {
                "ufm_api_user": "admin",
                "ufm_api_token_r1": "pw1",
                "ufm_api_token_r2": "pw2",
            }
        }
    )

    async with UFMClient(host="ufm.example.com") as client:
        # Simulate pw2 was previously working
        client._working_password = "pw2"

        with aioresponses() as m:
            # pw2 now fails
            m.get("https://ufm.example.com/ufmRest/test", status=401)
            # pw1 succeeds
            m.get(
                "https://ufm.example.com/ufmRest/test",
                status=200,
                payload={},
            )

            await client.request("GET", "/test")

            # Working password should now be pw1
            assert client._working_password == "pw1"


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.client.ufm.load_config")
async def test_get_ports_returns_all_ports(mock_load_config):
    """Test get_ports returns all ports when unhealthy_only=False."""
    mock_load_config.return_value = _create_config(
        {"ufm": {"ufm_api_user": "admin", "ufm_api_token_r1": "password"}}
    )

    ports_response = [
        {
            "number": "1",
            "label": "Port 1",
            "physical_state": "Link Up",
            "logical_state": "Active",
            "system_name": "System1",
            "node_description": "Node 1",
            "peer_node_name": "Peer1",
            "peer_port_dname": "2",
            "peer_node_description": "Peer Node 1",
            "guid": "0x0000000000000001",
        },
        {
            "number": "2",
            "label": "Port 2",
            "physical_state": "Link Down",
            "logical_state": "Inactive",
            "system_name": "System1",
            "node_description": "Node 1",
            "peer_node_name": "Peer2",
            "peer_port_dname": "3",
            "peer_node_description": "Peer Node 2",
            "guid": "0x0000000000000002",
        },
    ]

    async with UFMClient(host="ufm.example.com") as client:
        with aioresponses() as m:
            m.get(
                "https://ufm.example.com/ufmRest/resources/ports",
                status=200,
                payload=ports_response,
            )

            result = await client.get_ports()

            assert len(result) == 2
            assert result[0]["port"] == "1"
            assert result[1]["port"] == "2"
            assert result[0]["guid"] == "0x0000000000000001"
            assert result[1]["guid"] == "0x0000000000000002"


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.client.ufm.load_config")
async def test_get_ports_filters_unhealthy(mock_load_config):
    """Test get_ports filters to only unhealthy ports when unhealthy_only=True."""
    mock_load_config.return_value = _create_config(
        {"ufm": {"ufm_api_user": "admin", "ufm_api_token_r1": "password"}}
    )

    ports_response = [
        {
            "number": "1",
            "label": "Port 1",
            "physical_state": "Link Up",
            "logical_state": "Active",
            "system_name": "System1",
        },
        {
            "number": "2",
            "label": "Port 2",
            "physical_state": "Link Down",
            "logical_state": "Inactive",
            "system_name": "System1",
        },
    ]

    async with UFMClient(host="ufm.example.com") as client:
        with aioresponses() as m:
            m.get(
                "https://ufm.example.com/ufmRest/resources/ports",
                status=200,
                payload=ports_response,
            )

            result = await client.get_ports(unhealthy_only=True)

            assert len(result) == 1
            assert result[0]["port"] == "2"
            assert result[0]["physical_state"] == "Link Down"


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.client.ufm.load_config")
async def test_get_ports_handles_empty_response(mock_load_config):
    """Test get_ports handles empty response."""
    mock_load_config.return_value = _create_config(
        {"ufm": {"ufm_api_user": "admin", "ufm_api_token_r1": "password"}}
    )

    async with UFMClient(host="ufm.example.com") as client:
        with aioresponses() as m:
            m.get(
                "https://ufm.example.com/ufmRest/resources/ports",
                status=200,
                payload=[],
            )

            result = await client.get_ports()

            assert result == []


@pytest.mark.asyncio
@patch("nv_config_manager.temporal.client.ufm.load_config")
async def test_get_ports_handles_non_list_response(mock_load_config):
    """Test get_ports handles unexpected non-list response."""
    mock_load_config.return_value = _create_config(
        {"ufm": {"ufm_api_user": "admin", "ufm_api_token_r1": "password"}}
    )

    async with UFMClient(host="ufm.example.com") as client:
        with aioresponses() as m:
            m.get(
                "https://ufm.example.com/ufmRest/resources/ports",
                status=200,
                payload={"error": "unexpected"},
            )

            result = await client.get_ports()

            assert result == []
