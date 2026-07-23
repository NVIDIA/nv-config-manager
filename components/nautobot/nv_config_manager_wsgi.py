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
"""uWSGI entrypoint that preloads Nautobot's GraphQL schema."""

from importlib import import_module

from nautobot.core.wsgi import application

# Import the dynamic schema only after Nautobot has initialized Django and
# registered its uWSGI post-fork connection cleanup. uWSGI loads this module in
# the master process, so workers inherit a fully generated schema rather than
# racing to build it on their first requests.
_graphql_schema = import_module("nautobot.core.graphql.schema_init").schema

__all__ = ["application"]
