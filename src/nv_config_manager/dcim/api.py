# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Compatibility imports for the standalone DCIM SDK.

NVCM services import this module during the transition. Provider authors must
import :mod:`nv_config_manager_dcim` directly.
"""

from nv_config_manager_dcim.api import (
    DCIM_PROVIDER_API_VERSION,
    DCIMClient,
    DCIMEventProvider,
    DCIMParameterClient,
    DCIMParameterProvider,
    DCIMProvider,
    DCIMProviderMetadata,
    DCIMRenderEventHandler,
    DCIMRenderEventProvider,
    DCIMRenderEventRegistry,
    DCIMWorkflowClient,
    DCIMWorkflowProvider,
    NautobotMCPClient,
    NautobotMCPProvider,
    ProviderSettings,
)

__all__ = [
    "DCIM_PROVIDER_API_VERSION",
    "DCIMClient",
    "DCIMEventProvider",
    "DCIMParameterClient",
    "DCIMParameterProvider",
    "DCIMProvider",
    "DCIMProviderMetadata",
    "DCIMRenderEventHandler",
    "DCIMRenderEventProvider",
    "DCIMRenderEventRegistry",
    "DCIMWorkflowClient",
    "DCIMWorkflowProvider",
    "NautobotMCPClient",
    "NautobotMCPProvider",
    "ProviderSettings",
]
