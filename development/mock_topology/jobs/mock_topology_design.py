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
"""Mock Network Topology Design Job.

This job creates mock network topologies for testing purposes using
the Design Builder pattern compatible with Nautobot git repository mounts.
"""

import logging
from typing import Any

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from nautobot.apps.jobs import StringVar, register_jobs
from nautobot.dcim.models import Device, Interface
from nautobot.extras.models import Relationship, RelationshipAssociation, Role, Status
from nautobot.ipam.models import IPAddress, Prefix
from nautobot_bgp_models.models import AutonomousSystem, BGPRoutingInstance
from nautobot_design_builder.choices import DesignModeChoices
from nautobot_design_builder.contrib.ext import CableConnectionExtension, LookupExtension
from nautobot_design_builder.design_job import DesignJob

from ..context import BaseContext, get_mock_topology_context_class

name = "Mock Topology"
logger = logging.getLogger(__name__)

ACTIVE_STATUS_NAME = "Active"
BGP_ASN_KEY = "asn"
BGP_DEVICE_KEY = "device"
BGP_ROUTING_INSTANCES_KEY = "bgp_routing_instances"
BGP_STATUS_CONTENT_TYPES = (
    "nautobot_bgp_models.autonomoussystem",
    "nautobot_bgp_models.bgproutinginstance",
)
DEFAULT_NAMESPACE_NAME = "Global"
GLOBAL_DEFAULTS_KEY = "global_defaults"
LOOPBACK_INTERFACE_NAME = "lo"
PREFIX_GATEWAY_RELATIONSHIP_KEY = "prefix_to_gateway"


