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

"""API Views for Overlays app."""

from django.db import transaction
from django.db.models import Count
from nautobot.apps.api import NautobotModelViewSet
from nautobot.extras.models import Status
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from nautobot_app_overlays import filters, models
from nautobot_app_overlays.api import serializers


class OverlayViewSet(NautobotModelViewSet):
    """API ViewSet for Overlay model."""

    queryset = models.Overlay.objects.annotate(member_count=Count("assignments"))
    serializer_class = serializers.OverlaySerializer
    filterset_class = filters.OverlayFilterSet

    @action(detail=True, methods=["post"], url_path="allocate")
    def allocate(self, request, pk=None):  # noqa: ARG002
        """Bulk allocate objects to this overlay.

        POST /api/plugins/overlays/overlays/{id}/allocate/

        Request body:
        {
            "object_type": "device",  # or "interface", "rack", "vrf", "vlan", "prefix"
            "object_ids": ["uuid1", "uuid2", ...],
            "role": "optional-role",
            "guid": "optional-guid"  # required for IB PKey overlays
        }
        """
        overlay = self.get_object()
        serializer = serializers.BulkAllocationSerializer(
            data=request.data,
            context={"overlay": overlay},
        )
        serializer.is_valid(raise_exception=True)

        content_type = serializer.validated_data["object_type"]
        object_ids = serializer.validated_data["object_ids"]
        role = serializer.validated_data.get("role", "")
        guid = serializer.validated_data.get("guid", "")

        member_status = Status.objects.get_for_model(models.OverlayAssignment).filter(name="Active").first()
        if not member_status:
            member_status = Status.objects.get_for_model(models.OverlayAssignment).first()

        created_members = []
        skipped_members = []

        with transaction.atomic():
            for object_id in object_ids:
                existing = models.OverlayAssignment.objects.filter(
                    overlay=overlay,
                    assigned_object_type=content_type,
                    assigned_object_id=object_id,
                ).first()

                if existing:
                    skipped_members.append(str(object_id))
                    continue

                member = models.OverlayAssignment(
                    overlay=overlay,
                    assigned_object_type=content_type,
                    assigned_object_id=object_id,
                    role=role,
                    guid=guid,
                    status=member_status,
                )
                member.full_clean()
                member.save()
                created_members.append(str(member.pk))

        return Response(
            {
                "overlay": str(overlay.pk),
                "created": len(created_members),
                "skipped": len(skipped_members),
                "created_member_ids": created_members,
                "skipped_object_ids": skipped_members,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"], url_path="deallocate")
    def deallocate(self, request, pk=None):  # noqa: ARG002
        """Bulk deallocate members from this overlay.

        POST /api/plugins/overlays/overlays/{id}/deallocate/

        Request body:
        {
            "member_ids": ["uuid1", "uuid2", ...]
        }
        """
        overlay = self.get_object()
        serializer = serializers.BulkDeallocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        member_ids = serializer.validated_data["member_ids"]

        with transaction.atomic():
            qs = models.OverlayAssignment.objects.filter(pk__in=member_ids, overlay=overlay)
            found_ids = set(qs.values_list("pk", flat=True))
            not_found = [str(mid) for mid in member_ids if mid not in found_ids]
            deleted_count, _ = qs.delete()

        return Response(
            {
                "overlay": str(overlay.pk),
                "deleted": deleted_count,
                "not_found": not_found,
            },
            status=status.HTTP_200_OK,
        )


class OverlayAssignmentViewSet(NautobotModelViewSet):
    """API ViewSet for OverlayAssignment model."""

    queryset = models.OverlayAssignment.objects.all()
    serializer_class = serializers.OverlayAssignmentSerializer
    filterset_class = filters.OverlayAssignmentFilterSet


class VXLANViewSet(NautobotModelViewSet):
    """API ViewSet for VXLAN model."""

    queryset = models.VXLAN.objects.all()
    serializer_class = serializers.VXLANSerializer
    filterset_class = filters.VXLANFilterSet


class InfiniBandPKeyViewSet(NautobotModelViewSet):
    """API ViewSet for InfiniBandPKey model."""

    queryset = models.InfiniBandPKey.objects.all()
    serializer_class = serializers.InfiniBandPKeySerializer
    filterset_class = filters.InfiniBandPKeyFilterSet


class InfiniBandMKeyViewSet(NautobotModelViewSet):
    """API ViewSet for InfiniBandMKey model."""

    queryset = models.InfiniBandMKey.objects.all()
    serializer_class = serializers.InfiniBandMKeySerializer
    filterset_class = filters.InfiniBandMKeyFilterSet
