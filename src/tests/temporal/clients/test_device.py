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
import json
from configparser import ConfigParser
from unittest.mock import MagicMock, patch

import paramiko
import pytest

from nv_config_manager.temporal.client.device import (
    ConfigSyntaxException,
    CumulusConnection,
    DiffChangedException,
    JunosConnection,
    MockNetworkConnection,
    NetworkConnection,
)
from nv_config_manager.temporal.common.mixins.device import NetworkDeviceData
from nv_config_manager.temporal.common.secrets import clear_secrets_cache


@pytest.fixture(autouse=True)
def reset_secrets_cache():
    """Clear the secrets config cache before and after each test."""
    clear_secrets_cache()
    yield
    clear_secrets_cache()


class TestNetworkConnectionPasswordRotation:
    """Tests for NetworkConnection password initialization behavior."""

    @patch("nv_config_manager.temporal.client.device.load_config")
    def test_uses_rotation_passwords_sorted_by_revision(self, mock_load_config):
        """Test that rotation passwords are used in order of revision (newest first)."""
        config = ConfigParser()
        config.add_section("device")
        config.set("device", "username", "admin")
        config.set("device", "api_user_key_r1", "old_pw")
        config.set("device", "api_user_key_r2", "new_pw")
        mock_load_config.return_value = config

        conn = NetworkConnection("host", 22)

        assert conn._passwords_to_try == ["new_pw", "old_pw"]

    @patch("nv_config_manager.temporal.client.device.load_config")
    def test_falls_back_to_password_when_no_rotation_keys(self, mock_load_config):
        """Test fallback to password field when no rotation keys exist."""
        config = ConfigParser()
        config.add_section("device")
        config.set("device", "username", "admin")
        config.set("device", "password", "fallback_pw")
        mock_load_config.return_value = config

        conn = NetworkConnection("host", 22)

        assert conn._passwords_to_try == ["fallback_pw"]

    @patch("nv_config_manager.temporal.client.device.load_config")
    def test_uses_explicit_password_only(self, mock_load_config):
        """Test that explicit password is used exclusively, ignoring config passwords."""
        config = ConfigParser()
        config.add_section("device")
        config.set("device", "username", "admin")
        config.set("device", "api_user_key_r1", "config_pw")
        mock_load_config.return_value = config

        conn = NetworkConnection("host", 22, password="explicit_pw")

        assert conn._passwords_to_try == ["explicit_pw"]

    @patch("nv_config_manager.temporal.client.device.load_config")
    def test_no_passwords_available(self, mock_load_config):
        """Test empty password list when no passwords configured."""
        config = ConfigParser()
        config.add_section("device")
        config.set("device", "username", "admin")
        mock_load_config.return_value = config

        conn = NetworkConnection("host", 22)

        assert conn._passwords_to_try == []

    @patch("nv_config_manager.temporal.client.device.load_config")
    def test_uses_secrets_config_for_site_passwords(self, mock_load_config, tmp_path):
        """Test that secrets config is used for site-specific passwords when available."""
        # Setup main config (will be used for username only)
        main_config = ConfigParser()
        main_config.add_section("device")
        main_config.set("device", "username", "admin")
        main_config.set("device", "api_user_key_r1", "main_pw")
        mock_load_config.return_value = main_config

        # Create secrets config file
        secrets_file = tmp_path / "config-secrets.ini"
        secrets_file.write_text("[site.site-a]\napi_user_key_r1 = secrets_pw\n")

        with patch.dict("os.environ", {"NV_CONFIG_MANAGER_CONFIG_SECRET_PATH": str(secrets_file)}):
            conn = NetworkConnection("host", 22, site="Site A")

            assert conn._passwords_to_try == ["secrets_pw"]

    @patch("nv_config_manager.temporal.client.device.load_config")
    def test_falls_back_to_main_config_when_no_secrets_file(self, mock_load_config):
        """Test fallback to main config global section when secrets file doesn't exist."""
        # Setup main config with global device section only
        main_config = ConfigParser()
        main_config.add_section("device")
        main_config.set("device", "username", "admin")
        main_config.set("device", "api_user_key_r1", "main_global_pw")
        mock_load_config.return_value = main_config

        # Point to non-existent file
        with patch.dict(
            "os.environ",
            {"NV_CONFIG_MANAGER_CONFIG_SECRET_PATH": "/nonexistent/config-secrets.ini"},
        ):
            # Site is provided but secrets file doesn't exist, falls back to global
            conn = NetworkConnection("host", 22, site="Site A")

            assert conn._passwords_to_try == ["main_global_pw"]

    @patch("nv_config_manager.temporal.client.device.load_config")
    def test_falls_back_to_global_when_site_not_in_secrets(self, mock_load_config):
        """Test fallback to global device section when secrets env var is not set."""
        # Setup main config with global section only
        main_config = ConfigParser()
        main_config.add_section("device")
        main_config.set("device", "username", "admin")
        main_config.set("device", "api_user_key_r1", "main_global_pw")
        mock_load_config.return_value = main_config

        # Don't set NV_CONFIG_MANAGER_CONFIG_SECRET_PATH - secrets config won't be loaded
        # This tests the fallback to main config when no secrets file is configured
        conn = NetworkConnection("host", 22, site="Site B")

        # No secrets config, falls back to main config's global device section
        assert conn._passwords_to_try == ["main_global_pw"]


