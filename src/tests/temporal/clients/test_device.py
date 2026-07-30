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
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import paramiko
import pytest
from jnpr.junos.exception import (
    CommitError,
    ConfigLoadError,
    ConnectAuthError,
    ProbeError,
)
from lxml import etree
from temporalio.exceptions import ApplicationError

from nv_config_manager.temporal.client.device import (
    ConfigSyntaxException,
    CumulusConnection,
    DiffChangedException,
    JuniperConnection,
    MockNetworkConnection,
    NetworkConnection,
    NetworkDeviceException,
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


# =============================================================================
# JuniperConnection (PyEZ / NETCONF)
# =============================================================================

_JUNIPER_DEVICE = NetworkDeviceData(
    id="a1b2c3d4-1111-2222-3333-444455556666",
    name="test-router",
    role="backbone-router",
    platform="juniper-junos",
    site="SITEA",
    device_type="ptx10002-36qdd",
    primary_ip4="192.0.2.10",
    primary_ip6=None,
)


class _FakeConfigCM:
    """Stand-in for PyEZ's Config context manager wrapping a mock utility."""

    def __init__(self, cu: MagicMock) -> None:
        self._cu = cu

    def __enter__(self) -> MagicMock:
        return self._cu

    def __exit__(self, *exc: object) -> bool:
        return False


def _rpc_error_rsp(message: str, severity: str = "error") -> etree._Element:
    """Build a minimal Junos <rpc-error> element for PyEZ exception construction."""
    return etree.fromstring(
        f"<rpc-error><error-severity>{severity}</error-severity>"
        f"<error-message>{message}</error-message></rpc-error>"
    )


@pytest.fixture
def juniper_conn():
    """A JuniperConnection built with load_config patched (no network at init)."""
    config = ConfigParser()
    config.add_section("device")
    config.set("device", "username", "shooks")
    config.set("device", "password", "pw")
    with patch("nv_config_manager.temporal.client.device.load_config", return_value=config):
        yield JuniperConnection("192.0.2.10", password="pw")


@patch("nv_config_manager.temporal.client.device.load_config")
def test_from_device_data_returns_juniper_when_mock_false(mock_load_config):
    """Config with mock = false + juniper-junos platform → JuniperConnection on the NETCONF port."""
    mock_load_config.return_value = _mock_config(mock=False)
    conn = NetworkConnection.from_device_data(_JUNIPER_DEVICE)
    assert isinstance(conn, JuniperConnection)
    assert conn._port == 830


def test_get_device_connects_once_and_caches(juniper_conn):
    """The NETCONF session is opened lazily on first use and reused afterwards."""
    fake_device = MagicMock()
    with patch(
        "nv_config_manager.temporal.client.device.Device", return_value=fake_device
    ) as mock_device:
        first = juniper_conn._get_device()
        second = juniper_conn._get_device()
    assert first is fake_device
    assert second is fake_device
    fake_device.open.assert_called_once()
    assert mock_device.call_count == 1
    assert mock_device.call_args.kwargs["port"] == 830


def test_connect_rotates_then_raises_on_auth_failure(juniper_conn):
    """Genuine auth failures exhaust password rotation and raise NetworkDeviceException."""
    with patch("nv_config_manager.temporal.client.device.Device") as mock_device:
        mock_device.return_value.open.side_effect = ConnectAuthError(
            dev=SimpleNamespace(hostname="test-router")
        )
        with pytest.raises(NetworkDeviceException):
            juniper_conn._get_device()


def test_connect_raises_clear_error_on_probe_failure(juniper_conn):
    """A probe (reachability) failure raises immediately with a NETCONF-specific message."""
    with patch("nv_config_manager.temporal.client.device.Device") as mock_device:
        mock_device.return_value.open.side_effect = ProbeError(
            dev=SimpleNamespace(hostname="test-router")
        )
        with pytest.raises(NetworkDeviceException, match="NETCONF"):
            juniper_conn._get_device()


def test_close_is_safe_before_device_assigned(juniper_conn):
    """close() must not raise even if _device was never set (failed init path)."""
    del juniper_conn._device
    juniper_conn.close()


def test_context_manager_closes_session(juniper_conn):
    """Using the connection as a context manager closes the session on exit."""
    device = MagicMock()
    juniper_conn._device = device
    with juniper_conn as conn:
        assert conn is juniper_conn
    device.close.assert_called_once()
    assert juniper_conn._device is None


def test_rpc_requests_json_and_converts_flag_params(juniper_conn):
    """_rpc asks for JSON format and turns empty values into boolean flags."""
    device = MagicMock()
    device.rpc.get_interface_information.return_value = {"interface-information": []}
    with patch.object(juniper_conn, "_get_device", return_value=device):
        result = juniper_conn._rpc("get-interface-information", params={"terse": ""})
    assert result == {"interface-information": []}
    args, kwargs = device.rpc.get_interface_information.call_args
    assert args[0] == {"format": "json"}
    assert kwargs == {"terse": True}


def test_get_running_configuration_returns_text_format(juniper_conn):
    """Backup returns full hierarchical text config terminated by a newline."""
    device = MagicMock()
    device.rpc.get_config.return_value = SimpleNamespace(text="system {\n    host-name RTR1;\n}")
    with patch.object(juniper_conn, "_get_device", return_value=device):
        config = juniper_conn.get_running_configuration()
    assert config == "system {\n    host-name RTR1;\n}\n"
    assert device.rpc.get_config.call_args.kwargs["options"]["format"] == "text"


def test_get_configuration_text_returns_hierarchical(juniper_conn):
    """The text getter requests hierarchical (curly-brace) format."""
    device = MagicMock()
    device.rpc.get_config.return_value = SimpleNamespace(text="system {\n    host-name RTR1;\n}")
    with patch.object(juniper_conn, "_get_device", return_value=device):
        text = juniper_conn.get_configuration_text()
    assert "host-name RTR1" in text
    assert device.rpc.get_config.call_args.kwargs["options"]["format"] == "text"


def test_get_hostname_and_running_image_use_facts(juniper_conn):
    """Hostname and running image come from PyEZ facts."""
    device = MagicMock()
    device.facts = {"hostname": "RTR1", "version": "24.4R2-S3.7-EVO"}
    with patch.object(juniper_conn, "_get_device", return_value=device):
        assert juniper_conn.get_hostname() == "RTR1"
        assert juniper_conn.get_running_image() == "24.4R2-S3.7-EVO"


def test_get_hostname_raises_when_absent(juniper_conn):
    """A missing hostname fact raises a non-retryable error."""
    device = MagicMock()
    device.facts = {"hostname": None}
    with patch.object(juniper_conn, "_get_device", return_value=device):
        with pytest.raises(ApplicationError):
            juniper_conn.get_hostname()


def test_get_uptime_parses_seconds(juniper_conn):
    """Uptime is parsed from the junos:seconds attribute."""
    data = {
        "system-uptime-information": [
            {"uptime-information": [{"up-time": [{"attributes": {"junos:seconds": "12345"}}]}]}
        ]
    }
    with patch.object(juniper_conn, "_rpc", return_value=data):
        assert juniper_conn.get_uptime() == 12345


def test_get_uptime_raises_on_unexpected_shape(juniper_conn):
    """Uptime raises a clear error when the response shape is unexpected."""
    with patch.object(juniper_conn, "_rpc", return_value={"unexpected": True}):
        with pytest.raises(NetworkDeviceException):
            juniper_conn.get_uptime()


def test_perform_candidate_diff_loads_full_config_rolls_back_and_returns_diff(juniper_conn):
    """perform_candidate_diff loads the full config with load update, returns the diff, discards."""
    cu = MagicMock()
    cu.diff.return_value = "[edit system]\n-  host-name OLD;\n+  host-name RTR1;"
    with (
        patch.object(juniper_conn, "_get_device", return_value=MagicMock()),
        patch("nv_config_manager.temporal.client.device.Config", return_value=_FakeConfigCM(cu)),
    ):
        diff = juniper_conn.perform_candidate_diff("system { host-name RTR1; }")
    assert "host-name" in diff
    cu.load.assert_called_once_with("system { host-name RTR1; }", format="text", update=True)
    cu.rollback.assert_called_once()
    cu.commit.assert_not_called()


def test_perform_candidate_diff_rejects_partial(juniper_conn):
    """Partial diffs are rejected; no config session is opened."""
    with patch("nv_config_manager.temporal.client.device.Config") as mock_config:
        with pytest.raises(NetworkDeviceException, match="Partial configuration is not supported"):
            juniper_conn.perform_candidate_diff("system { host-name RTR1; }", partial=True)
    mock_config.assert_not_called()


def test_commit_candidate_config_rejects_partial(juniper_conn):
    """Partial commits are rejected; no config session is opened."""
    with patch("nv_config_manager.temporal.client.device.Config") as mock_config:
        with pytest.raises(NetworkDeviceException, match="Partial configuration is not supported"):
            juniper_conn.commit_candidate_config(
                "system { host-name RTR1; }", approved_diff="d", partial=True
            )
    mock_config.assert_not_called()


def test_perform_candidate_diff_raises_config_syntax_on_load_error(juniper_conn):
    """A load failure surfaces as ConfigSyntaxException."""
    cu = MagicMock()
    cu.load.side_effect = ConfigLoadError(rsp=_rpc_error_rsp("syntax error"))
    with (
        patch.object(juniper_conn, "_get_device", return_value=MagicMock()),
        patch("nv_config_manager.temporal.client.device.Config", return_value=_FakeConfigCM(cu)),
    ):
        with pytest.raises(ConfigSyntaxException):
            juniper_conn.perform_candidate_diff("set nonsense")


def test_commit_candidate_config_raises_when_diff_changed(juniper_conn):
    """A mismatch between the fresh diff and the approved diff aborts before commit."""
    cu = MagicMock()
    cu.diff.return_value = "new-diff"
    with (
        patch.object(juniper_conn, "_get_device", return_value=MagicMock()),
        patch("nv_config_manager.temporal.client.device.Config", return_value=_FakeConfigCM(cu)),
    ):
        with pytest.raises(DiffChangedException):
            juniper_conn.commit_candidate_config("config", approved_diff="old-diff")
    cu.rollback.assert_called_once()
    cu.commit.assert_not_called()


def test_commit_candidate_config_no_diff_confirms_pending_commit(juniper_conn):
    """Empty diff with commit_confirm still issues the confirm."""
    cu = MagicMock()
    cu.diff.return_value = ""
    with (
        patch.object(juniper_conn, "_get_device", return_value=MagicMock()),
        patch("nv_config_manager.temporal.client.device.Config", return_value=_FakeConfigCM(cu)),
    ):
        juniper_conn.commit_candidate_config("config", approved_diff="", commit_confirm=True)
    cu.rollback.assert_called_once()
    cu.commit.assert_called_once()
    assert "confirm" not in cu.commit.call_args.kwargs


def test_commit_candidate_config_no_diff_direct_does_not_commit(juniper_conn):
    """Empty diff with commit_confirm=False issues no commit at all."""
    cu = MagicMock()
    cu.diff.return_value = ""
    with (
        patch.object(juniper_conn, "_get_device", return_value=MagicMock()),
        patch("nv_config_manager.temporal.client.device.Config", return_value=_FakeConfigCM(cu)),
    ):
        juniper_conn.commit_candidate_config("config", approved_diff="", commit_confirm=False)
    cu.commit.assert_not_called()
    cu.rollback.assert_called_once()


def test_commit_candidate_config_commit_confirm_then_confirms(juniper_conn):
    """commit_confirm=True commits with a rollback timer then confirms with a plain commit."""
    cu = MagicMock()
    cu.diff.return_value = "diff"
    with (
        patch.object(juniper_conn, "_get_device", return_value=MagicMock()),
        patch("nv_config_manager.temporal.client.device.Config", return_value=_FakeConfigCM(cu)),
    ):
        juniper_conn.commit_candidate_config("config", approved_diff="diff", commit_confirm=True)
    # First commit carries the confirm timer; the follow-up confirm commit does not.
    assert cu.commit.call_count == 2
    assert "confirm" in cu.commit.call_args_list[0].kwargs
    assert "confirm" not in cu.commit.call_args_list[1].kwargs


def test_commit_candidate_config_direct_commit(juniper_conn):
    """commit_confirm=False commits directly with no follow-up confirm."""
    cu = MagicMock()
    cu.diff.return_value = "diff"
    with (
        patch.object(juniper_conn, "_get_device", return_value=MagicMock()),
        patch("nv_config_manager.temporal.client.device.Config", return_value=_FakeConfigCM(cu)),
    ):
        juniper_conn.commit_candidate_config("config", approved_diff="diff", commit_confirm=False)
    cu.commit.assert_called_once()
    assert "confirm" not in cu.commit.call_args.kwargs


def test_commit_candidate_config_raises_on_commit_error(juniper_conn):
    """A commit failure surfaces as NetworkDeviceException."""
    cu = MagicMock()
    cu.diff.return_value = "diff"
    cu.commit.side_effect = CommitError(rsp=_rpc_error_rsp("commit failed"))
    with (
        patch.object(juniper_conn, "_get_device", return_value=MagicMock()),
        patch("nv_config_manager.temporal.client.device.Config", return_value=_FakeConfigCM(cu)),
    ):
        with pytest.raises(NetworkDeviceException):
            juniper_conn.commit_candidate_config("config", approved_diff="diff")


# ---------------------------------------------------------------------------
# Numbered rollback and rescue configuration.
# ---------------------------------------------------------------------------


def test_get_rollback_diff_returns_diff(juniper_conn):
    """get_rollback_diff compares the active config against a numbered rollback."""
    cu = MagicMock()
    cu.diff.return_value = "rollback-diff"
    with (
        patch.object(juniper_conn, "_get_device", return_value=MagicMock()),
        patch("nv_config_manager.temporal.client.device.Config", return_value=_FakeConfigCM(cu)),
    ):
        diff = juniper_conn.get_rollback_diff(3)
    assert diff == "rollback-diff"
    cu.diff.assert_called_once_with(rb_id=3)
    cu.rollback.assert_called_once()


def test_rollback_configuration_commits_when_diff(juniper_conn):
    """rollback_configuration loads the numbered revision and commits when it differs."""
    cu = MagicMock()
    cu.diff.return_value = "diff"
    with (
        patch.object(juniper_conn, "_get_device", return_value=MagicMock()),
        patch("nv_config_manager.temporal.client.device.Config", return_value=_FakeConfigCM(cu)),
    ):
        juniper_conn.rollback_configuration(2, commit_confirm=False)
    cu.rollback.assert_called_once_with(rb_id=2)
    cu.commit.assert_called_once()


def test_rollback_configuration_noop_when_no_diff(juniper_conn):
    """When the numbered revision matches the active config, nothing is committed."""
    cu = MagicMock()
    cu.diff.return_value = ""
    with (
        patch.object(juniper_conn, "_get_device", return_value=MagicMock()),
        patch("nv_config_manager.temporal.client.device.Config", return_value=_FakeConfigCM(cu)),
    ):
        juniper_conn.rollback_configuration(2, commit_confirm=False)
    # rollback(rb_id=2) to load, then rollback() to discard the unchanged candidate.
    assert cu.rollback.call_count == 2
    cu.commit.assert_not_called()


def test_save_rescue_configuration_calls_rescue_save(juniper_conn):
    """save_rescue_configuration issues a rescue save."""
    with (
        patch.object(juniper_conn, "_get_device", return_value=MagicMock()),
        patch("nv_config_manager.temporal.client.device.Config") as mock_config,
    ):
        juniper_conn.save_rescue_configuration()
    mock_config.return_value.rescue.assert_called_once_with(action="save")


def test_get_rescue_configuration_returns_text(juniper_conn):
    """get_rescue_configuration returns the saved rescue text."""
    with (
        patch.object(juniper_conn, "_get_device", return_value=MagicMock()),
        patch("nv_config_manager.temporal.client.device.Config") as mock_config,
    ):
        mock_config.return_value.rescue.return_value = "system { host-name RTR1; }"
        rescue = juniper_conn.get_rescue_configuration()
    assert rescue == "system { host-name RTR1; }"
    mock_config.return_value.rescue.assert_called_once_with(action="get", format="text")


def test_get_rescue_configuration_returns_none_when_absent(juniper_conn):
    """get_rescue_configuration returns None when no rescue config is set."""
    with (
        patch.object(juniper_conn, "_get_device", return_value=MagicMock()),
        patch("nv_config_manager.temporal.client.device.Config") as mock_config,
    ):
        mock_config.return_value.rescue.return_value = None
        assert juniper_conn.get_rescue_configuration() is None


def test_delete_rescue_configuration_calls_rescue_delete(juniper_conn):
    """delete_rescue_configuration issues a rescue delete."""
    with (
        patch.object(juniper_conn, "_get_device", return_value=MagicMock()),
        patch("nv_config_manager.temporal.client.device.Config") as mock_config,
    ):
        juniper_conn.delete_rescue_configuration()
    mock_config.return_value.rescue.assert_called_once_with(action="delete")


def test_rollback_to_rescue_reloads_and_commits(juniper_conn):
    """rollback_to_rescue reloads the rescue config and commits when it differs."""
    cu = MagicMock()
    cu.diff.return_value = "diff"
    with (
        patch.object(juniper_conn, "_get_device", return_value=MagicMock()),
        patch("nv_config_manager.temporal.client.device.Config", return_value=_FakeConfigCM(cu)),
    ):
        juniper_conn.rollback_to_rescue(commit_confirm=False)
    cu.rescue.assert_called_once_with(action="reload")
    cu.commit.assert_called_once()


def test_rollback_to_rescue_noop_when_no_diff(juniper_conn):
    """rollback_to_rescue does nothing when the rescue config matches the active config."""
    cu = MagicMock()
    cu.diff.return_value = ""
    with (
        patch.object(juniper_conn, "_get_device", return_value=MagicMock()),
        patch("nv_config_manager.temporal.client.device.Config", return_value=_FakeConfigCM(cu)),
    ):
        juniper_conn.rollback_to_rescue(commit_confirm=False)
    cu.commit.assert_not_called()
    cu.rollback.assert_called_once()


def test_run_diagnostic_command_dispatches_supported_junos_command(juniper_conn):
    """A supported Junos diagnostic maps to its RPC and serialises to JSON."""
    with patch.object(juniper_conn, "_rpc", return_value={"host-name": "test-router"}) as mock_rpc:
        raw = juniper_conn.run_diagnostic_command("show_version")
    mock_rpc.assert_called_once_with("get-software-information")
    assert json.loads(raw) == {"host-name": "test-router"}


def test_run_diagnostic_command_unsupported_junos_raises_network_exception(juniper_conn):
    """Junos diagnostics with no RPC mapping surface a NetworkDeviceException, not
    a raw NotImplementedError from the base stub."""
    with pytest.raises(NetworkDeviceException, match="not implemented for JuniperConnection"):
        juniper_conn.run_diagnostic_command("show_bgp_summary")
