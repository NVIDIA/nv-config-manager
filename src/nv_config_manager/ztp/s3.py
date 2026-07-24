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
"""S3 Proxy Client."""

import os
from time import monotonic
from types import TracebackType
from typing import Any, BinaryIO, Self

import aioboto3  # type: ignore[import-untyped]
from boto3.s3.transfer import TransferConfig
from botocore.config import Config
from botocore.exceptions import ClientError

from nv_config_manager.common.log import LogCategory, escape_log_newlines, get_logger
from nv_config_manager.ztp.storage import (
    ObjectStorageByteRange,
    ObjectStorageChangedException,
    ObjectStorageClient,
    ObjectStorageDownload,
    ObjectStorageException,
    ObjectStorageExistsException,
    ObjectStorageNotAuthorizedException,
    ObjectStorageNotFoundException,
    ObjectStorageRangeNotSatisfiableException,
    parse_http_range,
)

logger = get_logger(__name__, category=LogCategory.ZTP)


class S3Exception(ObjectStorageException):
    """Generic S3 Exception."""


class S3ExistsException(ObjectStorageExistsException):
    """File already exists exception."""


class S3NotFoundException(ObjectStorageNotFoundException):
    """File not found in S3."""


class S3NotAuthorizedException(ObjectStorageNotAuthorizedException):
    """Not authorized to modify this file."""