def test_format_nvue_config_syntax_error():
    """Test formatting of NVUE API syntax error JSON."""
    error_json = {
        "detail": "Error: Unevaluated properties are not "
        "allowed ('ROUTE-SERVER-CLIENTS' was "
        "unexpected: expected ['@clear', "
        "'address-family', "
        "'autonomous-system', 'confederation', "
        "'dynamic-neighbor', 'enable', 'in', "
        "'neighbor', 'out', 'path-selection', "
        "'peer-group', 'rd', 'route-export', "
        "'route-import', 'route-reflection', "
        "'router-id', 'soft', 'timers'])",
        "status": 400,
        "title": "Bad Request",
        "type": "about:blank",
        "validation": {
            "selected_errors": [
                {
                    "error": "Unevaluated "
                    "properties "
                    "are "
                    "not "
                    "allowed "
                    "('ROUTE-SERVER-CLIENTS' "
                    "was "
                    "unexpected: "
                    "expected "
                    "['@clear', "
                    "'address-family', "
                    "'autonomous-system', "
                    "'confederation', "
                    "'dynamic-neighbor', "
                    "'enable', "
                    "'in', "
                    "'neighbor', "
                    "'out', "
                    "'path-selection', "
                    "'peer-group', "
                    "'rd', "
                    "'route-export', "
                    "'route-import', "
                    "'route-reflection', "
                    "'router-id', "
                    "'soft', "
                    "'timers'])",
                    "instanceLocation": "#/vrf/default/router/bgp",
                    "keywordLocation": "#/allOf/0/properties/vrf/allOf/0/additionalProperties/allOf/0/properties/router/allOf/0/properties/bgp/x-unevaluatedProperties",
                }
            ]
        },
    }
    expected_output = (
        "Error at '#/vrf/default/router/bgp': "
        "Unevaluated properties are not allowed ('ROUTE-SERVER-CLIENTS' was "
        "unexpected: expected ['@clear', "
        "'address-family', "
        "'autonomous-system', "
        "'confederation', "
        "'dynamic-neighbor', "
        "'enable', 'in', 'neighbor', 'out', 'path-selection', "
        "'peer-group', 'rd', 'route-export', 'route-import', "
        "'route-reflection', 'router-id', 'soft', 'timers'])"
    )
    assert ConfigSyntaxException.format_nvue_error(error_json) == expected_output


# =============================================================================
# MockNetworkConnection — diagnostic methods
# =============================================================================

_TEST_HOST = "192.0.2.1"


def test_mock_run_diagnostic_command_returns_valid_json():
    """run_diagnostic_command returns a valid JSON string with the expected keys."""
    conn = MockNetworkConnection(_TEST_HOST)
    raw = conn.run_diagnostic_command("show_version")
    parsed = json.loads(raw)
    assert "mock" in parsed
    assert "command" in parsed


def test_mock_run_diagnostic_command_includes_command_name():
    """The 'command' field in the returned JSON matches the input name."""
    conn = MockNetworkConnection(_TEST_HOST)
    raw = conn.run_diagnostic_command("show_bgp_summary")
    parsed = json.loads(raw)
    assert parsed["command"] == "show_bgp_summary"


def test_mock_get_tech_support_bundle_returns_bytes():
    """get_tech_support_bundle returns (bytes, log_str)."""
    conn = MockNetworkConnection(_TEST_HOST)
    content, log = conn.get_tech_support_bundle()
    assert isinstance(content, bytes)
    assert content == b"[mock tech-support bundle]"
    assert isinstance(log, str)


