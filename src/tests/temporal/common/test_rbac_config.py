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
"""Test RBAC Configuration Loader."""

import os
import tempfile
from unittest.mock import patch

import pytest
import yaml

from nv_config_manager.temporal.common.rbac_config import RBACConfig


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def config_path(temp_dir):
    """Create a temporary RBAC config file."""
    config_path = os.path.join(temp_dir, "rbac.yaml")

    # Test configuration
    test_config = {
        "admin_roles": ["admin"],
        "workflows": [
            {
                "name": "TestWorkflow1",
                "read_roles": ["ALL"],
                "execute_roles": ["ngc-cfa", "ngc-gni"],
            },
            {
                "name": "TestWorkflow2",
                "read_roles": ["ngc-cfa"],
                "execute_roles": ["ngc-cfa"],
            },
        ],
    }

    # Write the test configuration to the temporary file
    with open(config_path, "w", encoding="utf-8") as f:
        yaml.dump(test_config, f)

    return config_path


@patch("nv_config_manager.temporal.common.rbac_config.RBACConfig._config_path")
def test_load_config(mock_config_path, config_path):
    """Test loading RBAC configuration."""
    # Set the config path to our temporary file
    mock_config_path.__get__ = lambda *args: config_path

    # Reset the singleton instance
    RBACConfig._instance = None

    # Create a new instance
    rbac_config = RBACConfig()

    # Check if the configuration was loaded correctly
    workflow1_roles = rbac_config.get_workflow_roles("TestWorkflow1")
    assert workflow1_roles is not None
    assert "ALL" in workflow1_roles["read_roles"]
    assert "ngc-cfa" in workflow1_roles["execute_roles"]
    assert "ngc-gni" in workflow1_roles["execute_roles"]

    workflow2_roles = rbac_config.get_workflow_roles("TestWorkflow2")
    assert workflow2_roles is not None
    assert "ngc-cfa" in workflow2_roles["read_roles"]
    assert "ngc-cfa" in workflow2_roles["execute_roles"]

    # Test non-existent workflow
    assert rbac_config.get_workflow_roles("NonExistentWorkflow") is None

    # Test admin roles
    assert "admin" in rbac_config.get_admin_roles()


@patch("nv_config_manager.temporal.common.rbac_config.RBACConfig._config_path")
def test_singleton(mock_config_path, config_path):
    """Test that RBACConfig is a singleton."""
    # Set the config path to our temporary file
    mock_config_path.__get__ = lambda *args: config_path

    # Reset the singleton instance
    RBACConfig._instance = None

    # Create two instances
    rbac_config1 = RBACConfig()
    rbac_config2 = RBACConfig()

    # Check that they are the same instance
    assert rbac_config1 is rbac_config2
