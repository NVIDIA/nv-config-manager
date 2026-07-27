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
"""Tests for the admin v1 API endpoints."""

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from nv_config_manager.render.api.main import app


class MockConsumerInfo:
    """Mock consumer info object."""

    def __init__(self, num_pending=0, num_ack_pending=0, consumer_seq=100):
        self.num_pending = num_pending
        self.num_ack_pending = num_ack_pending
        self.delivered = MagicMock()
        self.delivered.consumer_seq = consumer_seq


def create_test_mocks():
    """Helper to create consistent mocks for tests."""
    # Setup config mock
    mock_config_obj = MagicMock()
    mock_config_obj.__getitem__.return_value = {
        "queue": "test-queue",
        "config_manager_stream": "nv-config-manager",
        "config_manager_api_prefix": "$JS.API",
        "config_manager_subjects": "nv-config-manager.nautobotchange,nv-config-manager.devicechange,nv-config-manager.workflow.result",
        "render_change_stream": "nv-config-manager",
        "render_change_api_prefix": "$JS.API",
        "render_change_subject": "nv-config-manager.nautobotchange",
        "device_change_stream": "nv-config-manager",
        "device_change_api_prefix": "$JS.API",
        "device_change_subject": "nv-config-manager.devicechange",
        "nautobot_stream": "nautobot",
        "nautobot_api_prefix": "$JS.CUSTOM.API",
        "nautobot_subjects": "nautobot",
        "nautobot_subject": "nautobot",
    }

    # Setup NATS connection mock - return a non-async mock directly
    mock_conn = MagicMock()
    mock_js = MagicMock()
    mock_conn.jetstream.return_value = mock_js
    mock_conn.close = AsyncMock()

    # The async function should return the mock directly
    async def mock_get_connection():
        return mock_conn

    return mock_config_obj, mock_get_connection, mock_conn, mock_js


class TestConsumerList:
    """Tests for listing consumers."""

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    def test_list_consumers_success(self, mock_get_conn, mock_load_config):
        """Test successful consumer listing."""
        mock_config_obj, mock_get_connection, mock_conn, mock_js = create_test_mocks()
        mock_load_config.return_value = mock_config_obj
        mock_get_conn.side_effect = mock_get_connection

        # Setup consumer info responses - make it async
        async def mock_consumer_info(stream, consumer):
            if consumer == "test-queue-nautobot":
                return MockConsumerInfo(num_pending=10, num_ack_pending=1, consumer_seq=100)
            elif consumer == "test-queue-device":
                return MockConsumerInfo(num_pending=5, num_ack_pending=0, consumer_seq=200)

        mock_js.consumer_info.side_effect = mock_consumer_info

        client = TestClient(app)
        response = client.get("/v1/admin/consumers")

        assert response.status_code == 200
        data = response.json()
        assert "consumers" in data
        assert len(data["consumers"]) == 2

        # Check first consumer
        consumer = data["consumers"][0]
        assert consumer["name"] == "test-queue-nautobot"
        assert consumer["stream"] == "nautobot"
        assert consumer["subject"] == "nautobot"
        assert consumer["num_pending"] == 10
        assert consumer["num_ack_pending"] == 1
        assert consumer["num_delivered"] == 100
        mock_conn.jetstream.assert_any_call(prefix="$JS.CUSTOM.API")
        mock_conn.jetstream.assert_any_call(prefix="$JS.API")

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    def test_list_consumers_with_missing_consumer(self, mock_get_conn, mock_load_config):
        """Test listing consumers when one consumer is missing."""
        mock_config_obj, mock_get_connection, mock_conn, mock_js = create_test_mocks()
        mock_load_config.return_value = mock_config_obj
        mock_get_conn.side_effect = mock_get_connection

        # First consumer exists, second throws exception
        async def mock_consumer_info(stream, consumer):
            if consumer == "test-queue-nautobot":
                return MockConsumerInfo(num_pending=10, num_ack_pending=1, consumer_seq=100)
            elif consumer == "test-queue-device":
                raise Exception("Consumer not found")

        mock_js.consumer_info.side_effect = mock_consumer_info

        client = TestClient(app)
        response = client.get("/v1/admin/consumers")

        assert response.status_code == 200
        data = response.json()
        assert len(data["consumers"]) == 2

        # Check that missing consumer shows -1 values
        missing_consumer = data["consumers"][1]
        assert missing_consumer["num_pending"] == -1
        assert missing_consumer["num_ack_pending"] == -1
        assert missing_consumer["num_delivered"] == -1

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    def test_list_consumers_connection_error(self, mock_get_conn, mock_load_config):
        """Test listing consumers with connection error."""
        mock_config_obj, _, _, _ = create_test_mocks()
        mock_load_config.return_value = mock_config_obj

        async def mock_get_connection_error():
            raise Exception("Connection failed")

        mock_get_conn.side_effect = mock_get_connection_error

        client = TestClient(app)
        response = client.get("/v1/admin/consumers")

        assert response.status_code == 500
        assert "Failed to list consumers" in response.json()["detail"]


