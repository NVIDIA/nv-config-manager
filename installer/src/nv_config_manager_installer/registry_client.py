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
"""Docker Registry V2 tag listing client.

Supports the full Docker V2 Bearer-token authentication flow used by
NVCR, Docker Hub, GCR, private OCI registries, and other production registries:

1. ``GET /v2/<repo>/tags/list`` → 401 with ``Www-Authenticate`` header
2. Parse the ``realm``, ``service``, and ``scope`` from that header
3. ``GET <realm>?service=...&scope=...`` with Basic-auth credentials
4. Retry the original request with ``Authorization: Bearer <token>``
"""

from __future__ import annotations

import re
from typing import Any

import requests

_WWW_AUTH_RE = re.compile(r'(\w+)="([^"]*)"')


def _parse_www_authenticate(header: str) -> dict[str, str]:
    """Extract key=value pairs from a ``Www-Authenticate: Bearer ...`` header."""
    return dict(_WWW_AUTH_RE.findall(header))


def _fetch_bearer_token(
    www_auth: dict[str, str],
    username: str,
    password: str,
    timeout: int,
) -> str | None:
    """Request a bearer token from the auth realm using Basic credentials."""
    realm = www_auth.get("realm", "")
    if not realm:
        return None

    params: dict[str, str] = {}
    if "service" in www_auth:
        params["service"] = www_auth["service"]
    if "scope" in www_auth:
        params["scope"] = www_auth["scope"]

    auth = (username, password) if username and password else None
    try:
        resp = requests.get(realm, params=params, auth=auth, timeout=timeout)
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()
    except Exception:
        return None

    return data.get("token") or data.get("access_token") or None


def list_tags(
    registry: str,
    repository: str,
    username: str = "",
    password: str = "",
    *,
    timeout: int = 15,
) -> tuple[list[str], str]:
    """Query a Docker V2 registry for available tags on *repository*.

    Returns ``(tags, error_message)``.  On success *error_message* is empty.
    On failure *tags* is empty and *error_message* describes what went wrong.
    """
    parts = registry.rstrip("/").split("/", 1)
    host = parts[0]
    path_prefix = parts[1] if len(parts) > 1 else ""

    full_repo = f"{path_prefix}/{repository}" if path_prefix else repository
    full_repo = full_repo.strip("/")

    url = f"https://{host}/v2/{full_repo}/tags/list"

    auth = (username, password) if username and password else None
    try:
        resp = requests.get(url, auth=auth, timeout=timeout)
    except requests.ConnectionError:
        return [], f"Cannot reach registry {host}: connection refused"
    except requests.RequestException as exc:
        return [], f"Registry query failed: {exc}"

    if resp.ok:
        return _extract_tags(resp.json())

    if resp.status_code != 401:
        return _http_error(resp.status_code, resp.reason, full_repo, host)

    # 401 — try bearer-token flow
    www_auth_header = resp.headers.get("Www-Authenticate", "")
    if "bearer" not in www_auth_header.lower():
        return [], "Authentication failed — registry requires credentials."

    www_auth = _parse_www_authenticate(www_auth_header)
    bearer = _fetch_bearer_token(www_auth, username, password, timeout)
    if not bearer:
        return (
            [],
            "Authentication failed — could not obtain bearer token. Check your registry key.",
        )

    try:
        resp2 = requests.get(url, headers={"Authorization": f"Bearer {bearer}"}, timeout=timeout)
    except requests.RequestException as exc:
        return [], f"Registry query failed: {exc}"

    if resp2.ok:
        return _extract_tags(resp2.json())
    return _http_error(resp2.status_code, resp2.reason, full_repo, host)


_SEMVER_RE = re.compile(
    r"^v?(\d+)\.(\d+)\.(\d+)"
    r"(?:-((?:rc|alpha|beta|dev)\.?\d*))?"
    r"$",
    re.IGNORECASE,
)

_ARCH_SUFFIX_RE = re.compile(r"-(arm64|amd64|linux|windows|s390x|ppc64le)$", re.IGNORECASE)

_PRERELEASE_ORDER = {"rc": 0, "beta": 1, "alpha": 2, "dev": 3}


def _prerelease_sort_key(pre: str) -> tuple[int, int]:
    """Return (kind_rank, number) for a pre-release label like 'rc1' or 'beta.2'."""
    pre_lower = pre.lower()
    for prefix, rank in _PRERELEASE_ORDER.items():
        if pre_lower.startswith(prefix):
            num_str = pre_lower[len(prefix) :].lstrip(".")
            num = int(num_str) if num_str.isdigit() else 0
            return rank, num
    return 99, 0


def _tag_sort_key(tag: str) -> tuple[int, tuple[int, ...], tuple[int, ...], str]:
    """Produce a sort key that orders tags: releases > pre-releases > other.

    Lower key values sort first. Within each tier, higher version numbers
    come first (achieved by negating the version components).
    """
    m = _SEMVER_RE.match(tag)
    if m:
        major, minor, patch = int(m.group(1)), int(m.group(2)), int(m.group(3))
        ver = (-major, -minor, -patch)
        pre = m.group(4)
        if pre:
            kind_rank, num = _prerelease_sort_key(pre)
            return (1, ver, (kind_rank, -num), tag)
        return (0, ver, (0, 0), tag)
    if tag == "latest":
        return (2, (0, 0, 0), (0, 0), tag)
    return (3, (0, 0, 0), (0, 0), tag)


def _extract_tags(data: dict[str, Any]) -> tuple[list[str], str]:
    raw_tags = data.get("tags") or []
    if not isinstance(raw_tags, list):
        return [], "Unexpected response format from registry."
    tags = [t for t in raw_tags if not _ARCH_SUFFIX_RE.search(t)]
    tags.sort(key=_tag_sort_key)
    return tags, ""


def _http_error(code: int, reason: str, full_repo: str, host: str) -> tuple[list[str], str]:
    if code == 401:
        return [], "Authentication failed — check your registry key."
    if code == 404:
        return [], f"Repository '{full_repo}' not found on {host}."
    return [], f"Registry returned HTTP {code}: {reason}"
