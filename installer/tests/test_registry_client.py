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
"""Tests for nv_config_manager_installer.registry_client -- Docker V2 tag listing."""

from __future__ import annotations

import requests as _requests
import responses

from nv_config_manager_installer.registry_client import _tag_sort_key, list_tags


class TestTagSorting:
    """Verify semver-aware sorting: releases > pre-releases > other."""

    def test_releases_before_prerelease(self):
        tags = ["v1.2.1-rc1", "v1.2.1", "v1.2.0"]
        result = sorted(tags, key=_tag_sort_key)
        assert result == ["v1.2.1", "v1.2.0", "v1.2.1-rc1"]

    def test_higher_version_first(self):
        tags = ["v1.0.0", "v2.0.0", "v1.5.0"]
        result = sorted(tags, key=_tag_sort_key)
        assert result == ["v2.0.0", "v1.5.0", "v1.0.0"]

    def test_rc_ordering(self):
        tags = ["v1.2.1-rc1", "v1.2.1-rc100", "v1.2.2-rc1"]
        result = sorted(tags, key=_tag_sort_key)
        assert result == ["v1.2.2-rc1", "v1.2.1-rc100", "v1.2.1-rc1"]

    def test_full_realistic_sort(self):
        tags = [
            "ffc7e707",
            "latest",
            "v1.2.1-rc1",
            "v1.2.2-rc1",
            "v1.2.1",
            "ffc7e707-arm64",
            "v1.2.0",
        ]
        result = sorted(
            [t for t in tags if not t.endswith(("-arm64", "-amd64"))],
            key=_tag_sort_key,
        )
        assert result[0] == "v1.2.1"
        assert result[1] == "v1.2.0"
        assert result[2] == "v1.2.2-rc1"
        assert result[3] == "v1.2.1-rc1"
        assert "latest" in result
        assert "ffc7e707" in result

    def test_latest_after_semver(self):
        tags = ["latest", "v1.0.0"]
        result = sorted(tags, key=_tag_sort_key)
        assert result == ["v1.0.0", "latest"]

    def test_commit_hashes_at_end(self):
        tags = ["v1.0.0", "abc123", "def456"]
        result = sorted(tags, key=_tag_sort_key)
        assert result[0] == "v1.0.0"

    def test_no_v_prefix(self):
        tags = ["1.2.3", "1.2.4-rc2", "1.2.4"]
        result = sorted(tags, key=_tag_sort_key)
        assert result == ["1.2.4", "1.2.3", "1.2.4-rc2"]


