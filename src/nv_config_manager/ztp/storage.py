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

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Any, BinaryIO, Self


class ObjectStorageException(Exception):
    """Generic Object Storage Exception."""


class ObjectStorageExistsException(ObjectStorageException):
    """File already exists exception."""


class ObjectStorageNotFoundException(ObjectStorageException):
    """File not found in object storage."""


class ObjectStorageNotAuthorizedException(ObjectStorageException):
    """Not authorized to modify this file."""


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
    async def get_firmware_object(self, platform: str, image: str) -> tuple[str, Any]:
        """Return the filename and file handle for the given device firmware.

        Args:
            platform: Platform name (e.g., "cumulus-linux", "mlnx-os")
            image: Version string (e.g., "5.14.0")

        Returns:
            Tuple of (filename, file_handle)
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
    async def get_object(self, platform: str, version: str, filename: str) -> tuple[str, Any]:
        """Get an arbitrary file stored under a given platform/version.

        Args:
            platform: Platform name
            version: Version string
            filename: Name of the file to retrieve

        Returns:
            Tuple of (filename, file_handle)
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
