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
import argparse
import asyncio
import errno
import io
import logging
import os
import signal
import socket
import threading
import time
from typing import Any, cast

import paramiko
from paramiko import (
    ServerInterface,
    SFTPAttributes,
    SFTPHandle,
    SFTPServer,
    SFTPServerInterface,
)
from paramiko.channel import Channel
from paramiko.common import (
    AUTH_SUCCESSFUL,
    OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED,
    OPEN_SUCCEEDED,
)
from paramiko.sftp import (
    SFTP_FAILURE,
    SFTP_NO_SUCH_FILE,
    SFTP_OK,
    SFTP_PERMISSION_DENIED,
)
from paramiko.transport import Transport

from nv_config_manager.common.config import get_storage_client
from nv_config_manager.common.log import (
    EscapingLoggerAdapter,
    LogCategory,
    configure_logging,
    get_logger,
)
from nv_config_manager.ztp.nautobot import NautobotClient
from nv_config_manager.ztp.storage import ObjectStorageNotFoundException

logger = get_logger(__name__, category=LogCategory.ZTP)

# Global flag to control server shutdown
shutdown_event = threading.Event()


def is_localhost(addr: tuple[str, int]) -> bool:
    """Check if the connection is from localhost."""
    return addr[0] in ("127.0.0.1", "::1", "localhost")


def get_logger_for_addr(addr: tuple[str, int]) -> logging.Logger | logging.LoggerAdapter:
    """Get a logger with appropriate level based on client address."""
    if is_localhost(addr):
        healthcheck_logger = logging.getLogger(f"{__name__}.localhost")
        healthcheck_logger.setLevel(logging.WARNING)
        return EscapingLoggerAdapter(healthcheck_logger, extra={"category": LogCategory.ZTP})
    return logger


def signal_handler(signum: int, frame: Any) -> None:
    """Handle shutdown signals from Kubernetes."""
    logger.info("Received signal %d, initiating graceful shutdown", signum)
    shutdown_event.set()


class ZTPServer(ServerInterface):
    def check_auth_password(self, username: str, password: str) -> int:
        """Allow all password authentication attempts."""
        # all are allowed
        return cast(int, AUTH_SUCCESSFUL)

    def get_allowed_auths(self, username: str) -> str:
        """Return the list of allowed authentication methods."""
        return "password"

    def check_channel_request(self, kind: str, chanid: int) -> int:
        """Check if the requested channel type is allowed."""
        if kind == "session":
            return cast(int, OPEN_SUCCEEDED)
        return cast(int, OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED)


