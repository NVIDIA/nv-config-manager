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
"""Shared installer input validation helpers."""

from __future__ import annotations

import re

# Kubernetes namespace names must be RFC 1123 DNS labels (lowercase).
_KUBERNETES_NAMESPACE_RE = re.compile(r"^[a-z0-9](?:[-a-z0-9]{0,61}[a-z0-9])?$")


def normalize_kubernetes_namespace(value: str) -> str:
    """Trim and validate a Kubernetes namespace name."""
    normalized = value.strip()
    if not normalized:
        raise ValueError("namespace must not be empty")
    if not _KUBERNETES_NAMESPACE_RE.fullmatch(normalized):
        raise ValueError(
            "namespace must be a lowercase DNS-1123 label (alphanumeric, hyphens, "
            "start/end with alphanumeric, max 63 characters)"
        )
    return normalized