@patch("nv_config_manager.temporal.client.device.paramiko.SSHClient")
def test_sftp_download_closes_client_when_connect_fails(mock_ssh_client):
    """SFTP closes the SSH client when connection setup fails."""
    ssh = mock_ssh_client.return_value
    ssh.connect.side_effect = paramiko.SSHException("connection failed")
    conn = CumulusConnection.__new__(CumulusConnection)
    conn._host = _TEST_HOST
    conn._username = "admin"

    with pytest.raises(paramiko.SSHException, match="connection failed"):
        conn._sftp_download("password", "/tmp/support.tar", None)

    ssh.close.assert_called_once_with()


# =============================================================================
# NetworkConnection.from_device_data — mock routing
# =============================================================================

_CUMULUS_DEVICE = NetworkDeviceData(
    id="c8f7a95e-4b2a-4e8c-9d5f-1a2b3c4d5e6f",
    name="test-switch",
    role="tor-switch",
    platform="cumulus-linux",
    site="SITEA",
    device_type="sn5600",
    primary_ip4="192.0.2.100",
    primary_ip6=None,
)


def _mock_config(*, mock: bool) -> ConfigParser:
    config = ConfigParser()
    config.add_section("device")
    config.set("device", "username", "admin")
    config.set("device", "mock", "true" if mock else "false")
    return config


@patch("nv_config_manager.temporal.client.device.load_config")
def test_from_device_data_returns_mock_when_config_mock_true(mock_load_config):
    """Config with [device] mock = true → from_device_data() returns MockNetworkConnection."""
    mock_load_config.return_value = _mock_config(mock=True)
    conn = NetworkConnection.from_device_data(_CUMULUS_DEVICE)
    assert isinstance(conn, MockNetworkConnection)


@patch("nv_config_manager.temporal.client.device.load_config")
def test_from_device_data_returns_cumulus_when_mock_false(mock_load_config):
    """Config with [device] mock = false + cumulus-linux platform → returns CumulusConnection."""
    mock_load_config.return_value = _mock_config(mock=False)
    conn = NetworkConnection.from_device_data(_CUMULUS_DEVICE)
    assert isinstance(conn, CumulusConnection)


@patch("nv_config_manager.temporal.client.device.JunosConnection")
@patch("nv_config_manager.temporal.client.device.load_config")
def test_from_device_data_routes_junos_to_netconf(mock_load_config, mock_junos):
    """Juniper Junos devices select the NETCONF connection outside mock mode."""
    mock_load_config.return_value = _mock_config(mock=False)
    device = _CUMULUS_DEVICE.model_copy(update={"platform": "juniper-junos"})

    connection = NetworkConnection.from_device_data(device)

    assert connection is mock_junos.return_value
    mock_junos.assert_called_once_with("192.0.2.100", site="SITEA")


def test_junos_candidate_diff_uses_candidate_datastore() -> None:
    """Junos diff loads rendered text through NETCONF and returns show-compare output."""
    connection = JunosConnection.__new__(JunosConnection)
    connection._manager = MagicMock()
    connection._manager.compare_configuration.return_value.xml = (
        '<rpc-reply xmlns="urn:ietf:params:xml:ns:netconf:base:1.0">'
        "<configuration-information><configuration-output>"
        "[edit protocols isis interface ae100]\n+ metric 1000000;"
        "</configuration-output></configuration-information></rpc-reply>"
    )

    diff = connection.perform_candidate_diff("system { host-name test; }")

    assert diff == "[edit protocols isis interface ae100]\n+ metric 1000000;"
    connection._manager.load_configuration.assert_called_once_with(
        action="override",
        format="text",
        config="system { host-name test; }",
    )
    connection._manager.validate.assert_called_once_with(source="candidate")
    connection._manager.discard_changes.assert_called()


def test_junos_apply_rechecks_approved_diff() -> None:
    """Junos apply aborts if the candidate changed after operator approval."""
    connection = JunosConnection.__new__(JunosConnection)
    connection._manager = MagicMock()
    connection._candidate_diff = MagicMock(return_value="different diff")

    with pytest.raises(DiffChangedException, match="changed since approval"):
        connection.commit_candidate_config("rendered config", "approved diff")

    connection._manager.commit.assert_not_called()
    connection._manager.discard_changes.assert_called()
