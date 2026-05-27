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
"""Render tests for public reference templates."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
import yaml

from nv_config_manager_templates.filters import FilterException
from nv_config_manager_templates.filters.device import site_name
from nv_config_manager_templates.render import Renderer

RESOURCES_DIR = Path(__file__).resolve().parents[1] / "resources"
EXPECTED_CONFIG_DIR = RESOURCES_DIR / "expected_config"
NAUTOBOT_MOCK_DIR = RESOURCES_DIR / "nautobot"


def pytest_generate_tests(metafunc: pytest.Metafunc) -> None:
    """Generate render tests from expected_config/{device}/{firmware_version}/{entrypoint}."""
    if "expected_config" not in metafunc.fixturenames:
        return

    tests = []
    ids = []
    for device_dir in sorted(path for path in EXPECTED_CONFIG_DIR.iterdir() if path.is_dir()):
        nb_mock_path = NAUTOBOT_MOCK_DIR / f"{device_dir.name}.json"
        if not nb_mock_path.is_file():
            continue
        for version_dir in sorted(path for path in device_dir.iterdir() if path.is_dir()):
            for config_path in sorted(path for path in version_dir.iterdir() if path.is_file()):
                tests.append(
                    (nb_mock_path, version_dir.name, f"{config_path.name}.j2", config_path)
                )
                ids.append(f"{device_dir.name}/{version_dir.name}/{config_path.name}")

    metafunc.parametrize(
        "nautobot_input,firmware_version,entrypoint,expected_config", tests, ids=ids
    )


def test_rendered_config(
    nautobot_input: Path,
    firmware_version: str,
    entrypoint: str,
    expected_config: Path,
) -> None:
    """Test rendering a template using mock Nautobot data."""
    os.environ["NV_CONFIG_MANAGER_SKIP_VAULT"] = "1"

    with nautobot_input.open(encoding="utf-8") as f:
        nautobot_mock_data = json.load(f)

    nautobot_mock_data["data"]["device"]["config_context"]["intended-firmware"]["version"] = (
        firmware_version
    )

    location = site_name(nautobot_mock_data)
    with (NAUTOBOT_MOCK_DIR / f"{location}.json").open(encoding="utf-8") as f:
        location_mock_data = json.load(f)

    expected_output = expected_config.read_text(encoding="utf-8")

    renderer = Renderer("test", "test")
    template = next(
        template
        for template in renderer.list_entrypoints(nautobot_mock_data)
        if template.endswith(f"/{entrypoint}")
    )

    output = renderer.render(template, nautobot_mock_data, location_mock_data)

    if template.endswith(".yaml.j2"):
        try:
            yaml.safe_load(output)
        except yaml.scanner.ScannerError as exc:
            pytest.fail(f"Rendered configuration did not produce valid YAML: {exc}")

    assert output.rstrip() == expected_output.rstrip()


def test_missing_site_aggregate_fails_edge_render() -> None:
    """Edge templates must fail when the required Site-Aggregate prefix is missing."""
    os.environ["NV_CONFIG_MANAGER_SKIP_VAULT"] = "1"

    with (NAUTOBOT_MOCK_DIR / "a09-u28-p01-bleaf-01.json").open(encoding="utf-8") as f:
        nautobot_mock_data = json.load(f)
    nautobot_mock_data["data"]["device"]["config_context"]["intended-firmware"]["version"] = (
        "5.16.1"
    )

    with (NAUTOBOT_MOCK_DIR / "TEST-SITE.json").open(encoding="utf-8") as f:
        location_mock_data = json.load(f)
    location_mock_data["data"]["prefixes"] = []

    renderer = Renderer("test", "test")
    template = next(
        template
        for template in renderer.list_entrypoints(nautobot_mock_data)
        if template.endswith("/startup.yaml.j2")
    )

    with pytest.raises(FilterException, match="Found no aggregates in role 'Site-Aggregate'"):
        renderer.render(template, nautobot_mock_data, location_mock_data)
