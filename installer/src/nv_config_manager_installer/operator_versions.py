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
"""Shared operator/dependency version pins for installer-managed prerequisites."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

_MANIFEST_NAME = "operator-versions.env"


@dataclass(frozen=True)
class OperatorVersions:
    """Versions used for prerequisite operator installs and airgap bundling."""

    gateway_api_version: str
    envoy_gateway_version: str
    cert_manager_version: str
    cnpg_operator_version: str
    ingress_nginx_version: str
    prometheus_crd_version: str
    prometheus_operator_version: str

    env_keys: ClassVar[dict[str, str]] = {
        "GATEWAY_API_VERSION": "gateway_api_version",
        "ENVOY_GATEWAY_VERSION": "envoy_gateway_version",
        "CERT_MANAGER_VERSION": "cert_manager_version",
        "CNPG_OPERATOR_VERSION": "cnpg_operator_version",
        "INGRESS_NGINX_VERSION": "ingress_nginx_version",
        "PROMETHEUS_CRD_VERSION": "prometheus_crd_version",
        "PROMETHEUS_OPERATOR_VERSION": "prometheus_operator_version",
    }

    @classmethod
    def from_mapping(cls, data: dict[str, str]) -> OperatorVersions:
        """Build versions from parsed env-file data, validating required keys."""
        missing = [key for key in cls.env_keys if not data.get(key)]
        if missing:
            missing_text = ", ".join(sorted(missing))
            raise ValueError(f"Missing operator version pin(s): {missing_text}")
        kwargs = {field: data[key] for key, field in cls.env_keys.items()}
        return cls(**kwargs)


def parse_operator_versions(text: str) -> OperatorVersions:
    """Parse an operator-versions.env style manifest."""
    values: dict[str, str] = {}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return OperatorVersions.from_mapping(values)


def find_operator_versions_file(start: Path | str | None = None) -> Path | None:
    """Find the shared operator version manifest near a chart, bundle, or repo root."""
    seen: set[Path] = set()
    for directory in _candidate_dirs(start):
        for candidate in (directory / _MANIFEST_NAME, directory / "deploy" / _MANIFEST_NAME):
            if candidate in seen:
                continue
            seen.add(candidate)
            if candidate.is_file():
                return candidate
    return None


def load_operator_versions(start: Path | str | None = None) -> OperatorVersions:
    """Load the shared operator version manifest."""
    path = find_operator_versions_file(start)
    if path is None:
        hint = f"{_MANIFEST_NAME} or deploy/{_MANIFEST_NAME}"
        raise FileNotFoundError(f"Could not find {hint}")
    return parse_operator_versions(path.read_text())


def _candidate_dirs(start: Path | str | None) -> list[Path]:
    candidates: list[Path] = []

    if start is not None:
        candidates.extend(_parents(Path(start)))

    candidates.extend(_parents(Path.cwd()))
    candidates.extend(_parents(Path(__file__).resolve()))

    unique: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        unique.append(candidate)
    return unique


def _parents(path: Path) -> list[Path]:
    resolved = path.expanduser().resolve()
    if resolved.is_file():
        resolved = resolved.parent
    return [resolved, *resolved.parents]
