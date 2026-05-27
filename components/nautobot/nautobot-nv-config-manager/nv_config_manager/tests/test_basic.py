#  SPDX-FileCopyrightText: Copyright (c) "2025" NVIDIA CORPORATION & AFFILIATES. All rights reserved.
#  SPDX-License-Identifier: Apache-2.0
#
#  Licensed under the Apache License, Version 2.0 (the "License")
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#  http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Basic tests that do not require Django."""

import unittest
from importlib.metadata import version

from nv_config_manager import __version__ as project_version


class TestVersion(unittest.TestCase):
    """Test Version is the same."""

    def test_version(self):
        """Verify that the app version matches the installed distribution version."""
        self.assertEqual(project_version, version("nautobot-nv-config-manager"))
