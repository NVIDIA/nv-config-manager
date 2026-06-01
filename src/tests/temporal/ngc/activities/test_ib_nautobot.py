# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Tests for the IB context resolver activity."""

from __future__ import annotations

from configparser import ConfigParser
from typing import Any
from unittest.mock import patch

import pytest
from aioresponses import aioresponses
from temporalio.exceptions import ApplicationError

from nv_config_manager.temporal.common.secrets import clear_secrets_cache
from nv_config_manager.temporal.ngc.activities.ib_nautobot import (
    ResolveIBContextInput,
    _normalize_pkey,
    _select_pkey_match,
    resolve_ib_context,
)

NB_URL = "https://nautobot.example.com"
NB_GRAPHQL = f"{NB_URL}/api/graphql/"

DEVICE_NAME = "ufm-01"
DEVICE_IP = "10.0.0.1"
DEVICE_ID = "dev-1234"
LOCATION_ID = "loc-7890"
LOCATION_NAME = "test-site"
OVERLAY_ID = "ovl-aaaa"
OVERLAY_NAME = "ib-pkey-0x0100"
PKEY_ID = "pky-bbbb"


def _nb_config() -> ConfigParser:
    config = ConfigParser()
    config.add_section("nautobot")
    config.set("nautobot", "server", NB_URL)
    config.set("nautobot", "token", "test-token")
    config.set("nautobot", "verify", "false")
    return config


@pytest.fixture(autouse=True)
def reset_secrets_cache() -> Any:
    clear_secrets_cache()
    yield
    clear_secrets_cache()


@pytest.fixture()
def mock_nb_config() -> Any:
    with patch(
        "nv_config_manager.temporal.client.nautobot.load_config",
        return_value=_nb_config(),
    ):
        yield


def _device_payload(
    *,
    pkeys: list[dict[str, str]] | None = None,
    overlay_id: str = OVERLAY_ID,
    overlay_name: str = OVERLAY_NAME,
    device_id: str = DEVICE_ID,
) -> dict[str, Any]:
    return {
        "id": device_id,
        "name": DEVICE_NAME,
        "primary_ip4": {"host": DEVICE_IP},
        "location": {
            "id": LOCATION_ID,
            "name": LOCATION_NAME,
            "overlays": [
                {
                    "id": overlay_id,
                    "name": overlay_name,
                    "pkeys": pkeys if pkeys is not None else [{"id": PKEY_ID, "pkey": "0x0100"}],
                }
            ],
        },
    }


# ---------------------------------------------------------------------------
# _normalize_pkey -- pure helper
# ---------------------------------------------------------------------------


class TestNormalizePkey:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("0x100", "0x0100"),
            ("0x0100", "0x0100"),
            ("0X0100", "0x0100"),
            ("0xFFF", "0x0fff"),
            ("0x8001", "0x8001"),
            ("0x1", "0x0001"),
            ("0xfffe", "0xfffe"),
        ],
    )
    def test_canonicalizes_valid_forms(self, raw: str, expected: str) -> None:
        assert _normalize_pkey(raw) == expected

    @pytest.mark.parametrize(
        "bad",
        ["", "100", "0x", "0x12345", "0xZZZZ", "not-hex", "0x-1"],
    )
    def test_rejects_invalid(self, bad: str) -> None:
        with pytest.raises(ApplicationError, match="does not match required format"):
            _normalize_pkey(bad)


# ---------------------------------------------------------------------------
# _select_pkey_match -- pure helper
# ---------------------------------------------------------------------------


class TestSelectPkeyMatch:
    def test_finds_single_match(self) -> None:
        device = _device_payload()
        overlay, pkey_record = _select_pkey_match(device, "0x0100")
        assert overlay["id"] == OVERLAY_ID
        assert pkey_record["id"] == PKEY_ID

    def test_matches_across_pkey_format_variants(self) -> None:
        device = _device_payload(pkeys=[{"id": "p1", "pkey": "0x100"}])
        _, pkey_record = _select_pkey_match(device, "0x0100")
        assert pkey_record["id"] == "p1"

    def test_no_match_raises(self) -> None:
        device = _device_payload(pkeys=[{"id": "p1", "pkey": "0x8001"}])
        with pytest.raises(ApplicationError, match="not found at location"):
            _select_pkey_match(device, "0x0100")

    def test_ambiguous_match_raises(self) -> None:
        device = {
            "location": {
                "id": LOCATION_ID,
                "name": LOCATION_NAME,
                "overlays": [
                    {
                        "id": "ovl-a",
                        "name": "A",
                        "pkeys": [{"id": "p1", "pkey": "0x0100"}],
                    },
                    {
                        "id": "ovl-b",
                        "name": "B",
                        "pkeys": [{"id": "p2", "pkey": "0x100"}],
                    },
                ],
            },
        }
        with pytest.raises(ApplicationError, match="ambiguous at location"):
            _select_pkey_match(device, "0x0100")

    def test_ignores_malformed_pkey_in_data(self) -> None:
        device = _device_payload(
            pkeys=[{"id": "p1", "pkey": "junk"}, {"id": "p2", "pkey": "0x0100"}]
        )
        _, pkey_record = _select_pkey_match(device, "0x0100")
        assert pkey_record["id"] == "p2"

    def test_empty_overlays_raises_not_found(self) -> None:
        device = {"location": {"id": LOCATION_ID, "name": LOCATION_NAME, "overlays": []}}
        with pytest.raises(ApplicationError, match="not found at location"):
            _select_pkey_match(device, "0x0100")


