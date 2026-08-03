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
"""Object storage client abstract base class."""

import re
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from types import TracebackType
from typing import Any, BinaryIO, Self

from prometheus_client import Counter, Histogram

_RANGE_HEADER_RE = re.compile(r"^bytes=(?P<start>\d*)-(?P<end>\d*)$")

STORAGE_DOWNLOADS = Counter(
    "storage_downloads",
    "Storage downloads by backend, protocol, and outcome.",
    labelnames=("backend", "protocol", "outcome"),
    namespace="nv_config_manager",
    subsystem="ztp",
)
STORAGE_DOWNLOAD_BYTES = Counter(
    "storage_download_bytes",
    "Bytes received from object storage by backend and protocol.",
    labelnames=("backend", "protocol"),
    namespace="nv_config_manager",
    subsystem="ztp",
)
STORAGE_DOWNLOAD_DURATION_SECONDS = Histogram(
    "storage_download_duration_seconds",
    "Object storage download duration by backend, protocol, and outcome.",
    labelnames=("backend", "protocol", "outcome"),
    namespace="nv_config_manager",
    subsystem="ztp",
)


class ObjectStorageException(Exception):
    """Generic Object Storage Exception."""


class ObjectStorageExistsException(ObjectStorageException):
    """File already exists exception."""


class ObjectStorageNotFoundException(ObjectStorageException):
    """File not found in object storage."""


class ObjectStorageNotAuthorizedException(ObjectStorageException):
    """Not authorized to modify this file."""


class ObjectStorageChangedException(ObjectStorageException):
    """The object changed after a multi-request download was opened."""


class ObjectStorageRangeNotSatisfiableException(ObjectStorageException):
    """The requested byte range cannot be served for an object."""

    def __init__(self, total_length: int) -> None:
        super().__init__(
            f"Requested range is not satisfiable for an object of {total_length} bytes"
        )
        self.total_length = total_length


@dataclass(frozen=True)
class ObjectStorageByteRange:
    """An inclusive byte range within an object."""

    start: int
    end: int

    @property
    def length(self) -> int:
        """Return the number of bytes in the range."""
        return self.end - self.start + 1


@dataclass(frozen=True)
class ObjectStorageDownload:
    """An opened object-storage download with its transfer metadata."""

    filename: str
    file_handle: Any
    content_length: int
    total_length: int
    backend: str
    object_key: str
    byte_range: ObjectStorageByteRange | None = None
    request_id: str | None = None
    endpoint: str | None = None
    etag: str | None = None

    def __iter__(self) -> Iterator[Any]:
        """Support existing callers that unpack a download into filename and handle."""
        yield self.filename
        yield self.file_handle


def parse_http_range(range_header: str | None, total_length: int) -> ObjectStorageByteRange | None:
    """Parse one HTTP ``Range`` header against an object's known length.

    Only a single ``bytes`` range is supported.  A valid range produces an
    inclusive start/end pair; absent headers return ``None``.  Invalid,
    multi-range, and unsatisfiable headers raise a single exception that API
    callers can map to HTTP 416.
    """
    if range_header is None:
        return None

    match = _RANGE_HEADER_RE.fullmatch(range_header)
    if match is None or "," in range_header or total_length <= 0:
        raise ObjectStorageRangeNotSatisfiableException(total_length)

    start_text = match.group("start")
    end_text = match.group("end")
    if not start_text and not end_text:
        raise ObjectStorageRangeNotSatisfiableException(total_length)

    if start_text:
        start = int(start_text)
        if start >= total_length:
            raise ObjectStorageRangeNotSatisfiableException(total_length)
        end = int(end_text) if end_text else total_length - 1
        if end < start:
            raise ObjectStorageRangeNotSatisfiableException(total_length)
        return ObjectStorageByteRange(start=start, end=min(end, total_length - 1))

    suffix_length = int(end_text)
    if suffix_length <= 0:
        raise ObjectStorageRangeNotSatisfiableException(total_length)
    return ObjectStorageByteRange(
        start=max(total_length - suffix_length, 0),
        end=total_length - 1,
    )