class TestGetConsumerInfo:
    """Tests for getting individual consumer info."""

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    def test_get_consumer_info_success(self, mock_get_conn, mock_load_config):
        """Test getting consumer info successfully."""
        mock_config_obj, mock_get_connection, mock_conn, mock_js = create_test_mocks()
        mock_load_config.return_value = mock_config_obj
        mock_get_conn.side_effect = mock_get_connection

        async def mock_consumer_info(stream, consumer):
            return MockConsumerInfo(num_pending=25, num_ack_pending=2, consumer_seq=150)

        mock_js.consumer_info.side_effect = mock_consumer_info

        client = TestClient(app)
        response = client.get("/v1/admin/consumers/device")

        assert response.status_code == 200
        mock_conn.jetstream.assert_called_once_with(prefix="$JS.API")
        data = response.json()
        assert data["name"] == "test-queue-device"
        assert data["stream"] == "nv-config-manager"
        assert data["subject"] == "nv-config-manager.nautobotchange"
        assert data["num_pending"] == 25
        assert data["num_ack_pending"] == 2
        assert data["num_delivered"] == 150

    def test_get_consumer_info_invalid_type(self):
        """Test getting consumer info with invalid consumer type."""
        client = TestClient(app)
        response = client.get("/v1/admin/consumers/invalid")

        assert response.status_code == 422
        # FastAPI enum validation returns a different error format
        assert "detail" in response.json()

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    def test_get_consumer_info_not_found(self, mock_get_conn, mock_load_config):
        """Test getting consumer info when consumer doesn't exist."""
        mock_config_obj, mock_get_connection, mock_conn, mock_js = create_test_mocks()
        mock_load_config.return_value = mock_config_obj
        mock_get_conn.side_effect = mock_get_connection

        async def mock_consumer_info(stream, consumer):
            raise Exception("Consumer not found")

        mock_js.consumer_info.side_effect = mock_consumer_info

        client = TestClient(app)
        response = client.get("/v1/admin/consumers/device")

        assert response.status_code == 404
        assert "Consumer 'test-queue-device' not found" in response.json()["detail"]