# ---------------------------------------------------------------------------
# resolve_ib_context activity -- name path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestResolveIBContextByName:
    async def test_happy_path(self, mock_nb_config: Any) -> None:
        payload = {"data": {"devices": [_device_payload()]}}
        with aioresponses() as m:
            m.post(NB_GRAPHQL, payload=payload)
            result = await resolve_ib_context(ResolveIBContextInput(host=DEVICE_NAME, pkey="0x100"))
        assert result.ufm_device_id == DEVICE_ID
        assert result.ufm_device_name == DEVICE_NAME
        assert result.location_id == LOCATION_ID
        assert result.location_name == LOCATION_NAME
        assert result.overlay_id == OVERLAY_ID
        assert result.overlay_name == OVERLAY_NAME
        assert result.pkey_id == PKEY_ID
        assert result.pkey == "0x0100"
        assert result.ufm_device_primary_ip == DEVICE_IP

    async def test_device_not_found(self, mock_nb_config: Any) -> None:
        with aioresponses() as m:
            m.post(NB_GRAPHQL, payload={"data": {"devices": []}})
            with pytest.raises(ApplicationError, match="not found in Nautobot"):
                await resolve_ib_context(ResolveIBContextInput(host=DEVICE_NAME, pkey="0x0100"))

    async def test_multiple_devices_match(self, mock_nb_config: Any) -> None:
        payload = {
            "data": {
                "devices": [
                    _device_payload(),
                    _device_payload(device_id="dev-other"),
                ]
            }
        }
        with aioresponses() as m:
            m.post(NB_GRAPHQL, payload=payload)
            with pytest.raises(ApplicationError, match="Multiple UFM devices"):
                await resolve_ib_context(ResolveIBContextInput(host=DEVICE_NAME, pkey="0x0100"))

    async def test_invalid_pkey_raises_before_query(self, mock_nb_config: Any) -> None:
        with aioresponses() as m:
            m.post(NB_GRAPHQL, payload={"data": {"devices": []}})
            with pytest.raises(ApplicationError, match="does not match required format"):
                await resolve_ib_context(ResolveIBContextInput(host=DEVICE_NAME, pkey="bogus"))


# ---------------------------------------------------------------------------
# resolve_ib_context activity -- IP path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
class TestResolveIBContextByIP:
    async def test_happy_path(self, mock_nb_config: Any) -> None:
        payload = {
            "data": {
                "ip_addresses": [
                    {
                        "address": "10.0.0.1/32",
                        "interfaces": [{"device": _device_payload()}],
                    }
                ]
            }
        }
        with aioresponses() as m:
            m.post(NB_GRAPHQL, payload=payload)
            result = await resolve_ib_context(ResolveIBContextInput(host=DEVICE_IP, pkey="0x0100"))
        assert result.ufm_device_id == DEVICE_ID
        assert result.pkey == "0x0100"

    async def test_ip_not_assigned(self, mock_nb_config: Any) -> None:
        with aioresponses() as m:
            m.post(NB_GRAPHQL, payload={"data": {"ip_addresses": []}})
            with pytest.raises(ApplicationError, match="not found in Nautobot"):
                await resolve_ib_context(ResolveIBContextInput(host=DEVICE_IP, pkey="0x0100"))

    async def test_dedupes_same_device_on_multiple_interfaces(self, mock_nb_config: Any) -> None:
        # IP path can list multiple interfaces, all belonging to the same device.
        payload = {
            "data": {
                "ip_addresses": [
                    {
                        "address": "10.0.0.1/32",
                        "interfaces": [
                            {"device": _device_payload()},
                            {"device": _device_payload()},
                        ],
                    }
                ]
            }
        }
        with aioresponses() as m:
            m.post(NB_GRAPHQL, payload=payload)
            result = await resolve_ib_context(ResolveIBContextInput(host=DEVICE_IP, pkey="0x0100"))
        assert result.ufm_device_id == DEVICE_ID

    async def test_distinct_devices_share_ip_raises(self, mock_nb_config: Any) -> None:
        payload = {
            "data": {
                "ip_addresses": [
                    {
                        "address": "10.0.0.1/32",
                        "interfaces": [
                            {"device": _device_payload()},
                            {"device": _device_payload(device_id="dev-other")},
                        ],
                    }
                ]
            }
        }
        with aioresponses() as m:
            m.post(NB_GRAPHQL, payload=payload)
            with pytest.raises(ApplicationError, match="Multiple UFM devices"):
                await resolve_ib_context(ResolveIBContextInput(host=DEVICE_IP, pkey="0x0100"))
