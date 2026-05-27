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
"""Tests for the template updater module."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nv_config_manager_templates.version import TemplateVersion

from nv_config_manager.render.producer import load_stale_renders, update_stale_renders

CURRENT_VERSION = "engine=nv-config-manager-templates:1.0.0;plugins=none"
NEWER_VERSION = "engine=nv-config-manager-templates:1.1.0;plugins=none"
OLDER_VERSION = "engine=nv-config-manager-templates:0.9.0;plugins=none"


@pytest.fixture
def mock_nautobot_client():
    """Mock Nautobot client."""
    with patch("nv_config_manager.render.producer.pynautobot_client") as mock:
        mock_instance = MagicMock()
        mock_instance.status.return_value = {"plugins": {"nv_config_manager": "1.0.0"}}
        mock_instance.graphql.query.return_value.json = {
            "data": {
                "config_manager_devices": [
                    {
                        "device": {"id": "device1"},
                        "intended_config": {"template_version": CURRENT_VERSION},
                    }
                ]
            }
        }
        mock.return_value = mock_instance
        yield mock_instance


def test_load_stale_renders_no_config_manager_plugin(mock_nautobot_client):
    """Test load_stale_renders when nv-config-manager plugin is not available."""
    mock_nautobot_client.status.return_value = {"plugins": {"other_plugin": "1.0.0"}}

    result = load_stale_renders(CURRENT_VERSION)
    assert result == []


def test_load_stale_renders_no_stale_renders(mock_nautobot_client):
    """Test load_stale_renders when no stale renders exist."""
    mock_nautobot_client.graphql.query.return_value.json = {
        "data": {
            "config_manager_devices": [
                {
                    "device": {"id": "device1"},
                    "intended_config": {"template_version": CURRENT_VERSION},
                }
            ]
        }
    }

    result = load_stale_renders(CURRENT_VERSION)
    assert result == []


def test_load_stale_renders_with_stale_renders(mock_nautobot_client):
    """Test load_stale_renders when stale renders exist."""
    mock_nautobot_client.graphql.query.return_value.json = {
        "data": {
            "config_manager_devices": [
                {
                    "device": {"id": "device1"},
                    "intended_config": {"template_version": OLDER_VERSION},
                },
                {
                    "device": {"id": "device2"},
                    "intended_config": {"template_version": CURRENT_VERSION},
                },
            ]
        }
    }

    result = load_stale_renders(CURRENT_VERSION)
    assert result == ["device1"]


def test_load_stale_renders_no_intended_config(mock_nautobot_client):
    """Test load_stale_renders when device has no intended config."""
    mock_nautobot_client.graphql.query.return_value.json = {
        "data": {"config_manager_devices": [{"device": {"id": "device1"}, "intended_config": None}]}
    }

    result = load_stale_renders(CURRENT_VERSION)
    assert result == []


def test_load_stale_renders_does_not_update_incomparable_versions(mock_nautobot_client):
    """Test load_stale_renders when plugin version vectors diverge."""
    mock_nautobot_client.graphql.query.return_value.json = {
        "data": {
            "config_manager_devices": [
                {
                    "device": {"id": "device1"},
                    "intended_config": {
                        "template_version": (
                            "engine=nv-config-manager-templates:1.0.0;plugins=nv-config-manager-dgxc-templates:1.0.0"
                        )
                    },
                },
            ]
        }
    }

    result = load_stale_renders(
        "engine=nv-config-manager-templates:1.0.0;plugins=nv-config-manager-azure-templates:1.0.0"
    )
    assert result == []


@pytest.mark.asyncio
@patch("nv_config_manager.render.producer.execute_render", new_callable=AsyncMock)
@patch("nv_config_manager.render.producer.create_lock")
async def test_update_stale_renders_locks_and_renders_devices(
    mock_create_lock,
    mock_execute_render,
    mock_nautobot_client,
):
    """Test update_stale_renders locks each device before rendering."""
    mock_nautobot_client.graphql.query.return_value.json = {
        "data": {
            "config_manager_devices": [
                {
                    "device": {"id": "device1"},
                    "intended_config": {"template_version": OLDER_VERSION},
                },
                {
                    "device": {"id": "device2"},
                    "intended_config": {"template_version": OLDER_VERSION},
                },
            ]
        }
    }
    mock_lock = MagicMock()
    mock_lock.acquire = AsyncMock(return_value=True)
    mock_lock.release = AsyncMock(return_value=True)
    mock_create_lock.return_value = mock_lock

    result = await update_stale_renders(
        desired_version=TemplateVersion.parse(CURRENT_VERSION),
        concurrency=2,
        lock_timeout=10,
    )

    assert result == 2
    assert mock_create_lock.call_count == 2
    mock_create_lock.assert_any_call("device1", blocking=True, blocking_timeout=10)
    mock_create_lock.assert_any_call("device2", blocking=True, blocking_timeout=10)
    assert mock_lock.acquire.await_count == 2
    assert mock_lock.release.await_count == 2
    mock_execute_render.assert_any_await(
        "device1",
        f"Template version change: {CURRENT_VERSION}",
        "template-updater",
    )
    mock_execute_render.assert_any_await(
        "device2",
        f"Template version change: {CURRENT_VERSION}",
        "template-updater",
    )


@pytest.mark.asyncio
@patch("nv_config_manager.render.producer.execute_render", new_callable=AsyncMock)
@patch("nv_config_manager.render.producer.create_lock")
async def test_update_stale_renders_logs_lock_failure_without_failing_job(
    mock_create_lock,
    mock_execute_render,
    mock_nautobot_client,
):
    """Test update_stale_renders skips devices when a lock cannot be acquired."""
    mock_nautobot_client.graphql.query.return_value.json = {
        "data": {
            "config_manager_devices": [
                {
                    "device": {"id": "device1"},
                    "intended_config": {"template_version": OLDER_VERSION},
                }
            ]
        }
    }
    mock_lock = MagicMock()
    mock_lock.acquire = AsyncMock(return_value=False)
    mock_lock.release = AsyncMock(return_value=True)
    mock_create_lock.return_value = mock_lock

    result = await update_stale_renders(
        desired_version=TemplateVersion.parse(CURRENT_VERSION),
        concurrency=1,
        lock_timeout=10,
    )

    assert result == 0
    mock_execute_render.assert_not_awaited()
    mock_lock.release.assert_not_awaited()


@pytest.mark.asyncio
@patch("nv_config_manager.render.producer.execute_render", new_callable=AsyncMock)
@patch("nv_config_manager.render.producer.create_lock")
async def test_update_stale_renders_logs_render_failure_without_failing_job(
    mock_create_lock,
    mock_execute_render,
    mock_nautobot_client,
):
    """Test update_stale_renders does not fail the job when one render fails."""
    mock_nautobot_client.graphql.query.return_value.json = {
        "data": {
            "config_manager_devices": [
                {
                    "device": {"id": "device1"},
                    "intended_config": {"template_version": OLDER_VERSION},
                },
                {
                    "device": {"id": "device2"},
                    "intended_config": {"template_version": OLDER_VERSION},
                },
            ]
        }
    }
    mock_lock = MagicMock()
    mock_lock.acquire = AsyncMock(return_value=True)
    mock_lock.release = AsyncMock(return_value=True)
    mock_create_lock.return_value = mock_lock
    mock_execute_render.side_effect = [RuntimeError("bad render data"), None]

    result = await update_stale_renders(
        desired_version=TemplateVersion.parse(CURRENT_VERSION),
        concurrency=2,
        lock_timeout=10,
    )

    assert result == 1
    assert mock_execute_render.await_count == 2
    assert mock_lock.release.await_count == 2
