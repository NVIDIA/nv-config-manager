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
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from nv_config_manager.common.client import ConfigFile, ConfigFileMetadata
from nv_config_manager.common.client.render import FileCommit
from nv_config_manager.render.render import execute_render

TEMPLATE_VERSION = "engine=nv-config-manager-templates:0.0.1;plugins=none"


@patch("nv_config_manager.render.render.pynautobot_client")
@patch("nv_config_manager.render.render.config_store_client")
@patch("nv_config_manager.render.render.Renderer")
@patch("nv_config_manager.render.render.template_version_key", return_value=TEMPLATE_VERSION)
@patch("nv_config_manager.render.render.datetime")
@patch(
    "nv_config_manager.render.render.config_store_ui_url",
    return_value="https://config-manager.example.com/",
)
@pytest.mark.asyncio
async def test_execute_render(
    mock_config_store_ui_url,
    mock_datetime,
    mock_template_version_key,
    mock_renderer,
    mock_config_store,
    mock_nb,
):
    """Test render execution."""
    # Setup Mocking
    mock_config_manager_tag = MagicMock()
    mock_config_manager_tag.name = "nv-config-manager-managed-full"

    mock_site = MagicMock()
    mock_site.tags = [mock_config_manager_tag]
    mock_site.name = "SITEA"

    mock_tenant = MagicMock()
    mock_tenant.name = "TenantA"

    mock_status = MagicMock()
    mock_status.value = "provisioning"

    mock_device = MagicMock()
    mock_device.id = uuid4()
    mock_device.name = "sitea-leaf-1.tan.gpod1"
    mock_device.tenant = mock_tenant
    mock_device.site = mock_site
    mock_device.status = mock_status

    mock_nb.return_value.dcim.devices.get.return_value = mock_device

    intended_config_endpoint = mock_nb.return_value.plugins.nv_config_manager.intendedconfig
    intended_config_endpoint.get.return_value = None

    # Change to relevant file
    mock_renderer.return_value.render_entrypoints.return_value = {
        "startup.yaml": "test",
        "boot-script": "test",
    }
    commit_id = "12345"
    # Setup async context manager mock
    mock_client_instance = AsyncMock()
    mock_client_instance.target = "https://api.config-store.config-manager.example.com/"
    mock_client_instance.file_type = "intended"
    mock_client_instance.persist_files.return_value = [
        ConfigFileMetadata(commit=commit_id, filename="startup.yaml")
    ]
    mock_client_instance.__aenter__.return_value = mock_client_instance
    mock_client_instance.__aexit__.return_value = None
    mock_config_store.return_value = mock_client_instance

    mock_datetime.now.return_value.isoformat.return_value = "2024-04-04T15:41:22.083507"

    result = await execute_render(mock_device.id, "test commit message", "test user")
    assert result == [FileCommit(filename="startup.yaml", commit=commit_id)]

    expected_call = {
        "device_id": mock_device.id,
        "config_store_instance": "https://config-manager.example.com/",
        "path": "startup.yaml",
        "commit_id": "12345",
        "updated": "2024-04-04T15:41:22.083507",
        "updated_by": "test user",
        "commit_message": "test commit message",
        "template_version": TEMPLATE_VERSION,
    }
    intended_config_endpoint.create.assert_called_with(expected_call)

    # Change to file not relevant to NB
    intended_config_endpoint.create.reset_mock()
    intended_config_endpoint.update.reset_mock()
    mock_client_instance.persist_files.return_value = [
        ConfigFileMetadata(commit=commit_id, filename="boot-script")
    ]

    result = await execute_render(mock_device.id, "test commit message", "test user")
    assert result == [FileCommit(filename="boot-script", commit=commit_id)]
    # Full update not called
    intended_config_endpoint.create.assert_not_called()
    # Template version update called
    intended_config_endpoint.update.assert_called_once_with(
        id=mock_device.id,
        data={
            "template_version": TEMPLATE_VERSION,
        },
    )

    # No file change — re-syncs Nautobot with latest Config Store version
    intended_config_endpoint.create.reset_mock()
    intended_config_endpoint.update.reset_mock()
    mock_client_instance.persist_files.return_value = None
    config_store_timestamp = "2024-03-15T10:30:00.000000"
    mock_client_instance.load_file.return_value = ConfigFile(
        content="test",
        commit="42",
        filename="startup.yaml",
        sha="abc123",
        created_at=config_store_timestamp,
    )
    result = await execute_render(mock_device.id, "test commit message", "test user")
    assert result == []
    mock_client_instance.load_file.assert_called_with(mock_device.id, "startup.yaml")
    expected_resync_call = {
        "device_id": mock_device.id,
        "config_store_instance": "https://config-manager.example.com/",
        "path": "startup.yaml",
        "commit_id": "42",
        "updated": config_store_timestamp,
        "updated_by": "test user",
        "commit_message": "test commit message",
        "template_version": TEMPLATE_VERSION,
    }
    intended_config_endpoint.create.assert_called_with(expected_resync_call)

    # Test 2 files with different commit IDs, make sure only the deployable file commit ID is used
    intended_config_endpoint.create.reset_mock()
    intended_config_endpoint.update.reset_mock()
    mock_client_instance.persist_files.return_value = [
        ConfigFileMetadata(commit="3", filename="boot-script"),
        ConfigFileMetadata(commit="20", filename="startup.yaml"),
    ]
    result = await execute_render(mock_device.id, "test commit message", "test user")
    assert result == [
        FileCommit(filename="boot-script", commit="3"),
        FileCommit(filename="startup.yaml", commit="20"),
    ]
    expected_call = {
        "device_id": mock_device.id,
        "config_store_instance": "https://config-manager.example.com/",
        "path": "startup.yaml",
        "commit_id": "20",
        "updated": "2024-04-04T15:41:22.083507",
        "updated_by": "test user",
        "commit_message": "test commit message",
        "template_version": TEMPLATE_VERSION,
    }
    intended_config_endpoint.create.assert_called_with(expected_call)
    intended_config_endpoint.update.assert_not_called()
