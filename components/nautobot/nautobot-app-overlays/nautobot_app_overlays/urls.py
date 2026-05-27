#  SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

"""URL patterns for Overlays app."""

from django.urls import path
from nautobot.apps.urls import NautobotUIViewSetRouter

from nautobot_app_overlays import views

app_name = "nautobot_app_overlays"

router = NautobotUIViewSetRouter()

# Generic overlay CRUD (kept for backward-compat and API redirect targets)
router.register("overlays", views.OverlayUIViewSet)

# Type-specific overlay views — each pre-filters by isolation_type
router.register("vxlan-overlays", views.VXLANOverlayViewSet, basename="vxlanoverlay")
router.register("spectrum-x-overlays", views.SpectrumXOverlayViewSet, basename="spectrumxoverlay")
router.register("nvlink-partition-overlays", views.NVLinkPartitionOverlayViewSet, basename="nvlinkpartitionoverlay")
router.register("ib-pkey-overlays", views.IBPKeyOverlayViewSet, basename="ibpkeyoverlay")
router.register("ib-mkey-overlays", views.IBMKeyOverlayViewSet, basename="ibmkeyoverlay")

# Other model CRUD
router.register("overlay-assignments", views.OverlayAssignmentUIViewSet)
router.register("vxlans", views.VXLANUIViewSet)
router.register("pkeys", views.InfiniBandPKeyUIViewSet)
router.register("mkeys", views.InfiniBandMKeyUIViewSet)

urlpatterns = [
    path(
        "overlays/<uuid:pk>/assign/",
        views.OverlayAssignmentCreateView.as_view(),
        name="overlay_assignment_create",
    ),
    # Bulk allocation views
    path(
        "overlays/<uuid:pk>/bulk-allocate/",
        views.OverlayBulkAllocateView.as_view(),
        name="overlay_bulk_allocate",
    ),
    path(
        "overlays/<uuid:pk>/bulk-deallocate/",
        views.OverlayBulkDeallocateView.as_view(),
        name="overlay_bulk_deallocate",
    ),
] + router.urls
