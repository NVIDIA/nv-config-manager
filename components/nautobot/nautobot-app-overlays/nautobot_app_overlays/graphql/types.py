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

"""GraphQL type extensions for Overlays."""

import graphene
from graphene_django import DjangoObjectType

from nautobot_app_overlays.models import (
    VXLAN,
    InfiniBandMKey,
    InfiniBandPKey,
    Overlay,
    OverlayAssignment,
)


class VXLANType(DjangoObjectType):
    """GraphQL type for VXLAN model."""

    class Meta:
        """Meta class."""

        model = VXLAN
        exclude = ["created", "last_updated"]


class OverlayType(DjangoObjectType):
    """GraphQL type for Overlay model."""

    vxlans = graphene.List(VXLANType)

    class Meta:
        """Meta class."""

        model = Overlay
        exclude = ["created", "last_updated"]

    def resolve_vxlans(self, info):
        """Resolve VXLAN objects associated with this overlay."""
        return self.vxlans.all()


class OverlayAssignmentType(DjangoObjectType):
    """GraphQL type for OverlayAssignment model."""

    class Meta:
        """Meta class."""

        model = OverlayAssignment
        exclude = ["created", "last_updated"]


class InfiniBandPKeyType(DjangoObjectType):
    """GraphQL type for InfiniBandPKey model."""

    class Meta:
        """Meta class."""

        model = InfiniBandPKey
        exclude = ["created", "last_updated"]


class InfiniBandMKeyType(DjangoObjectType):
    """GraphQL type for InfiniBandMKey model."""

    class Meta:
        """Meta class."""

        model = InfiniBandMKey
        exclude = ["created", "last_updated"]


# List of GraphQL type classes for Nautobot to register
graphql_types = [
    VXLANType,
    OverlayType,
    OverlayAssignmentType,
    InfiniBandPKeyType,
    InfiniBandMKeyType,
]
