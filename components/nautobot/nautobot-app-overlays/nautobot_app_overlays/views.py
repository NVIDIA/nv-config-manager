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

"""Views for Overlays app."""

import logging

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django_tables2 import RequestConfig
from nautobot.apps.views import NautobotUIViewSet
from nautobot.dcim.models import Device, Interface, Rack
from nautobot.extras.models import Status

from nautobot_app_overlays import filters, forms, models, tables
from nautobot_app_overlays.choices import IsolationTypeChoices, VNITypeChoices

logger = logging.getLogger(__name__)


class OverlayUIViewSet(NautobotUIViewSet):
    """UI ViewSet for Overlay model."""

    bulk_update_form_class = forms.OverlayBulkEditForm
    filterset_class = filters.OverlayFilterSet
    filterset_form_class = forms.OverlayFilterForm
    form_class = forms.OverlayForm
    lookup_field = "pk"
    queryset = models.Overlay.objects.annotate(assignment_count=Count("assignments"))
    serializer_class = None  # Will be set in API
    table_class = tables.OverlayTable

    def get_extra_context(self, request, instance=None):
        """Add additional context for the detail view."""
        context = super().get_extra_context(request, instance)

        if instance is None or not instance.pk:
            return context

        vxlan_ct = ContentType.objects.get(app_label="nautobot_app_overlays", model="vxlan")

        non_vxlan_assignments = instance.assignments.exclude(assigned_object_type=vxlan_ct).select_related(
            "assigned_object_type", "status"
        )
        assignments_table = tables.OverlayAssignmentInlineTable(non_vxlan_assignments, orderable=False)
        RequestConfig(request, paginate={"per_page": 25}).configure(assignments_table)
        context["assignments_table"] = assignments_table

        if instance.isolation_type == IsolationTypeChoices.VXLAN_EVPN:
            vxlan_assignments = (
                instance.assignments.filter(assigned_object_type=vxlan_ct)
                .select_related("assigned_object_type", "status")
                .prefetch_related("import_targets", "export_targets")
            )
            vxlan_assignments_table = tables.VXLANAssignmentInlineTable(vxlan_assignments, orderable=False)
            RequestConfig(request, paginate={"per_page": 25}).configure(vxlan_assignments_table)
            context["vxlan_assignments_table"] = vxlan_assignments_table

        elif instance.isolation_type == IsolationTypeChoices.SPECTRUM_X_VRF:
            vxlans = (
                instance.vxlans.filter(vni_type=VNITypeChoices.L3_VNI)
                .select_related("vrf", "status")
                .prefetch_related(
                    "vrf__import_targets",
                    "vrf__export_targets",
                )
            )
            vxlans_table = tables.SpectrumXVXLANInlineTable(vxlans, orderable=False)
            RequestConfig(request, paginate={"per_page": 25}).configure(vxlans_table)
            context["vxlans_table"] = vxlans_table

        elif instance.isolation_type == IsolationTypeChoices.IB_PKEY:
            pkeys = instance.pkeys.all().select_related("tenant")
            pkeys_table = tables.InfiniBandPKeyTable(pkeys, orderable=False)
            RequestConfig(request, paginate={"per_page": 25}).configure(pkeys_table)
            context["pkeys_table"] = pkeys_table

        elif instance.isolation_type == IsolationTypeChoices.IB_MKEY:
            mkeys = instance.mkeys.all().select_related("tenant", "ufm_device")
            mkeys_table = tables.InfiniBandMKeyTable(mkeys, orderable=False)
            RequestConfig(request, paginate={"per_page": 25}).configure(mkeys_table)
            context["mkeys_table"] = mkeys_table

        return context


class VXLANOverlayViewSet(OverlayUIViewSet):
    """UI ViewSet for VXLAN/EVPN overlay type."""

    filterset_form_class = forms.VXLANOverlayFilterForm
    form_class = forms.VXLANOverlayForm
    queryset = models.Overlay.objects.filter(isolation_type=IsolationTypeChoices.VXLAN_EVPN).annotate(
        assignment_count=Count("assignments")
    )
    table_class = tables.VXLANOverlayTable


class NVLinkPartitionOverlayViewSet(OverlayUIViewSet):
    """UI ViewSet for NVLink Partition overlay type."""

    filterset_form_class = forms.NVLinkPartitionOverlayFilterForm
    form_class = forms.NVLinkPartitionOverlayForm
    queryset = models.Overlay.objects.filter(isolation_type=IsolationTypeChoices.NVLINK_PARTITION).annotate(
        assignment_count=Count("assignments")
    )
    table_class = tables.NVLinkPartitionOverlayTable


class IBPKeyOverlayViewSet(OverlayUIViewSet):
    """UI ViewSet for IB PKey overlay type."""

    filterset_form_class = forms.IBPKeyOverlayFilterForm
    form_class = forms.IBPKeyOverlayForm
    queryset = models.Overlay.objects.filter(isolation_type=IsolationTypeChoices.IB_PKEY).annotate(
        assignment_count=Count("assignments")
    )
    table_class = tables.IBPKeyOverlayTable


