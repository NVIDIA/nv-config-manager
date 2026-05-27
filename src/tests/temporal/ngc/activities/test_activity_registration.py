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
"""Ensure all activities are registered."""

import inspect
from pathlib import Path

from nv_config_manager.temporal.ngc import activities
from nv_config_manager.temporal.ngc.activities import REGISTERED_ACTIVITIES


def _load_all_activity_methods():
    """Load all workflow classes from the workflows module."""
    activity_methods = []
    activity_path = Path(inspect.getsourcefile(activities)).parent
    for path in activity_path.glob("*.py"):
        if path.stem == "__init__":
            continue
        module = getattr(activities, path.stem)

        for _, obj in inspect.getmembers(module, inspect.isfunction):
            # Risky if temporal SDK changes, but not finding a better method
            # for identifying functions with @activity.defn decorator
            if hasattr(obj, "__temporal_activity_definition"):
                activity_methods.append(obj)

    return activity_methods


def test_activity_registration():
    """Test that all activities are registered."""
    activity_methods = _load_all_activity_methods()
    for activity_method in activity_methods:
        assert activity_method in REGISTERED_ACTIVITIES, (
            f"Activity {activity_method.__name__} not registered"
        )
