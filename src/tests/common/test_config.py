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
"""Tests for nv_config_manager.common.config module."""

import os
from configparser import ConfigParser
from unittest.mock import patch

from nv_config_manager.common.config import _read_spiffe_jwt, get_internal_auth_headers


def _config_with_spiffe_path(jwt_path: str) -> ConfigParser:
    """Return a ConfigParser with [auth.spiffe] jwt_svid_path set."""
    cp = ConfigParser()
    cp.add_section("auth.spiffe")
    cp.set("auth.spiffe", "jwt_svid_path", jwt_path)
    return cp


class TestGetInternalAuthHeaders:
    """Tests for get_internal_auth_headers function."""

    def test_explicit_service_name(self):
        """Test with explicitly provided service name."""
        with patch("nv_config_manager.common.config.load_config", return_value=ConfigParser()):
            headers = get_internal_auth_headers(service_name="my-service")
        assert headers == {
            "X-Auth-Request-Email": "my-service",
            "X-Auth-Request-User": "my-service",
            "X-Auth-Request-Groups": "nv-config-manager",
        }

    def test_custom_group(self):
        """Test with custom group."""
        with patch("nv_config_manager.common.config.load_config", return_value=ConfigParser()):
            headers = get_internal_auth_headers(service_name="my-service", group="admin")
        assert headers == {
            "X-Auth-Request-Email": "my-service",
            "X-Auth-Request-User": "my-service",
            "X-Auth-Request-Groups": "admin",
        }

    def test_fallback_to_hostname(self):
        """Test fallback to HOSTNAME environment variable."""
        with (
            patch.dict(os.environ, {"HOSTNAME": "nv-config-manager-render-api-5f8d9c7b6-abc12"}),
            patch("nv_config_manager.common.config.load_config", return_value=ConfigParser()),
        ):
            headers = get_internal_auth_headers()
            assert headers["X-Auth-Request-Email"] == "nv-config-manager-render-api-5f8d9c7b6-abc12"
            assert headers["X-Auth-Request-User"] == "nv-config-manager-render-api-5f8d9c7b6-abc12"
            assert headers["X-Auth-Request-Groups"] == "nv-config-manager"

    def test_fallback_to_default(self):
        """Test fallback when HOSTNAME is not set."""
        env = {k: v for k, v in os.environ.items() if k != "HOSTNAME"}
        with (
            patch.dict(os.environ, env, clear=True),
            patch("nv_config_manager.common.config.load_config", return_value=ConfigParser()),
        ):
            headers = get_internal_auth_headers()
            assert headers["X-Auth-Request-Email"] == "internal-service"
            assert headers["X-Auth-Request-User"] == "internal-service"
            assert headers["X-Auth-Request-Groups"] == "nv-config-manager"

    def test_explicit_overrides_hostname(self):
        """Test that explicit service_name overrides HOSTNAME."""
        with (
            patch.dict(os.environ, {"HOSTNAME": "nv-config-manager-ztp-abc123-xyz99"}),
            patch("nv_config_manager.common.config.load_config", return_value=ConfigParser()),
        ):
            headers = get_internal_auth_headers(service_name="explicit-service")
            assert headers["X-Auth-Request-Email"] == "explicit-service"


