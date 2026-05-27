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
"""Management command to populate sample Overlays data."""

from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from nautobot.dcim.models import (
    Device,
    DeviceType,
    Interface,
    Location,
    LocationType,
    Manufacturer,
    Platform,
    Rack,
    RackGroup,
)
from nautobot.extras.models import Role, Status
from nautobot.ipam.models import VLAN, VRF, IPAddress, Namespace, Prefix, RouteTarget, VLANGroup
from nautobot.tenancy.models import Tenant

from nautobot_app_overlays import choices, models


class Command(BaseCommand):
    """Populate sample Overlays data for development and testing."""

    help = "Populate sample Overlays data for development and testing"

    def add_arguments(self, parser):
        """Add command arguments."""
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all existing Overlays data before populating",
        )
        parser.add_argument(
            "--superpod",
            action="store_true",
            help="Create superpod-specific test data with VXLAN/EVPN configuration",
        )

    def handle(self, *args, **options):
        """Execute the command."""
        if options["flush"]:
            self.stdout.write("Flushing existing Overlays data...")
            self._flush_data()

        if options.get("superpod"):
            self.stdout.write("Populating Superpod Overlays data...")
            self._create_superpod_data()
            self.stdout.write(self.style.SUCCESS("Successfully populated Superpod Overlays data"))
        else:
            self.stdout.write("Populating Overlays data...")
            self._create_data()
            self.stdout.write(self.style.SUCCESS("Successfully populated Overlays data"))

    def _flush_data(self):
        """Delete all existing Overlays data."""
        models.OverlayAssignment.objects.all().delete()
        models.VXLAN.objects.all().delete()
        models.InfiniBandPKey.objects.all().delete()
        models.Overlay.objects.all().delete()
        self.stdout.write(self.style.WARNING("Deleted all existing Overlays data"))

    def _get_or_create_status(self, model_class, status_name="Active"):
        """Get or create a status for a model."""
        content_type = ContentType.objects.get_for_model(model_class)
        status = Status.objects.filter(name=status_name).first()
        if status is None:
            status = Status.objects.create(name=status_name)
        if not status.content_types.filter(pk=content_type.pk).exists():
            status.content_types.add(content_type)
        return status

    def _create_data(self):
        """Create sample data."""
        overlay_status = self._get_or_create_status(models.Overlay)
        assignment_status = self._get_or_create_status(models.OverlayAssignment)
        vxlan_status = self._get_or_create_status(models.VXLAN)
        pkey_status = self._get_or_create_status(models.InfiniBandPKey)
        location_status = Status.objects.get_for_model(Location).first()
        vlan_status = Status.objects.get_for_model(VLAN).first()
        vrf_status = Status.objects.get_for_model(VRF).first()

        tenant_compute, _ = Tenant.objects.get_or_create(name="Compute Tenant")
        tenant_storage, _ = Tenant.objects.get_or_create(name="Storage Tenant")
        tenant_ai, _ = Tenant.objects.get_or_create(name="AI/ML Tenant")

        # Create or get location type and locations
        location_type, _ = LocationType.objects.get_or_create(name="Data Center")
        location_type.content_types.add(ContentType.objects.get_for_model(Device))
        location_type.content_types.add(ContentType.objects.get_for_model(VLAN))
        location_type.content_types.add(ContentType.objects.get_for_model(Prefix))
        location_type.content_types.add(ContentType.objects.get_for_model(Rack))
        location_type.content_types.add(ContentType.objects.get_for_model(RackGroup))

        dc1, _ = Location.objects.get_or_create(
            name="DC-West-01",
            defaults={"location_type": location_type, "status": location_status},
        )
        dc2, _ = Location.objects.get_or_create(
            name="DC-East-01",
            defaults={"location_type": location_type, "status": location_status},
        )
        self.stdout.write(f"Created/found locations: {dc1}, {dc2}")

        # Create Rack Groups
        self.stdout.write("\nCreating Rack Groups...")
        rack_group_dc1, _ = RackGroup.objects.get_or_create(
            name="GPU-Racks-West",
            location=dc1,
        )
        rack_group_dc2, _ = RackGroup.objects.get_or_create(
            name="HPC-Racks-East",
            location=dc2,
        )
        self.stdout.write(f"  Created/found rack groups: {rack_group_dc1}, {rack_group_dc2}")

        # Create Racks
        self.stdout.write("\nCreating Racks...")
        rack_status = Status.objects.get_for_model(Rack).filter(name="Active").first()
        if not rack_status:
            rack_status = Status.objects.get_for_model(Rack).first()

        racks_data = [
            # DC West - GPU Racks
            {"name": "GPU-R01", "location": dc1, "rack_group": rack_group_dc1, "tenant": tenant_ai},
            {"name": "GPU-R02", "location": dc1, "rack_group": rack_group_dc1, "tenant": tenant_ai},
            {"name": "GPU-R03", "location": dc1, "rack_group": rack_group_dc1, "tenant": tenant_ai},
            {"name": "GPU-R04", "location": dc1, "rack_group": rack_group_dc1, "tenant": tenant_ai},
            {"name": "Storage-R01", "location": dc1, "rack_group": rack_group_dc1, "tenant": tenant_storage},
            {"name": "Storage-R02", "location": dc1, "rack_group": rack_group_dc1, "tenant": tenant_storage},
            # DC East - HPC Racks
            {"name": "HPC-R01", "location": dc2, "rack_group": rack_group_dc2, "tenant": tenant_compute},
            {"name": "HPC-R02", "location": dc2, "rack_group": rack_group_dc2, "tenant": tenant_compute},
            {"name": "HPC-R03", "location": dc2, "rack_group": rack_group_dc2, "tenant": tenant_compute},
            {"name": "HPC-R04", "location": dc2, "rack_group": rack_group_dc2, "tenant": tenant_compute},
        ]

        racks = []
        for data in racks_data:
            rack, created = Rack.objects.get_or_create(
                name=data["name"],
                location=data["location"],
                defaults={
                    "rack_group": data["rack_group"],
                    "tenant": data["tenant"],
                    "status": rack_status,
                    "u_height": 42,
                },
            )
            racks.append(rack)
            action = "Created" if created else "Found"
            self.stdout.write(f"  {action} rack: {rack}")

        # Create Manufacturers
        self.stdout.write("\nCreating Manufacturers...")
        nvidia_mfr, _ = Manufacturer.objects.get_or_create(name="NVIDIA")
        arista_mfr, _ = Manufacturer.objects.get_or_create(name="Arista")
        mellanox_mfr, _ = Manufacturer.objects.get_or_create(name="Mellanox")
        self.stdout.write(f"  Created/found: {nvidia_mfr}, {arista_mfr}, {mellanox_mfr}")

        # Create Device Types
        self.stdout.write("\nCreating Device Types...")
        device_types_data = [
            {"manufacturer": nvidia_mfr, "model": "DGX A100", "u_height": 6},
            {"manufacturer": nvidia_mfr, "model": "DGX H100", "u_height": 8},
            {"manufacturer": nvidia_mfr, "model": "Spectrum-4", "u_height": 1},
            {"manufacturer": arista_mfr, "model": "7050X3", "u_height": 1},
            {"manufacturer": mellanox_mfr, "model": "ConnectX-7 HCA", "u_height": 0},
            {"manufacturer": nvidia_mfr, "model": "EGX A100", "u_height": 4},
        ]

        device_types = {}
        for data in device_types_data:
            dt, created = DeviceType.objects.get_or_create(
                manufacturer=data["manufacturer"],
                model=data["model"],
                defaults={"u_height": data["u_height"]},
            )
            device_types[data["model"]] = dt
            action = "Created" if created else "Found"
            self.stdout.write(f"  {action} device type: {dt}")

        # Create Device Roles
        self.stdout.write("\nCreating Device Roles...")
        device_role_ct = ContentType.objects.get_for_model(Device)

        roles_data = [
            {"name": "GPU Server", "color": "4caf50"},
            {"name": "Network Switch", "color": "2196f3"},
            {"name": "Storage Node", "color": "ff9800"},
            {"name": "HPC Node", "color": "9c27b0"},
        ]

        device_roles = {}
        for data in roles_data:
            role, created = Role.objects.get_or_create(
                name=data["name"],
                defaults={"color": data["color"]},
            )
            role.content_types.add(device_role_ct)
            device_roles[data["name"]] = role
            action = "Created" if created else "Found"
            self.stdout.write(f"  {action} device role: {role}")

        # Create Devices
        self.stdout.write("\nCreating Devices...")
        device_status = Status.objects.get_for_model(Device).filter(name="Active").first()
        if not device_status:
            device_status = Status.objects.get_for_model(Device).first()

        devices_data = [
            # GPU Servers in DC West
            {
                "name": "gpu-node-01",
                "device_type": device_types["DGX A100"],
                "role": device_roles["GPU Server"],
                "location": dc1,
                "rack": racks[0],
                "position": 1,
                "tenant": tenant_ai,
            },
            {
                "name": "gpu-node-02",
                "device_type": device_types["DGX A100"],
                "role": device_roles["GPU Server"],
                "location": dc1,
                "rack": racks[0],
                "position": 7,
                "tenant": tenant_ai,
            },
            {
                "name": "gpu-node-03",
                "device_type": device_types["DGX H100"],
                "role": device_roles["GPU Server"],
                "location": dc1,
                "rack": racks[1],
                "position": 1,
                "tenant": tenant_ai,
            },
            {
                "name": "gpu-node-04",
                "device_type": device_types["DGX H100"],
                "role": device_roles["GPU Server"],
                "location": dc1,
                "rack": racks[1],
                "position": 9,
                "tenant": tenant_ai,
            },
            # Switches in DC West
            {
                "name": "spine-sw-01",
                "device_type": device_types["Spectrum-4"],
                "role": device_roles["Network Switch"],
                "location": dc1,
                "rack": racks[0],
                "position": 40,
                "tenant": tenant_ai,
            },
            {
                "name": "spine-sw-02",
                "device_type": device_types["Spectrum-4"],
                "role": device_roles["Network Switch"],
                "location": dc1,
                "rack": racks[1],
                "position": 40,
                "tenant": tenant_ai,
            },
            {
                "name": "leaf-sw-01",
                "device_type": device_types["7050X3"],
                "role": device_roles["Network Switch"],
                "location": dc1,
                "rack": racks[2],
                "position": 40,
                "tenant": tenant_ai,
            },
            # Storage nodes
            {
                "name": "storage-node-01",
                "device_type": device_types["EGX A100"],
                "role": device_roles["Storage Node"],
                "location": dc1,
                "rack": racks[4],
                "position": 1,
                "tenant": tenant_storage,
            },
            {
                "name": "storage-node-02",
                "device_type": device_types["EGX A100"],
                "role": device_roles["Storage Node"],
                "location": dc1,
                "rack": racks[4],
                "position": 5,
                "tenant": tenant_storage,
            },
            # HPC nodes in DC East
            {
                "name": "hpc-node-01",
                "device_type": device_types["DGX A100"],
                "role": device_roles["HPC Node"],
                "location": dc2,
                "rack": racks[6],
                "position": 1,
                "tenant": tenant_compute,
            },
            {
                "name": "hpc-node-02",
                "device_type": device_types["DGX A100"],
                "role": device_roles["HPC Node"],
                "location": dc2,
                "rack": racks[6],
                "position": 7,
                "tenant": tenant_compute,
            },
            {
                "name": "hpc-node-03",
                "device_type": device_types["DGX H100"],
                "role": device_roles["HPC Node"],
                "location": dc2,
                "rack": racks[7],
                "position": 1,
                "tenant": tenant_compute,
            },
        ]

        devices = []
        for data in devices_data:
            device, created = Device.objects.get_or_create(
                name=data["name"],
                defaults={
                    "device_type": data["device_type"],
                    "role": data["role"],
                    "location": data["location"],
                    "rack": data["rack"],
                    "position": data["position"],
                    "face": "front",
                    "tenant": data["tenant"],
                    "status": device_status,
                },
            )
            devices.append(device)
            action = "Created" if created else "Found"
            self.stdout.write(f"  {action} device: {device}")

        # Create Interfaces on devices
        self.stdout.write("\nCreating Interfaces...")
        interface_status = Status.objects.get_for_model(Interface).filter(name="Active").first()
        if not interface_status:
            interface_status = Status.objects.get_for_model(Interface).first()

        interfaces_created = 0
        for device in devices:
            # Create standard interfaces based on device type
            if "DGX" in device.device_type.model or "EGX" in device.device_type.model:
                # GPU/Compute servers get data and management interfaces
                interface_configs = [
                    {"name": "eth0", "type": "100gbase-x-qsfp28", "description": "Management"},
                    {"name": "eth1", "type": "100gbase-x-qsfp28", "description": "Data Port 1"},
                    {"name": "eth2", "type": "100gbase-x-qsfp28", "description": "Data Port 2"},
                    {"name": "eth3", "type": "100gbase-x-qsfp28", "description": "Storage Port"},
                    {"name": "ib0", "type": "infiniband-hdr", "description": "InfiniBand Port 1"},
                    {"name": "ib1", "type": "infiniband-hdr", "description": "InfiniBand Port 2"},
                ]
            elif "Spectrum" in device.device_type.model or "7050" in device.device_type.model:
                # Switches get more ports
                interface_configs = [
                    {"name": f"Ethernet{i}", "type": "100gbase-x-qsfp28", "description": f"Port {i}"}
                    for i in range(1, 9)
                ] + [{"name": "Management1", "type": "1000base-t", "description": "Management"}]
            else:
                interface_configs = [
                    {"name": "eth0", "type": "1000base-t", "description": "Management"},
                ]

            for iface_config in interface_configs:
                iface, created = Interface.objects.get_or_create(
                    device=device,
                    name=iface_config["name"],
                    defaults={
                        "type": iface_config["type"],
                        "description": iface_config["description"],
                        "status": interface_status,
                    },
                )
                if created:
                    interfaces_created += 1

        self.stdout.write(f"  Created {interfaces_created} interfaces across {len(devices)} devices")

        # Create or get namespace
        namespace = Namespace.objects.first() or Namespace.objects.create(name="Global")

        # Create VLAN Groups for each location
        vlan_group_dc1, _ = VLANGroup.objects.get_or_create(
            name="DC-West-VLANs",
            defaults={"location": dc1},
        )
        vlan_group_dc2, _ = VLANGroup.objects.get_or_create(
            name="DC-East-VLANs",
            defaults={"location": dc2},
        )
        self.stdout.write(f"Created/found VLAN groups: {vlan_group_dc1}, {vlan_group_dc2}")

        # Create VRFs
        self.stdout.write("\nCreating VRFs...")
        vrfs_data = [
            {"name": "VRF-GPU-Prod", "rd": "65001:10001", "tenant": tenant_ai, "description": "GPU Production VRF"},
            {"name": "VRF-GPU-Dev", "rd": "65001:20001", "tenant": tenant_ai, "description": "GPU Development VRF"},
            {"name": "VRF-Storage", "rd": "65001:30001", "tenant": tenant_storage, "description": "Storage Fabric VRF"},
            {
                "name": "VRF-HPC-Compute",
                "rd": "65002:10001",
                "tenant": tenant_compute,
                "description": "HPC Compute VRF",
            },
            {"name": "VRF-Management", "rd": "65002:20001", "tenant": tenant_compute, "description": "Management VRF"},
        ]

        vrfs = []
        for data in vrfs_data:
            vrf, created = VRF.objects.get_or_create(
                name=data["name"],
                namespace=namespace,
                defaults={
                    "rd": data["rd"],
                    "tenant": data["tenant"],
                    "description": data["description"],
                    "status": vrf_status,
                },
            )
            vrfs.append(vrf)
            action = "Created" if created else "Found"
            self.stdout.write(f"  {action} VRF: {vrf}")

        # Create Route Targets
        self.stdout.write("\nCreating Route Targets...")
        route_targets_data = [
            {"name": "65001:10001", "description": "GPU Prod Import/Export"},
            {"name": "65001:10002", "description": "GPU Prod Data RT"},
            {"name": "65001:20001", "description": "GPU Dev Import/Export"},
            {"name": "65001:30001", "description": "Storage Import/Export"},
            {"name": "65001:30002", "description": "Storage Data RT"},
            {"name": "65002:10001", "description": "HPC Compute RT"},
            {"name": "65002:20001", "description": "Management RT"},
        ]

        route_targets = []
        for data in route_targets_data:
            rt, created = RouteTarget.objects.get_or_create(
                name=data["name"],
                defaults={"description": data["description"]},
            )
            route_targets.append(rt)
            action = "Created" if created else "Found"
            self.stdout.write(f"  {action} Route Target: {rt}")

        # Create VLANs
        self.stdout.write("\nCreating VLANs...")
        vlans_data = [
            # DC West VLANs
            {"vid": 100, "name": "GPU-Prod-Data", "vlan_group": vlan_group_dc1, "tenant": tenant_ai, "location": dc1},
            {"vid": 101, "name": "GPU-Prod-Mgmt", "vlan_group": vlan_group_dc1, "tenant": tenant_ai, "location": dc1},
            {
                "vid": 102,
                "name": "GPU-Prod-Storage",
                "vlan_group": vlan_group_dc1,
                "tenant": tenant_ai,
                "location": dc1,
            },
            {"vid": 200, "name": "GPU-Dev-Data", "vlan_group": vlan_group_dc1, "tenant": tenant_ai, "location": dc1},
            {"vid": 201, "name": "GPU-Dev-Mgmt", "vlan_group": vlan_group_dc1, "tenant": tenant_ai, "location": dc1},
            {
                "vid": 300,
                "name": "Storage-Primary",
                "vlan_group": vlan_group_dc1,
                "tenant": tenant_storage,
                "location": dc1,
            },
            {
                "vid": 301,
                "name": "Storage-Replication",
                "vlan_group": vlan_group_dc1,
                "tenant": tenant_storage,
                "location": dc1,
            },
            # DC East VLANs
            {
                "vid": 400,
                "name": "HPC-Compute",
                "vlan_group": vlan_group_dc2,
                "tenant": tenant_compute,
                "location": dc2,
            },
            {
                "vid": 401,
                "name": "HPC-Storage",
                "vlan_group": vlan_group_dc2,
                "tenant": tenant_compute,
                "location": dc2,
            },
            {"vid": 500, "name": "Management", "vlan_group": vlan_group_dc2, "tenant": tenant_compute, "location": dc2},
        ]

        vlans = []
        for data in vlans_data:
            vlan, created = VLAN.objects.get_or_create(
                vid=data["vid"],
                vlan_group=data["vlan_group"],
                defaults={
                    "name": data["name"],
                    "tenant": data["tenant"],
                    "location": data["location"],
                    "status": vlan_status,
                },
            )
            vlans.append(vlan)
            action = "Created" if created else "Found"
            self.stdout.write(f"  {action} VLAN: {vlan}")

        # Create Overlays
        self.stdout.write("\nCreating Overlays...")
        overlays_data = [
            {
                "name": "GPU-Cluster-Prod",
                "tenant": tenant_ai,
                "location": dc1,
                "isolation_type": choices.IsolationTypeChoices.VXLAN_EVPN,
                "description": "Production GPU cluster for AI/ML workloads",
            },
            {
                "name": "GPU-Cluster-Dev",
                "tenant": tenant_ai,
                "location": dc1,
                "isolation_type": choices.IsolationTypeChoices.VXLAN_EVPN,
                "description": "Development GPU cluster for AI/ML workloads",
            },
            {
                "name": "Storage-Fabric-01",
                "tenant": tenant_storage,
                "location": dc1,
                "isolation_type": choices.IsolationTypeChoices.SPECTRUM_X_VRF,
                "description": "Storage fabric for NVMe-oF traffic (Spectrum X VRF isolation)",
            },
            {
                "name": "InfiniBand-HPC",
                "tenant": tenant_compute,
                "location": dc2,
                "isolation_type": choices.IsolationTypeChoices.IB_PKEY,
                "description": "InfiniBand fabric for HPC workloads",
            },
            {
                "name": "NVLink-Management",
                "tenant": tenant_compute,
                "location": dc2,
                "isolation_type": choices.IsolationTypeChoices.NVLINK_PARTITION,
                "description": "NVLink Partition for management traffic",
            },
        ]

        overlays = []
        for data in overlays_data:
            overlay, created = models.Overlay.objects.get_or_create(
                name=data["name"],
                location=data["location"],
                defaults={
                    "tenant": data["tenant"],
                    "isolation_type": data["isolation_type"],
                    "description": data["description"],
                    "status": overlay_status,
                },
            )
            overlays.append(overlay)
            action = "Created" if created else "Found"
            self.stdout.write(f"  {action} overlay: {overlay}")

        # Create VXLANs for VXLAN_EVPN overlays
        vxlans_data = [
            {"vnid": 10001, "name": "VXLAN-GPU-Prod-Data", "overlay": overlays[0]},
            {"vnid": 10002, "name": "VXLAN-GPU-Prod-Mgmt", "overlay": overlays[0]},
            {"vnid": 10003, "name": "VXLAN-GPU-Prod-Storage", "overlay": overlays[0]},
            {"vnid": 20001, "name": "VXLAN-GPU-Dev-Data", "overlay": overlays[1]},
            {"vnid": 20002, "name": "VXLAN-GPU-Dev-Mgmt", "overlay": overlays[1]},
        ]

        for data in vxlans_data:
            vxlan, created = models.VXLAN.objects.get_or_create(
                vnid=data["vnid"],
                namespace=namespace,
                defaults={
                    "name": data["name"],
                    "overlay": data["overlay"],
                    "tenant": data["overlay"].tenant,
                    "status": vxlan_status,
                },
            )
            action = "Created" if created else "Found"
            self.stdout.write(f"  {action} VXLAN: {vxlan}")

        # Create InfiniBand PKeys for IB_PKEY overlays
        pkeys_data = [
            {"pkey": "0x8001", "name": "PKey-HPC-Compute", "overlay": overlays[3], "membership_type": "full"},
            {"pkey": "0x8002", "name": "PKey-HPC-Storage", "overlay": overlays[3], "membership_type": "full"},
            {"pkey": "0x8003", "name": "PKey-HPC-Mgmt", "overlay": overlays[3], "membership_type": "limited"},
        ]

        for data in pkeys_data:
            pkey, created = models.InfiniBandPKey.objects.get_or_create(
                pkey=data["pkey"],
                overlay=data["overlay"],
                defaults={
                    "name": data["name"],
                    "tenant": data["overlay"].tenant,
                    "membership_type": data["membership_type"],
                    "status": pkey_status,
                },
            )
            action = "Created" if created else "Found"
            self.stdout.write(f"  {action} PKey: {pkey}")

        # Create Overlay Assignments (devices and interfaces)
        self.stdout.write("\nCreating Overlay Assignments...")
        device_content_type = ContentType.objects.get_for_model(Device)
        interface_content_type = ContentType.objects.get_for_model(Interface)

        # Map devices to overlays based on their purpose
        device_overlay_mapping = [
            # GPU Prod cluster
            {
                "devices": ["gpu-node-01", "gpu-node-02"],
                "overlay": overlays[0],
                "role": choices.OverlayAssignmentRoleChoices.COMPUTE,
            },
            {
                "devices": ["gpu-node-03", "gpu-node-04"],
                "overlay": overlays[0],
                "role": choices.OverlayAssignmentRoleChoices.COMPUTE,
            },
            # GPU Dev cluster - switches
            {
                "devices": ["spine-sw-01", "spine-sw-02"],
                "overlay": overlays[1],
                "role": choices.OverlayAssignmentRoleChoices.SPINE,
            },
            {"devices": ["leaf-sw-01"], "overlay": overlays[1], "role": choices.OverlayAssignmentRoleChoices.LEAF},
            # Storage fabric
            {
                "devices": ["storage-node-01", "storage-node-02"],
                "overlay": overlays[2],
                "role": choices.OverlayAssignmentRoleChoices.STORAGE,
            },
            # InfiniBand HPC
            {
                "devices": ["hpc-node-01", "hpc-node-02", "hpc-node-03"],
                "overlay": overlays[3],
                "role": choices.OverlayAssignmentRoleChoices.COMPUTE,
            },
        ]

        assignments_created = 0
        for mapping in device_overlay_mapping:
            for device_name in mapping["devices"]:
                device = Device.objects.filter(name=device_name).first()
                if device:
                    assignment, created = models.OverlayAssignment.objects.get_or_create(
                        overlay=mapping["overlay"],
                        assigned_object_type=device_content_type,
                        assigned_object_id=device.pk,
                        defaults={
                            "role": mapping["role"],
                            "status": assignment_status,
                        },
                    )
                    if created:
                        assignments_created += 1
                        self.stdout.write(f"  Created device assignment: {device.name} -> {mapping['overlay'].name}")

        # Create interface-level assignments for specific interfaces
        interface_overlay_mapping = [
            # GPU data interfaces to GPU Prod overlay
            {
                "device": "gpu-node-01",
                "interfaces": ["eth1", "eth2"],
                "overlay": overlays[0],
                "role": choices.OverlayAssignmentRoleChoices.COMPUTE,
            },
            {
                "device": "gpu-node-02",
                "interfaces": ["eth1", "eth2"],
                "overlay": overlays[0],
                "role": choices.OverlayAssignmentRoleChoices.COMPUTE,
            },
            # Storage interfaces
            {
                "device": "gpu-node-01",
                "interfaces": ["eth3"],
                "overlay": overlays[2],
                "role": choices.OverlayAssignmentRoleChoices.STORAGE,
            },
            {
                "device": "gpu-node-02",
                "interfaces": ["eth3"],
                "overlay": overlays[2],
                "role": choices.OverlayAssignmentRoleChoices.STORAGE,
            },
            # InfiniBand interfaces
            {
                "device": "hpc-node-01",
                "interfaces": ["ib0", "ib1"],
                "overlay": overlays[3],
                "role": choices.OverlayAssignmentRoleChoices.COMPUTE,
            },
            {
                "device": "hpc-node-02",
                "interfaces": ["ib0", "ib1"],
                "overlay": overlays[3],
                "role": choices.OverlayAssignmentRoleChoices.COMPUTE,
            },
        ]

        for mapping in interface_overlay_mapping:
            device = Device.objects.filter(name=mapping["device"]).first()
            if device:
                for iface_name in mapping["interfaces"]:
                    iface = Interface.objects.filter(device=device, name=iface_name).first()
                    if iface:
                        assignment, created = models.OverlayAssignment.objects.get_or_create(
                            overlay=mapping["overlay"],
                            assigned_object_type=interface_content_type,
                            assigned_object_id=iface.pk,
                            defaults={
                                "role": mapping["role"],
                                "status": assignment_status,
                            },
                        )
                        if created:
                            assignments_created += 1
                            self.stdout.write(
                                f"  Created interface assignment: {device.name}:{iface.name} -> {mapping['overlay'].name}"
                            )

        self.stdout.write(f"  Total overlay assignments created: {assignments_created}")

        # Print summary
        self.stdout.write("\nSummary:")
        self.stdout.write(f"  Overlays: {models.Overlay.objects.count()}")
        self.stdout.write(f"  VXLANs: {models.VXLAN.objects.count()}")
        self.stdout.write(f"  InfiniBand PKeys: {models.InfiniBandPKey.objects.count()}")
        self.stdout.write(f"  Overlay Assignments: {models.OverlayAssignment.objects.count()}")
        self.stdout.write(f"  Devices: {Device.objects.count()}")
        self.stdout.write(f"  Interfaces: {Interface.objects.count()}")
        self.stdout.write(f"  Racks: {Rack.objects.count()}")
        self.stdout.write(
            f"  VRF assignments: {models.OverlayAssignment.objects.filter(assigned_object_type__model='vrf').count()}"
        )

    def _create_superpod_data(self):
        """Create superpod-specific test data for VXLAN/EVPN configuration testing."""
        # Get statuses for all models (ensures content types are registered)
        overlay_status = self._get_or_create_status(models.Overlay)
        assignment_status = self._get_or_create_status(models.OverlayAssignment)
        vxlan_status = self._get_or_create_status(models.VXLAN)
        pkey_status = self._get_or_create_status(models.InfiniBandPKey)  # noqa: F841
        location_status = Status.objects.get_for_model(Location).first()
        vlan_status = Status.objects.get_for_model(VLAN).first()
        vrf_status = Status.objects.get_for_model(VRF).first()
        device_status = Status.objects.get_for_model(Device).filter(name="Active").first()
        if not device_status:
            device_status = Status.objects.get_for_model(Device).first()
        interface_status = Status.objects.get_for_model(Interface).filter(name="Active").first()
        if not interface_status:
            interface_status = Status.objects.get_for_model(Interface).first()

        # Create Superpod tenant
        self.stdout.write("\nCreating Superpod Tenant...")
        tenant_superpod, _ = Tenant.objects.get_or_create(name="Superpod")
        self.stdout.write(f"  Created/found tenant: {tenant_superpod}")

        # Create location hierarchy: Site -> Module
        self.stdout.write("\nCreating Location Hierarchy...")
        site_type, _ = LocationType.objects.get_or_create(name="Site")
        module_type, _ = LocationType.objects.get_or_create(name="Module", defaults={"parent": site_type})

        # Add content types to location types
        for loc_type in [site_type, module_type]:
            loc_type.content_types.add(ContentType.objects.get_for_model(Device))
            loc_type.content_types.add(ContentType.objects.get_for_model(VLAN))
            loc_type.content_types.add(ContentType.objects.get_for_model(Prefix))
            loc_type.content_types.add(ContentType.objects.get_for_model(Rack))

        site_mississippi, _ = Location.objects.get_or_create(
            name="MISSISSIPPI",
            defaults={"location_type": site_type, "status": location_status},
        )
        module_1, _ = Location.objects.get_or_create(
            name="MISSISSIPPI MODULE 1",
            defaults={"location_type": module_type, "status": location_status, "parent": site_mississippi},
        )
        self.stdout.write(f"  Created/found site: {site_mississippi}")
        self.stdout.write(f"  Created/found module: {module_1}")

        # Create Manufacturer and Device Type
        self.stdout.write("\nCreating Device Types...")
        nvidia_mfr, _ = Manufacturer.objects.get_or_create(name="NVIDIA")
        sn5600_type, _ = DeviceType.objects.get_or_create(
            manufacturer=nvidia_mfr,
            model="SN5600",
            defaults={"u_height": 1},
        )
        self.stdout.write(f"  Created/found device type: {sn5600_type}")

        # Create Superpod Device Roles
        self.stdout.write("\nCreating Superpod Device Roles...")
        device_role_ct = ContentType.objects.get_for_model(Device)
        superpod_roles_data = [
            {"name": "superpod-computeleaf", "color": "4caf50"},
            {"name": "superpod-borderleaf", "color": "2196f3"},
            {"name": "superpod-spine", "color": "ff9800"},
        ]
        device_roles = {}
        for data in superpod_roles_data:
            role, created = Role.objects.get_or_create(
                name=data["name"],
                defaults={"color": data["color"]},
            )
            role.content_types.add(device_role_ct)
            device_roles[data["name"]] = role
            action = "Created" if created else "Found"
            self.stdout.write(f"  {action} role: {role}")

        # Create or get namespace
        namespace = Namespace.objects.first() or Namespace.objects.create(name="Global")

        # Create Route Targets (matching superpod fixture patterns)
        self.stdout.write("\nCreating Route Targets...")
        route_targets_data = [
            {"name": "4001:4001", "description": "INBAND/STORAGE Import/Export RT"},
        ]
        route_targets = []
        for data in route_targets_data:
            rt, created = RouteTarget.objects.get_or_create(
                name=data["name"],
                defaults={"description": data["description"]},
            )
            route_targets.append(rt)
            action = "Created" if created else "Found"
            self.stdout.write(f"  {action} Route Target: {rt}")

        # Create VRFs (matching superpod fixture: INBAND, STORAGE, default, mgmt)
        self.stdout.write("\nCreating VRFs...")
        vrfs_data = [
            {
                "name": "INBAND",
                "rd": "10.0.7.226:1000",
                "tenant": tenant_superpod,
                "description": "Inband management VRF",
            },
            {
                "name": "STORAGE",
                "rd": "100.127.255.226:3000",
                "tenant": tenant_superpod,
                "description": "Storage traffic VRF",
            },
        ]
        vrfs = []
        for data in vrfs_data:
            vrf, created = VRF.objects.get_or_create(
                name=data["name"],
                namespace=namespace,
                defaults={
                    "rd": data["rd"],
                    "tenant": data["tenant"],
                    "description": data["description"],
                    "status": vrf_status,
                },
            )
            # Add route targets to VRF
            vrf.export_targets.add(route_targets[0])
            vrf.import_targets.add(route_targets[0])
            vrfs.append(vrf)
            action = "Created" if created else "Found"
            self.stdout.write(f"  {action} VRF: {vrf} (rd: {data['rd']})")

        # Create VLAN Group and VLANs
        self.stdout.write("\nCreating VLANs...")
        vlan_group, _ = VLANGroup.objects.get_or_create(
            name="Superpod-VLANs",
            defaults={"location": module_1},
        )

        vlans_data = [
            {"vid": 101, "name": "Internalnet", "tenant": tenant_superpod, "description": "Inband network VLAN"},
        ]
        vlans = []
        for data in vlans_data:
            vlan, created = VLAN.objects.get_or_create(
                vid=data["vid"],
                vlan_group=vlan_group,
                defaults={
                    "name": data["name"],
                    "tenant": data["tenant"],
                    "location": module_1,
                    "status": vlan_status,
                },
            )
            vlans.append(vlan)
            action = "Created" if created else "Found"
            self.stdout.write(f"  {action} VLAN: {vlan}")

        # Create Overlay
        self.stdout.write("\nCreating Superpod Overlay...")
        overlay, created = models.Overlay.objects.get_or_create(
            name="Superpod-Fabric",
            location=module_1,
            defaults={
                "tenant": tenant_superpod,
                "isolation_type": choices.IsolationTypeChoices.VXLAN_EVPN,
                "description": "Superpod VXLAN/EVPN overlay for testing",
                "status": overlay_status,
            },
        )
        action = "Created" if created else "Found"
        self.stdout.write(f"  {action} overlay: {overlay}")

        # Create VXLAN records - L2 VNI for VLAN and L3 VNI for VRFs
        self.stdout.write("\nCreating VXLAN VNI records...")
        vxlans_data = [
            # L2 VNI for VLAN 101
            {
                "vnid": 1001,
                "name": "L2-VNI-VLAN101",
                "vni_type": choices.VNITypeChoices.L2_VNI,
                "vlan": vlans[0],
                "vrf": None,
                "l3_vlan_id": None,
            },
            # L3 VNI for INBAND VRF
            {
                "vnid": 4001,
                "name": "L3-VNI-INBAND",
                "vni_type": choices.VNITypeChoices.L3_VNI,
                "vlan": None,
                "vrf": vrfs[0],  # INBAND
                "l3_vlan_id": 4001,
            },
            # L3 VNI for STORAGE VRF (same VNI as shown in fixture, different VRF)
            {
                "vnid": 4002,
                "name": "L3-VNI-STORAGE",
                "vni_type": choices.VNITypeChoices.L3_VNI,
                "vlan": None,
                "vrf": vrfs[1],  # STORAGE
                "l3_vlan_id": 4002,
            },
        ]

        vxlans = []
        for data in vxlans_data:
            vxlan, created = models.VXLAN.objects.get_or_create(
                vnid=data["vnid"],
                namespace=namespace,
                defaults={
                    "name": data["name"],
                    "vni_type": data["vni_type"],
                    "overlay": overlay,
                    "vlan": data["vlan"],
                    "vrf": data["vrf"],
                    "l3_vlan_id": data["l3_vlan_id"],
                    "tenant": tenant_superpod,
                    "status": vxlan_status,
                },
            )
            vxlans.append(vxlan)
            action = "Created" if created else "Found"
            vni_type_str = "L2" if data["vni_type"] == choices.VNITypeChoices.L2_VNI else "L3"
            self.stdout.write(f"  {action} VXLAN: VNI {vxlan.vnid} ({vni_type_str})")

        # Create Platform (Cumulus Linux)
        self.stdout.write("\nCreating Platform...")
        platform, created = Platform.objects.get_or_create(
            name="Cumulus Linux",
            defaults={
                "manufacturer": nvidia_mfr,
                "napalm_driver": "",
            },
        )
        action = "Created" if created else "Found"
        self.stdout.write(f"  {action} Platform: {platform}")

        # Get IP Address status
        ip_status = self._get_or_create_status(IPAddress, "Active")

        # Create Superpod Devices with full configuration
        self.stdout.write("\nCreating Superpod Devices...")
        devices_data = [
            {
                "name": "cleaf1-sp1-test",
                "role": device_roles["superpod-computeleaf"],
                "serial": "MT0000000013",
                "loopback_ip": "10.254.254.13/32",
                "bgp_asn": 4230000013,
            },
            {
                "name": "bleaf1-sp1-test",
                "role": device_roles["superpod-borderleaf"],
                "serial": "MT0000000016",
                "loopback_ip": "10.254.254.16/32",
                "bgp_asn": 4230000015,
            },
            {
                "name": "spine1-sp1-test",
                "role": device_roles["superpod-spine"],
                "serial": "MT0000000001",
                "loopback_ip": "10.254.254.2/32",
                "bgp_asn": 4230000001,
            },
        ]

        # Create Prefixes for all IP ranges
        prefix_status = self._get_or_create_status(Prefix, "Active")
        prefixes_to_create = [
            "10.254.254.0/24",  # Loopback IPs
            "10.254.1.0/24",  # Underlay P2P links (first block)
            "10.254.2.0/24",  # Underlay P2P links (second block)
            "100.127.1.0/24",  # Storage network P2P links
            "100.127.255.0/24",  # Storage VRF loopbacks
            "10.0.0.0/24",  # INBAND SVI addresses
        ]
        for prefix_str in prefixes_to_create:
            Prefix.objects.get_or_create(
                prefix=prefix_str,
                namespace=namespace,
                defaults={
                    "type": "network",
                    "status": prefix_status,
                },
            )

        devices = []
        device_interfaces = {}  # Store interfaces for IP assignment

        for data in devices_data:
            # Config context with BGP ASN matching fixture format
            config_context = {
                "bgp": {"asn": data["bgp_asn"]},
                "dhcp": {"superpod": {"ipv4": ["10.0.0.3", "10.0.0.4"]}},
                "intended-firmware": {"version": "5.14.0"},
            }

            device, created = Device.objects.get_or_create(
                name=data["name"],
                defaults={
                    "device_type": sn5600_type,
                    "role": data["role"],
                    "location": module_1,
                    "tenant": tenant_superpod,
                    "serial": data["serial"],
                    "status": device_status,
                    "platform": platform,
                    "local_config_context_data": config_context,
                },
            )
            # Update platform and config context if device already exists
            if not created:
                device.platform = platform
                device.local_config_context_data = config_context
                device.save()

            devices.append(device)
            device_interfaces[device.name] = {"loopback_ip": data["loopback_ip"]}
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action} device: {device} (role: {data['role'].name})")

        # Get VRFs by name for interface assignment
        vrf_inband = vrfs[0]  # INBAND
        vrf_storage = vrfs[1]  # STORAGE

        # Create comprehensive interfaces on devices (matching superpod patterns)
        self.stdout.write("\nCreating Interfaces and IP Addresses...")

        # Define interface configurations per device role
        borderleaf_interfaces = [
            {"name": "lo", "type": "virtual", "description": "", "mtu": 65536},
            # Spine uplinks
            {"name": "swp54", "type": "100gbase-x-qsfp28", "description": "", "mtu": 9216, "breakout": "2x"},
            {
                "name": "swp54s0",
                "type": "25gbase-x-sfp28",
                "description": "",
                "mtu": 9216,
                "parent": "swp54",
                "ip": "10.254.1.129/31",
            },
            {
                "name": "swp54s1",
                "type": "25gbase-x-sfp28",
                "description": "",
                "mtu": 9216,
                "parent": "swp54",
                "ip": "10.254.1.131/31",
            },
            # Storage interfaces
            {"name": "swp5", "type": "100gbase-x-qsfp28", "description": "", "mtu": 9216, "breakout": "4x"},
            {
                "name": "swp5s1",
                "type": "25gbase-x-sfp28",
                "description": "",
                "mtu": 9216,
                "parent": "swp5",
                "ip": "100.127.1.32/31",
                "vrf": "STORAGE",
            },
            {"name": "swp6", "type": "100gbase-x-qsfp28", "description": "", "mtu": 9216, "breakout": "4x"},
            {
                "name": "swp6s0",
                "type": "25gbase-x-sfp28",
                "description": "",
                "mtu": 9216,
                "parent": "swp6",
                "ip": "100.127.1.34/31",
                "vrf": "STORAGE",
            },
            # VLAN SVI
            {
                "name": "vlan101",
                "type": "virtual",
                "description": "Internalnet",
                "mtu": 9216,
                "ip": "10.0.0.2/24",
                "vrf": "INBAND",
                "untagged_vlan": 101,
            },
        ]

        computeleaf_interfaces = [
            {"name": "lo", "type": "virtual", "description": "", "mtu": 65536},
            # Spine uplinks
            {"name": "swp54", "type": "100gbase-x-qsfp28", "description": "", "mtu": 9216, "breakout": "2x"},
            {
                "name": "swp54s0",
                "type": "25gbase-x-sfp28",
                "description": "",
                "mtu": 9216,
                "parent": "swp54",
                "ip": "10.254.1.1/31",
            },
            {
                "name": "swp54s1",
                "type": "25gbase-x-sfp28",
                "description": "",
                "mtu": 9216,
                "parent": "swp54",
                "ip": "10.254.1.3/31",
            },
            # VLAN SVI
            {
                "name": "vlan101",
                "type": "virtual",
                "description": "Internalnet",
                "mtu": 9216,
                "ip": "10.0.0.1/24",
                "vrf": "INBAND",
                "untagged_vlan": 101,
            },
        ]

        spine_interfaces = [
            {"name": "lo", "type": "virtual", "description": "", "mtu": 65536},
            # Downlinks to leafs
            {"name": "swp1", "type": "100gbase-x-qsfp28", "description": "", "mtu": 9216, "breakout": "2x"},
            {
                "name": "swp1s0",
                "type": "25gbase-x-sfp28",
                "description": "",
                "mtu": 9216,
                "parent": "swp1",
                "ip": "10.254.1.0/31",
            },
            {
                "name": "swp1s1",
                "type": "25gbase-x-sfp28",
                "description": "",
                "mtu": 9216,
                "parent": "swp1",
                "ip": "10.254.1.2/31",
            },
            {"name": "swp10", "type": "100gbase-x-qsfp28", "description": "", "mtu": 9216, "breakout": "2x"},
            {
                "name": "swp10s0",
                "type": "25gbase-x-sfp28",
                "description": "",
                "mtu": 9216,
                "parent": "swp10",
                "ip": "10.254.1.128/31",
            },
            {
                "name": "swp10s1",
                "type": "25gbase-x-sfp28",
                "description": "",
                "mtu": 9216,
                "parent": "swp10",
                "ip": "10.254.1.130/31",
            },
        ]

        interfaces_created = 0
        ips_created = 0

        # Map device roles to interface configs
        role_interface_map = {
            "superpod-borderleaf": borderleaf_interfaces,
            "superpod-computeleaf": computeleaf_interfaces,
            "superpod-spine": spine_interfaces,
        }

        for device in devices:
            interface_configs = role_interface_map.get(device.role.name, [])
            device_ifaces = {}  # Store created interfaces for parent lookup

            for iface_config in interface_configs:
                # Determine parent interface
                parent_iface = None
                if "parent" in iface_config:
                    parent_iface = device_ifaces.get(iface_config["parent"])

                # Determine VRF
                iface_vrf = None
                if "vrf" in iface_config:
                    if iface_config["vrf"] == "INBAND":
                        iface_vrf = vrf_inband
                    elif iface_config["vrf"] == "STORAGE":
                        iface_vrf = vrf_storage

                # Determine untagged VLAN
                untagged_vlan = None
                if "untagged_vlan" in iface_config:
                    untagged_vlan = vlans[0]  # VLAN 101

                iface, created = Interface.objects.get_or_create(
                    device=device,
                    name=iface_config["name"],
                    defaults={
                        "type": iface_config["type"],
                        "description": iface_config.get("description", ""),
                        "mtu": iface_config.get("mtu", 1500),
                        "status": interface_status,
                        "parent_interface": parent_iface,
                        "vrf": iface_vrf,
                        "untagged_vlan": untagged_vlan,
                    },
                )
                device_ifaces[iface_config["name"]] = iface

                if created:
                    interfaces_created += 1

                # Create IP address if specified
                if "ip" in iface_config:
                    ip_addr, ip_created = IPAddress.objects.get_or_create(
                        address=iface_config["ip"],
                        namespace=namespace,
                        defaults={
                            "status": ip_status,
                        },
                    )
                    # Assign IP to interface
                    ip_addr.interfaces.add(iface)
                    if ip_created:
                        ips_created += 1

            # Create loopback IP and assign to device
            lo_iface = device_ifaces.get("lo")
            if lo_iface:
                loopback_ip = device_interfaces[device.name]["loopback_ip"]
                lo_ip, ip_created = IPAddress.objects.get_or_create(
                    address=loopback_ip,
                    namespace=namespace,
                    defaults={
                        "status": ip_status,
                    },
                )
                lo_ip.interfaces.add(lo_iface)
                if ip_created:
                    ips_created += 1

                # Set as primary IP for device
                device.primary_ip4 = lo_ip
                device.save()

        self.stdout.write(f"  Created {interfaces_created} interfaces")
        self.stdout.write(f"  Created {ips_created} IP addresses")

        # Create Overlay Assignments
        self.stdout.write("\nCreating Overlay Assignments...")
        device_content_type = ContentType.objects.get_for_model(Device)

        device_role_mapping = {
            "superpod-computeleaf": choices.OverlayAssignmentRoleChoices.LEAF,
            "superpod-borderleaf": choices.OverlayAssignmentRoleChoices.LEAF,
            "superpod-spine": choices.OverlayAssignmentRoleChoices.SPINE,
        }

        assignments_created = 0
        for device in devices:
            assignment_role = device_role_mapping.get(device.role.name, choices.OverlayAssignmentRoleChoices.COMPUTE)
            assignment, created = models.OverlayAssignment.objects.get_or_create(
                overlay=overlay,
                assigned_object_type=device_content_type,
                assigned_object_id=device.pk,
                defaults={
                    "role": assignment_role,
                    "status": assignment_status,
                },
            )
            if created:
                assignments_created += 1
                self.stdout.write(f"  Created assignment: {device.name} -> {overlay.name} (role: {assignment_role})")

        # Print summary
        self.stdout.write("\n" + "=" * 50)
        self.stdout.write("SUPERPOD DATA SUMMARY")
        self.stdout.write("=" * 50)
        self.stdout.write(f"  Tenant: {tenant_superpod}")
        self.stdout.write(f"  Location: {module_1} (parent: {site_mississippi})")
        self.stdout.write(f"  Platform: {platform}")
        self.stdout.write(f"  Overlay: {overlay.name}")
        self.stdout.write(f"  VRFs: {[v.name for v in vrfs]} (tracked via VXLAN VNI records)")
        self.stdout.write(f"  VLANs: {[f'VLAN{v.vid}' for v in vlans]} (tracked via VXLAN VNI records)")
        self.stdout.write("\nVXLAN VNI Assignments:")
        for vxlan in vxlans:
            if vxlan.vni_type == choices.VNITypeChoices.L2_VNI:
                self.stdout.write(f"  - L2 VNI {vxlan.vnid} -> VLAN {vxlan.vlan.vid if vxlan.vlan else 'N/A'}")
            else:
                self.stdout.write(
                    f"  - L3 VNI {vxlan.vnid} -> VRF {vxlan.vrf.name if vxlan.vrf else 'N/A'} "
                    f"(L3 VLAN: {vxlan.l3_vlan_id})"
                )
        self.stdout.write("\nDevices in Overlay:")
        for device in devices:
            self.stdout.write(f"  - {device.name} ({device.role.name}) - Primary IP: {device.primary_ip4}")
        self.stdout.write("=" * 50)
