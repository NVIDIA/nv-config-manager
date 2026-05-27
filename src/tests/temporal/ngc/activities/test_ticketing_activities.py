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
"""Tests for validate_ticket, upload_attachment, and add_ticket_comment activities.

Code under test:
  src/nv_config_manager/temporal/ngc/activities/ticketing.py
    - validate_ticket()                    line 77
    - upload_attachment()                  line 108
    - add_ticket_comment()                 line 127
    - UploadAttachmentInput._coerce_bytes  line 47

get_ticketing_provider is patched so no real HTTP or config-file access occurs.
The mock provider uses AsyncMock so that async with / await calls resolve correctly.
"""

from unittest.mock import AsyncMock, patch

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from nv_config_manager.temporal.ngc.activities.ticketing import (
        AddCommentInput,
        AddCommentOutput,
        UploadAttachmentInput,
        UploadAttachmentOutput,
        ValidateTicketInput,
        ValidateTicketOutput,
        add_ticket_comment,
        upload_attachment,
        validate_ticket,
    )


# =============================================================================
# Shared test data
# =============================================================================

PLATFORM = "jira"
ISSUE_KEY = "GNI-1234"

# Jira-shaped response: top-level "self" URL + nested "fields"
JIRA_ISSUE_RESPONSE = {
    "self": "https://jira.example.com/rest/api/latest/issue/GNI-1234",
    "fields": {
        "summary": "Switch GNI-1234 link flapping",
        "status": {"name": "In Progress"},
    },
}


# =============================================================================
# Helpers
# =============================================================================


def _make_mock_provider(
    issue: dict | None = None,
    attachment_result: str = "https://jira.example.com/attachment/12345",
    comment_id: str = "99001",
) -> AsyncMock:
    """Return a mock TicketingProvider that supports async with and await."""
    provider = AsyncMock()
    provider.__aenter__.return_value = provider
    provider.__aexit__.return_value = None
    provider.validate_issue.return_value = issue if issue is not None else JIRA_ISSUE_RESPONSE
    provider.upload_attachment.return_value = attachment_result
    provider.add_comment.return_value = comment_id
    return provider


# =============================================================================
# validate_ticket
# =============================================================================


async def test_validate_ticket_calls_get_ticketing_provider():
    """get_ticketing_provider is called with the activity input's ticketing_platform."""
    mock_provider = _make_mock_provider()
    with patch(
        "nv_config_manager.temporal.ngc.activities.ticketing.get_ticketing_provider",
        return_value=mock_provider,
    ) as mock_factory:
        await validate_ticket(ValidateTicketInput(ticketing_platform=PLATFORM, issue_key=ISSUE_KEY))

    mock_factory.assert_called_once_with(PLATFORM)


async def test_validate_ticket_returns_validate_ticket_output():
    """Activity returns a ValidateTicketOutput instance."""
    mock_provider = _make_mock_provider()
    with patch(
        "nv_config_manager.temporal.ngc.activities.ticketing.get_ticketing_provider",
        return_value=mock_provider,
    ):
        result = await validate_ticket(
            ValidateTicketInput(ticketing_platform=PLATFORM, issue_key=ISSUE_KEY)
        )

    assert isinstance(result, ValidateTicketOutput)


async def test_validate_ticket_calls_validate_issue():
    """validate_issue is called with the activity input's issue_key."""
    mock_provider = _make_mock_provider()
    with patch(
        "nv_config_manager.temporal.ngc.activities.ticketing.get_ticketing_provider",
        return_value=mock_provider,
    ):
        await validate_ticket(ValidateTicketInput(ticketing_platform=PLATFORM, issue_key=ISSUE_KEY))

    mock_provider.validate_issue.assert_called_once_with(ISSUE_KEY)


async def test_validate_ticket_extracts_summary():
    """Output summary is extracted from fields.summary in a nested Jira response."""
    mock_provider = _make_mock_provider()
    with patch(
        "nv_config_manager.temporal.ngc.activities.ticketing.get_ticketing_provider",
        return_value=mock_provider,
    ):
        result = await validate_ticket(
            ValidateTicketInput(ticketing_platform=PLATFORM, issue_key=ISSUE_KEY)
        )

    assert result.summary == "Switch GNI-1234 link flapping"


