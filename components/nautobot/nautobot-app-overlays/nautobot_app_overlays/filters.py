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

"""Filters for Overlays app."""

import django_filters
from nautobot.apps.filters import NautobotFilterSet, SearchFilter
from nautobot.dcim.models import Device, Location
from nautobot.ipam.models import Namespace, RouteTarget
from nautobot.tenancy.models import Tenant

from nautobot_app_overlays import models
from nautobot_app_overlays.choices import (
    IsolationTypeChoices,
    OverlayAssignmentRoleChoices,
    PKeyMembershipTypeChoices,
    VNITypeChoices,
)


class OverlayFilterSet(NautobotFilterSet):
    """FilterSet for Overlay model."""

    q = SearchFilter(filter_predicates={"name": "icontains", "description": "icontains"})
    tenant = django_filters.ModelMultipleChoiceFilter(
        queryset=Tenant.objects.all(),
        label="Tenant",
    )
    location = django_filters.ModelMultipleChoiceFilter(
        queryset=Location.objects.all(),
        label="Location",
    )
    isolation_type = django_filters.MultipleChoiceFilter(choices=IsolationTypeChoices)

    class Meta:
        """Meta class."""

        model = models.Overlay
        fields = ["id", "name", "tenant", "location", "isolation_type", "status"]


class OverlayAssignmentFilterSet(NautobotFilterSet):
    """FilterSet for OverlayAssignment model."""

    q = SearchFilter(filter_predicates={"guid": "icontains"})
    overlay = django_filters.ModelMultipleChoiceFilter(
        queryset=models.Overlay.objects.all(),
        label="Overlay",
    )
    role = django_filters.MultipleChoiceFilter(choices=OverlayAssignmentRoleChoices)
    membership_type = django_filters.MultipleChoiceFilter(choices=PKeyMembershipTypeChoices)
    guid = django_filters.CharFilter(lookup_expr="icontains", label="GUID")
    has_guid = django_filters.BooleanFilter(
        method="filter_has_guid",
        label="Has GUID",
    )
    assigned_object_id = django_filters.UUIDFilter(label="Assigned Object ID")

    import_targets = django_filters.ModelMultipleChoiceFilter(
        queryset=RouteTarget.objects.all(),
        label="Import route targets",
    )
    export_targets = django_filters.ModelMultipleChoiceFilter(
        queryset=RouteTarget.objects.all(),
        label="Export route targets",
    )

    class Meta:
        """Meta class."""

        model = models.OverlayAssignment
        fields = [
            "id",
            "overlay",
            "role",
            "membership_type",
            "guid",
            "import_targets",
            "export_targets",
            "status",
            "assigned_object_id",
        ]

    def filter_has_guid(self, queryset, name, value):  # noqa: ARG002 - name required by django_filters
        """Filter assignments that have/don't have a GUID set."""
        if value:
            return queryset.exclude(guid="")
        return queryset.filter(guid="")


class VXLANFilterSet(NautobotFilterSet):
    """FilterSet for VXLAN model."""

    q = SearchFilter(filter_predicates={"name": "icontains"})
    vni_type = django_filters.MultipleChoiceFilter(
        choices=VNITypeChoices,
        label="VNI Type",
    )
    l3_vlan_id = django_filters.NumberFilter(label="L3 VLAN ID")
    namespace = django_filters.ModelMultipleChoiceFilter(
        queryset=Namespace.objects.all(),
        label="Namespace",
    )
    overlay = django_filters.ModelMultipleChoiceFilter(
        queryset=models.Overlay.objects.all(),
        label="Overlay",
    )
    tenant = django_filters.ModelMultipleChoiceFilter(
        queryset=Tenant.objects.all(),
        label="Tenant",
    )
    import_targets = django_filters.ModelMultipleChoiceFilter(
        queryset=RouteTarget.objects.all(),
        label="Import route targets",
    )
    export_targets = django_filters.ModelMultipleChoiceFilter(
        queryset=RouteTarget.objects.all(),
        label="Export route targets",
    )
    vnid = django_filters.NumberFilter()
    vnid__gte = django_filters.NumberFilter(field_name="vnid", lookup_expr="gte")
    vnid__lte = django_filters.NumberFilter(field_name="vnid", lookup_expr="lte")

    class Meta:
        """Meta class."""

        model = models.VXLAN
        fields = [
            "id",
            "vnid",
            "name",
            "vni_type",
            "l3_vlan_id",
            "namespace",
            "overlay",
            "tenant",
            "import_targets",
            "export_targets",
            "status",
        ]


class InfiniBandPKeyFilterSet(NautobotFilterSet):
    """FilterSet for InfiniBandPKey model."""

    q = SearchFilter(filter_predicates={"name": "icontains", "pkey": "icontains"})
    overlay = django_filters.ModelMultipleChoiceFilter(
        queryset=models.Overlay.objects.all(),
        label="Overlay",
    )
    tenant = django_filters.ModelMultipleChoiceFilter(
        queryset=Tenant.objects.all(),
        label="Tenant",
    )
    membership_type = django_filters.MultipleChoiceFilter(choices=PKeyMembershipTypeChoices)

    class Meta:
        """Meta class."""

        model = models.InfiniBandPKey
        fields = ["id", "pkey", "name", "overlay", "tenant", "membership_type", "status"]


class InfiniBandMKeyFilterSet(NautobotFilterSet):
    """FilterSet for InfiniBandMKey model."""

    q = SearchFilter(filter_predicates={"name": "icontains", "mkey_value": "icontains"})
    overlay = django_filters.ModelMultipleChoiceFilter(
        queryset=models.Overlay.objects.all(),
        label="Overlay",
    )
    tenant = django_filters.ModelMultipleChoiceFilter(
        queryset=Tenant.objects.all(),
        label="Tenant",
    )
    ufm_device = django_filters.ModelMultipleChoiceFilter(
        queryset=Device.objects.all(),
        label="UFM Device",
    )
    mkey_per_port = django_filters.BooleanFilter(label="MKey Per Port")

    class Meta:
        """Meta class."""

        model = models.InfiniBandMKey
        fields = ["id", "name", "mkey_value", "mkey_per_port", "overlay", "tenant", "ufm_device", "status"]
