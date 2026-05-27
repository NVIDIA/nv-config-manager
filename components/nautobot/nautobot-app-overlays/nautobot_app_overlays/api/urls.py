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

"""API URL patterns for Overlays app."""

from nautobot.apps.api import OrderedDefaultRouter

from nautobot_app_overlays.api import views

router = OrderedDefaultRouter()
router.register("overlays", views.OverlayViewSet)
router.register("overlay-assignments", views.OverlayAssignmentViewSet)
router.register("vxlans", views.VXLANViewSet)
router.register("pkeys", views.InfiniBandPKeyViewSet)
router.register("mkeys", views.InfiniBandMKeyViewSet)

urlpatterns = router.urls