async def test_validate_ticket_extracts_status():
    """Output status is extracted from fields.status.name in a nested Jira response."""
    mock_provider = _make_mock_provider()
    with patch(
        "nv_config_manager.temporal.ngc.activities.ticketing.get_ticketing_provider",
        return_value=mock_provider,
    ):
        result = await validate_ticket(
            ValidateTicketInput(ticketing_platform=PLATFORM, issue_key=ISSUE_KEY)
        )

    assert result.status == "In Progress"


async def test_validate_ticket_extracts_url():
    """Output url is extracted from the top-level 'self' key in the provider response."""
    mock_provider = _make_mock_provider()
    with patch(
        "nv_config_manager.temporal.ngc.activities.ticketing.get_ticketing_provider",
        return_value=mock_provider,
    ):
        result = await validate_ticket(
            ValidateTicketInput(ticketing_platform=PLATFORM, issue_key=ISSUE_KEY)
        )

    assert result.url == "https://jira.example.com/rest/api/latest/issue/GNI-1234"


async def test_validate_ticket_flat_provider_response():
    """A flat provider dict (no 'fields' key) is used directly for summary and status."""
    flat_issue = {
        "self": "https://jira.example.com/rest/api/latest/issue/GNI-1234",
        "summary": "Flat response summary",
        "status": "Open",
    }
    mock_provider = _make_mock_provider(issue=flat_issue)
    with patch(
        "nv_config_manager.temporal.ngc.activities.ticketing.get_ticketing_provider",
        return_value=mock_provider,
    ):
        result = await validate_ticket(
            ValidateTicketInput(ticketing_platform=PLATFORM, issue_key=ISSUE_KEY)
        )

    assert result.summary == "Flat response summary"
    assert result.status == "Open"


async def test_validate_ticket_missing_summary_defaults_to_empty():
    """When 'summary' is absent, output summary is ''."""
    mock_provider = _make_mock_provider(
        issue={"self": "http://x", "fields": {"status": {"name": "Open"}}}
    )
    with patch(
        "nv_config_manager.temporal.ngc.activities.ticketing.get_ticketing_provider",
        return_value=mock_provider,
    ):
        result = await validate_ticket(
            ValidateTicketInput(ticketing_platform=PLATFORM, issue_key=ISSUE_KEY)
        )

    assert result.summary == ""


# =============================================================================
# upload_attachment
# =============================================================================


async def test_upload_attachment_calls_get_ticketing_provider():
    """get_ticketing_provider is called with the activity input's ticketing_platform."""
    mock_provider = _make_mock_provider()
    with patch(
        "nv_config_manager.temporal.ngc.activities.ticketing.get_ticketing_provider",
        return_value=mock_provider,
    ) as mock_factory:
        await upload_attachment(
            UploadAttachmentInput(
                ticketing_platform=PLATFORM,
                issue_key=ISSUE_KEY,
                filename="diag.txt",
                content=b"data",
                content_type="text/plain",
            )
        )

    mock_factory.assert_called_once_with(PLATFORM)


async def test_upload_attachment_returns_upload_attachment_output():
    """Activity returns an UploadAttachmentOutput instance."""
    mock_provider = _make_mock_provider()
    with patch(
        "nv_config_manager.temporal.ngc.activities.ticketing.get_ticketing_provider",
        return_value=mock_provider,
    ):
        result = await upload_attachment(
            UploadAttachmentInput(
                ticketing_platform=PLATFORM,
                issue_key=ISSUE_KEY,
                filename="diag.txt",
                content=b"data",
                content_type="text/plain",
            )
        )

    assert isinstance(result, UploadAttachmentOutput)


async def test_upload_attachment_populates_both_fields():
    """Both attachment_id and attachment_url are set to the provider's return value."""
    url = "https://jira.example.com/attachment/99"
    mock_provider = _make_mock_provider(attachment_result=url)
    with patch(
        "nv_config_manager.temporal.ngc.activities.ticketing.get_ticketing_provider",
        return_value=mock_provider,
    ):
        result = await upload_attachment(
            UploadAttachmentInput(
                ticketing_platform=PLATFORM,
                issue_key=ISSUE_KEY,
                filename="diag.txt",
                content=b"data",
                content_type="text/plain",
            )
        )

    assert result.attachment_id == url
    assert result.attachment_url == url


