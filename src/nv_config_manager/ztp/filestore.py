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
"""File Storage Client for PVC-based image storage."""

import asyncio
import json
import os
from pathlib import Path
from types import TracebackType
from typing import Any, BinaryIO, Self

from nv_config_manager.ztp.storage import (
    ObjectStorageClient,
    ObjectStorageException,
    ObjectStorageExistsException,
    ObjectStorageNotAuthorizedException,
    ObjectStorageNotFoundException,
)


class FileStoreException(ObjectStorageException):
    """Generic File Storage Exception."""


class FileStoreExistsException(ObjectStorageExistsException):
    """File already exists exception."""


class FileStoreNotFoundException(ObjectStorageNotFoundException):
    """File not found in file storage."""


class FileStoreNotAuthorizedException(ObjectStorageNotAuthorizedException):
    """Not authorized to modify this file."""


_PATH_TRAVERSAL_MSG = "Path traversal detected: resolved path escapes base directory"


class FileStoreClient(ObjectStorageClient):
    """Async file storage client for PVC-based storage.

    Implements the ObjectStorageClient interface for local/PVC-mounted file storage.

    Note: All file I/O operations are executed in a thread pool using asyncio.to_thread()
    to maintain compatibility with S3Client's async interface and prevent blocking the
    event loop during concurrent requests.

    Uses a manifest.json file to map platform/version to files and checksums,
    instead of relying on file suffixes.
    """

    def __init__(self) -> None:
        """Initialize the file storage client with the base path from environment."""
        base_path_str = os.environ.get("FILE_STORE_PATH")
        if not base_path_str:
            raise FileStoreException(
                "FILE_STORE_PATH environment variable must be set to use FileStoreClient"
            )
        self.base_path = Path(base_path_str)
        if not self.base_path.exists():
            raise FileStoreException(f"File store base path does not exist: {self.base_path}")

        # Load manifest
        self.manifest_path = self.base_path / "manifest.json"
        self.manifest: dict[str, Any] | None = None

    async def connect(self) -> Self:
        """Connect to file storage (loads manifest)."""
        await self._load_manifest()
        return self

    async def close(self) -> None:
        """Close the file storage client session (no-op)."""
        pass

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        return await self.connect()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Async context manager exit."""
        await self.close()

    async def _load_manifest(self) -> None:
        """Load the manifest.json file, creating an empty one if it doesn't exist."""

        def _load() -> dict[str, Any]:
            if not self.manifest_path.exists():
                # First run on an empty PVC — bootstrap an empty manifest so
                # uploads can proceed without requiring pre-populated images.
                empty: dict[str, Any] = {"images": []}
                self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
                with open(self.manifest_path, "w") as f:
                    json.dump(empty, f, indent=2)
                return empty

            with open(self.manifest_path) as f:
                return dict(json.loads(f.read()))

        self.manifest = await asyncio.to_thread(_load)

    def _get_image_from_manifest(self, platform: str, version: str) -> dict[str, Any]:
        """Get image information from manifest for a platform/version.

        Returns:
            dict with keys: platform, version, path, filename, sha256
        """
        if not self.manifest:
            raise FileStoreException("Manifest not loaded")

        # Normalize platform name
        platform_normalized = platform.replace(" ", "_").lower()

        for image in self.manifest.get("images", []):
            img_platform = image["platform"].replace(" ", "_").lower()
            if img_platform == platform_normalized and image["version"] == version:
                return dict(image)

        raise FileStoreNotFoundException(
            f"Image not found in manifest: platform={platform}, version={version}"
        )

    def _get_file_path(self, platform: str, version: str, filename: str) -> Path:
        """Get the full file path for a given platform/version/filename.

        Raises FileStoreException if the resolved path escapes the base directory.
        """
        platform_normalized = platform.replace(" ", "_").lower()
        file_path = (self.base_path / platform_normalized / version / filename).resolve()
        if not file_path.is_relative_to(self.base_path.resolve()):
            raise FileStoreException(_PATH_TRAVERSAL_MSG)
        return file_path

    async def get_firmware_object(self, platform: str, image: str) -> tuple[str, Any]:
        """Return the filename and file handle for the given device firmware.

        Args:
            platform: Platform name (e.g., "cumulus-linux", "mlnx-os")
            image: Version string (e.g., "5.14.0")
        """
        # Get image info from manifest (non-blocking, just dict lookup)
        image_info = self._get_image_from_manifest(platform, image)

        # Build full path
        file_path = self.base_path / image_info["path"]

        def _open_file() -> BinaryIO:
            if not file_path.exists():
                raise FileStoreNotFoundException(f"Firmware image file not found: {file_path}")
            return open(file_path, mode="rb")

        file_handle = await asyncio.to_thread(_open_file)
        return str(image_info["filename"]), file_handle

    async def get_firmware_checksum(self, platform: str, image: str) -> str:
        """Get the checksum for the firmware image from manifest."""
        image_info = self._get_image_from_manifest(platform, image)
        return str(image_info["sha256"])

    async def get_object(self, platform: str, version: str, filename: str) -> tuple[str, Any]:
        """Get an arbitrary file stored under a given platform/version."""
        file_path = self._get_file_path(platform, version, filename)

        def _open_file() -> BinaryIO:
            if not file_path.exists():
                raise FileStoreNotFoundException(f"File not found: {file_path}")
            return open(file_path, mode="rb")

        file_handle = await asyncio.to_thread(_open_file)
        return filename, file_handle

    async def get_checksum(self, platform: str, version: str, filename: str) -> str:
        """Get checksum for a file from manifest."""
        # Get from manifest
        image_info = self._get_image_from_manifest(platform, version)
        if image_info["filename"] == filename:
            return str(image_info["sha256"])

        raise FileStoreNotFoundException(
            f"Checksum not found for file: {filename}. File not in manifest."
        )

    async def get_object_metadata(
        self, platform: str, version: str, filename: str
    ) -> dict[str, Any]:
        """Get object metadata without downloading the file content."""
        file_path = self._get_file_path(platform, version, filename)

        def _get_stat() -> os.stat_result:
            if not file_path.exists():
                raise FileStoreNotFoundException(f"File not found: {file_path}")
            return file_path.stat()

        stat = await asyncio.to_thread(_get_stat)

        # Get checksum from manifest (non-blocking dict lookup)
        checksum = None
        try:
            checksum = await self.get_checksum(platform, version, filename)
        except FileStoreNotFoundException:
            pass

        return {
            "size": stat.st_size,
            "last_modified": stat.st_mtime,
            "metadata": {"sha256-checksum": checksum} if checksum else {},
            "etag": None,  # File storage doesn't have ETags
        }

    async def list_object_keys(self, platform: str, version: str) -> list[dict[str, Any]]:
        """List objects within the given platform and version directory."""
        dir_path = (self.base_path / platform.replace(" ", "_").lower() / version).resolve()
        if not dir_path.is_relative_to(self.base_path.resolve()):
            raise FileStoreException(_PATH_TRAVERSAL_MSG)

        def _scan_directory() -> list[dict[str, Any]]:
            if not dir_path.exists():
                return []

            objects: list[dict[str, Any]] = []
            for entry in os.scandir(str(dir_path)):
                if entry.is_file():
                    stat = entry.stat()
                    objects.append(
                        {
                            "file": entry.name,
                            "last_modified": stat.st_mtime,
                            "size": stat.st_size,
                        }
                    )
            return objects

        return await asyncio.to_thread(_scan_directory)

    async def list_all_objects(self) -> list[dict[str, Any]]:
        """List all objects in file storage with metadata.

        Uses manifest for firmware images, scans filesystem for other files.
        """
        objects: list[dict[str, Any]] = []

        if not self.manifest:
            return objects

        # Add all images from manifest
        for image_info in self.manifest.get("images", []):
            file_path = self.base_path / image_info["path"]
            if file_path.exists():
                stat_info = file_path.stat()
                objects.append(
                    {
                        "key": image_info["path"],
                        "last_modified": stat_info.st_mtime,
                        "size": stat_info.st_size,
                        "etag": None,
                        "metadata": {"sha256-checksum": image_info["sha256"]},
                        "tags": image_info.get("tags", {}),
                    }
                )

        return objects

    async def upload_file(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        platform: str,
        version: str,
        filename: str,
        checksum: str,
        file: BinaryIO,
        overwrite: bool = False,
        firmware_image: bool = False,
    ) -> None:
        """Upload a file to file storage.

        Note: Firmware images defined in manifest cannot be overwritten.
        """
        file_path = self._get_file_path(platform, version, filename)

        # Check for firmware-image conflict: only one firmware image per platform/version
        try:
            image_info = self._get_image_from_manifest(platform, version)
            if firmware_image and image_info["filename"] != filename:
                raise FileStoreExistsException(
                    f"A different firmware image already exists for "
                    f"{platform}/{version}: '{image_info['filename']}'. "
                    f"Remove it first or upload with the same filename."
                )
        except FileStoreNotFoundException:
            # No existing firmware image for this platform/version, proceed
            pass

        def _write_file() -> None:
            if file_path.exists() and not overwrite:
                raise FileStoreExistsException(f"File already exists: {file_path}")

            # Create directory if it doesn't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)

            # Write the file
            with open(file_path, mode="wb") as f:
                while True:
                    chunk = file.read(10 * 1024 * 1024)  # 10MB chunks
                    if not chunk:
                        break
                    f.write(chunk)

        await asyncio.to_thread(_write_file)

        tags = {"firmware-image": ""} if firmware_image else None
        # Update manifest with the new upload
        await self._add_to_manifest(platform, version, filename, checksum, tags)

    async def _add_to_manifest(
        self,
        platform: str,
        version: str,
        filename: str,
        checksum: str,
        tags: dict[str, str] | None = None,
    ) -> None:
        """Add or update an entry in the manifest and persist to disk."""
        if self.manifest is None:
            self.manifest = {"images": []}

        platform_normalized = platform.replace(" ", "_").lower()
        rel_path = f"{platform_normalized}/{version}/{filename}"

        resolved = (self.base_path / rel_path).resolve()
        if not resolved.is_relative_to(self.base_path.resolve()):
            raise FileStoreException(_PATH_TRAVERSAL_MSG)

        # Check if entry already exists and update it
        for image in self.manifest.get("images", []):
            if image.get("path") == rel_path:
                image["sha256"] = checksum
                if tags is not None:
                    image["tags"] = tags
                break
        else:
            # New entry
            entry: dict[str, Any] = {
                "platform": platform,
                "version": version,
                "filename": filename,
                "path": rel_path,
                "sha256": checksum,
            }
            if tags:
                entry["tags"] = tags
            self.manifest.setdefault("images", []).append(entry)

        def _persist() -> None:
            with open(self.manifest_path, "w") as f:
                json.dump(self.manifest, f, indent=2)

        await asyncio.to_thread(_persist)
