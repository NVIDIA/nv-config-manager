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

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from nats.errors import NoRespondersError
from nats.errors import TimeoutError as NatsTimeoutError
from nats.js.errors import NotFoundError, ServiceUnavailableError

from nv_config_manager.render.api.admin_v1 import ConsumerResetRejected, fast_forward_consumer
from nv_config_manager.render.api.main import app


class MockConsumerInfo:
    """Mock consumer info object."""

    def __init__(self, num_pending=0, num_ack_pending=0, consumer_seq=100, stream_seq=500):
        self.num_pending = num_pending
        self.num_ack_pending = num_ack_pending
        self.delivered = MagicMock()
        self.delivered.consumer_seq = consumer_seq
        self.delivered.stream_seq = stream_seq


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
        "render_change_subject": "nv-config-manager.nautobotchange",
        "device_change_stream": "nv-config-manager",
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


def setup_consumer_reset(mock_conn, mock_js, backlog, last_seq=1000, remaining=0):
    """Wire the reset path: `backlog` pending on entry, `remaining` once reset lands.

    ``consumer_info`` is read either side of the reset, so returning two counts mirrors
    what a real consumer reports before and after its cursor moves.
    """
    seen: dict[str, int] = {}

    async def mock_consumer_info(stream, consumer):
        # Tracked per consumer so reset-all sees an entry backlog for each of them.
        reads = seen.get(consumer, 0)
        seen[consumer] = reads + 1
        return MockConsumerInfo(num_pending=backlog if reads == 0 else remaining)

    mock_js.consumer_info.side_effect = mock_consumer_info

    async def mock_stream_info(stream):
        info = MagicMock()
        info.state.last_seq = last_seq
        return info

    mock_js.stream_info.side_effect = mock_stream_info

    mock_conn.request = AsyncMock(
        return_value=MagicMock(data=json.dumps({"reset_seq": last_seq + 1}).encode())
    )
    return mock_conn.request


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

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    def test_get_consumer_info_nautobot_uses_imported_prefix(self, mock_get_conn, mock_load_config):
        """The nautobot stream is owned by another account, so info must use its import prefix."""
        mock_config_obj, mock_get_connection, mock_conn, mock_js = create_test_mocks()
        mock_load_config.return_value = mock_config_obj
        mock_get_conn.side_effect = mock_get_connection

        async def mock_consumer_info(stream, consumer):
            return MockConsumerInfo(num_pending=7, num_ack_pending=1, consumer_seq=42)

        mock_js.consumer_info.side_effect = mock_consumer_info

        client = TestClient(app)
        response = client.get("/v1/admin/consumers/nautobot")

        assert response.status_code == 200
        mock_conn.jetstream.assert_called_once_with(prefix="$JS.CUSTOM.API")

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
            raise NotFoundError

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
        """Reset moves the consumer past its backlog and reports how much it skipped."""
        mock_config_obj, mock_get_connection, mock_conn, mock_js = create_test_mocks()
        mock_load_config.return_value = mock_config_obj
        mock_get_conn.side_effect = mock_get_connection

        setup_consumer_reset(mock_conn, mock_js, backlog=50, last_seq=1000)

        client = TestClient(app)
        response = client.delete("/v1/admin/consumers/nautobot/reset")

        assert response.status_code == 200
        mock_conn.jetstream.assert_called_once_with(prefix="$JS.CUSTOM.API")
        data = response.json()
        assert data["consumer_name"] == "test-queue-nautobot"
        assert data["stream"] == "nautobot"
        assert data["status"] == "success"
        assert data["skipped"] == 50
        assert data["remaining_pending"] == 0
        assert data["reset_seq"] == 1001

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    def test_reset_consumer_never_deletes(self, mock_get_conn, mock_load_config):
        """The imported stream exports no consumer delete, so reset must not attempt one."""
        mock_config_obj, mock_get_connection, mock_conn, mock_js = create_test_mocks()
        mock_load_config.return_value = mock_config_obj
        mock_get_conn.side_effect = mock_get_connection

        request = setup_consumer_reset(mock_conn, mock_js, backlog=5, last_seq=42)

        client = TestClient(app)
        response = client.delete("/v1/admin/consumers/nautobot/reset")

        assert response.status_code == 200
        mock_js.delete_consumer.assert_not_called()

        # The reset subject carries the imported stream's prefix, and the target sits one
        # past the last stored sequence so the consumer lands at the head of the stream.
        subject, payload = request.await_args.args[0], request.await_args.args[1]
        assert subject == "$JS.CUSTOM.API.CONSUMER.RESET.nautobot.test-queue-nautobot"
        assert json.loads(payload) == {"seq": 43}

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    def test_reset_consumer_reports_new_arrivals_as_success(self, mock_get_conn, mock_load_config):
        """Reset is atomic, so a backlog afterwards is new traffic rather than a failure."""
        mock_config_obj, mock_get_connection, mock_conn, mock_js = create_test_mocks()
        mock_load_config.return_value = mock_config_obj
        mock_get_conn.side_effect = mock_get_connection

        setup_consumer_reset(mock_conn, mock_js, backlog=1000, remaining=7)

        client = TestClient(app)
        response = client.delete("/v1/admin/consumers/device/reset")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["skipped"] == 1000
        assert data["remaining_pending"] == 7
        assert "arrived since" in data["message"]

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    def test_reset_consumer_unavailable_when_server_lacks_reset(
        self, mock_get_conn, mock_load_config
    ):
        """A server below 2.14, or a stream missing the export, leaves the call unanswered."""
        mock_config_obj, mock_get_connection, mock_conn, mock_js = create_test_mocks()
        mock_load_config.return_value = mock_config_obj
        mock_get_conn.side_effect = mock_get_connection

        setup_consumer_reset(mock_conn, mock_js, backlog=10)
        mock_conn.request = AsyncMock(side_effect=NoRespondersError)

        client = TestClient(app)
        response = client.delete("/v1/admin/consumers/device/reset")

        assert response.status_code == 503
        assert "2.14.0+" in response.json()["detail"]
        mock_conn.close.assert_awaited_once()

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    def test_reset_consumer_unavailable_when_server_rejects(self, mock_get_conn, mock_load_config):
        """The server refuses reset on an ineligible consumer; surface its reason."""
        mock_config_obj, mock_get_connection, mock_conn, mock_js = create_test_mocks()
        mock_load_config.return_value = mock_config_obj
        mock_get_conn.side_effect = mock_get_connection

        setup_consumer_reset(mock_conn, mock_js, backlog=10)
        rejection = {"error": {"err_code": 10166, "description": "deliver policy not supported"}}
        mock_conn.request = AsyncMock(return_value=MagicMock(data=json.dumps(rejection).encode()))

        client = TestClient(app)
        response = client.delete("/v1/admin/consumers/device/reset")

        assert response.status_code == 503
        assert "deliver policy not supported" in response.json()["detail"]

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    def test_reset_consumer_not_found(self, mock_get_conn, mock_load_config):
        """A consumer that does not exist has no cursor to advance."""
        mock_config_obj, mock_get_connection, mock_conn, mock_js = create_test_mocks()
        mock_load_config.return_value = mock_config_obj
        mock_get_conn.side_effect = mock_get_connection

        async def mock_consumer_info(stream, consumer):
            raise NotFoundError

        mock_js.consumer_info.side_effect = mock_consumer_info

        client = TestClient(app)
        response = client.delete("/v1/admin/consumers/device/reset")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]
        # nats_connection opens a fresh connection per call, so an error path that
        # returns without closing leaks one connection per request.
        mock_conn.close.assert_awaited_once()

    def test_reset_consumer_invalid_type(self):
        """Test resetting with invalid consumer type."""
        client = TestClient(app)
        response = client.delete("/v1/admin/consumers/invalid/reset")

        assert response.status_code == 422
        # FastAPI enum validation returns a different error format
        assert "detail" in response.json()

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    def test_reset_consumer_unexpected_error(self, mock_get_conn, mock_load_config):
        """An unexpected failure during reset surfaces as a server error."""
        mock_config_obj, mock_get_connection, mock_conn, mock_js = create_test_mocks()
        mock_load_config.return_value = mock_config_obj
        mock_get_conn.side_effect = mock_get_connection

        setup_consumer_reset(mock_conn, mock_js, backlog=10)
        mock_conn.request = AsyncMock(side_effect=Exception("Unexpected error"))

        client = TestClient(app)
        # Must be a type get_consumer_configs actually returns; "template" is in the
        # enum but has no config, so it would 500 on a KeyError before reaching reset.
        response = client.delete("/v1/admin/consumers/device/reset")

        assert response.status_code == 500
        assert "Failed to reset consumer" in response.json()["detail"]
        mock_conn.close.assert_awaited_once()


