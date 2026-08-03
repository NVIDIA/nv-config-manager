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
"""Tests for object-storage HTTP streaming responses."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.requests import Request

from nv_config_manager.ztp.api.streaming import create_object_storage_streaming_response
from nv_config_manager.ztp.download_control import AsyncDownloadLimiter
from nv_config_manager.ztp.storage import (
    ObjectStorageDownload,
    ObjectStorageException,
)


@pytest.mark.asyncio
async def test_streaming_response_rejects_a_short_storage_body() -> None:
    """An early upstream EOF is logged and raised instead of silently succeeding."""
    body = MagicMock()

    async def iter_chunks(chunk_size: int):
        assert chunk_size > 0
        yield b"short"

    body.iter_chunks = iter_chunks
    storage_client = MagicMock()
    storage_client.connect = AsyncMock(return_value=storage_client)
    storage_client.close = AsyncMock(return_value=None)
    get_object = AsyncMock(
        return_value=ObjectStorageDownload(
            filename="image.bin",
            file_handle=body,
            content_length=10,
            total_length=10,
            backend="s3",
            object_key="platform/version/image.bin",
        )
    )
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "headers": [],
            "path": "/v1/files/platform/version/image.bin",
            "query_string": b"",
        }
    )

    response = await create_object_storage_streaming_response(
        storage_client,
        get_object,
        request=request,
    )

    assert response.headers["content-length"] == "10"
    with pytest.raises(ObjectStorageException, match="ended before its declared content length"):
        async for _ in response.body_iterator:
            pass

    storage_client.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_streaming_response_holds_admission_until_the_stream_finishes() -> None:
    """A queued download cannot open until the prior response has closed."""
    limiter = AsyncDownloadLimiter(1, protocol="test-http")

    def make_response_dependencies() -> tuple[MagicMock, AsyncMock, Request]:
        body = MagicMock()

        async def iter_chunks(chunk_size: int):
            assert chunk_size > 0
            yield b"data"

        body.iter_chunks = iter_chunks
        storage_client = MagicMock()
        storage_client.connect = AsyncMock(return_value=storage_client)
        storage_client.close = AsyncMock(return_value=None)
        get_object = AsyncMock(
            return_value=ObjectStorageDownload(
                filename="image.bin",
                file_handle=body,
                content_length=4,
                total_length=4,
                backend="s3",
                object_key="platform/version/image.bin",
            )
        )
        request = Request(
            {
                "type": "http",
                "method": "GET",
                "headers": [],
                "path": "/v1/files/platform/version/image.bin",
                "query_string": b"",
            }
        )
        return storage_client, get_object, request

    first_client, first_get_object, first_request = make_response_dependencies()
    first_response = await create_object_storage_streaming_response(
        first_client,
        first_get_object,
        request=first_request,
        download_limiter=limiter,
    )
    assert limiter.active == 1

    second_client, second_get_object, second_request = make_response_dependencies()
    second_response_task = asyncio.create_task(
        create_object_storage_streaming_response(
            second_client,
            second_get_object,
            request=second_request,
            download_limiter=limiter,
        )
    )
    await asyncio.sleep(0)
    assert not second_response_task.done()

    assert [chunk async for chunk in first_response.body_iterator] == [b"data"]
    second_response = await second_response_task
    assert limiter.active == 1

    assert [chunk async for chunk in second_response.body_iterator] == [b"data"]
    assert limiter.active == 0


@pytest.mark.asyncio
async def test_streaming_response_releases_admission_when_setup_is_cancelled() -> None:
    """Cancellation during backend setup closes storage and returns the permit."""
    limiter = AsyncDownloadLimiter(1, protocol="test-http-cancel")
    storage_client = MagicMock()
    storage_client.connect = AsyncMock(side_effect=asyncio.CancelledError())
    storage_client.close = AsyncMock(return_value=None)
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "headers": [],
            "path": "/v1/files/platform/version/image.bin",
            "query_string": b"",
        }
    )

    with pytest.raises(asyncio.CancelledError):
        await create_object_storage_streaming_response(
            storage_client,
            AsyncMock(),
            request=request,
            download_limiter=limiter,
        )

    storage_client.close.assert_awaited_once()
    assert limiter.active == 0

    await limiter.acquire()
    assert limiter.active == 1
    limiter.release()