class TestListTags:
    @responses.activate
    def test_successful_tag_listing_sorted(self):
        responses.get(
            "https://nvcr.io/v2/nvidian/cfa/nv-config-manager/tags/list",
            json={"tags": ["abc123", "v1.0.0", "v2.0.0", "v1.5.0-rc1", "latest"]},
        )
        tags, error = list_tags("nvcr.io/nvidian/cfa", "nv-config-manager")
        assert error == ""
        assert tags[0] == "v2.0.0"
        assert tags[1] == "v1.0.0"
        assert tags[2] == "v1.5.0-rc1"

    @responses.activate
    def test_arch_tags_filtered_out(self):
        responses.get(
            "https://nvcr.io/v2/nvidian/cfa/nv-config-manager/tags/list",
            json={"tags": ["v1.0.0", "v1.0.0-arm64", "v1.0.0-amd64", "abc-arm64", "abc"]},
        )
        tags, error = list_tags("nvcr.io/nvidian/cfa", "nv-config-manager")
        assert error == ""
        assert "v1.0.0-arm64" not in tags
        assert "v1.0.0-amd64" not in tags
        assert "abc-arm64" not in tags
        assert "v1.0.0" in tags
        assert "abc" in tags

    @responses.activate
    def test_auth_failure_no_bearer(self):
        responses.get(
            "https://nvcr.io/v2/nvidian/cfa/nv-config-manager/tags/list",
            status=401,
        )
        tags, error = list_tags(
            "nvcr.io/nvidian/cfa", "nv-config-manager", "$oauthtoken", "bad-key"
        )
        assert tags == []
        assert "Authentication failed" in error

    @responses.activate
    def test_bearer_token_flow(self):
        """Simulate the full bearer-token auth flow (401 → token → retry)."""
        responses.get(
            "https://nvcr.io/v2/nvidian/cfa/nv-config-manager/tags/list",
            status=401,
            headers={
                "Www-Authenticate": (
                    'Bearer realm="https://nvcr.io/proxy_auth",'
                    'service="nvcr.io",'
                    'scope="repository:nvidian/cfa/nv-config-manager:pull"'
                )
            },
        )
        responses.get(
            "https://nvcr.io/proxy_auth",
            json={"token": "my-bearer-token"},
        )
        responses.get(
            "https://nvcr.io/v2/nvidian/cfa/nv-config-manager/tags/list",
            json={"tags": ["v2.0.0", "v1.5.0", "v1.0.0"]},
        )

        tags, error = list_tags(
            "nvcr.io/nvidian/cfa", "nv-config-manager", "$oauthtoken", "my-ngc-key"
        )
        assert error == ""
        assert tags == ["v2.0.0", "v1.5.0", "v1.0.0"]

        assert len(responses.calls) == 3
        assert responses.calls[2].request.headers["Authorization"] == "Bearer my-bearer-token"

    @responses.activate
    def test_bearer_token_fetch_fails(self):
        """When the token endpoint itself fails, return auth error."""
        responses.get(
            "https://nvcr.io/v2/nvidian/cfa/nv-config-manager/tags/list",
            status=401,
            headers={
                "Www-Authenticate": (
                    'Bearer realm="https://nvcr.io/proxy_auth",'
                    'scope="repository:nvidian/cfa/nv-config-manager:pull"'
                )
            },
        )
        responses.get(
            "https://nvcr.io/proxy_auth",
            body=_requests.ConnectionError("connection reset"),
        )

        tags, error = list_tags(
            "nvcr.io/nvidian/cfa", "nv-config-manager", "$oauthtoken", "bad-key"
        )
        assert tags == []
        assert "bearer token" in error.lower()

    @responses.activate
    def test_bearer_token_with_access_token_field(self):
        """Some registries return 'access_token' instead of 'token'."""
        responses.get(
            "https://host/v2/repo/tags/list",
            status=401,
            headers={"Www-Authenticate": 'Bearer realm="https://host/auth"'},
        )
        responses.get("https://host/auth", json={"access_token": "alt-token"})
        responses.get("https://host/v2/repo/tags/list", json={"tags": ["latest"]})

        tags, error = list_tags("host", "repo", "user", "pass")
        assert error == ""
        assert tags == ["latest"]

    @responses.activate
    def test_repo_not_found(self):
        responses.get(
            "https://nvcr.io/v2/nvidian/cfa/missing/tags/list",
            status=404,
        )
        tags, error = list_tags("nvcr.io/nvidian/cfa", "missing")
        assert tags == []
        assert "not found" in error

    @responses.activate
    def test_network_error(self):
        responses.get(
            "https://unreachable.io/v2/nv-config-manager/tags/list",
            body=_requests.ConnectionError("Connection refused"),
        )
        tags, error = list_tags("unreachable.io", "nv-config-manager")
        assert tags == []
        assert "Cannot reach" in error

    @responses.activate
    def test_empty_tags(self):
        responses.get("https://registry.io/v2/nv-config-manager/tags/list", json={"tags": []})
        tags, error = list_tags("registry.io", "nv-config-manager")
        assert tags == []
        assert error == ""

    @responses.activate
    def test_null_tags(self):
        responses.get("https://registry.io/v2/nv-config-manager/tags/list", json={"tags": None})
        tags, error = list_tags("registry.io", "nv-config-manager")
        assert tags == []
        assert error == ""

    @responses.activate
    def test_simple_registry_no_path_prefix(self):
        responses.get(
            "https://registry.example.com/v2/nv-config-manager/tags/list", json={"tags": ["latest"]}
        )
        tags, error = list_tags("registry.example.com", "nv-config-manager")
        assert tags == ["latest"]
        assert error == ""
        assert (
            responses.calls[0].request.url
            == "https://registry.example.com/v2/nv-config-manager/tags/list"
        )

    @responses.activate
    def test_auth_header_sent_on_first_request(self):
        responses.get(
            "https://nvcr.io/v2/nvidian/cfa/nv-config-manager/tags/list", json={"tags": ["v1"]}
        )
        list_tags("nvcr.io/nvidian/cfa", "nv-config-manager", "$oauthtoken", "my-key")
        assert "Authorization" in responses.calls[0].request.headers
        assert responses.calls[0].request.headers["Authorization"].startswith("Basic ")

    @responses.activate
    def test_no_auth_header_when_no_credentials(self):
        responses.get("https://registry.io/v2/nv-config-manager/tags/list", json={"tags": ["v1"]})
        list_tags("registry.io", "nv-config-manager")
        assert "Authorization" not in responses.calls[0].request.headers
