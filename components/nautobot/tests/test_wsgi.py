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
"""Tests for the Nautobot uWSGI entrypoint."""

import sys
from importlib import import_module
from types import ModuleType
from unittest.mock import sentinel


def test_wsgi_entrypoint_preloads_graphql_schema(monkeypatch):
    """The custom entrypoint exports Nautobot and retains the generated schema."""
    wsgi = ModuleType("nautobot.core.wsgi")
    wsgi.application = sentinel.application
    graphql = ModuleType("nautobot.core.graphql")
    schema_init = ModuleType("nautobot.core.graphql.schema_init")
    schema_init.schema = sentinel.graphql_schema

    monkeypatch.setitem(sys.modules, "nautobot.core.wsgi", wsgi)
    monkeypatch.setitem(sys.modules, "nautobot.core.graphql", graphql)
    monkeypatch.setitem(sys.modules, "nautobot.core.graphql.schema_init", schema_init)
    monkeypatch.delitem(sys.modules, "nv_config_manager_wsgi", raising=False)

    entrypoint = import_module("nv_config_manager_wsgi")

    assert entrypoint.application is sentinel.application
    assert entrypoint._graphql_schema is sentinel.graphql_schema
    assert entrypoint.__all__ == ["application"]
