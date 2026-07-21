# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Compatibility imports for standalone DCIM SDK models."""

from nv_config_manager_dcim.models import *  # noqa: F403
from nv_config_manager_dcim.render import (  # noqa: F401
    DeviceRenderData,
    LocationRenderData,
    RenderData,
)
from nv_config_manager_dcim.workflow_models import (  # noqa: F401
    DeviceBayData,
    DeviceData,
    HostDeviceData,
    InterfaceData,
    NetworkDeviceData,
    Platform,
)