class TestFastForward:
    """Tests for the reset helper that backs the endpoints."""

    async def _reset(self, backlog, last_seq=1000, remaining=0, api_prefix="$JS.API"):
        mock_conn = MagicMock()
        mock_js = MagicMock()
        request = setup_consumer_reset(
            mock_conn, mock_js, backlog=backlog, last_seq=last_seq, remaining=remaining
        )
        config = {
            "durable_name": "test-queue-nautobot",
            "stream": "nautobot",
            "api_prefix": api_prefix,
        }
        return request, await fast_forward_consumer(mock_conn, mock_js, config)

    @pytest.mark.asyncio
    async def test_targets_one_past_the_last_stored_sequence(self):
        """Reset asks for the sequence after the stream head so nothing stored is delivered."""
        request, (skipped, remaining, reset_seq) = await self._reset(600, last_seq=5000)

        assert (skipped, remaining, reset_seq) == (600, 0, 5001)
        assert json.loads(request.await_args.args[1]) == {"seq": 5001}

    @pytest.mark.asyncio
    async def test_uses_the_streams_configured_api_prefix(self):
        """An imported stream is reachable only under the prefix its account was mapped to."""
        request, _ = await self._reset(10, api_prefix="$JS.CEREBRO.API")

        assert request.await_args.args[0].startswith("$JS.CEREBRO.API.CONSUMER.RESET.")

    @pytest.mark.asyncio
    async def test_empty_backlog_still_resets(self):
        """Reset costs one call regardless of backlog, so an idle consumer is not special-cased."""
        request, (skipped, remaining, _) = await self._reset(0)

        assert (skipped, remaining) == (0, 0)
        request.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_falls_back_to_consumer_state_without_stream_info(self):
        """An imported stream exports no STREAM.INFO, so the target comes from the consumer."""
        mock_conn, mock_js = MagicMock(), MagicMock()
        request = setup_consumer_reset(mock_conn, mock_js, backlog=40, last_seq=9999)
        mock_js.stream_info.side_effect = ServiceUnavailableError
        config = {"durable_name": "test-queue-nautobot", "stream": "nautobot"}

        await fast_forward_consumer(mock_conn, mock_js, config)

        # delivered.stream_seq (500) + num_pending (40), then one past that.
        assert json.loads(request.await_args.args[1]) == {"seq": 541}

    @pytest.mark.asyncio
    async def test_no_response_is_rejected(self):
        """A server without the reset API never replies, which must not look like success."""
        mock_conn, mock_js = MagicMock(), MagicMock()
        setup_consumer_reset(mock_conn, mock_js, backlog=5)
        mock_conn.request = AsyncMock(side_effect=NatsTimeoutError)
        config = {"durable_name": "test-queue-nautobot", "stream": "nautobot"}

        with pytest.raises(ConsumerResetRejected, match="2.14.0"):
            await fast_forward_consumer(mock_conn, mock_js, config)


