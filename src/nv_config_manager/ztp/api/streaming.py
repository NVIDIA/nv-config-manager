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
import re
from collections.abc import AsyncIterator, Callable
from typing import Any
from urllib.parse import quote

from fastapi.responses import StreamingResponse

from nv_config_manager.common.log import LogCategory, escape_log_newlines, get_logger
from nv_config_manager.ztp.storage import ObjectStorageClient

logger = get_logger(__name__, category=LogCategory.ZTP)


async def create_object_storage_streaming_response(
    storage_client: ObjectStorageClient, get_method: Callable[..., Any], *args: Any, **kwargs: Any
) -> StreamingResponse:
    """Create a streaming response that properly manages the storage client lifecycle.

    The key issue this solves: The storage client session must remain open while
    the response is streaming. This function creates an async generator that
    keeps the session alive for the entire duration of the stream.

    Args:
        storage_client: The ObjectStorageClient instance to use (S3Client or FileStoreClient)
        get_method: The async method to call (e.g., storage_client.get_firmware_object)
        *args: Positional arguments for the get_method
        **kwargs: Keyword arguments for the get_method

    Returns:
        StreamingResponse configured for optimal large file streaming
    """
    chunk_size = 256 * 1024 * 1024  # 256MB chunks

    # Open storage connection but don't close it until streaming is done
    await storage_client.connect()

    try:
        filename, file_handle = await get_method(*args, **kwargs)
        logger.info("Streaming file: %s", escape_log_newlines(filename))
    except Exception:
        # Close client and let the exception bubble up to the endpoint
        # The endpoint will handle specific exceptions (like ObjectStorageNotFoundException)
        await storage_client.close()
        raise

    # Create a proper async generator that reads from the file handle
    async def stream_from_storage() -> AsyncIterator[bytes]:
        try:
            logger.debug("Starting to stream file, chunk_size=%d", chunk_size)

            # Read and yield chunks - works for both S3 StreamingBody and regular file handles
            if hasattr(file_handle, "iter_chunks"):
                # S3 StreamingBody - use async iteration
                async for chunk in file_handle.iter_chunks(chunk_size):
                    yield chunk
            else:
                # Regular file handle (from FileStoreClient) - use async read to avoid blocking
                while True:
                    # Use asyncio.to_thread to prevent blocking the event loop
                    chunk = await asyncio.to_thread(file_handle.read, chunk_size)
                    if not chunk:
                        break
                    yield chunk

            logger.debug("All chunks yielded successfully")
        except Exception as e:
            logger.error("Error during streaming: %s", escape_log_newlines(e), exc_info=True)
            raise
        finally:
            logger.debug("Stream generator cleanup: closing file handle and storage client")
            # Close the file handle
            if callable(getattr(file_handle, "close", None)):
                # Use asyncio.to_thread for sync close to avoid blocking
                await asyncio.to_thread(file_handle.close)
            # Close the storage client
            if callable(getattr(storage_client, "close", None)):
                await storage_client.close()
            logger.debug("Storage client closed")

    ascii_filename = re.sub(r'[\x00-\x1f\x7f"\\]', "", filename)
    encoded_filename = quote(filename, safe="")
    return StreamingResponse(
        content=stream_from_storage(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"{ascii_filename}\"; filename*=UTF-8''{encoded_filename}"
            ),
            "Cache-Control": "no-cache",
        },
    )