class MockTopologyDesign(DesignJob):
    """Build a mock network topology for testing purposes."""

    blueprint = StringVar(
        default="superpod",
        description="Context directory name under mock_topology/context/",
        label="Topology Blueprint",
    )

    deployment_name = StringVar(
        description="Unique name for this deployment (used in location names)",
        label="Deployment Name",
        default="test",
    )

    def run(self, *args: Any, **kwargs: Any) -> Any:
        """Run the design job."""
        self.Meta.context_class = get_mock_topology_context_class(
            kwargs.get("blueprint", "superpod")
        )
        with transaction.atomic():
            self._ensure_role_content_type_memberships(kwargs)
            result = super().run(*args, **kwargs)
            self._ensure_bgp_routing_instances(kwargs)
            self._ensure_prefix_gateway_relationships(kwargs)
            return result

    def _ensure_role_content_type_memberships(self, data: dict[str, Any]) -> None:
        """Add required role content types without removing existing memberships."""
        try:
            job_result = self.job_result
        except AttributeError:
            job_result = None

        context = self.Meta.context_class(data=data, job_result=job_result)
        role_data = [
            *context.json.get("role_content_type_extensions", []),
            *context.json.get("roles", []),
        ]

        seen_roles = set()
        for role in role_data:
            name = role.get("name")
            if not name or name in seen_roles:
                continue
            seen_roles.add(name)

            content_types = [
                self._get_content_type(content_type)
                for content_type in role.get("content_types", [])
            ]
            content_types = [content_type for content_type in content_types if content_type]
            if not content_types:
                continue

            role_obj, _ = Role.objects.get_or_create(name=name, defaults={"color": "2196f3"})
            role_obj.content_types.add(*content_types)
            role_obj.validated_save()

    def _ensure_bgp_routing_instances(self, data: dict[str, Any]) -> None:
        """Create BGP model objects required by render templates."""
        active_status = self._ensure_status_content_type_memberships(
            ACTIVE_STATUS_NAME,
            BGP_STATUS_CONTENT_TYPES,
        )

        try:
            job_result = self.job_result
        except AttributeError:
            job_result = None

        context = self.Meta.context_class(data=data, job_result=job_result)
        for routing_instance_data in context.json.get(BGP_ROUTING_INSTANCES_KEY, []):
            device_name = routing_instance_data.get(BGP_DEVICE_KEY)
            asn = routing_instance_data.get(BGP_ASN_KEY)
            if asn is None:
                continue

            if not device_name:
                continue

            try:
                asn_int = int(asn)
            except (TypeError, ValueError) as exc:
                logger.warning("Could not use BGP ASN %r for %s: %s", asn, device_name, exc)
                continue

            try:
                device = Device.objects.get(name=device_name)
            except Device.DoesNotExist:
                logger.warning("Could not find device %r while creating BGP objects", device_name)
                continue

            router_id = self._get_device_router_id(device)
            asn_obj, asn_created = AutonomousSystem.objects.get_or_create(
                asn=asn_int,
                defaults={"status": active_status},
            )
            asn_changed = asn_obj.status_id != active_status.id
            if asn_changed:
                asn_obj.status = active_status
            if asn_created or asn_changed:
                asn_obj.validated_save()

            routing_instance, routing_created = BGPRoutingInstance.objects.get_or_create(
                device=device,
                autonomous_system=asn_obj,
                defaults={
                    "router_id": router_id,
                    "status": active_status,
                },
            )
            routing_changed = routing_instance.status_id != active_status.id
            if routing_changed:
                routing_instance.status = active_status
            if router_id and routing_instance.router_id_id != router_id.id:
                routing_instance.router_id = router_id
                routing_changed = True
            if routing_created or routing_changed:
                routing_instance.validated_save()

    def _ensure_prefix_gateway_relationships(self, data: dict[str, Any]) -> None:
        """Create explicit prefix-to-gateway relationships for DHCP prefixes."""
        try:
            relationship = Relationship.objects.get(key=PREFIX_GATEWAY_RELATIONSHIP_KEY)
        except Relationship.DoesNotExist:
            logger.warning(
                "Could not find relationship %r while creating prefix gateways",
                PREFIX_GATEWAY_RELATIONSHIP_KEY,
            )
            return

        try:
            job_result = self.job_result
        except AttributeError:
            job_result = None

        context = self.Meta.context_class(data=data, job_result=job_result)
        global_defaults = getattr(context, GLOBAL_DEFAULTS_KEY, None) or context.json.get(
            GLOBAL_DEFAULTS_KEY,
            {},
        )
        namespace_name = global_defaults.get("namespace", DEFAULT_NAMESPACE_NAME)
        prefix_type = ContentType.objects.get_for_model(Prefix)
        ip_address_type = ContentType.objects.get_for_model(IPAddress)

        for link in context.json.get("prefix_gateway_relationships", []):
            prefix_value = link.get("prefix")
            gateway_value = link.get("gateway")
            if not (prefix_value and gateway_value):
                continue

            prefix = (
                Prefix.objects.filter(namespace__name=namespace_name)
                .net_equals(prefix_value)
                .first()
            )
            if not prefix:
                logger.warning("Could not find prefix %r while creating gateway", prefix_value)
                continue

            gateway = IPAddress.objects.filter(parent=prefix, host=gateway_value).first()
            if not gateway:
                logger.warning(
                    "Could not find gateway IP %r for prefix %r",
                    gateway_value,
                    prefix_value,
                )
                continue

            association = RelationshipAssociation.objects.filter(
                relationship=relationship,
                source_type=prefix_type,
                source_id=prefix.id,
            ).first()
            if association:
                changed = (
                    association.destination_type_id != ip_address_type.id
                    or association.destination_id != gateway.id
                )
                if changed:
                    association.destination_type = ip_address_type
                    association.destination_id = gateway.id
                    association.validated_save()
                continue

            RelationshipAssociation(
                relationship=relationship,
                source_type=prefix_type,
                source_id=prefix.id,
                destination_type=ip_address_type,
                destination_id=gateway.id,
            ).validated_save()

    @staticmethod
    def _get_device_router_id(device: Device) -> Any | None:
        """Return the device loopback IP address for BGP router ID."""
        if device.primary_ip4:
            return device.primary_ip4

        loopback = Interface.objects.filter(
            device=device,
            name=LOOPBACK_INTERFACE_NAME,
        ).first()
        if not loopback:
            return None
        return loopback.ip_addresses.filter(ip_version=4).first()

    def _ensure_status_content_type_memberships(
        self,
        status_name: str,
        content_type_names: tuple[str, ...],
    ) -> Status:
        """Add required status content types without removing existing memberships."""
        content_types = [
            self._get_content_type(content_type_name)
            for content_type_name in content_type_names
        ]
        content_types = [content_type for content_type in content_types if content_type]

        status_obj, _ = Status.objects.get_or_create(
            name=status_name,
            defaults={"color": "4caf50"},
        )
        if content_types:
            status_obj.content_types.add(*content_types)
            status_obj.validated_save()
        return status_obj

    @staticmethod
    def _get_content_type(content_type: str) -> ContentType | None:
        """Resolve an app.model content type string."""
        try:
            app_label, model = content_type.split(".")
            return ContentType.objects.get(app_label=app_label, model=model)
        except (ValueError, ContentType.DoesNotExist) as exc:
            logger.warning("Could not resolve content type %r: %s", content_type, exc)
            return None

    class Meta:
        """Metadata."""

        name = "Mock Network Topology"
        version = "1.0.0"
        commit_default = False
        extensions = [LookupExtension, CableConnectionExtension]
        # Order is significant.
        # Designs are in jobs/designs/ subdirectory
        design_files = [
            "designs/roles.yaml.j2",
            "designs/tags.yaml.j2",
            "designs/tenants.yaml.j2",
            "designs/statuses.yaml.j2",
            "designs/manufacturers.yaml.j2",
            "designs/namespaces.yaml.j2",
            "designs/platforms.yaml.j2",
            "designs/location_types.yaml.j2",
            "designs/locations.yaml.j2",
            "designs/config_contexts.yaml.j2",
            "designs/device_types.yaml.j2",
            "designs/prefixes.yaml.j2",
            "designs/vrfs.yaml.j2",
            "designs/vlans.yaml.j2",
            "designs/overlays.yaml.j2",
            "designs/vxlans.yaml.j2",
            "designs/ip_addresses.yaml.j2",
            "designs/devices.yaml.j2",
            "designs/vrf_device_assignments.yaml.j2",
            "designs/overlay_assignments.yaml.j2",
            "designs/interfaces.yaml.j2",
            "designs/primary_ip4.yaml.j2",
            "designs/cables.yaml.j2",
            "designs/managed_devices.yaml.j2",
            "designs/infiniband_pkeys.yaml.j2",
        ]
        context_class = BaseContext  # Overriden in run()
        has_sensitive_variables = False
        nautobot_version = ">=2"
        design_mode = DesignModeChoices.DEPLOYMENT
        description = "Builds a mock network topology for testing."
        docs = """Builds a mock network topology for testing, including all necessary components:

* Locations
* Config Contexts
* Devices
* Interfaces
* Cables
* VRFs
* VLANs
* Overlays
* VXLANs

Certain global data is loaded from the context directory, including:
* Manufacturers
* Device Types
* Roles
* Tags
* Statuses
* Prefixes

The device data is loaded from JSON files in the topology context directories.
"""


register_jobs(MockTopologyDesign)