class TestResetAllConsumers:
    """Tests for resetting all consumers."""

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    def test_reset_all_consumers_success(self, mock_get_conn, mock_load_config):
        """Every consumer is fast-forwarded, each through its own stream's API prefix."""
        mock_config_obj, mock_get_connection, mock_conn, mock_js = create_test_mocks()
        mock_load_config.return_value = mock_config_obj
        mock_get_conn.side_effect = mock_get_connection

        setup_consumer_reset(mock_conn, mock_js, backlog=10)

        client = TestClient(app)
        response = client.delete("/v1/admin/consumers/reset-all")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        for result in data:
            assert result["status"] == "success"
            assert "fast-forwarded past" in result["message"]

        mock_js.delete_consumer.assert_not_called()
        mock_conn.jetstream.assert_any_call(prefix="$JS.CUSTOM.API")
        mock_conn.jetstream.assert_any_call(prefix="$JS.API")
        mock_conn.close.assert_awaited_once()

    @patch("nv_config_manager.render.api.admin_v1.load_config")
    @patch("nv_config_manager.render.api.admin_v1.nats_connection")
    def test_reset_all_consumers_reports_missing_as_not_found(
        self, mock_get_conn, mock_load_config
    ):
        """An absent consumer is reported as not_found, matching the single-consumer 404."""
        mock_config_obj, mock_get_connection, mock_conn, mock_js = create_test_mocks()
        mock_load_config.return_value = mock_config_obj
        mock_get_conn.side_effect = mock_get_connection

        mock_conn.flush = AsyncMock()

        async def mock_consumer_info(stream, consumer):
            raise NotFoundError

        mock_js.consumer_info.side_effect = mock_consumer_info

        client = TestClient(app)
        response = client.delete("/v1/admin/consumers/reset-all")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

        for result in data:
            assert result["status"] == "not_found"
            assert "does not exist" in result["message"]
            assert result["skipped"] == 0

        mock_js.delete_consumer.assert_not_called()
        mock_conn.close.assert_awaited_once()

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
            "render_change_subject": "nv-config-manager.nautobotchange",
            "device_change_stream": "nv-config-manager",
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

        # Reset moves the consumer past those 100 messages without deleting it.
        setup_consumer_reset(mock_conn, mock_js, backlog=100)

        response = client.delete("/v1/admin/consumers/device/reset")
        assert response.status_code == 200
        assert response.json()["status"] == "success"
        assert response.json()["skipped"] == 100

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
