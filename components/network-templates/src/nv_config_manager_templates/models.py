# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""Compatibility re-exports for provider-neutral render data.

``RenderData`` is owned by :mod:`nv_config_manager_dcim`.  These imports stay
available while external template plugins migrate to the standalone SDK.
"""

from nv_config_manager_dcim.render import (
    RENDER_DATA_CACHE_SCHEMA_VERSION,
    DeviceRenderData,
    LocationRenderData,
    RenderData,
)

__all__ = [
    "RENDER_DATA_CACHE_SCHEMA_VERSION",
    "DeviceRenderData",
    "LocationRenderData",
    "RenderData",
]