async def test_upload_attachment_passes_all_args_to_provider():
    """provider.upload_attachment is called with issue_key, filename, content, content_type."""
    mock_provider = _make_mock_provider()
    with patch(
        "nv_config_manager.temporal.ngc.activities.ticketing.get_ticketing_provider",
        return_value=mock_provider,
    ):
        await upload_attachment(
            UploadAttachmentInput(
                ticketing_platform=PLATFORM,
                issue_key=ISSUE_KEY,
                filename="bundle.tar.gz",
                content=b"\x1f\x8b",
                content_type="application/gzip",
            )
        )

    mock_provider.upload_attachment.assert_called_once_with(
        ISSUE_KEY, "bundle.tar.gz", b"\x1f\x8b", "application/gzip"
    )


# =============================================================================
# add_ticket_comment
# =============================================================================


async def test_add_ticket_comment_calls_get_ticketing_provider():
    """get_ticketing_provider is called with the activity input's ticketing_platform."""
    mock_provider = _make_mock_provider()
    with patch(
        "nv_config_manager.temporal.ngc.activities.ticketing.get_ticketing_provider",
        return_value=mock_provider,
    ) as mock_factory:
        await add_ticket_comment(
            AddCommentInput(ticketing_platform=PLATFORM, issue_key=ISSUE_KEY, body="Test comment")
        )

    mock_factory.assert_called_once_with(PLATFORM)


async def test_add_ticket_comment_returns_add_comment_output():
    """Activity returns an AddCommentOutput instance."""
    mock_provider = _make_mock_provider()
    with patch(
        "nv_config_manager.temporal.ngc.activities.ticketing.get_ticketing_provider",
        return_value=mock_provider,
    ):
        result = await add_ticket_comment(
            AddCommentInput(ticketing_platform=PLATFORM, issue_key=ISSUE_KEY, body="Test comment")
        )

    assert isinstance(result, AddCommentOutput)


async def test_add_ticket_comment_id_in_output():
    """Output comment_id matches the provider's return value."""
    mock_provider = _make_mock_provider(comment_id="55123")
    with patch(
        "nv_config_manager.temporal.ngc.activities.ticketing.get_ticketing_provider",
        return_value=mock_provider,
    ):
        result = await add_ticket_comment(
            AddCommentInput(ticketing_platform=PLATFORM, issue_key=ISSUE_KEY, body="Test comment")
        )

    assert result.comment_id == "55123"


async def test_add_ticket_comment_passes_body_to_provider():
    """provider.add_comment is called with the issue_key and plain-text body."""
    mock_provider = _make_mock_provider()
    with patch(
        "nv_config_manager.temporal.ngc.activities.ticketing.get_ticketing_provider",
        return_value=mock_provider,
    ):
        await add_ticket_comment(
            AddCommentInput(
                ticketing_platform=PLATFORM,
                issue_key=ISSUE_KEY,
                body="Device check complete.",
            )
        )

    mock_provider.add_comment.assert_called_once_with(ISSUE_KEY, "Device check complete.")


# =============================================================================
# UploadAttachmentInput._coerce_bytes — Temporal serialization regression
# =============================================================================


def test_upload_attachment_input_coerces_list_to_bytes():
    """Temporal serialises bytes as list[int]. _coerce_bytes must convert back.
    Regression: without this, Temporal activity input deserialization raises ValidationError."""
    inp = UploadAttachmentInput(
        ticketing_platform=PLATFORM,
        issue_key=ISSUE_KEY,
        filename="diag.txt",
        content=[104, 101, 108, 108, 111],  # "hello" as list[int]
        content_type="text/plain",
    )
    assert inp.content == b"hello"


def test_upload_attachment_input_accepts_real_bytes():
    """When content is already bytes (direct construction), no coercion needed."""
    inp = UploadAttachmentInput(
        ticketing_platform=PLATFORM,
        issue_key=ISSUE_KEY,
        filename="diag.txt",
        content=b"hello",
        content_type="text/plain",
    )
    assert inp.content == b"hello"


def test_upload_attachment_input_empty_list_coerces_to_empty_bytes():
    """Empty list[int] coerces to b''."""
    inp = UploadAttachmentInput(
        ticketing_platform=PLATFORM,
        issue_key=ISSUE_KEY,
        filename="diag.txt",
        content=[],
        content_type="text/plain",
    )
    assert inp.content == b""
