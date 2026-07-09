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
import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from paramiko import (
    AUTH_SUCCESSFUL,
    OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED,
    OPEN_SUCCEEDED,
    SFTP_OK,
    SFTPAttributes,
)

from nv_config_manager.ztp.sftp.main import (
    ZTPServer,
    ZTPSFTPHandle,
    ZTPSFTPServer,
    handle_connection,
    shutdown_event,
    start_server,
)


@pytest.fixture
def ztp_server():
    return ZTPServer()


@pytest.fixture
def sftp_handle():
    handle = ZTPSFTPHandle(0)
    handle.readfile = io.BytesIO(b"test content")
    return handle


@pytest.fixture
def sftp_server():
    server = ZTPServer()
    return ZTPSFTPServer(server, client_addr="192.168.1.1")


def test_check_auth_password(ztp_server):
    """Test that all password authentication attempts are allowed."""
    result = ztp_server.check_auth_password("testuser", "testpass")
    assert result == AUTH_SUCCESSFUL


def test_get_allowed_auths(ztp_server):
    """Test that only password authentication is allowed."""
    result = ztp_server.get_allowed_auths("testuser")
    assert result == "password"


def test_check_channel_request(ztp_server):
    """Test channel request handling."""
    # Test session channel
    result = ztp_server.check_channel_request("session", 1)
    assert result == OPEN_SUCCEEDED

    # Test other channel types
    result = ztp_server.check_channel_request("other", 1)
    assert result == OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED


def test_close(sftp_handle):
    """Test file handle closing."""
    result = sftp_handle.close()
    assert result == SFTP_OK
    # The readfile should be closed but not None
    assert sftp_handle.readfile.closed


def test_read(sftp_handle):
    """Test reading from file handle."""
    # Test reading from start
    result = sftp_handle.read(0, 4)
    assert result == b"test"

    # Test reading from offset
    result = sftp_handle.read(5, 4)
    assert result == b"cont"


@patch("nv_config_manager.ztp.sftp.main.NautobotClient")
def test_load_ztp_file(mock_nb_client, sftp_server, mock_device_data):
    """Test loading ZTP configuration file."""
    # Mock device data
    mock_device = MagicMock()
    mock_device.addresses = ["192.168.1.1"]
    # Make load_file an async mock
    mock_device.load_file = AsyncMock(return_value="test config")

    # Create a mock NautobotClient instance (async context manager)
    mock_nb_instance = MagicMock()
    mock_nb_instance.get_device_data = AsyncMock(return_value=mock_device)
    mock_nb_instance.__aenter__ = AsyncMock(return_value=mock_nb_instance)
    mock_nb_instance.__aexit__ = AsyncMock(return_value=None)
    mock_nb_client.return_value = mock_nb_instance

    result = sftp_server._load_ztp_file("device1", "config.txt")
    assert isinstance(result, io.BytesIO)
    assert result.getvalue() == b"test config"


@patch("nv_config_manager.ztp.sftp.main.get_storage_client")
def test_load_s3_file(mock_s3_client, sftp_server):
    """Test loading file from S3."""
    # Create a mock StreamingBody with async read
    mock_streaming_body = MagicMock()
    mock_streaming_body.read = AsyncMock(return_value=b"s3 content")

    # Mock the async context manager and get_object method
    mock_s3_instance = MagicMock()
    mock_s3_instance.__aenter__ = AsyncMock(return_value=mock_s3_instance)
    mock_s3_instance.__aexit__ = AsyncMock(return_value=None)
    mock_s3_instance.get_object = AsyncMock(return_value=("config.txt", mock_streaming_body))
    mock_s3_client.return_value = mock_s3_instance

    result = sftp_server._load_s3_file("cisco", "1.0", "config.txt")
    assert isinstance(result, io.BytesIO)
    assert result.getvalue() == b"s3 content"