def record_storage_download(
    *,
    backend: str,
    protocol: str,
    outcome: str,
    bytes_received: int,
    duration_seconds: float,
) -> None:
    """Record bounded, backend-level telemetry for an object download."""
    STORAGE_DOWNLOADS.labels(backend=backend, protocol=protocol, outcome=outcome).inc()
    STORAGE_DOWNLOAD_BYTES.labels(backend=backend, protocol=protocol).inc(bytes_received)
    STORAGE_DOWNLOAD_DURATION_SECONDS.labels(
        backend=backend,
        protocol=protocol,
        outcome=outcome,
    ).observe(duration_seconds)


class ObjectStorageClient(ABC):
    """Abstract base class for object storage clients.

    Defines the interface that all object storage implementations (S3, File Storage, etc.)
    must implement.
    """

    @abstractmethod
    async def connect(self) -> Self:
        """Connect to the storage backend and initialize the client session."""
        pass

    @abstractmethod
    async def close(self) -> None:
        """Close the storage client session."""
        pass

    @abstractmethod
    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        pass

    @abstractmethod
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        pass

    @abstractmethod
    async def get_firmware_object(
        self, platform: str, image: str, *, range_header: str | None = None
    ) -> ObjectStorageDownload:
        """Return the filename and file handle for the given device firmware.

        Args:
            platform: Platform name (e.g., "cumulus-linux", "mlnx-os")
            image: Version string (e.g., "5.14.0")

        Returns:
            Opened object download and its transfer metadata
        """
        pass

    @abstractmethod
    async def get_firmware_checksum(self, platform: str, image: str) -> str:
        """Get the checksum for the firmware image.

        Args:
            platform: Platform name
            image: Version string

        Returns:
            SHA256 checksum string
        """
        pass

    @abstractmethod
    async def get_object(
        self,
        platform: str,
        version: str,
        filename: str,
        *,
        range_header: str | None = None,
        known_total_length: int | None = None,
        if_match: str | None = None,
    ) -> ObjectStorageDownload:
        """Get an arbitrary file stored under a given platform/version.

        Args:
            platform: Platform name
            version: Version string
            filename: Name of the file to retrieve
            range_header: Optional single HTTP byte range
            known_total_length: Previously observed object size, avoiding another metadata request
            if_match: Previously observed revision token that the object must still match

        Returns:
            Opened object download and its transfer metadata
        """
        pass

    @abstractmethod
    async def get_checksum(self, platform: str, version: str, filename: str) -> str:
        """Get the checksum for an arbitrary file.

        Args:
            platform: Platform name
            version: Version string
            filename: Name of the file

        Returns:
            SHA256 checksum string
        """
        pass

    @abstractmethod
    async def get_object_metadata(
        self, platform: str, version: str, filename: str
    ) -> dict[str, Any]:
        """Get object metadata without downloading the file content.

        Args:
            platform: Platform name
            version: Version string
            filename: Name of the file

        Returns:
            Dictionary containing metadata (size, last_modified, checksum, etc.)
        """
        pass

    @abstractmethod
    async def list_object_keys(self, platform: str, version: str) -> list[dict[str, Any]]:
        """List objects within the given platform and version.

        Args:
            platform: Platform name
            version: Version string

        Returns:
            List of dictionaries with file information
        """
        pass

    @abstractmethod
    async def list_all_objects(self) -> list[dict[str, Any]]:
        """List all objects in the storage backend.

        Returns:
            List of dictionaries with object information
        """
        pass

    @abstractmethod
    async def upload_file(
        self,
        platform: str,
        version: str,
        filename: str,
        checksum: str,
        file: BinaryIO,
        overwrite: bool = False,
        firmware_image: bool = False,
    ) -> None:
        """Upload a file to storage.

        Args:
            platform: Platform name
            version: Version string
            filename: Name of the file
            checksum: SHA256 checksum of the file
            file: File-like object to upload
            overwrite: Whether to overwrite existing files
            firmware_image: If True, tag as the OS/firmware image for this
                platform/version.  Only one firmware image is allowed per
                directory; the upload is rejected if a different file already
                holds that role.
        """
        pass
