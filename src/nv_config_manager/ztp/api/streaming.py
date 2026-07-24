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
"""Streaming response utilities for large file downloads."""

import asyncio
import inspect
import re
from collections.abc import AsyncIterator, Callable
from time import monotonic
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse

from nv_config_manager.common.log import LogCategory, escape_log_newlines, get_logger
from nv_config_manager.ztp.download_control import AsyncDownloadLimiter, get_positive_int_env
from nv_config_manager.ztp.storage import (
    ObjectStorageClient,
    ObjectStorageDownload,
    ObjectStorageException,
    ObjectStorageRangeNotSatisfiableException,
    record_storage_download,
)

logger = get_logger(__name__, category=LogCategory.ZTP)

HTTP_STREAM_CHUNK_BYTES = get_positive_int_env("ZTP_HTTP_STREAM_CHUNK_BYTES", 64 * 1024 * 1024)
HTTP_DOWNLOAD_LIMITER = AsyncDownloadLimiter(
    get_positive_int_env("ZTP_HTTP_MAX_CONCURRENT_DOWNLOADS", 2),
    protocol="http",
)


async def create_object_storage_streaming_response(
    storage_client: ObjectStorageClient,
    get_method: Callable[..., Any],
    *args: Any,
    request: Request,
    download_limiter: AsyncDownloadLimiter | None = None,
    **kwargs: Any,
) -> StreamingResponse:
    """Create a streaming response that properly manages the storage client lifecycle.

    The key issue this solves: The storage client session must remain open while
    the response is streaming. This function creates an async generator that
    keeps the session alive for the entire duration of the stream.

    Args:
        storage_client: The ObjectStorageClient instance to use (S3Client or FileStoreClient)
        get_method: The async method to call (e.g., storage_client.get_firmware_object)
        *args: Positional arguments for the get_method
        request: The HTTP request, used to propagate a single Range header to storage
        **kwargs: Keyword arguments for the get_method

    Returns:
        StreamingResponse configured for optimal large file streaming
    """
    chunk_size = HTTP_STREAM_CHUNK_BYTES
    limiter = download_limiter or HTTP_DOWNLOAD_LIMITER

    range_header = request.headers.get("range")

    admission_wait_seconds = await limiter.acquire()

    # Open storage connection but don't close it until streaming is done.
    try:
        await storage_client.connect()

        download: ObjectStorageDownload = await get_method(
            *args,
            range_header=range_header,
            **kwargs,
        )
    except asyncio.CancelledError:
        # CancelledError is a BaseException, so it must be handled separately or
        # the admission permit remains held forever. Shield backend cleanup long
        # enough to give aiohttp/aiobotocore a chance to close its session.
        try:
            await asyncio.shield(storage_client.close())
        except Exception:
            logger.exception("Storage client cleanup failed after request cancellation")
        finally:
            limiter.release()
        raise
    except ObjectStorageRangeNotSatisfiableException as exc:
        try:
            await storage_client.close()
        finally:
            limiter.release()
        raise HTTPException(
            status_code=416,
            detail="Requested range is not satisfiable.",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Range": f"bytes */{exc.total_length}",
            },
        ) from exc
    except Exception:
        # Close client and let the exception bubble up to the endpoint
        # The endpoint will handle specific exceptions (like ObjectStorageNotFoundException)
        try:
            await storage_client.close()
        finally:
            limiter.release()
        raise

    transfer_id = uuid4().hex

    def log_fields(**extra: Any) -> dict[str, Any]:
        """Return safe structured fields shared by each transfer log entry."""
        return {
            "transfer_id": transfer_id,
            "storage_backend": escape_log_newlines(download.backend),
            "storage_key": escape_log_newlines(download.object_key),
            "storage_endpoint": (
                escape_log_newlines(download.endpoint) if download.endpoint else None
            ),
            "s3_request_id": (
                escape_log_newlines(download.request_id) if download.request_id else None
            ),
            "storage_filename": escape_log_newlines(download.filename),
            "content_length": download.content_length,
            "total_length": download.total_length,
            "range_start": download.byte_range.start if download.byte_range else None,
            "range_end": download.byte_range.end if download.byte_range else None,
            "range_header": escape_log_newlines(range_header) if range_header else None,
            **extra,
        }

    logger.info(
        "Storage stream opened",
        extra=log_fields(
            protocol="http",
            admission_wait_seconds=admission_wait_seconds,
            active_downloads=limiter.active,
        ),
    )

    # Create a proper async generator that reads from the file handle
    async def stream_from_storage() -> AsyncIterator[bytes]:
        bytes_streamed = 0
        started_at = monotonic()
        try:
            logger.info(
                "Storage stream started",
                extra=log_fields(protocol="http", chunk_size=chunk_size),
            )

            # Read and yield chunks - works for both S3 StreamingBody and regular file handles
            if hasattr(download.file_handle, "iter_chunks"):
                # S3 StreamingBody - use async iteration
                async for chunk in download.file_handle.iter_chunks(chunk_size):
                    if not chunk:
                        continue
                    if bytes_streamed + len(chunk) > download.content_length:
                        raise ObjectStorageException(
                            "Storage response exceeded its declared content length "
                            f"({download.content_length} bytes)"
                        )
                    bytes_streamed += len(chunk)
                    yield chunk
            else:
                # Regular file handle (from FileStoreClient) - use async read to avoid blocking
                while bytes_streamed < download.content_length:
                    # Use asyncio.to_thread to prevent blocking the event loop
                    chunk = await asyncio.to_thread(
                        download.file_handle.read,
                        min(chunk_size, download.content_length - bytes_streamed),
                    )
                    if not chunk:
                        break
                    bytes_streamed += len(chunk)
                    yield chunk

            if bytes_streamed != download.content_length:
                raise ObjectStorageException(
                    "Storage response ended before its declared content length: "
                    f"received {bytes_streamed} of {download.content_length} bytes"
                )

            duration_seconds = monotonic() - started_at
            record_storage_download(
                backend=download.backend,
                protocol="http",
                outcome="completed",
                bytes_received=bytes_streamed,
                duration_seconds=duration_seconds,
            )
            logger.info(
                "Storage stream completed",
                extra=log_fields(
                    protocol="http",
                    outcome="completed",
                    bytes_streamed=bytes_streamed,
                    duration_seconds=duration_seconds,
                    bytes_per_second=(bytes_streamed / duration_seconds if duration_seconds else 0),
                ),
            )
        except asyncio.CancelledError:
            duration_seconds = monotonic() - started_at
            record_storage_download(
                backend=download.backend,
                protocol="http",
                outcome="cancelled",
                bytes_received=bytes_streamed,
                duration_seconds=duration_seconds,
            )
            logger.warning(
                "Storage stream cancelled",
                extra=log_fields(
                    protocol="http",
                    outcome="cancelled",
                    bytes_streamed=bytes_streamed,
                    duration_seconds=duration_seconds,
                ),
            )
            raise
        except Exception as exc:
            duration_seconds = monotonic() - started_at
            record_storage_download(
                backend=download.backend,
                protocol="http",
                outcome="failed",
                bytes_received=bytes_streamed,
                duration_seconds=duration_seconds,
            )
            logger.exception(
                "Storage stream failed",
                extra=log_fields(
                    protocol="http",
                    outcome="failed",
                    bytes_streamed=bytes_streamed,
                    duration_seconds=duration_seconds,
                    error_type=type(exc).__name__,
                    error=escape_log_newlines(exc),
                ),
            )
            raise
        finally:
            logger.debug("Stream generator cleanup: closing file handle and storage client")
            try:
                # Close the file handle.
                if callable(getattr(download.file_handle, "close", None)):
                    close_result = download.file_handle.close()
                    if inspect.isawaitable(close_result):
                        await close_result
            finally:
                try:
                    # Close the storage client.
                    if callable(getattr(storage_client, "close", None)):
                        await storage_client.close()
                    logger.debug("Storage client closed")
                finally:
                    limiter.release()

    ascii_filename = re.sub(r'[\x00-\x1f\x7f"\\]', "", download.filename)
    encoded_filename = quote(download.filename, safe="")
    headers = {
        "Content-Disposition": (
            f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}"
        ),
        "Cache-Control": "no-cache",
        "Accept-Ranges": "bytes",
        "Content-Length": str(download.content_length),
    }
    if download.byte_range is not None:
        headers["Content-Range"] = (
            f"bytes {download.byte_range.start}-{download.byte_range.end}/{download.total_length}"
        )
    return StreamingResponse(
        content=stream_from_storage(),
        media_type="application/octet-stream",
        headers=headers,
        status_code=206 if download.byte_range is not None else 200,
    )
