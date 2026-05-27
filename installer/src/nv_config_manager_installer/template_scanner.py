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
"""Scan user-supplied Jinja2 template plugins to discover required config secrets.

Performs static regex analysis of ``.j2`` files to find:

* ``"key_name"|load_secret(...)`` — literal secret keys
* ``|encrypt(...)`` — implies ``hash_salt`` / ``hash_salt_t7`` are required
* ``user.password_key|load_secret(...)`` — dynamic keys from config context
  (already handled by the Accounts screen, noted but not emitted)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

_LITERAL_LOAD_SECRET_RE = re.compile(
    r"""
    ["']                        # opening quote
    (?P<key>[a-z][a-z0-9_]*)    # the secret key name
    ["']                        # closing quote
    \s*\|\s*load_secret         # pipe into load_secret filter
    """,
    re.VERBOSE,
)

_DYNAMIC_LOAD_SECRET_RE = re.compile(
    r"\buser\.password_key\s*\|\s*load_secret",
)

_ENCRYPT_RE = re.compile(
    r"""
    \|\s*encrypt\s*\(
    \s*["'](?P<algo>[a-z0-9]+)["']
    """,
    re.VERBOSE,
)

_ROTATION_SUFFIX_RE = re.compile(r"^(?P<base>.+?)_(?P<rot>r\d+)$")

_INTERNAL_KEYS = frozenset({"hash_salt", "hash_salt_t7"})


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class DiscoveredSecret:
    """A secret key discovered via template scanning."""

    secret_key: str
    rotation: str = "r1"
    name: str = ""
    source_files: list[str] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        return self.name or _humanize_key(self.secret_key)


@dataclass
class ScanResult:
    """Aggregated results from scanning template plugin directories."""

    secrets: list[DiscoveredSecret] = field(default_factory=list)
    needs_hash_salt: bool = False
    needs_hash_salt_t7: bool = False
    dynamic_user_keys_found: bool = False
    scanned_files: int = 0
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _humanize_key(key: str) -> str:
    """``bgp_password`` → ``BGP Password``."""
    return key.replace("_", " ").title()


def _decompose_key(raw_key: str) -> tuple[str, str]:
    """``bgp_password_r1`` → ``("bgp_password", "r1")``."""
    m = _ROTATION_SUFFIX_RE.match(raw_key)
    if m:
        return m.group("base"), m.group("rot")
    return raw_key, ""


# ---------------------------------------------------------------------------
# Core scanning
# ---------------------------------------------------------------------------


def _merge_secret(seen: dict[str, DiscoveredSecret], ds: DiscoveredSecret) -> None:
    """Merge a discovered secret into the *seen* accumulator."""
    if ds.secret_key in seen:
        existing = seen[ds.secret_key]
        for sf in ds.source_files:
            if sf not in existing.source_files:
                existing.source_files.append(sf)
    else:
        seen[ds.secret_key] = ds


def _merge_result(
    target: ScanResult, source: ScanResult, seen: dict[str, DiscoveredSecret]
) -> None:
    """Merge *source* scan result into *target* and the *seen* dict."""
    target.scanned_files += source.scanned_files
    target.errors.extend(source.errors)
    target.dynamic_user_keys_found = (
        target.dynamic_user_keys_found or source.dynamic_user_keys_found
    )
    target.needs_hash_salt = target.needs_hash_salt or source.needs_hash_salt
    target.needs_hash_salt_t7 = target.needs_hash_salt_t7 or source.needs_hash_salt_t7
    for ds in source.secrets:
        _merge_secret(seen, ds)


def _scan_text(text: str, rel_path: str) -> ScanResult:
    """Extract secrets and encrypt usage from template text."""
    result = ScanResult(scanned_files=1)
    if _DYNAMIC_LOAD_SECRET_RE.search(text):
        result.dynamic_user_keys_found = True

    seen: dict[str, DiscoveredSecret] = {}
    for m in _LITERAL_LOAD_SECRET_RE.finditer(text):
        raw_key = m.group("key")
        if raw_key in _INTERNAL_KEYS:
            continue
        base_key, rotation = _decompose_key(raw_key)
        _merge_secret(
            seen,
            DiscoveredSecret(
                secret_key=base_key, rotation=rotation or "r1", source_files=[rel_path]
            ),
        )

    result.secrets = list(seen.values())

    for m in _ENCRYPT_RE.finditer(text):
        if m.group("algo") == "ciscot7":
            result.needs_hash_salt_t7 = True
        else:
            result.needs_hash_salt = True
    return result


def scan_file(filepath: Path, root: Path | None = None) -> ScanResult:
    """Scan a single ``.j2`` file for secret references."""
    try:
        text = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        result = ScanResult(scanned_files=1)
        result.errors.append(f"{filepath}: {exc}")
        return result
    rel_path = str(filepath.relative_to(root)) if root else str(filepath)
    return _scan_text(text, rel_path)


def scan_directory(templates_dir: Path) -> ScanResult:
    """Recursively scan a directory of ``.j2`` files."""
    aggregate = ScanResult()
    if not templates_dir.is_dir():
        aggregate.errors.append(f"Not a directory: {templates_dir}")
        return aggregate

    seen: dict[str, DiscoveredSecret] = {}
    for j2_file in sorted(templates_dir.rglob("*.j2")):
        _merge_result(aggregate, scan_file(j2_file, root=templates_dir), seen)

    aggregate.secrets = list(seen.values())
    return aggregate


# ---------------------------------------------------------------------------
# Plugin scanning entry point
# ---------------------------------------------------------------------------


def _find_templates_subdir(plugin_dir: Path) -> Path:
    """Locate the ``templates/`` subtree inside a plugin package.

    Typical layouts: ``src/<pkg>/templates/`` or ``templates/``.
    Falls back to the plugin dir itself.
    """
    for start in [plugin_dir / "src", plugin_dir]:
        if not start.is_dir():
            continue
        for sub in start.rglob("templates"):
            if sub.is_dir() and any(sub.rglob("*.j2")):
                return sub
    return plugin_dir


def scan_plugins(plugin_paths: list[str | Path]) -> ScanResult:
    """Scan one or more user-supplied template plugin directories."""
    aggregate = ScanResult()
    seen: dict[str, DiscoveredSecret] = {}

    for plugin_path in plugin_paths:
        p = Path(plugin_path)
        if not p.is_dir():
            aggregate.errors.append(f"Skipping non-directory: {p}")
            continue
        tpl_dir = _find_templates_subdir(p)
        _merge_result(aggregate, scan_directory(tpl_dir), seen)

    aggregate.secrets = list(seen.values())
    _append_hash_salt_if_needed(aggregate, seen)
    return aggregate


def _append_hash_salt_if_needed(result: ScanResult, seen: dict[str, DiscoveredSecret]) -> None:
    """Append implicit hash_salt / hash_salt_t7 if encrypt filters were found."""
    if result.needs_hash_salt and "hash_salt" not in seen:
        result.secrets.append(
            DiscoveredSecret(secret_key="hash_salt", rotation="", name="Hash Salt (encrypt filter)")
        )
    if result.needs_hash_salt_t7 and "hash_salt_t7" not in seen:
        result.secrets.append(
            DiscoveredSecret(
                secret_key="hash_salt_t7", rotation="", name="Hash Salt T7 (Cisco Type-7)"
            )
        )
