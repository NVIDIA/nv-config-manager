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
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from botocore.exceptions import ClientError
from botocore.response import StreamingBody

from nv_config_manager.ztp.s3 import (
    S3Client,
    S3Exception,
    S3ExistsException,
    S3NotFoundException,
)
from nv_config_manager.ztp.storage import ObjectStorageChangedException

MOCK_CONTENT = b"testcontent"


class MockBoto3S3Client(MagicMock):
    def get_object_tagging(self, **kwargs):
        if kwargs["Key"] in [
            "cumulus_linux/5.7.0/image.bin",
            "cumulus_linux/5.7.0/image2.bin",
        ]:
            return {"TagSet": [{"Key": "firmware-image", "Value": ""}]}
        return {"TagSet": []}


class RecordingSession:
    def __init__(self):
        self.calls = []

    def client(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self

    async def __aenter__(self):
        return MockBoto3S3Client()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return None


def test_s3_client_uses_constructor_overrides(monkeypatch):
    monkeypatch.setenv("CUSTOM_S3_BUCKET", "env-bucket")
    monkeypatch.setenv("CUSTOM_S3_ENDPOINT", "https://env-s3.example.test")
    monkeypatch.setenv("CUSTOM_S3_ACCESS_KEY", "env-access-key")
    monkeypatch.setenv("CUSTOM_S3_SECRET_KEY", "env-secret-key")

    client = S3Client(
        bucket="ini-bucket",
        custom_endpoint="https://s3.example.test",
        custom_access_key="ini-access-key",
        custom_secret_key="ini-secret-key",
    )

    assert client.bucket == "ini-bucket"
    assert client.custom_endpoint == "https://s3.example.test"
    assert client.custom_access_key == "ini-access-key"
    assert client.custom_secret_key == "ini-secret-key"


@pytest.mark.parametrize(
    ("kwarg", "value"),
    [
        ("bucket", ""),
        ("bucket", "   "),
        ("custom_endpoint", ""),
        ("custom_access_key", ""),
        ("custom_secret_key", ""),
    ],
)
def test_s3_client_rejects_empty_constructor_overrides(kwarg: str, value: str):
    with pytest.raises(ValueError, match=f"{kwarg} cannot be empty"):
        S3Client(**{kwarg: value})


@pytest.mark.asyncio
async def test_s3_client_passes_credentials_without_custom_endpoint():
    client = S3Client(custom_access_key="access", custom_secret_key="secret")
    session = RecordingSession()
    client.session = session

    await client.connect()

    args, kwargs = session.calls[0]
    assert args == ("s3",)
    assert kwargs["aws_access_key_id"] == "access"
    assert kwargs["aws_secret_access_key"] == "secret"
    assert "endpoint_url" not in kwargs


@pytest.mark.asyncio
async def test_s3_client_uses_default_credential_chain_for_irsa(monkeypatch):
    """Do not pass static credentials when EKS provides a web identity token."""
    for name in ("CUSTOM_S3_ACCESS_KEY", "CUSTOM_S3_SECRET_KEY"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AWS_ROLE_ARN", "arn:aws:iam::123456789012:role/nv-config-manager-s3")
    monkeypatch.setenv("AWS_WEB_IDENTITY_TOKEN_FILE", "/var/run/secrets/eks.amazonaws.com/token")

    client = S3Client(region="us-west-2")
    session = RecordingSession()
    client.session = session

    await client.connect()

    args, kwargs = session.calls[0]
    assert args == ("s3",)
    assert kwargs["region_name"] == "us-west-2"
    assert "aws_access_key_id" not in kwargs
    assert "aws_secret_access_key" not in kwargs


@pytest.mark.asyncio
async def test_get_firmware_object():
    client = S3Client()
    client._client_instance = MockBoto3S3Client()

    client._client.get_object = AsyncMock(
        return_value={
            "Body": StreamingBody(io.BytesIO(MOCK_CONTENT), len(MOCK_CONTENT)),
            "ContentLength": len(MOCK_CONTENT),
        }
    )
    client._client.list_objects = AsyncMock(
        return_value={
            "Contents": [
                {"Key": "cumulus_linux/5.7.0/image.bin"},
                {"Key": "cumulus_linux/5.7.0/randomfile"},
            ]
        }
    )
    client._client.get_object_tagging = AsyncMock(
        side_effect=lambda **kwargs: (
            {"TagSet": [{"Key": "firmware-image", "Value": ""}]}
            if kwargs["Key"]
            in [
                "cumulus_linux/5.7.0/image.bin",
                "cumulus_linux/5.7.0/image2.bin",
            ]
            else {"TagSet": []}
        )
    )

    # Found object
    fname, obj = await client.get_firmware_object("Cumulus Linux", "5.7.0")
    assert fname == "image.bin"
    assert obj.read() == MOCK_CONTENT

    # Not Found Object
    client._client.list_objects = AsyncMock(
        return_value={
            "Contents": [
                {"Key": "cumulus_linux/5.7.0/randomfile"},
            ]
        }
    )
    with pytest.raises(S3NotFoundException):
        await client.get_firmware_object("Cumulus Linux", "5.7.0")

    # Found too many objects
    client._client.list_objects = AsyncMock(
        return_value={
            "Contents": [
                {"Key": "cumulus_linux/5.7.0/image.bin"},
                {"Key": "cumulus_linux/5.7.0/image2.bin"},
                {"Key": "cumulus_linux/5.7.0/randomfile"},
            ]
        }
    )
    with pytest.raises(
        S3Exception,
        match="Found multiple files in path cumulus_linux/5.7.0/ tagged as firmware.",
    ):
        await client.get_firmware_object("Cumulus Linux", "5.7.0")


@pytest.mark.asyncio
async def test_get_firmware_checksum():
    client = S3Client()
    client._client_instance = MockBoto3S3Client()

    client._client.head_object = AsyncMock(
        return_value={"Metadata": {"sha256-checksum": "testchecksum"}}
    )
    client._client.list_objects = AsyncMock(
        return_value={
            "Contents": [
                {"Key": "cumulus_linux/5.7.0/image.bin"},
                {"Key": "cumulus_linux/5.7.0/randomfile"},
            ]
        }
    )
    client._client.get_object_tagging = AsyncMock(
        side_effect=lambda **kwargs: (
            {"TagSet": [{"Key": "firmware-image", "Value": ""}]}
            if kwargs["Key"]
            in [
                "cumulus_linux/5.7.0/image.bin",
                "cumulus_linux/5.7.0/image2.bin",
            ]
            else {"TagSet": []}
        )
    )

    # Found object
    checksum = await client.get_firmware_checksum("Cumulus Linux", "5.7.0")
    assert checksum == "testchecksum"

    # Not Found Object
    client._client.list_objects = AsyncMock(
        return_value={
            "Contents": [
                {"Key": "cumulus_linux/5.7.0/randomfile"},
            ]
        }
    )
    with pytest.raises(S3NotFoundException):
        await client.get_firmware_checksum("Cumulus Linux", "5.7.0")

    # Found too many objects
    client._client.list_objects = AsyncMock(
        return_value={
            "Contents": [
                {"Key": "cumulus_linux/5.7.0/image.bin"},
                {"Key": "cumulus_linux/5.7.0/image2.bin"},
                {"Key": "cumulus_linux/5.7.0/randomfile"},
            ]
        }
    )
    with pytest.raises(
        S3Exception,
        match="Found multiple files in path cumulus_linux/5.7.0/ tagged as firmware.",
    ):
        await client.get_firmware_checksum("Cumulus Linux", "5.7.0")


@pytest.mark.asyncio
async def test_get_object():
    client = S3Client()
    client._client_instance = MockBoto3S3Client()

    client._client.get_object = AsyncMock(
        return_value={
            "Body": StreamingBody(io.BytesIO(MOCK_CONTENT), len(MOCK_CONTENT)),
            "ContentLength": len(MOCK_CONTENT),
        }
    )

    fname, obj = await client.get_object("Cumulus Linux", "5.7.0", "image.bin")
    assert fname == "image.bin"
    assert obj.read() == MOCK_CONTENT

    client._client.get_object = AsyncMock(
        side_effect=ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
    )
    with pytest.raises(
        S3NotFoundException, match="Did not find Cumulus Linux/5.7.0/image.bin in S3."
    ):
        await client.get_object("Cumulus Linux", "5.7.0", "image.bin")


@pytest.mark.asyncio
async def test_get_object_range():
    """A requested HTTP range is validated and passed through to S3."""
    client = S3Client()
    client._client_instance = MockBoto3S3Client()
    client._client.head_object = AsyncMock(return_value={"ContentLength": len(MOCK_CONTENT)})
    client._client.get_object = AsyncMock(
        return_value={
            "Body": StreamingBody(io.BytesIO(MOCK_CONTENT[2:6]), len(MOCK_CONTENT[2:6])),
            "ContentLength": len(MOCK_CONTENT[2:6]),
        }
    )

    download = await client.get_object(
        "Cumulus Linux",
        "5.7.0",
        "image.bin",
        range_header="bytes=2-5",
    )

    assert download.content_length == 4
    assert download.total_length == len(MOCK_CONTENT)
    assert download.byte_range is not None
    assert download.byte_range.start == 2
    assert download.byte_range.end == 5
    client._client.get_object.assert_awaited_once_with(
        Bucket="ngc-network-firmware-images",
        Key="Cumulus Linux/5.7.0/image.bin",
        Range="bytes=2-5",
    )


@pytest.mark.asyncio
async def test_get_object_range_uses_known_revision_without_another_head():
    """SFTP range reads reuse open metadata and pin every GET to its ETag."""
    client = S3Client()
    client._client_instance = MockBoto3S3Client()
    client._client.head_object = AsyncMock()
    client._client.get_object = AsyncMock(
        return_value={
            "Body": StreamingBody(io.BytesIO(MOCK_CONTENT[2:6]), 4),
            "ContentLength": 4,
            "ETag": '"revision-1"',
        }
    )

    download = await client.get_object(
        "Cumulus Linux",
        "5.7.0",
        "image.bin",
        range_header="bytes=2-5",
        known_total_length=len(MOCK_CONTENT),
        if_match='"revision-1"',
    )

    client._client.head_object.assert_not_awaited()
    client._client.get_object.assert_awaited_once_with(
        Bucket="ngc-network-firmware-images",
        Key="Cumulus Linux/5.7.0/image.bin",
        Range="bytes=2-5",
        IfMatch='"revision-1"',
    )
    assert download.etag == '"revision-1"'


@pytest.mark.asyncio
async def test_get_object_range_rejects_changed_revision():
    """An S3 precondition failure cannot splice two object revisions together."""
    client = S3Client()
    client._client_instance = MockBoto3S3Client()
    client._client.get_object = AsyncMock(
        side_effect=ClientError(
            {"Error": {"Code": "PreconditionFailed"}},
            "GetObject",
        )
    )

    with pytest.raises(ObjectStorageChangedException, match="changed while"):
        await client.get_object(
            "Cumulus Linux",
            "5.7.0",
            "image.bin",
            range_header="bytes=2-5",
            known_total_length=len(MOCK_CONTENT),
            if_match='"revision-1"',
        )


@pytest.mark.asyncio
async def test_get_checksum():
    client = S3Client()
    client._client_instance = MockBoto3S3Client()

    client._client.head_object = AsyncMock(
        return_value={"Metadata": {"sha256-checksum": "testchecksum"}}
    )

    checksum = await client.get_checksum("Cumulus Linux", "5.7.0", "image.bin")
    assert checksum == "testchecksum"

    client._client.head_object = AsyncMock(
        side_effect=ClientError({"Error": {"Code": "404"}}, "GetObject")
    )
    with pytest.raises(
        S3NotFoundException, match="Did not find Cumulus Linux/5.7.0/image.bin in S3."
    ):
        await client.get_checksum("Cumulus Linux", "5.7.0", "image.bin")


@pytest.mark.asyncio
async def test_list_objects():
    client = S3Client()
    client._client_instance = MockBoto3S3Client()

    client._client.list_objects = AsyncMock(
        return_value={
            "Contents": [
                {
                    "Key": "cumulus_linux/5.7.0/image.bin",
                    "LastModified": datetime(2015, 1, 1),
                    "Size": 12345,
                },
                {
                    "Key": "cumulus_linux/5.7.0/image2.bin",
                    "LastModified": datetime(2015, 1, 1),
                    "Size": 12345,
                },
                {
                    "Key": "cumulus_linux/5.7.0/randomfile",
                    "LastModified": datetime(2015, 1, 1),
                    "Size": 12345,
                },
            ]
        }
    )

    objects = await client.list_object_keys("cumulus_linux", "5.7.0")
    assert objects == [
        {"file": "image.bin", "last_modified": datetime(2015, 1, 1), "size": 12345},
        {"file": "image2.bin", "last_modified": datetime(2015, 1, 1), "size": 12345},
        {"file": "randomfile", "last_modified": datetime(2015, 1, 1), "size": 12345},
    ]


@pytest.mark.asyncio
async def test_file_upload():
    client = S3Client()
    client._client_instance = MockBoto3S3Client()

    # No existing file
    client._client.head_object = AsyncMock(
        side_effect=ClientError({"Error": {"Code": "404"}}, "HeadObject")
    )
    client._client.upload_fileobj = AsyncMock()
    file = io.BytesIO(b"test")

    await client.upload_file("cumulus_linux", "5.7.0", "test", "testchecksum", file, False)
    # Verify upload_fileobj was called (we check the key arguments)
    assert client._client.upload_fileobj.called
    call_kwargs = client._client.upload_fileobj.call_args.kwargs
    assert call_kwargs["Bucket"] == "ngc-network-firmware-images"
    assert call_kwargs["Key"] == "cumulus_linux/5.7.0/test"
    assert call_kwargs["ExtraArgs"]["Metadata"]["sha256-checksum"] == "testchecksum"

    # Existing file, overwrite False
    client._client.head_object = AsyncMock(return_value={})

    with pytest.raises(
        S3ExistsException,
        match="File with path cumulus_linux/5.7.0/test already exists.",
    ):
        await client.upload_file("cumulus_linux", "5.7.0", "test", "testchecksum", file, False)

    # Existing file, overwrite True
    client._client.upload_fileobj.reset_mock()

    await client.upload_file("cumulus_linux", "5.7.0", "test", "testchecksum", file, True)
    # Verify upload_fileobj was called again
    assert client._client.upload_fileobj.called
    call_kwargs = client._client.upload_fileobj.call_args.kwargs
    assert call_kwargs["Bucket"] == "ngc-network-firmware-images"
    assert call_kwargs["Key"] == "cumulus_linux/5.7.0/test"
    assert call_kwargs["ExtraArgs"]["Metadata"]["sha256-checksum"] == "testchecksum"

    # Existing firmware-image file, overwrite True — should now succeed
    client._client.upload_fileobj.reset_mock()

    await client.upload_file("cumulus_linux", "5.7.0", "test", "testchecksum", file, True)
    assert client._client.upload_fileobj.called