class IBMKeyOverlayViewSet(OverlayUIViewSet):
    """UI ViewSet for IB MKey overlay type."""

    filterset_form_class = forms.IBMKeyOverlayFilterForm
    form_class = forms.IBMKeyOverlayForm
    queryset = models.Overlay.objects.filter(isolation_type=IsolationTypeChoices.IB_MKEY).annotate(
        assignment_count=Count("assignments")
    )
    table_class = tables.IBMKeyOverlayTable


class SpectrumXOverlayViewSet(OverlayUIViewSet):
    """UI ViewSet for Spectrum X (VRF-based) overlay type."""

    filterset_form_class = forms.SpectrumXOverlayFilterForm
    form_class = forms.SpectrumXOverlayForm
    queryset = models.Overlay.objects.filter(isolation_type=IsolationTypeChoices.SPECTRUM_X_VRF).annotate(
        assignment_count=Count("assignments")
    )
    table_class = tables.SpectrumXOverlayTable


class OverlayAssignmentUIViewSet(NautobotUIViewSet):
    """UI ViewSet for OverlayAssignment model."""

    bulk_update_form_class = forms.OverlayAssignmentBulkEditForm
    filterset_class = filters.OverlayAssignmentFilterSet
    filterset_form_class = forms.OverlayAssignmentFilterForm
    form_class = forms.OverlayAssignmentForm
    lookup_field = "pk"
    queryset = models.OverlayAssignment.objects.all()
    serializer_class = None
    table_class = tables.OverlayAssignmentTable


class VXLANUIViewSet(NautobotUIViewSet):
    """UI ViewSet for VXLAN model."""

    bulk_update_form_class = forms.VXLANBulkEditForm
    filterset_class = filters.VXLANFilterSet
    filterset_form_class = forms.VXLANFilterForm
    form_class = forms.VXLANForm
    lookup_field = "pk"
    queryset = models.VXLAN.objects.all()
    serializer_class = None
    table_class = tables.VXLANTable

    def get_queryset(self):
        """Prefetch route targets for VXLAN and linked VRF."""
        qs = super().get_queryset()
        return qs.select_related("namespace", "overlay", "vlan", "tenant", "vrf").prefetch_related(
            "import_targets",
            "export_targets",
            "vrf__import_targets",
            "vrf__export_targets",
        )

    def get_extra_context(self, request, instance=None):
        """Add overlay assignments table to the VXLAN detail view."""
        context = super().get_extra_context(request, instance)

        if instance is None or not instance.pk:
            return context

        vxlan_ct = ContentType.objects.get(app_label="nautobot_app_overlays", model="vxlan")
        overlay_assignments = (
            models.OverlayAssignment.objects.filter(
                assigned_object_type=vxlan_ct,
                assigned_object_id=instance.pk,
            )
            .select_related("overlay", "status")
            .prefetch_related("import_targets", "export_targets")
        )
        overlay_assignments_table = tables.VXLANOverlayAssignmentInlineTable(overlay_assignments, orderable=False)
        RequestConfig(request, paginate={"per_page": 25}).configure(overlay_assignments_table)
        context["overlay_assignments_table"] = overlay_assignments_table

        return context


class InfiniBandPKeyUIViewSet(NautobotUIViewSet):
    """UI ViewSet for InfiniBandPKey model."""

    bulk_update_form_class = forms.InfiniBandPKeyBulkEditForm
    filterset_class = filters.InfiniBandPKeyFilterSet
    filterset_form_class = forms.InfiniBandPKeyFilterForm
    form_class = forms.InfiniBandPKeyForm
    lookup_field = "pk"
    queryset = models.InfiniBandPKey.objects.all()
    serializer_class = None
    table_class = tables.InfiniBandPKeyTable


class InfiniBandMKeyUIViewSet(NautobotUIViewSet):
    """UI ViewSet for InfiniBandMKey model."""

    bulk_update_form_class = forms.InfiniBandMKeyBulkEditForm
    filterset_class = filters.InfiniBandMKeyFilterSet
    filterset_form_class = forms.InfiniBandMKeyFilterForm
    form_class = forms.InfiniBandMKeyForm
    lookup_field = "pk"
    queryset = models.InfiniBandMKey.objects.all()
    serializer_class = None
    table_class = tables.InfiniBandMKeyTable


class OverlayAssignmentCreateView(View):
    """Type-aware view for creating an OverlayAssignment from an overlay's detail page."""

    template_name = "nautobot_app_overlays/overlay_assignment_create.html"

    _FORM_MAP = {
        IsolationTypeChoices.IB_PKEY: forms.IBPKeyOverlayAssignmentForm,
    }

    def _get_form_class(self, overlay):
        return self._FORM_MAP.get(overlay.isolation_type, forms.GeneralOverlayAssignmentForm)

    def _get_context(self, overlay, form):
        return {
            "obj": overlay,
            "form": form,
            "return_url": overlay.get_absolute_url(),
        }

    def get(self, request, pk):
        """Render the type-appropriate assignment form."""
        overlay = get_object_or_404(models.Overlay, pk=pk)
        form_class = self._get_form_class(overlay)
        form = form_class(initial={"overlay": overlay})
        return render(request, self.template_name, self._get_context(overlay, form))

    def post(self, request, pk):
        """Save the assignment and redirect back to the overlay."""
        overlay = get_object_or_404(models.Overlay, pk=pk)
        form_class = self._get_form_class(overlay)
        form = form_class(request.POST)

        if not form.is_valid():
            return render(request, self.template_name, self._get_context(overlay, form))

        try:
            with transaction.atomic():
                assignment = form.save()
            messages.success(request, f"Created assignment: {assignment}")
        except Exception as exc:  # noqa: BLE001
            messages.error(request, f"Failed to create assignment: {exc}")
            logger.exception("Error creating overlay assignment for overlay %s", overlay.pk)
            return render(request, self.template_name, self._get_context(overlay, form))

        return redirect(overlay.get_absolute_url())