class TestResetConsumer:
    """Tests for resetting individual consumers."""

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    def test_reset_consumer_success(self, mock_get_conn, mock_load_config):
        """Test successful consumer reset."""
        mock_config_obj, mock_get_connection, mock_conn, mock_js = create_test_mocks()
        mock_load_config.return_value = mock_config_obj
        mock_get_conn.side_effect = mock_get_connection

        # Mock consumer info (before deletion)
        async def mock_consumer_info(stream, consumer):
            return MockConsumerInfo(num_pending=50, num_ack_pending=1, consumer_seq=200)

        mock_js.consumer_info.side_effect = mock_consumer_info

        # Mock successful deletion
        async def mock_delete_consumer(stream, consumer):
            return None

        mock_js.delete_consumer.side_effect = mock_delete_consumer

        client = TestClient(app)
        response = client.delete("/v1/admin/consumers/nautobot/reset")

        assert response.status_code == 200
        mock_conn.jetstream.assert_called_once_with(prefix="$JS.CUSTOM.API")
        data = response.json()
        assert data["consumer_name"] == "test-queue-nautobot"
        assert data["stream"] == "nautobot"
        assert data["status"] == "success"
        assert "Had 50 pending messages" in data["message"]
        assert "automatically recreated within seconds" in data["message"]

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    def test_reset_consumer_already_deleted(self, mock_get_conn, mock_load_config):
        """Test resetting a consumer that's already deleted."""
        mock_config_obj, mock_get_connection, mock_conn, mock_js = create_test_mocks()
        mock_load_config.return_value = mock_config_obj
        mock_get_conn.side_effect = mock_get_connection

        # Mock consumer info fails (consumer doesn't exist)
        async def mock_consumer_info(stream, consumer):
            raise Exception("Consumer not found")

        mock_js.consumer_info.side_effect = mock_consumer_info

        # Mock deletion also fails with "not found"
        async def mock_delete_consumer(stream, consumer):
            raise Exception("Consumer not found")

        mock_js.delete_consumer.side_effect = mock_delete_consumer

        client = TestClient(app)
        response = client.delete("/v1/admin/consumers/device/reset")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "was already deleted" in data["message"]

    def test_reset_consumer_invalid_type(self):
        """Test resetting with invalid consumer type."""
        client = TestClient(app)
        response = client.delete("/v1/admin/consumers/invalid/reset")

        assert response.status_code == 422
        # FastAPI enum validation returns a different error format
        assert "detail" in response.json()

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    def test_reset_consumer_deletion_error(self, mock_get_conn, mock_load_config):
        """Test consumer reset with deletion error."""
        mock_config_obj, mock_get_connection, mock_conn, mock_js = create_test_mocks()
        mock_load_config.return_value = mock_config_obj
        mock_get_conn.side_effect = mock_get_connection

        # Mock consumer info succeeds
        async def mock_consumer_info(stream, consumer):
            return MockConsumerInfo(num_pending=10)

        mock_js.consumer_info.side_effect = mock_consumer_info

        # Mock deletion fails with unexpected error
        async def mock_delete_consumer(stream, consumer):
            raise Exception("Unexpected error")

        mock_js.delete_consumer.side_effect = mock_delete_consumer

        client = TestClient(app)
        response = client.delete("/v1/admin/consumers/template/reset")

        assert response.status_code == 500
        assert "Failed to reset consumer" in response.json()["detail"]


class TestResetAllConsumers:
    """Tests for resetting all consumers."""

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    def test_reset_all_consumers_success(self, mock_get_conn, mock_load_config):
        """Test successful reset of all consumers."""
        mock_config_obj, mock_get_connection, mock_conn, mock_js = create_test_mocks()
        mock_load_config.return_value = mock_config_obj
        mock_get_conn.side_effect = mock_get_connection

        # Mock consumer info for all configured consumers
        call_count = [0]  # Use list to modify in nested function

        async def mock_consumer_info(stream, consumer):
            responses = [
                MockConsumerInfo(num_pending=10, num_ack_pending=0, consumer_seq=100),
                MockConsumerInfo(num_pending=20, num_ack_pending=1, consumer_seq=200),
            ]
            result = responses[call_count[0]]
            call_count[0] += 1
            return result

        mock_js.consumer_info.side_effect = mock_consumer_info

        # Mock successful deletions
        async def mock_delete_consumer(stream, consumer):
            return None

        mock_js.delete_consumer.side_effect = mock_delete_consumer

        client = TestClient(app)
        response = client.delete("/v1/admin/consumers/reset-all")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        # Check all consumers were reset successfully
        for result in data:
            assert result["status"] == "success"
            assert "deleted successfully" in result["message"]

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    def test_reset_all_consumers_connection_error(self, mock_get_conn, mock_load_config):
        """Test reset all consumers with connection error."""
        mock_config_obj, _, _, _ = create_test_mocks()
        mock_load_config.return_value = mock_config_obj

        async def mock_get_connection_error():
            raise Exception("Connection failed")

        mock_get_conn.side_effect = mock_get_connection_error

        client = TestClient(app)
        response = client.delete("/v1/admin/consumers/reset-all")

        assert response.status_code == 500
        assert "Failed to reset consumers" in response.json()["detail"]