class S3Client(ObjectStorageClient):
    """Async S3 proxy client.

    Implements the ObjectStorageClient interface for S3/Ceph object storage.
    """

    def __init__(
        self,
        *,
        bucket: str | None = None,
        custom_endpoint: str | None = None,
        region: str | None = None,
        custom_access_key: str | None = None,
        custom_secret_key: str | None = None,
    ) -> None:
        """Initialize the S3 client with optimized configuration for large file transfers."""
        # Optimized configuration for large file streaming performance
        config = Config(
            # Increase connection pool size for better throughput
            max_pool_connections=50,
            # Optimize retry strategy for large files
            retries={"max_attempts": 3, "mode": "adaptive"},
            # Increase read timeout for large chunks
            read_timeout=300,  # 5 minutes for very large chunks
            # TCP keep-alive for long transfers
            tcp_keepalive=True,
        )

        self._validate_optional_override("bucket", bucket)
        self._validate_optional_override("custom_endpoint", custom_endpoint)
        self._validate_optional_override("region", region)
        self._validate_optional_override("custom_access_key", custom_access_key)
        self._validate_optional_override("custom_secret_key", custom_secret_key)

        self.bucket = (
            bucket
            if bucket is not None
            else os.environ.get("CUSTOM_S3_BUCKET") or "ngc-network-firmware-images"
        )
        self.config = config
        self.custom_endpoint = (
            custom_endpoint if custom_endpoint is not None else os.environ.get("CUSTOM_S3_ENDPOINT")
        )
        self.region = (
            region
            if region is not None
            else os.environ.get("CUSTOM_S3_REGION")
            or os.environ.get("AWS_REGION")
            or os.environ.get("AWS_DEFAULT_REGION")
        )
        self.custom_access_key = (
            custom_access_key
            if custom_access_key is not None
            else os.environ.get("CUSTOM_S3_ACCESS_KEY")
        )
        self.custom_secret_key = (
            custom_secret_key
            if custom_secret_key is not None
            else os.environ.get("CUSTOM_S3_SECRET_KEY")
        )

        # Create session for async operations
        self.session = aioboto3.Session()
        self._client_instance: Any = None

    @staticmethod
    def _validate_optional_override(name: str, value: str | None) -> None:
        if value is not None and not value.strip():
            raise ValueError(f"{name} cannot be empty when provided")

    @property
    def _client(self) -> Any:
        """Get the S3 client, raising if not connected."""
        if self._client_instance is None:
            raise RuntimeError("S3Client not connected. Use 'async with' or call connect() first.")
        return self._client_instance

    @property
    def _endpoint(self) -> str:
        """Return the configured endpoint in a form suitable for diagnostics."""
        if self.custom_endpoint:
            return self.custom_endpoint
        if self.region:
            return f"s3.{self.region}.amazonaws.com"
        return "s3.amazonaws.com"

    @staticmethod
    def _content_length(response: dict[str, Any], operation: str, key: str) -> int:
        """Extract and validate an S3 response content length."""
        content_length = response.get("ContentLength")
        if not isinstance(content_length, int) or content_length < 0:
            raise S3Exception(
                f"{operation} for {key} returned an invalid ContentLength: {content_length!r}"
            )
        return content_length

    @staticmethod
    def _request_id(response: dict[str, Any]) -> str | None:
        """Return the S3 request ID when S3 included one in its response metadata."""
        metadata = response.get("ResponseMetadata", {})
        request_id = metadata.get("RequestId") if isinstance(metadata, dict) else None
        return str(request_id) if request_id is not None else None

    def _s3_log_extra(
        self,
        *,
        operation: str,
        key: str,
        duration_seconds: float,
        request_id: str | None = None,
        range_header: str | None = None,
    ) -> dict[str, Any]:
        """Build safe, consistent fields for S3 diagnostic logs."""
        return {
            "storage_backend": "s3",
            "storage_operation": operation,
            "storage_key": escape_log_newlines(key),
            "storage_bucket": escape_log_newlines(self.bucket),
            "storage_endpoint": escape_log_newlines(self._endpoint),
            "s3_request_id": escape_log_newlines(request_id) if request_id else None,
            "range_header": escape_log_newlines(range_header) if range_header else None,
            "duration_seconds": duration_seconds,
        }

    async def connect(self) -> Self:
        """Connect to S3 and initialize the client session."""
        client_kwargs: dict[str, Any] = {}
        if self.region is not None:
            client_kwargs["region_name"] = self.region
        if self.custom_access_key is not None:
            client_kwargs["aws_access_key_id"] = self.custom_access_key
        if self.custom_secret_key is not None:
            client_kwargs["aws_secret_access_key"] = self.custom_secret_key
        if self.custom_endpoint:
            custom_config = Config(
                signature_version="s3v4",
                max_pool_connections=50,
                retries={"max_attempts": 3, "mode": "adaptive"},
                read_timeout=300,
                tcp_keepalive=True,
            )
            self._client_instance = await self.session.client(
                "s3",
                endpoint_url=self.custom_endpoint,
                config=custom_config,
                verify=False,
                **client_kwargs,
            ).__aenter__()
        else:
            self._client_instance = await self.session.client(
                "s3",
                config=self.config,
                **client_kwargs,
            ).__aenter__()
        return self

    async def close(self) -> None:
        """Close the S3 client session."""
        if self._client_instance:
            await self._client_instance.__aexit__(None, None, None)
            self._client_instance = None

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

    async def _key_exists(self, key: str) -> bool:
        """Check whether an object key exists in the bucket."""
        try:
            await self._client.head_object(Bucket=self.bucket, Key=key)
            return True
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "404":
                return False
            raise S3Exception(exc) from exc

    async def _get_firmware_key(self, platform: str, image: str) -> tuple[str, str]:
        """Get the object key and shortname from the platform and image."""
        platform = platform.replace(" ", "_").lower()
        prefix = f"{platform}/{image}/"
        rsp = await self._client.list_objects(Bucket=self.bucket, Prefix=prefix)
        keys = []
        for content in rsp.get("Contents", []):
            key = content["Key"]
            tag_content = await self._client.get_object_tagging(Bucket=self.bucket, Key=key)
            tag_names = [tag["Key"] for tag in tag_content["TagSet"]]
            if "firmware-image" in tag_names:
                keys.append((content["Key"], content["Key"].replace(prefix, "")))
        if not keys:
            raise S3NotFoundException(f"Did not find a firmware image in path {prefix}")
        if len(keys) > 1:
            raise S3Exception(f"Found multiple files in path {prefix} tagged as firmware.")
        return keys[0]

    async def _get_object_download(
        self,
        key: str,
        filename: str,
        *,
        range_header: str | None,
        known_total_length: int | None = None,
        if_match: str | None = None,
    ) -> ObjectStorageDownload:
        """Open an S3 object and capture the metadata needed to stream it safely."""
        byte_range: ObjectStorageByteRange | None = None
        total_length = known_total_length

        if range_header is not None and total_length is None:
            metadata_started_at = monotonic()
            try:
                metadata = await self._client.head_object(Bucket=self.bucket, Key=key)
                total_length = self._content_length(metadata, "HeadObject", key)
            except ClientError as exc:
                logger.exception(
                    "S3 HeadObject for range request failed",
                    extra=self._s3_log_extra(
                        operation="HeadObject",
                        key=key,
                        duration_seconds=monotonic() - metadata_started_at,
                        range_header=range_header,
                    ),
                )
                code = str(exc.response.get("Error", {}).get("Code", ""))
                if code in {"404", "NoSuchKey"}:
                    raise S3NotFoundException(f"Did not find {key} in S3.") from exc
                raise S3Exception(exc) from exc
            else:
                logger.info(
                    "S3 HeadObject for range request completed",
                    extra=self._s3_log_extra(
                        operation="HeadObject",
                        key=key,
                        duration_seconds=monotonic() - metadata_started_at,
                        request_id=self._request_id(metadata),
                        range_header=range_header,
                    ),
                )
        if range_header is not None:
            if total_length is None:
                raise S3Exception(f"Could not determine the size of {key}")
            byte_range = parse_http_range(range_header, total_length)

        get_kwargs: dict[str, str] = {"Bucket": self.bucket, "Key": key}
        if byte_range is not None:
            get_kwargs["Range"] = f"bytes={byte_range.start}-{byte_range.end}"
        if if_match is not None:
            get_kwargs["IfMatch"] = if_match

        started_at = monotonic()
        try:
            response = await self._client.get_object(**get_kwargs)
            content_length = self._content_length(response, "GetObject", key)
            if total_length is None:
                total_length = content_length
            if byte_range is not None and content_length != byte_range.length:
                raise S3Exception(
                    f"GetObject for {key} returned {content_length} bytes for "
                    f"requested range {byte_range.start}-{byte_range.end}"
                )
        except ClientError as exc:
            logger.exception(
                "S3 GetObject failed before the response body could be streamed",
                extra=self._s3_log_extra(
                    operation="GetObject",
                    key=key,
                    duration_seconds=monotonic() - started_at,
                    range_header=range_header,
                ),
            )
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in {"404", "NoSuchKey"}:
                raise S3NotFoundException(f"Did not find {key} in S3.") from exc
            if code in {"416", "InvalidRange"} and total_length is not None:
                raise ObjectStorageRangeNotSatisfiableException(total_length) from exc
            if code in {"412", "PreconditionFailed"}:
                raise ObjectStorageChangedException(
                    f"{key} changed while it was being downloaded"
                ) from exc
            raise S3Exception(exc) from exc
        except Exception:
            logger.exception(
                "S3 GetObject failed before the response body could be streamed",
                extra=self._s3_log_extra(
                    operation="GetObject",
                    key=key,
                    duration_seconds=monotonic() - started_at,
                    range_header=range_header,
                ),
            )
            raise

        request_id = self._request_id(response)
        logger.info(
            "S3 GetObject opened response body",
            extra={
                **self._s3_log_extra(
                    operation="GetObject",
                    key=key,
                    duration_seconds=monotonic() - started_at,
                    request_id=request_id,
                    range_header=range_header,
                ),
                "content_length": content_length,
                "total_length": total_length,
                "range_start": byte_range.start if byte_range else None,
                "range_end": byte_range.end if byte_range else None,
            },
        )
        return ObjectStorageDownload(
            filename=filename,
            file_handle=response["Body"],
            content_length=content_length,
            total_length=total_length,
            backend="s3",
            object_key=key,
            byte_range=byte_range,
            request_id=request_id,
            endpoint=self._endpoint,
            etag=response.get("ETag"),
        )

    async def get_firmware_object(
        self, platform: str, image: str, *, range_header: str | None = None
    ) -> ObjectStorageDownload:
        """Return the object and checksum for the given device."""
        key, fname = await self._get_firmware_key(platform, image)
        return await self._get_object_download(key, fname, range_header=range_header)

    async def get_firmware_checksum(self, platform: str, image: str) -> str:
        """Get the checksum for the image."""
        key, _ = await self._get_firmware_key(platform, image)
        rsp = await self._client.head_object(Bucket=self.bucket, Key=key)
        return str(rsp.get("Metadata", {}).get("sha256-checksum", ""))

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
        """Get an arbitrary file stored under a given platform/version."""
        key = f"{platform}/{version}/{filename}"
        return await self._get_object_download(
            key,
            filename,
            range_header=range_header,
            known_total_length=known_total_length,
            if_match=if_match,
        )

    async def get_checksum(self, platform: str, version: str, filename: str) -> str:
        """Get an arbitrary file checksum stored under a given platform/version."""
        key = f"{platform}/{version}/{filename}"
        try:
            rsp = await self._client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as exc:
            if exc.response["Error"]["Code"] == "404":
                raise S3NotFoundException(f"Did not find {key} in S3.") from exc
            raise S3Exception(exc) from exc
        return str(rsp.get("Metadata", {}).get("sha256-checksum", ""))

    async def get_object_metadata(
        self, platform: str, version: str, filename: str
    ) -> dict[str, Any]:
        """Get object metadata without downloading the file content."""
        key = f"{platform}/{version}/{filename}"
        started_at = monotonic()
        try:
            rsp = await self._client.head_object(Bucket=self.bucket, Key=key)
            result = {
                "size": rsp.get("ContentLength"),
                "last_modified": rsp.get("LastModified"),
                "metadata": rsp.get("Metadata", {}),
                "etag": rsp.get("ETag"),
            }
        except ClientError as exc:
            logger.exception(
                "S3 HeadObject failed",
                extra=self._s3_log_extra(
                    operation="HeadObject",
                    key=key,
                    duration_seconds=monotonic() - started_at,
                ),
            )
            if exc.response["Error"]["Code"] in ["404", "NoSuchKey"]:
                raise S3NotFoundException(f"Did not find {key} in S3.") from exc
            raise S3Exception(exc) from exc
        else:
            logger.info(
                "S3 HeadObject completed",
                extra=self._s3_log_extra(
                    operation="HeadObject",
                    key=key,
                    duration_seconds=monotonic() - started_at,
                    request_id=self._request_id(rsp),
                ),
            )
        return result

    async def list_object_keys(self, platform: str, version: str) -> list[dict[str, Any]]:
        """List objects within the given platform and version directory."""
        prefix = f"{platform}/{version}/"
        rsp = await self._client.list_objects(Bucket=self.bucket, Prefix=prefix)
        objects = []
        for content in rsp.get("Contents", []):
            objects.append(
                {
                    "file": content["Key"].replace(prefix, ""),
                    "last_modified": content["LastModified"],
                    "size": content["Size"],
                }
            )
        return objects

    async def list_all_objects(self) -> list[dict[str, Any]]:
        """List all objects in the bucket with metadata for sync purposes."""
        objects = []
        paginator = self._client.get_paginator("list_objects_v2")

        async for page in paginator.paginate(Bucket=self.bucket):
            for content in page.get("Contents", []):
                key = content["Key"]

                # Get metadata and tags for each object
                try:
                    head_response = await self._client.head_object(Bucket=self.bucket, Key=key)
                    tags_response = await self._client.get_object_tagging(
                        Bucket=self.bucket, Key=key
                    )

                    objects.append(
                        {
                            "key": key,
                            "last_modified": content["LastModified"],
                            "size": content["Size"],
                            "etag": content["ETag"].strip('"'),
                            "metadata": head_response.get("Metadata", {}),
                            "tags": {
                                tag["Key"]: tag["Value"] for tag in tags_response.get("TagSet", [])
                            },
                        }
                    )
                except ClientError:
                    # Skip objects we can't access
                    continue

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
        """Upload a file to S3 using optimized multipart upload for large files.

        Uses multipart upload with larger chunk sizes (10MB) for better throughput
        on large files. This allows parallel chunk uploads and is much faster than
        simple put_object for files > 10MB.
        """
        key = f"{platform}/{version}/{filename}"

        if not overwrite and await self._key_exists(key):
            raise S3ExistsException(f"File with path {key} already exists.")

        # Only one file per platform/version may carry the firmware-image tag.
        if firmware_image:
            prefix = f"{platform}/{version}/"
            rsp = await self._client.list_objects(Bucket=self.bucket, Prefix=prefix)
            for content in rsp.get("Contents", []):
                other_key = content["Key"]
                if other_key == key:
                    continue  # same file — will be overwritten
                other_tags = await self._client.get_object_tagging(
                    Bucket=self.bucket, Key=other_key
                )
                other_tag_names = [t["Key"] for t in other_tags["TagSet"]]
                if "firmware-image" in other_tag_names:
                    other_name = other_key.replace(prefix, "")
                    raise S3ExistsException(
                        f"A different firmware image already exists in "
                        f"{prefix}: '{other_name}'. Remove it first or upload "
                        f"with the same filename."
                    )

        # Use the managed uploader which automatically uses multipart for large files
        # with optimized chunk size (10MB chunks) for better throughput
        transfer_config = TransferConfig(
            multipart_threshold=10 * 1024 * 1024,  # 10MB threshold
            multipart_chunksize=10 * 1024 * 1024,  # 10MB chunks
            max_concurrency=10,  # Upload up to 10 parts concurrently
            use_threads=True,
        )

        await self._client.upload_fileobj(
            Fileobj=file,
            Bucket=self.bucket,
            Key=key,
            ExtraArgs={
                "Metadata": {"sha256-checksum": checksum},
            },
            Config=transfer_config,
        )

        # Apply firmware-image tag after successful upload
        if firmware_image:
            await self._client.put_object_tagging(
                Bucket=self.bucket,
                Key=key,
                Tagging={
                    "TagSet": [{"Key": "firmware-image", "Value": ""}],
                },
            )