class OverlayBulkAllocateView(View):
    """View for bulk allocating objects to an overlay."""

    template_name = "nautobot_app_overlays/overlay_bulk_allocate.html"

    def get_return_url(self, overlay):
        """Get the URL to return to after form submission."""
        return overlay.get_absolute_url()

    def get_context(self, overlay, form):
        """Get standard Nautobot context for the template."""
        return {
            "obj": overlay,
            "obj_type": "Bulk Allocate Assignments",
            "form": form,
            "return_url": self.get_return_url(overlay),
            "editing": False,
        }

    def get(self, request, pk):
        """Render the bulk allocation form."""
        overlay = get_object_or_404(models.Overlay, pk=pk)
        form = forms.BulkAllocationForm()
        return render(request, self.template_name, self.get_context(overlay, form))

    def post(self, request, pk):
        """Process bulk allocation."""
        overlay = get_object_or_404(models.Overlay, pk=pk)
        form = forms.BulkAllocationForm(request.POST)

        if not form.is_valid():
            logger.warning("Bulk allocation form validation failed: %s", form.errors)
            return render(request, self.template_name, self.get_context(overlay, form))

        role = form.cleaned_data.get("role", "")
        devices = form.cleaned_data.get("devices", [])
        interfaces = form.cleaned_data.get("interfaces", [])
        racks = form.cleaned_data.get("racks", [])

        assignment_status = Status.objects.get_for_model(models.OverlayAssignment).filter(name="Active").first()
        if not assignment_status:
            assignment_status = Status.objects.get_for_model(models.OverlayAssignment).first()
            if not assignment_status:
                messages.error(request, "No valid status found for overlay assignments.")
                logger.error("No status available for OverlayAssignment model")
                return redirect(overlay.get_absolute_url())

        created_count = 0
        skipped_count = 0

        object_groups = [
            (ContentType.objects.get_for_model(Device), devices),
            (ContentType.objects.get_for_model(Interface), interfaces),
            (ContentType.objects.get_for_model(Rack), racks),
        ]

        with transaction.atomic():
            for content_type, objects in object_groups:
                for obj in objects:
                    existing = models.OverlayAssignment.objects.filter(
                        overlay=overlay,
                        assigned_object_type=content_type,
                        assigned_object_id=obj.pk,
                    ).exists()

                    if existing:
                        skipped_count += 1
                        logger.debug("Skipping existing assignment: %s", obj)
                        continue

                    member = models.OverlayAssignment(
                        overlay=overlay,
                        assigned_object_type=content_type,
                        assigned_object_id=obj.pk,
                        role=role,
                        status=assignment_status,
                    )
                    try:
                        member.full_clean()
                    except ValidationError as exc:
                        messages.error(request, f"Cannot assign {obj}: {exc.message_dict}")
                        logger.warning("Validation error assigning %s to overlay %s: %s", obj, overlay.name, exc)
                        return render(request, self.template_name, self.get_context(overlay, form))
                    member.save()
                    created_count += 1
                    logger.info("Created overlay assignment for %s in overlay %s", obj, overlay.name)

        if created_count > 0:
            messages.success(request, f"Successfully allocated {created_count} object(s) to overlay.")
        if skipped_count > 0:
            messages.warning(request, f"Skipped {skipped_count} object(s) that were already assigned.")

        return redirect(overlay.get_absolute_url())


class OverlayBulkDeallocateView(View):
    """View for bulk deallocating assignments from an overlay."""

    def post(self, request, pk):
        """Process bulk deallocation."""
        overlay = get_object_or_404(models.Overlay, pk=pk)
        assignment_ids = request.POST.getlist("pk")

        if not assignment_ids:
            messages.warning(request, "No assignments selected for removal.")
            return redirect(overlay.get_absolute_url())

        with transaction.atomic():
            qs = models.OverlayAssignment.objects.filter(pk__in=assignment_ids, overlay=overlay)
            found_ids = set(qs.values_list("pk", flat=True))
            not_found_count = len(assignment_ids) - len(found_ids)
            deleted_count, _ = qs.delete()

        if deleted_count > 0:
            messages.success(request, f"Successfully removed {deleted_count} assignment(s) from overlay.")
        if not_found_count > 0:
            messages.warning(request, f"{not_found_count} selected assignment(s) were not found.")

        return redirect(overlay.get_absolute_url())