class TestSpiffeJwtAuth:
    """Tests for SPIFFE JWT-SVID auth in get_internal_auth_headers."""

    def test_spiffe_jwt_returns_bearer_header(self, tmp_path):
        """When [auth.spiffe] jwt_svid_path points to a valid JWT file, return Bearer header."""
        jwt_file = tmp_path / "jwt-svid"
        jwt_file.write_text("eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test.sig")

        cp = _config_with_spiffe_path(str(jwt_file))
        with patch("nv_config_manager.common.config.load_config", return_value=cp):
            headers = get_internal_auth_headers()

        assert headers == {
            "Authorization": "Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.test.sig",
        }

    def test_spiffe_jwt_takes_precedence_over_service_name(self, tmp_path):
        """SPIFFE JWT should be used even when service_name is provided."""
        jwt_file = tmp_path / "jwt-svid"
        jwt_file.write_text("eyJ0b2tlbi5zcGlmZmU")

        cp = _config_with_spiffe_path(str(jwt_file))
        with patch("nv_config_manager.common.config.load_config", return_value=cp):
            headers = get_internal_auth_headers(service_name="my-service")

        assert "Authorization" in headers
        assert "X-Auth-Request-Email" not in headers

    def test_spiffe_jwt_empty_file_falls_back(self, tmp_path):
        """An empty JWT file should fall back to X-Auth-Request-* headers."""
        jwt_file = tmp_path / "jwt-svid"
        jwt_file.write_text("")

        cp = _config_with_spiffe_path(str(jwt_file))
        with patch("nv_config_manager.common.config.load_config", return_value=cp):
            headers = get_internal_auth_headers(service_name="my-service")

        assert "X-Auth-Request-Email" in headers
        assert "Authorization" not in headers

    def test_spiffe_jwt_whitespace_only_falls_back(self, tmp_path):
        """A whitespace-only JWT file should fall back."""
        jwt_file = tmp_path / "jwt-svid"
        jwt_file.write_text("   \n  ")

        cp = _config_with_spiffe_path(str(jwt_file))
        with patch("nv_config_manager.common.config.load_config", return_value=cp):
            headers = get_internal_auth_headers(service_name="my-service")

        assert "X-Auth-Request-Email" in headers
        assert "Authorization" not in headers

    def test_spiffe_jwt_missing_file_falls_back(self, tmp_path):
        """A missing JWT file should fall back gracefully."""
        missing_path = str(tmp_path / "nonexistent" / "jwt-svid")

        cp = _config_with_spiffe_path(missing_path)
        with patch("nv_config_manager.common.config.load_config", return_value=cp):
            headers = get_internal_auth_headers(service_name="my-service")

        assert "X-Auth-Request-Email" in headers
        assert "Authorization" not in headers

    def test_spiffe_jwt_not_configured_falls_back(self):
        """When [auth.spiffe] jwt_svid_path is missing, fall back to X-Auth-Request-*."""
        with patch("nv_config_manager.common.config.load_config", return_value=ConfigParser()):
            headers = get_internal_auth_headers(service_name="my-service")

        assert "X-Auth-Request-Email" in headers
        assert "Authorization" not in headers

    def test_spiffe_jwt_refreshed_per_call(self, tmp_path):
        """Each call should re-read the file to pick up rotated tokens."""
        jwt_file = tmp_path / "jwt-svid"
        jwt_file.write_text("token-v1")

        cp = _config_with_spiffe_path(str(jwt_file))
        with patch("nv_config_manager.common.config.load_config", return_value=cp):
            h1 = get_internal_auth_headers()
            assert h1["Authorization"] == "Bearer token-v1"

            jwt_file.write_text("token-v2")
            h2 = get_internal_auth_headers()
            assert h2["Authorization"] == "Bearer token-v2"

    def test_read_spiffe_jwt_strips_whitespace(self, tmp_path):
        """_read_spiffe_jwt should strip leading/trailing whitespace and newlines."""
        jwt_file = tmp_path / "jwt-svid"
        jwt_file.write_text("  eyJhbGciOiJSUzI1NiJ9.payload.sig  \n")

        cp = _config_with_spiffe_path(str(jwt_file))
        with patch("nv_config_manager.common.config.load_config", return_value=cp):
            token = _read_spiffe_jwt()

        assert token == "eyJhbGciOiJSUzI1NiJ9.payload.sig"

    def test_read_spiffe_jwt_returns_none_when_unset(self):
        """_read_spiffe_jwt returns None when no section is configured."""
        with patch("nv_config_manager.common.config.load_config", return_value=ConfigParser()):
            assert _read_spiffe_jwt() is None
