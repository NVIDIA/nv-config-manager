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
"""Tests for the TICKETING_PROVIDERS registry and get_ticketing_provider factory.

Code under test:
  src/nv_config_manager/temporal/client/ticketing.py
    - TICKETING_PROVIDERS   line 84
    - get_ticketing_provider line 87

  src/nv_config_manager/temporal/client/jira.py
    - Registration side-effect at module import (line 246)

get_ticketing_provider calls from_config() — that is patched so no nv-config-manager.ini
or real HTTP connections are needed.
"""

from unittest.mock import MagicMock, patch

import pytest
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    # Importing jira triggers TICKETING_PROVIDERS["jira"] = JiraTicketingProvider
    import nv_config_manager.temporal.client.jira  # noqa: F401
    from nv_config_manager.temporal.client.jira import JiraTicketingProvider
    from nv_config_manager.temporal.client.ticketing import (
        TICKETING_PROVIDERS,
        get_ticketing_provider,
    )


# =============================================================================
# TICKETING_PROVIDERS registry
# =============================================================================


def test_registry_contains_jira():
    """Importing nv_config_manager.temporal.client.jira registers 'jira' in TICKETING_PROVIDERS."""
    assert "jira" in TICKETING_PROVIDERS


def test_registry_jira_maps_to_jira_provider_class():
    """TICKETING_PROVIDERS['jira'] points to JiraTicketingProvider."""
    assert TICKETING_PROVIDERS["jira"] is JiraTicketingProvider


def test_registry_values_are_ticketing_provider_subclasses():
    """Every registered class is a subclass of TicketingProvider."""
    from nv_config_manager.temporal.client.ticketing import TicketingProvider

    for name, cls in TICKETING_PROVIDERS.items():
        assert issubclass(cls, TicketingProvider), f"{name!r} is not a TicketingProvider subclass"


# =============================================================================
# get_ticketing_provider
# =============================================================================


def test_get_ticketing_provider_raises_for_unknown_platform():
    """ValueError is raised for a platform name not in the registry."""
    with pytest.raises(ValueError, match="unknown_platform"):
        get_ticketing_provider("unknown_platform")


def test_get_ticketing_provider_error_message_lists_known_platforms():
    """The ValueError message includes the list of registered platforms."""
    with pytest.raises(ValueError) as exc_info:
        get_ticketing_provider("unknown_platform")

    assert "jira" in str(exc_info.value)


def test_get_ticketing_provider_calls_from_config():
    """get_ticketing_provider calls from_config() on the resolved provider class."""
    mock_instance = MagicMock()
    with patch.object(JiraTicketingProvider, "from_config", return_value=mock_instance) as mock_fc:
        result = get_ticketing_provider("jira")

    mock_fc.assert_called_once_with()
    assert result is mock_instance


def test_get_ticketing_provider_returns_provider_instance():
    """get_ticketing_provider returns whatever from_config() returns."""
    mock_instance = MagicMock()
    with patch.object(JiraTicketingProvider, "from_config", return_value=mock_instance):
        result = get_ticketing_provider("jira")

    assert result is mock_instance


def test_get_ticketing_provider_case_sensitive():
    """Platform names are case-sensitive — 'Jira' is not the same as 'jira'."""
    with pytest.raises(ValueError):
        get_ticketing_provider("Jira")