@patch("nv_config_manager.ztp.sftp.main.get_storage_client")
def test_load_s3_file_binary(mock_s3_client, sftp_server):
    """Test loading binary file from S3."""
    # Create a mock StreamingBody with binary content and async read
    mock_streaming_body = MagicMock()
    mock_streaming_body.read = AsyncMock(return_value=b"\x00\x01\x02\x03\x04\x05")

    # Mock the async context manager and get_object method
    mock_s3_instance = MagicMock()
    mock_s3_instance.__aenter__ = AsyncMock(return_value=mock_s3_instance)
    mock_s3_instance.__aexit__ = AsyncMock(return_value=None)
    mock_s3_instance.get_object = AsyncMock(return_value=("firmware.bin", mock_streaming_body))
    mock_s3_client.return_value = mock_s3_instance

    result = sftp_server._load_s3_file("cisco", "1.0", "firmware.bin")
    assert isinstance(result, io.BytesIO)
    assert result.getvalue() == b"\x00\x01\x02\x03\x04\x05"


def test_load_path(sftp_server):
    """Test path loading with different path types."""
    # Test healthcheck path
    result = sftp_server._load_path("/healthcheck")
    assert isinstance(result, io.BytesIO)
    assert result.getvalue() == b"OK"

    # Test unknown path type
    with pytest.raises(FileNotFoundError):
        sftp_server._load_path("/unknown/path")


def test_mock_stat(sftp_server):
    """Test file attribute generation."""
    with patch.object(sftp_server, "_load_path", return_value=io.StringIO("test")):
        result = sftp_server._mock_stat("/test/path")
        assert isinstance(result, SFTPAttributes)
        assert result.st_size == 4


def test_stat(sftp_server):
    """Test stat operation."""
    sftp_server.logger = MagicMock()
    with patch.object(sftp_server, "_mock_stat", return_value=SFTPAttributes()):
        result = sftp_server.stat("/test/path")
        assert isinstance(result, SFTPAttributes)
    sftp_server.logger.debug.assert_called_once_with("stat request: %s", "/test/path")


def test_lstat(sftp_server):
    """Test lstat operation."""
    with patch.object(sftp_server, "_mock_stat", return_value=SFTPAttributes()):
        result = sftp_server.lstat("/test/path")
        assert isinstance(result, SFTPAttributes)


def test_open(sftp_server):
    """Test file opening."""
    with patch.object(sftp_server, "_load_path", return_value=io.StringIO("test")):
        result = sftp_server.open("/test/path", 0, None)
        assert isinstance(result, ZTPSFTPHandle)


@patch("nv_config_manager.ztp.sftp.main.paramiko.Transport")
def test_handle_connection(mock_transport):
    """Test connection handling."""
    # Create mock socket and address
    mock_socket = MagicMock()
    mock_addr = ("192.168.1.1", 12345)
    mock_host_key = MagicMock()

    # Mock transport and channel
    mock_channel = MagicMock()
    mock_transport_instance = MagicMock()
    mock_transport.return_value = mock_transport_instance
    mock_transport_instance.accept.return_value = mock_channel

    # Set up transport lifecycle
    mock_transport_instance.is_active.side_effect = [
        True,
        True,
        False,
    ]  # Will return True twice, then False

    # Run the connection handler
    handle_connection(mock_socket, mock_addr, mock_host_key)

    # Verify transport was set up and started
    mock_transport_instance.add_server_key.assert_called_once_with(mock_host_key)
    mock_transport_instance.start_server.assert_called_once()
    mock_transport_instance.close.assert_called_once()


@pytest.mark.timeout(0)  # override default timeout, sftp startup takes a bit
@patch("nv_config_manager.ztp.sftp.main.socket.socket")
def test_start_server(mock_socket):
    """Test server startup."""
    # Mock socket instance
    mock_socket_instance = MagicMock()
    mock_socket.return_value = mock_socket_instance

    # Start the server with shutdown_event set so it stops after bringup
    shutdown_event.set()
    start_server(host="127.0.0.1", port=2222, level="INFO")

    # Verify socket was set up correctly
    mock_socket_instance.bind.assert_called_once_with(("127.0.0.1", 2222))
    mock_socket_instance.listen.assert_called_once_with(10)
    mock_socket_instance.close.assert_called_once()
