# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0
"""Tests for shared operator version manifest loading."""

from __future__ import annotations

import pytest

from nv_config_manager_installer.operator_versions import (
    find_operator_versions_file,
    load_operator_versions,
    parse_operator_versions,
)

_VERSIONS = """\
GATEWAY_API_VERSION=v1.4.1
ENVOY_GATEWAY_VERSION=v1.6.5
CERT_MANAGER_VERSION=v1.20.2
CNPG_OPERATOR_VERSION=0.28.0
INGRESS_NGINX_VERSION=4.15.1
PROMETHEUS_CRD_VERSION=v0.90.1
PROMETHEUS_OPERATOR_VERSION=84.5.0
"""


def test_parse_operator_versions() -> None:
    versions = parse_operator_versions(_VERSIONS)

    assert versions.gateway_api_version == "v1.4.1"
    assert versions.envoy_gateway_version == "v1.6.5"
    assert versions.cert_manager_version == "v1.20.2"
    assert versions.cnpg_operator_version == "0.28.0"
    assert versions.prometheus_crd_version == "v0.90.1"


def test_parse_operator_versions_requires_all_keys() -> None:
    with pytest.raises(ValueError, match="CERT_MANAGER_VERSION"):
        parse_operator_versions("GATEWAY_API_VERSION=v1.4.1\n")


def test_find_operator_versions_from_chart_dir(tmp_path) -> None:
    root = tmp_path / "bundle"
    chart_dir = root / "helm"
    chart_dir.mkdir(parents=True)
    manifest = root / "operator-versions.env"
    manifest.write_text(_VERSIONS)

    assert find_operator_versions_file(chart_dir) == manifest
    assert load_operator_versions(chart_dir).cert_manager_version == "v1.20.2"