class ZTPSFTPHandle(SFTPHandle):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize a new SFTP file handle."""
        super().__init__(*args)
        self.readfile: io.StringIO | io.BytesIO | None = None
        self.logger: logging.Logger | logging.LoggerAdapter = logger
        self.filename: str = ""

    def set_logger(self, logger: logging.Logger | logging.LoggerAdapter) -> None:
        """Set the logger for this handle."""
        self.logger = logger

    def close(self) -> int:  # type: ignore[override, ty:invalid-method-override]
        """Close the file handle and release resources."""
        self.logger.debug("Closing file handle for: %s", self.filename or "unknown")
        try:
            if self.readfile:
                self.readfile.close()

        except Exception as e:
            self.logger.error("Error closing file handle: %s", e)
        return int(SFTP_OK)

    def read(self, offset: int, length: int) -> bytes | int:
        """Read a specified number of bytes from the file at the given offset."""
        self.logger.debug(
            "Reading %d bytes at offset %d from %s",
            length,
            offset,
            self.filename or "unknown",
        )
        try:
            if self.readfile is None:
                return SFTPServer.convert_errno(errno.ENOENT)
            self.readfile.seek(offset)
            data = self.readfile.read(length)
            if isinstance(data, str):
                data = data.encode("utf-8")
            self.logger.debug("Read %d bytes successfully", len(data))
            return data
        except OSError as e:
            self.logger.error("Error reading from file: %s", e)
            return SFTPServer.convert_errno(e.errno or errno.EIO)


class ZTPSFTPServer(SFTPServerInterface):
    def __init__(self, server: ServerInterface, *args: Any, **kwargs: Any) -> None:
        """Initialize the SFTP server with the given server instance and client address."""
        super().__init__(server)
        self._path_cache: dict[str, io.StringIO | io.BytesIO] = {}  # Cache for resolved paths
        self._client_addr: str | None = kwargs.get("client_addr")
        self.logger = get_logger_for_addr((self._client_addr or "unknown", 0))
        self.logger.info("SFTP server initialized for client %s", self._client_addr)

        # Create a dedicated event loop for this SFTP session
        # This avoids the overhead of creating/destroying loops for each async call
        self._event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._event_loop)

    def _load_path(self, path: str) -> io.BytesIO:
        """Load file content from the given path."""
        if path in self._path_cache:
            self.logger.debug("Cache hit for path: %s", path)
            cached = self._path_cache[path]
            if isinstance(cached, io.BytesIO):
                return cached
            # Convert StringIO to BytesIO if needed
            return io.BytesIO(cached.getvalue().encode("utf-8"))

        self.logger.info("Request for path: %s from %s", path, self._client_addr)
        path_parts = path.split("/")
        if path_parts[1] == "device":
            content = self._load_ztp_file(path_parts[2], path_parts[3])
            self._path_cache[path] = content
            return content
        if path_parts[1] == "file":
            content = self._load_s3_file(path_parts[2], path_parts[3], path_parts[4])
            self._path_cache[path] = content
            return content
        if path_parts[1] == "healthcheck":
            return io.BytesIO(b"OK")

        raise FileNotFoundError(f"Unknown path type: {path_parts[0]}")

    def _load_ztp_file(self, device_id: str, config_file: str) -> io.BytesIO:
        """Load a ZTP configuration file from the config store or return a cached version."""
        self.logger.info(
            "Loading file for Device: %s, Config: %s from %s",
            device_id,
            config_file,
            self._client_addr,
        )

        # Get device data from Nautobot using the session's event loop
        nb_client = NautobotClient()

        # Check if client is from localhost (bypass IP auth for testing/healthchecks)
        client_is_localhost = self._client_addr in ("127.0.0.1", "::1", "localhost")

        async def get_device_and_file() -> tuple[Any, str | None]:
            async with nb_client:
                device = await nb_client.get_device_data(device_id)
            if not device:
                return None, None
            # Bypass IP validation for localhost connections (testing/port-forward)
            if not client_is_localhost and self._client_addr not in device.addresses:
                raise PermissionError(
                    f"Access denied. Expected IP(s): {device.addresses}, Actual IP: {self._client_addr}"
                )
            # Load file content
            file_content = await device.load_file(config_file)
            return device, file_content

        device, file_content = self._event_loop.run_until_complete(get_device_and_file())

        if not device or file_content is None:
            raise FileNotFoundError("File not found")

        # Convert string content to bytes
        return io.BytesIO(file_content.encode("utf-8"))

    def _load_s3_file(self, platform: str, version: str, filename: str) -> io.BytesIO:
        """Load a ZTP configuration file from S3."""
        self.logger.info(
            "Loading file from S3: %s/%s/%s for %s",
            platform,
            version,
            filename,
            self._client_addr,
        )
        storage_client = get_storage_client()
        try:
            # Define async function to fetch from S3
            async def get_s3_object() -> bytes:
                async with storage_client:
                    _, body = await storage_client.get_object(platform, version, filename)
                    # Read the entire content (aioboto3 StreamingBody.read() is async)
                    content = await body.read()
                    return cast(bytes, content)

            # Use the session's event loop
            content = self._event_loop.run_until_complete(get_s3_object())
            # Return the bytes
            return io.BytesIO(content)
        except ObjectStorageNotFoundException as exc:
            raise FileNotFoundError(
                f"File not found in S3: {platform}/{version}/{filename}"
            ) from exc

    def finish_subsystem(self) -> None:  # type: ignore[override]
        """Clean up resources when the SFTP subsystem is finished."""
        self.logger.debug("Clearing path cache and closing event loop")
        self._path_cache.clear()

        # Close the event loop to free resources
        if self._event_loop and not self._event_loop.is_closed():
            self._event_loop.close()

        super().finish_subsystem()  # type: ignore[misc, ty:unresolved-attribute]

    def _mock_stat(self, path: str) -> SFTPAttributes | int:
        """Return mock file attributes for the given path."""
        # Optimize for S3 files - use head_object instead of downloading the entire file
        path_parts = path.split("/")
        if path_parts[1] == "file" and len(path_parts) >= 5:
            # This is an S3 file path: /file/platform/version/filename
            platform, version, filename = (
                path_parts[2],
                path_parts[3],
                "/".join(path_parts[4:]),
            )
            return self._stat_s3_file(platform, version, filename)

        # For non-S3 paths, fall back to loading the full file
        try:
            file = self._load_path(path)
            self.logger.debug("Successfully loaded file for stat: %s", path)
        except Exception as exc:
            self.logger.error(
                "Error loading file %s for stat: %s",
                path,
                exc,
            )
            if isinstance(exc, FileNotFoundError):
                return SFTP_NO_SUCH_FILE
            if isinstance(exc, PermissionError):
                return SFTP_PERMISSION_DENIED
            return SFTP_FAILURE
        attr = SFTPAttributes()
        # Set the size of the file-like object
        if isinstance(file, io.StringIO):
            file.seek(0, os.SEEK_END)
            attr.st_size = file.tell()
            file.seek(0)  # Reset the file pointer
        elif isinstance(file, io.BytesIO):
            attr.st_size = len(file.getvalue())
        else:
            raise TypeError("Unsupported file type")

        # Set other attributes
        attr.st_uid = os.getuid()  # Current user ID
        attr.st_gid = os.getgid()  # Current group ID
        attr.st_mode = 0o100644  # Regular file with 644 permissions
        current_time = int(time.time())
        attr.st_atime = current_time  # Access time
        attr.st_mtime = current_time  # Modification time
        self.logger.debug(
            "Created attributes for file %s: size=%d",
            path,
            attr.st_size,
        )
        return attr

    def _stat_s3_file(self, platform: str, version: str, filename: str) -> SFTPAttributes | int:
        """Get file attributes for an S3 file using head_object (no download)."""
        self.logger.info(
            "Getting metadata for S3 file: %s/%s/%s",
            platform,
            version,
            filename,
        )
        storage_client = get_storage_client()
        try:

            async def get_metadata() -> dict[str, Any]:
                async with storage_client:
                    result = await storage_client.get_object_metadata(platform, version, filename)
                    return dict(result)

            metadata = self._event_loop.run_until_complete(get_metadata())

            attr = SFTPAttributes()
            attr.st_size = metadata["size"]
            attr.st_uid = os.getuid()
            attr.st_gid = os.getgid()
            attr.st_mode = 0o100644  # Regular file with 644 permissions

            # Use last_modified time if available
            if metadata.get("last_modified"):
                mtime = int(metadata["last_modified"].timestamp())
                attr.st_atime = mtime
                attr.st_mtime = mtime
            else:
                current_time = int(time.time())
                attr.st_atime = current_time
                attr.st_mtime = current_time

            self.logger.debug(
                "Created attributes for S3 file %s/%s/%s: size=%d",
                platform,
                version,
                filename,
                attr.st_size,
            )
            return attr
        except ObjectStorageNotFoundException:
            self.logger.error(
                "S3 file not found: %s/%s/%s",
                platform,
                version,
                filename,
            )
            return SFTP_NO_SUCH_FILE
        except Exception as exc:
            self.logger.error("Error getting S3 metadata: %s", exc)
            return SFTP_FAILURE

    def stat(self, path: str) -> SFTPAttributes | int:
        """Return file attributes for the given path."""
        self.logger.debug("stat request: %s", path)
        return self._mock_stat(path)

    def lstat(self, path: str) -> SFTPAttributes | int:
        """Return file attributes for the given path without following symbolic links."""
        self.logger.debug("lstat request: %s", path)
        return self._mock_stat(path)

    def open(self, path: str, flags: int, attr: SFTPAttributes | None) -> ZTPSFTPHandle | int:
        """Open a file handle for the given path with the specified flags."""
        self.logger.debug("open request: %s, flags: %s", path, flags)
        try:
            file = self._load_path(path)
            self.logger.debug("Successfully loaded file for path: %s", path)
        except Exception as exc:
            self.logger.error(
                "Error loading file %s: %s",
                path,
                exc,
            )
            if isinstance(exc, FileNotFoundError):
                return SFTP_NO_SUCH_FILE
            if isinstance(exc, PermissionError):
                return SFTP_PERMISSION_DENIED
            return SFTP_FAILURE

        try:
            fobj = ZTPSFTPHandle(flags)
            fobj.set_logger(self.logger)  # Set the logger after creation
            fobj.filename = path.split("/")[-1]
            fobj.readfile = file
            self.logger.debug("Created SFTP handle for file: %s", fobj.filename)
            return fobj
        except Exception as exc:
            self.logger.error("Error creating SFTP handle: %s", exc)
            return SFTP_FAILURE


def handle_connection(
    conn: socket.socket, addr: tuple[str, int], host_key: paramiko.RSAKey
) -> None:
    """Handle an individual client connection to the SFTP server."""
    logger = get_logger_for_addr(addr)
    logger.info("New connection from %s", addr)
    transport: Transport | None = None
    try:
        transport = paramiko.Transport(conn)
        transport.add_server_key(host_key)

        # Load system moduli file for group exchange KEX
        moduli_path = "/etc/ssh/moduli"
        if os.path.exists(moduli_path):
            transport.load_server_moduli(filename=moduli_path)

        # Set up the SFTP subsystem handler
        transport.set_subsystem_handler(
            "sftp", paramiko.SFTPServer, ZTPSFTPServer, client_addr=addr[0]
        )

        # Create server and start it
        server = ZTPServer()
        transport.start_server(server=server)

        # Wait for authentication and channel establishment
        channel: Channel | None = transport.accept(20)
        if channel is None:
            logger.error("No channel established")
            return

        # Keep the connection alive but with a timeout
        timeout: int = 3600
        start_time: float = time.time()

        while transport.is_active():
            # Check if we've been idle too long
            if time.time() - start_time > timeout:
                logger.info("Connection timeout after %d seconds", timeout)
                break
            time.sleep(1)
    except OSError as e:
        # Connection reset/closed by peer is normal for healthchecks from localhost
        if is_localhost(addr) and e.errno in (errno.ECONNRESET, errno.EPIPE, errno.ENOTCONN):
            logger.debug("Healthcheck connection closed: %s", e)
        else:
            logger.warning("Socket error from %s: %s", addr, e)
    except Exception as e:
        logger.exception("Error handling connection: %s", e)
    finally:
        try:
            if transport:
                transport.close()
        except Exception:  # nosec: B110
            pass
        conn.close()
        logger.info("Connection from %s closed", addr)


def start_server(host: str = "0.0.0.0", port: int = 8222, level: str = "INFO") -> None:  # nosec: B104
    """Start the SFTP server and listen for incoming connections."""
    # Set up signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    os.environ.setdefault("LOG_LEVEL", level)
    configure_logging(service="ztp-sftp")

    # Set paramiko's log level to WARN to reduce noise
    logging.getLogger("paramiko").setLevel(logging.WARNING)

    # Generate host key once at startup (RSA key generation is CPU-intensive)
    logger.info("Generating RSA host key...")
    host_key = paramiko.RSAKey.generate(2048)
    logger.info("RSA host key generated")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, True)
    server_socket.bind((host, port))
    server_socket.listen(10)

    logger.info("SFTP server listening on %s:%d", host, port)

    try:
        while not shutdown_event.is_set():
            # Set a timeout for accept to allow checking shutdown_event
            server_socket.settimeout(1)
            try:
                conn, addr = server_socket.accept()
                # Handle each client in a separate thread
                t = threading.Thread(target=handle_connection, args=(conn, addr, host_key))
                t.daemon = True
                t.start()
            except TimeoutError:
                # Timeout occurred, check if we should shutdown
                continue
            except Exception as e:
                if not shutdown_event.is_set():
                    logger.error("Error accepting connection: %s", e)
                    continue
                break

        logger.info("Server shutting down gracefully")

        # Wait for all active connections to complete
        active_threads = threading.enumerate()
        for thread in active_threads:
            if thread != threading.current_thread() and thread.is_alive():
                logger.info("Waiting for thread %s to complete", thread.name)
                thread.join(timeout=30)  # Give threads 30 seconds to complete

    except Exception as e:
        logger.error("Server error: %s", e)
    finally:
        server_socket.close()
        logger.info("Server shutdown complete")


def main() -> None:
    """Main entry point for the SFTP server."""
    parser = argparse.ArgumentParser(description="Start the SFTP server")
    parser.add_argument(
        "--host",
        default="0.0.0.0",  # nosec: B104
        help="Host to bind to (default: 0.0.0.0)",
    )
    parser.add_argument("--port", type=int, default=8222, help="Port to listen on (default: 8222)")
    parser.add_argument(
        "--level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: INFO)",
    )

    args = parser.parse_args()
    start_server(host=args.host, port=args.port, level=args.level)


if __name__ == "__main__":
    main()