class TestConsumerConfigs:
    """Tests for consumer configuration logic."""

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    def test_get_consumer_configs(self, mock_load_config):
        """Test that consumer configs are correctly generated."""
        mock_config_obj = MagicMock()
        mock_config_obj.__getitem__.return_value = {
            "queue": "test-queue",
            "config_manager_stream": "nv-config-manager",
            "config_manager_api_prefix": "$JS.API",
            "config_manager_subjects": "nv-config-manager.nautobotchange,nv-config-manager.devicechange,nv-config-manager.workflow.result",
            "render_change_stream": "nv-config-manager",
            "render_change_api_prefix": "$JS.API",
            "render_change_subject": "nv-config-manager.nautobotchange",
            "device_change_stream": "nv-config-manager",
            "device_change_api_prefix": "$JS.API",
            "device_change_subject": "nv-config-manager.devicechange",
            "nautobot_stream": "nautobot",
            "nautobot_api_prefix": "$JS.CUSTOM.API",
            "nautobot_subjects": "nautobot",
            "nautobot_subject": "nautobot",
        }
        mock_load_config.return_value = mock_config_obj

        from nv_config_manager.render.api.admin_v1 import get_consumer_configs

        configs = get_consumer_configs()

        assert len(configs) == 2
        assert "nautobot" in configs
        assert "device" in configs

        # Check nautobot config
        nautobot_config = configs["nautobot"]
        assert nautobot_config["durable_name"] == "test-queue-nautobot"
        assert nautobot_config["stream"] == "nautobot"
        assert nautobot_config["subject"] == "nautobot"
        assert nautobot_config["api_prefix"] == "$JS.CUSTOM.API"

        # Check device config
        device_config = configs["device"]
        assert device_config["durable_name"] == "test-queue-device"
        assert device_config["stream"] == "nv-config-manager"
        assert device_config["subject"] == "nv-config-manager.nautobotchange"
        assert device_config["api_prefix"] == "$JS.API"


class TestIntegration:
    """Integration tests for the admin API."""

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    def test_full_consumer_lifecycle(self, mock_get_conn, mock_load_config):
        """Test the full lifecycle: get info -> reset."""
        mock_config_obj, mock_get_connection, mock_conn, mock_js = create_test_mocks()
        mock_load_config.return_value = mock_config_obj
        mock_get_conn.side_effect = mock_get_connection
        client = TestClient(app)

        # Initial get - consumer has pending messages
        async def mock_consumer_info(stream, consumer):
            return MockConsumerInfo(num_pending=100, num_ack_pending=5, consumer_seq=500)

        mock_js.consumer_info.side_effect = mock_consumer_info

        response = client.get("/v1/admin/consumers/device")
        assert response.status_code == 200
        assert response.json()["num_pending"] == 100

        # Reset the consumer
        async def mock_delete_consumer(stream, consumer):
            return None

        mock_js.delete_consumer.side_effect = mock_delete_consumer

        response = client.delete("/v1/admin/consumers/device/reset")
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    @patch.dict("os.environ", {"LOCAL_VENV": "1"})
    def test_admin_api_included_in_main_app(self, mock_get_conn, mock_load_config):
        """Test that admin routes are properly included in the main app."""
        mock_config_obj, mock_get_connection, mock_conn, mock_js = create_test_mocks()
        mock_load_config.return_value = mock_config_obj
        mock_get_conn.side_effect = mock_get_connection

        # Mock consumer info to return valid data
        async def mock_consumer_info(stream, consumer):
            return MockConsumerInfo(num_pending=0, num_ack_pending=0, consumer_seq=0)

        mock_js.consumer_info.side_effect = mock_consumer_info

        # Mock delete consumer
        async def mock_delete_consumer(stream, consumer):
            return None

        mock_js.delete_consumer.side_effect = mock_delete_consumer

        client = TestClient(app)

        # Test that admin endpoints exist and return valid responses
        response = client.get("/v1/admin/consumers")
        assert response.status_code != 404

        response = client.get("/v1/admin/consumers/device")
        assert response.status_code != 404

        response = client.delete("/v1/admin/consumers/device/reset")
        assert response.status_code != 404

        response = client.delete("/v1/admin/consumers/reset-all")
        assert response.status_code != 404
