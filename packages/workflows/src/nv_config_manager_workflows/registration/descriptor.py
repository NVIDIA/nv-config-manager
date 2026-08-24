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
"""Public contract every workflow plugin entry point must return."""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

UNKNOWN_PLUGIN_VERSION = "unknown"


class WorkflowPluginDescriptor(BaseModel):
    """What a ``nv_config_manager.workflows`` entry point resolves to.

    An entry point may point either at a descriptor instance or at a zero-argument
    callable returning one. ``name`` must match the entry-point name it is
    registered under, so an operator reading the entry-point table sees the same
    identity the registry reports in its diagnostics.

    ``version`` is optional: left unset, discovery fills it in from the
    distribution that registered the entry point, which is the version the
    environment actually installed. Declare it only to report something other
    than that.

    The three catalogs are tuples: a descriptor is validated once at startup and
    read by every consumer afterwards, so ``frozen`` has to mean the contents
    too, not just the field bindings. Plugins may pass any sequence. The model
    is not hashable — ``metadata`` is a mapping.
    """

    model_config = ConfigDict(frozen=True)

    name: str = Field(min_length=1)
    version: str | None = Field(default=None, min_length=1)
    workflows: tuple[type, ...] = ()
    activities: tuple[Callable[..., Any], ...] = ()
    schedulers: tuple[Any, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)
