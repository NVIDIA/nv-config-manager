# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
"""Tests for the mock UFM server.

Covers happy paths, error paths, and the dev helpers. Each test gets a fresh
app+store so the in-memory state does not leak between tests.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from mock_server import _Store, create_app


@pytest.fixture()
def client() -> TestClient:
    """Yield a TestClient bound to a fresh store per test."""
    app = create_app(_Store())
    return TestClient(app)


class TestHealthcheck:
    def test_returns_ok(self, client: TestClient) -> None:
        response = client.get("/healthcheck")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestListPKeys:
    def test_empty_by_default(self, client: TestClient) -> None:
        response = client.get("/ufmRest/resources/pkeys")
        assert response.status_code == 200
        assert response.json() == {}

    def test_returns_dict_keyed_by_pkey(self, client: TestClient) -> None:
        client.post(
            "/ufmRest/resources/pkeys/add",
            json={"pkey": "0x0001", "ip_over_ib": True},
        )
        client.post(
            "/ufmRest/resources/pkeys/add",
            json={"pkey": "0x0002", "ip_over_ib": False},
        )

        response = client.get("/ufmRest/resources/pkeys")
        body = response.json()
        assert set(body.keys()) == {"0x0001", "0x0002"}
        assert body["0x0001"]["ip_over_ib"] is True
        assert body["0x0002"]["ip_over_ib"] is False


class TestCreatePKey:
    def test_creates_pkey(self, client: TestClient) -> None:
        response = client.post(
            "/ufmRest/resources/pkeys/add",
            json={"pkey": "0x0042", "ip_over_ib": True},
        )
        assert response.status_code == 200
        assert response.json() == {"pkey": "0x0042", "status": "created"}

    def test_index0_round_trips(self, client: TestClient) -> None:
        client.post(
            "/ufmRest/resources/pkeys/add",
            json={"pkey": "0x0001", "ip_over_ib": True, "index0": False},
        )
        client.post(
            "/ufmRest/resources/pkeys/add",
            json={"pkey": "0x0002", "ip_over_ib": True},  # default index0=True
        )

        body = client.get("/ufmRest/resources/pkeys").json()
        assert body["0x0001"]["index0"] is False
        assert body["0x0002"]["index0"] is True

    def test_409_on_duplicate(self, client: TestClient) -> None:
        client.post(
            "/ufmRest/resources/pkeys/add",
            json={"pkey": "0x0042", "ip_over_ib": True},
        )
        response = client.post(
            "/ufmRest/resources/pkeys/add",
            json={"pkey": "0x0042", "ip_over_ib": True},
        )
        assert response.status_code == 409


class TestGetPKey:
    def test_404_for_unknown(self, client: TestClient) -> None:
        response = client.get("/ufmRest/resources/pkeys/0xdead")
        assert response.status_code == 404

    def test_summary_without_guids_data(self, client: TestClient) -> None:
        client.post(
            "/ufmRest/resources/pkeys/add",
            json={"pkey": "0x0001", "ip_over_ib": True},
        )

        response = client.get("/ufmRest/resources/pkeys/0x0001")
        body = response.json()
        assert body["partition"] == "ib-pkey-0x0001"
        assert body["ip_over_ib"] is True
        assert "guids" not in body

    def test_detail_with_guids_data(self, client: TestClient) -> None:
        client.post(
            "/ufmRest/resources/pkeys/add",
            json={"pkey": "0x0001", "ip_over_ib": True},
        )
        client.post(
            "/ufmRest/resources/pkeys/",
            json={
                "pkey": "0x0001",
                "guids": ["0xAAA", "0xBBB"],
                "membership": "full",
            },
        )

        response = client.get("/ufmRest/resources/pkeys/0x0001?guids_data=true")
        body = response.json()
        assert {entry["guid"] for entry in body["guids"]} == {"0xaaa", "0xbbb"}
        assert all(entry["membership"] == "full" for entry in body["guids"])


class TestAddMembers:
    def test_adds_lowercased_guids(self, client: TestClient) -> None:
        client.post(
            "/ufmRest/resources/pkeys/add",
            json={"pkey": "0x0001", "ip_over_ib": True},
        )
        response = client.post(
            "/ufmRest/resources/pkeys/",
            json={"pkey": "0x0001", "guids": ["0xABC", "0xDEF"]},
        )
        assert response.status_code == 200
        assert response.json() == {"pkey": "0x0001", "added": 2}

        state = client.get("/ufmRest/resources/pkeys/0x0001?guids_data=true").json()
        assert {entry["guid"] for entry in state["guids"]} == {"0xabc", "0xdef"}

    def test_idempotent_on_duplicate_guid(self, client: TestClient) -> None:
        client.post(
            "/ufmRest/resources/pkeys/add",
            json={"pkey": "0x0001", "ip_over_ib": True},
        )
        client.post(
            "/ufmRest/resources/pkeys/",
            json={"pkey": "0x0001", "guids": ["0xabc"]},
        )

        response = client.post(
            "/ufmRest/resources/pkeys/",
            json={"pkey": "0x0001", "guids": ["0xabc"]},
        )
        assert response.json() == {"pkey": "0x0001", "added": 0}

    def test_404_when_pkey_missing(self, client: TestClient) -> None:
        response = client.post(
            "/ufmRest/resources/pkeys/",
            json={"pkey": "0xnope", "guids": ["0xabc"]},
        )
        assert response.status_code == 404

    def test_grouped_single_membership_posts_assign_per_guid(self, client: TestClient) -> None:
        """Two single-membership POSTs assign per-GUID membership."""
        client.post(
            "/ufmRest/resources/pkeys/add",
            json={"pkey": "0x0001", "ip_over_ib": True},
        )
        client.post(
            "/ufmRest/resources/pkeys/",
            json={"pkey": "0x0001", "guids": ["0xa"], "membership": "full"},
        )
        client.post(
            "/ufmRest/resources/pkeys/",
            json={"pkey": "0x0001", "guids": ["0xb"], "membership": "limited"},
        )

        state = client.get("/ufmRest/resources/pkeys/0x0001?guids_data=true").json()
        by_guid = {e["guid"]: e["membership"] for e in state["guids"]}
        assert by_guid == {"0xa": "full", "0xb": "limited"}

    def test_single_membership_applies_to_all(self, client: TestClient) -> None:
        """A single `membership` string applies to every GUID."""
        client.post(
            "/ufmRest/resources/pkeys/add",
            json={"pkey": "0x0001", "ip_over_ib": True},
        )
        response = client.post(
            "/ufmRest/resources/pkeys/",
            json={"pkey": "0x0001", "guids": ["0xa", "0xb"], "membership": "limited"},
        )
        assert response.status_code == 200

        state = client.get("/ufmRest/resources/pkeys/0x0001?guids_data=true").json()
        by_guid = {e["guid"]: e["membership"] for e in state["guids"]}
        assert by_guid == {"0xa": "limited", "0xb": "limited"}

    def test_plural_memberships_key_is_ignored(self, client: TestClient) -> None:
        """POST ignores the plural `memberships` and members default to "full".

        Pins the mock to real UFM 6.19.x: the Add endpoint honors only a single
        `membership` string and silently drops a plural `memberships` array. Keeping
        the mock faithful to this quirk means integration tests that touch POST can't
        pass against a mock that is quietly more forgiving than production.
        """
        client.post(
            "/ufmRest/resources/pkeys/add",
            json={"pkey": "0x0001", "ip_over_ib": True},
        )
        response = client.post(
            "/ufmRest/resources/pkeys/",
            json={"pkey": "0x0001", "guids": ["0xa"], "memberships": ["limited"]},
        )
        assert response.status_code == 200

        state = client.get("/ufmRest/resources/pkeys/0x0001?guids_data=true").json()
        assert {e["guid"]: e["membership"] for e in state["guids"]} == {"0xa": "full"}


class TestRemoveMembers:
    def test_removes_guids_by_csv(self, client: TestClient) -> None:
        client.post(
            "/ufmRest/resources/pkeys/add",
            json={"pkey": "0x0001", "ip_over_ib": True},
        )
        client.post(
            "/ufmRest/resources/pkeys/",
            json={"pkey": "0x0001", "guids": ["0xa", "0xb", "0xc"]},
        )

        response = client.delete("/ufmRest/resources/pkeys/0x0001/guids/0xa,0xb")
        assert response.status_code == 200
        assert response.json() == {"pkey": "0x0001", "removed": 2, "pkey_removed": False}

        remaining = client.get("/ufmRest/resources/pkeys/0x0001?guids_data=true").json()
        assert {entry["guid"] for entry in remaining["guids"]} == {"0xc"}

    def test_remove_missing_guid_is_no_op(self, client: TestClient) -> None:
        client.post(
            "/ufmRest/resources/pkeys/add",
            json={"pkey": "0x0001", "ip_over_ib": True},
        )

        response = client.delete("/ufmRest/resources/pkeys/0x0001/guids/0xghost")
        assert response.status_code == 200
        assert response.json() == {"pkey": "0x0001", "removed": 0, "pkey_removed": False}
        # An already-empty partition is left intact (no removal occurred).
        assert client.get("/ufmRest/resources/pkeys/0x0001").status_code == 200

    def test_removing_last_member_deletes_partition(self, client: TestClient) -> None:
        """UFM auto-removes a PKey once its final member is removed."""
        client.post(
            "/ufmRest/resources/pkeys/add",
            json={"pkey": "0x0001", "ip_over_ib": True},
        )
        client.post(
            "/ufmRest/resources/pkeys/",
            json={"pkey": "0x0001", "guids": ["0xa", "0xb"]},
        )

        # Removing one of two members keeps the partition.
        first = client.delete("/ufmRest/resources/pkeys/0x0001/guids/0xa")
        assert first.json() == {"pkey": "0x0001", "removed": 1, "pkey_removed": False}
        assert client.get("/ufmRest/resources/pkeys/0x0001").status_code == 200

        # Removing the last member deletes the partition.
        last = client.delete("/ufmRest/resources/pkeys/0x0001/guids/0xb")
        assert last.json() == {"pkey": "0x0001", "removed": 1, "pkey_removed": True}
        assert client.get("/ufmRest/resources/pkeys/0x0001").status_code == 404
        assert client.get("/ufmRest/resources/pkeys").json() == {}

    def test_404_when_pkey_missing(self, client: TestClient) -> None:
        response = client.delete("/ufmRest/resources/pkeys/0xnope/guids/0xa")
        assert response.status_code == 404


class TestSetMembers:
    def test_overwrites_membership_atomically(self, client: TestClient) -> None:
        """PUT replaces the entire member list, dropping members not listed."""
        client.post(
            "/ufmRest/resources/pkeys/add",
            json={"pkey": "0x0001", "ip_over_ib": True},
        )
        client.post(
            "/ufmRest/resources/pkeys/",
            json={"pkey": "0x0001", "guids": ["0xa", "0xb"]},
        )

        response = client.put(
            "/ufmRest/resources/pkeys/",
            json={"pkey": "0x0001", "guids": ["0xb", "0xc"]},
        )
        assert response.status_code == 200
        assert response.json() == {"pkey": "0x0001", "guids_set": 2}

        state = client.get("/ufmRest/resources/pkeys/0x0001?guids_data=true").json()
        assert {entry["guid"] for entry in state["guids"]} == {"0xb", "0xc"}

    def test_creates_partition_when_missing(self, client: TestClient) -> None:
        """PUT creates the partition on the fly, mirroring UFM create-on-missing."""
        response = client.put(
            "/ufmRest/resources/pkeys/",
            json={"pkey": "0x0009", "guids": ["0xABC"], "ip_over_ib": False},
        )
        assert response.status_code == 200
        assert response.json() == {"pkey": "0x0009", "guids_set": 1}

        body = client.get("/ufmRest/resources/pkeys/0x0009?guids_data=true").json()
        assert {entry["guid"] for entry in body["guids"]} == {"0xabc"}
        assert body["ip_over_ib"] is False

    def test_refreshes_flags_on_existing_partition(self, client: TestClient) -> None:
        """PUT overwrites partition flags too, not just members, when it exists."""
        client.put(
            "/ufmRest/resources/pkeys/",
            json={"pkey": "0x0001", "guids": ["0xa"], "ip_over_ib": True, "index0": True},
        )
        client.put(
            "/ufmRest/resources/pkeys/",
            json={"pkey": "0x0001", "guids": ["0xa"], "ip_over_ib": False, "index0": False},
        )

        body = client.get("/ufmRest/resources/pkeys/0x0001?guids_data=true").json()
        assert body["ip_over_ib"] is False
        assert body["index0"] is False

    def test_unchanged_member_preserved(self, client: TestClient) -> None:
        """Re-setting a superset leaves the existing member's record intact."""
        client.put(
            "/ufmRest/resources/pkeys/",
            json={"pkey": "0x0001", "guids": ["0xa"], "membership": "full"},
        )
        client.put(
            "/ufmRest/resources/pkeys/",
            json={"pkey": "0x0001", "guids": ["0xa", "0xb"], "membership": "full"},
        )

        state = client.get("/ufmRest/resources/pkeys/0x0001?guids_data=true").json()
        by_guid = {entry["guid"]: entry for entry in state["guids"]}
        assert set(by_guid) == {"0xa", "0xb"}
        assert by_guid["0xa"] == {"guid": "0xa", "membership": "full"}
        assert by_guid["0xb"]["membership"] == "full"

    def test_put_per_guid_memberships_list(self, client: TestClient) -> None:
        """PUT honors the index-aligned plural `memberships` for an atomic set."""
        response = client.put(
            "/ufmRest/resources/pkeys/",
            json={
                "pkey": "0x0001",
                "guids": ["0xa", "0xb"],
                "memberships": ["limited", "full"],
            },
        )
        assert response.status_code == 200

        state = client.get("/ufmRest/resources/pkeys/0x0001?guids_data=true").json()
        by_guid = {e["guid"]: e["membership"] for e in state["guids"]}
        assert by_guid == {"0xa": "limited", "0xb": "full"}

    def test_put_memberships_length_mismatch_rejected(self, client: TestClient) -> None:
        """A plural `memberships` whose length differs from `guids` is rejected."""
        response = client.put(
            "/ufmRest/resources/pkeys/",
            json={"pkey": "0x0001", "guids": ["0xa", "0xb"], "memberships": ["full"]},
        )
        assert response.status_code == 400


class TestDevHelpers:
    def test_reset_clears_state(self, client: TestClient) -> None:
        client.post(
            "/ufmRest/resources/pkeys/add",
            json={"pkey": "0x0001", "ip_over_ib": True},
        )

        assert client.get("/ufmRest/resources/pkeys").json() != {}

        response = client.post("/_dev/reset")
        assert response.status_code == 200
        assert response.json() == {"status": "reset"}
        assert client.get("/ufmRest/resources/pkeys").json() == {}

    def test_state_dump_reflects_full_detail(self, client: TestClient) -> None:
        client.post(
            "/ufmRest/resources/pkeys/add",
            json={"pkey": "0x0001", "ip_over_ib": True},
        )
        client.post(
            "/ufmRest/resources/pkeys/",
            json={"pkey": "0x0001", "guids": ["0xabc"]},
        )

        state = client.get("/_dev/state").json()
        assert "0x0001" in state
        assert state["0x0001"]["guids"] == [{"guid": "0xabc", "membership": "full"}]
