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
"""Version-aware fixture loader for mock device API responses.

Resolution order: device override > version fixture > None (fall back to hardcoded).
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, cast

logger = logging.getLogger(__name__)

_DEFAULT_FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"


class FixtureLoader:
    """Load pre-recorded API response fixtures by platform, version, and device name.

    Fixture directory layout::

        fixtures/
          nvue/
            5.11.0/system.json
            5.14.0/system.json
          eapi/
            4.29.5M/show_version.json
          devices/
            leaf1-cp1-smn1-dc01/interface.json   (per-device overrides)
    """

    def __init__(
        self,
        platform: str,
        os_version: str,
        device_name: str,
        fixtures_dir: str | Path | None = None,
    ) -> None:
        """Initialise the loader for a given platform, OS version, and device name."""
        self._platform = platform
        self._os_version = os_version
        self._device_name = device_name
        self._fixtures_dir = Path(fixtures_dir) if fixtures_dir else _DEFAULT_FIXTURES_DIR
        self._cache: dict[str, Any | str | None] = {}

        logger.info(
            "FixtureLoader: platform=%s version=%s device=%s dir=%s",
            platform,
            os_version or "(none)",
            device_name,
            self._fixtures_dir,
        )

    def load(self, endpoint_key: str) -> dict[str, Any] | str | None:
        """Look up a fixture by endpoint key.

        Returns parsed JSON (dict) for ``.json`` files, raw string for ``.txt``
        files, or ``None`` if no fixture exists (caller should fall back to
        hardcoded response).
        """
        if endpoint_key in self._cache:
            return self._cache[endpoint_key]

        result = self._resolve(endpoint_key)
        self._cache[endpoint_key] = result
        return result

    def _resolve(self, key: str) -> dict[str, Any] | str | None:
        """Walk the candidate paths (device override → version fixture) and return the first hit."""
        candidates: list[Path] = []

        # 1. Per-device override
        device_dir = self._fixtures_dir / "devices" / self._device_name
        candidates.append(device_dir / f"{key}.json")
        candidates.append(device_dir / f"{key}.txt")

        # 2. Platform/version fixture
        if self._os_version:
            version_dir = self._fixtures_dir / self._platform / self._os_version
            candidates.append(version_dir / f"{key}.json")
            candidates.append(version_dir / f"{key}.txt")

        for path in candidates:
            if path.is_file():
                logger.debug("FixtureLoader: hit %s", path)
                return self._read(path)

        return None

    @staticmethod
    def _read(path: Path) -> dict[str, Any] | str:
        """Read a fixture file; parses JSON files and returns text files as raw strings."""
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            return cast(dict[str, Any], json.loads(text))
        return text
