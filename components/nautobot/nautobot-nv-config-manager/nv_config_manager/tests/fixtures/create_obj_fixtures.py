#  SPDX-FileCopyrightText: Copyright (c) "2025" NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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
"""Create fixtures for tests."""

import factory.random
from django.contrib.contenttypes.models import ContentType
from django.utils.crypto import get_random_string
from nautobot.core.choices import ColorChoices
from nautobot.dcim.models import (
    Device,
    DeviceType,
    Interface,
    Location,
    LocationType,
    Manufacturer,
    Platform,
    Rack,
)
from nautobot.extras.models import Role, Status
from nautobot.ipam.models import IPAddress, Namespace
from nautobot.tenancy.models import Tenant

from nv_config_manager.models import (
    BackupConfig,
    ConfigManagerDeviceStatus,
    IntendedConfig,
)
from nv_config_manager.tests.fixtures import mock_data as data


def create_device_with_ip(device_data, ip_address, namespace, interface_name="eth0"):
    """Create a device with a primary IPv4 address and interface."""
    device = Device.objects.create(**device_data)
    interface_status = Status.objects.get_for_model(Interface).first()
    ip_status = Status.objects.get_for_model(IPAddress).first()

    interface = Interface.objects.create(
        device=device,
        name=interface_name,
        status=interface_status,
    )
    ip_obj = IPAddress.objects.create(
        address=ip_address,
        namespace=namespace,
        status=ip_status,
    )

    ip_obj.primary_ip4 = device
    interface.ip_addresses.add(ip_obj)

    device.primary_ip4 = ip_obj
    device.validated_save()


def create_managed_device_and_config(device, create_backup=False):
    """Create ConfigManagerDeviceStatus and IntendedConfig for a given device."""
    managed_device, _ = ConfigManagerDeviceStatus.objects.get_or_create(device=device)
    _ = IntendedConfig.objects.get_or_create(
        device_id=managed_device,
        config_store_instance=data.CONFIG_STORE_UI_URL,
        path=data.CONFIG_PATH,
        commit_id=data.TEST_INTENDED_COMMIT_ID,
        updated="2025-01-08T04:45:01Z",
        updated_by=data.TEST_RENDER_USER,
        commit_message=data.TEST_COMMIT_MESSAGE,
        template_version=data.TEMPLATE_VERSION,
    )

    if create_backup:
        _ = BackupConfig.objects.get_or_create(
            device_id=managed_device,
            config_store_instance=data.CONFIG_STORE_UI_URL,
            path=data.BACKUP_CONFIG_PATH,
            commit_id=data.TEST_BACKUP_COMMIT_ID,
            deployed_commit_id=data.TEST_PENDING_DEPLOYED_COMMIT_ID,
            workflow_id=data.TEST_WORKFLOW_ID,
            updated="2025-01-08T06:12:41Z",
            updated_by=data.TEST_RENDER_USER,
            commit_message=data.TEST_BACKUP_COMMIT_MESSAGE,
        )


def create_managed_device_with_config_store(device, create_backup=False):
    """Create ConfigManagerDeviceStatus and IntendedConfig using a config store.

    Config store fields:
    - config_store_instance: Base URL of the config store UI
    - path: Filename (e.g., startup.yaml)
    - commit_id: Config Store version number
    """
    managed_device, _ = ConfigManagerDeviceStatus.objects.get_or_create(device=device)
    _ = IntendedConfig.objects.get_or_create(
        device_id=managed_device,
        config_store_instance=data.CONFIG_STORE_UI_URL,
        path=data.CONFIG_PATH,
        commit_id=data.TEST_INTENDED_COMMIT_ID,
        updated="2025-01-08T04:45:01Z",
        updated_by=data.TEST_RENDER_USER,
        commit_message=data.TEST_COMMIT_MESSAGE,
        template_version=data.TEMPLATE_VERSION,
    )

    if create_backup:
        _ = BackupConfig.objects.get_or_create(
            device_id=managed_device,
            config_store_instance=data.CONFIG_STORE_UI_URL,
            path=data.BACKUP_CONFIG_PATH,
            commit_id=data.TEST_BACKUP_COMMIT_ID,
            deployed_commit_id=data.TEST_INTENDED_COMMIT_ID,
            workflow_id=data.TEST_WORKFLOW_ID,
            updated="2025-01-08T06:12:41Z",
            updated_by=data.TEST_RENDER_USER,
            commit_message=data.TEST_BACKUP_COMMIT_MESSAGE,
        )


def create_nested_locations():  # pylint: disable=too-many-locals
    """Create nested locations with managed devices."""

    region_type, _ = LocationType.objects.get_or_create(name="Region")
    site_type, _ = LocationType.objects.get_or_create(name="Site", parent=region_type)
    building_type, _ = LocationType.objects.get_or_create(name="Data Center", parent=site_type)
    floor_type, _ = LocationType.objects.get_or_create(name="Floor", parent=building_type)
    room_type, _ = LocationType.objects.get_or_create(name="Room", parent=floor_type)

    location_status = Status.objects.get_for_model(Location).first()

    region, _ = Location.objects.get_or_create(name=data.REGION_NAME, status=location_status, location_type=region_type)
    site, _ = Location.objects.get_or_create(
        name=data.SITE_NAME, parent=region, status=location_status, location_type=site_type
    )

    building, _ = Location.objects.get_or_create(
        name=data.BUILDING_NAME,
        parent=site,
        status=location_status,
        location_type=building_type,
    )
    floor, _ = Location.objects.get_or_create(
        name=data.FLOOR_NAME,
        parent=building,
        status=location_status,
        location_type=floor_type,
    )
    room, _ = Location.objects.get_or_create(
        name=data.ROOM_NAME, parent=floor, status=location_status, location_type=room_type
    )

    tenant, _ = Tenant.objects.get_or_create(name=data.TENANT_NAME)
    tenant.locations.add(site)

    spine_role, _ = Role.objects.get_or_create(name=data.SPINE_ROLE_NAME)
    leaf_role, _ = Role.objects.get_or_create(name=data.LEAF_ROLE_NAME)
    manufacturer, _ = Manufacturer.objects.get_or_create(name=data.MANUFACTURER_NAME)
    platform, _ = Platform.objects.get_or_create(name=data.PLATFORM_NAME, napalm_driver="cumulus")
    device_type, _ = DeviceType.objects.get_or_create(
        manufacturer=manufacturer, model=data.DEVICE_TYPE_MODEL, u_height="2"
    )

    device_status = Status.objects.get_for_model(Device).first()

    device_1, _ = Device.objects.get_or_create(
        name=data.THIRD_DEVICE_NAME,
        location=building,
        tenant=tenant,
        device_type=device_type,
        role=spine_role,
        status=device_status,
        position="1",
        face="front",
        platform=platform,
        serial="SP101001",
    )
    device_2, _ = Device.objects.get_or_create(
        name=data.DEVICE_NAME,
        location=room,
        tenant=tenant,
        device_type=device_type,
        role=leaf_role,
        status=device_status,
        position="2",
        face="front",
        platform=platform,
        serial="LF101002",
    )
    device_3, _ = Device.objects.get_or_create(
        name=data.SECOND_DEVICE_NAME,
        location=floor,
        tenant=tenant,
        device_type=device_type,
        role=spine_role,
        status=device_status,
        position="1",
        face="front",
        platform=platform,
        serial="LF101003",
    )

    # Managed-device status for devices
    _ = ConfigManagerDeviceStatus.objects.get_or_create(device=device_1)
    _ = ConfigManagerDeviceStatus.objects.get_or_create(device=device_2)
    _ = ConfigManagerDeviceStatus.objects.get_or_create(device=device_3)


def create_env(seed: str | None = None, with_demo_objects: bool = False):  # pylint: disable=R0914,R0915
    """Populate Environment with basic Locations, Manufactures, Templates, etc."""

    if seed is None:
        seed = get_random_string(16)
    factory.random.reseed_random(seed)

    print("Creating Region and Site location types...")
    location_status = Status.objects.get_for_model(Location).first()
    provider_type = LocationType.objects.create(name="Provider")
    region_type = LocationType.objects.create(name="Region", nestable=True, parent=provider_type)
    site_type = LocationType.objects.create(
        name="Site",
        parent=region_type,
    )
    site_type.content_types.set([ContentType.objects.get_for_model(Device)])
    module_type = LocationType.objects.create(name="Module", parent=site_type)
    module_type.content_types.set([ContentType.objects.get_for_model(Device)])

    print("Creating Region, Site, and Module locations...")
    region = Location.objects.create(
        name=data.REGION_NAME,
        location_type=region_type,
        status=location_status,
    )
    site = Location.objects.create(
        name=data.SITE_NAME,
        parent=region,
        location_type=site_type,
        status=location_status,
    )
    module = Location.objects.create(
        name=data.MODULE_NAME,
        parent=site,
        status=location_status,
        location_type=module_type,
    )

    print("Creating tenant...")
    tenant = Tenant.objects.create(name=data.TENANT_NAME)
    tenant.locations.add(site)
    tenant.locations.add(module)

    print("Creating 2 Racks...")
    rack_status = Status.objects.get_for_model(Rack).first()
    rack1 = Rack.objects.create(
        name=data.RACK_1_NAME,
        u_height=52,
        location=module,
        tenant=tenant,
        status=rack_status,
    )
    rack2 = Rack.objects.create(
        name=data.RACK_2_NAME,
        u_height=52,
        location=module,
        tenant=tenant,
        status=rack_status,
    )

    print("Creating 4 Roles for devices...")
    role_colors = factory.random.randgen.sample(ColorChoices.CHOICES, 4)
    roles = {
        "spine": Role.objects.create(name=data.SPINE_ROLE_NAME, color=role_colors[0][0]),
        "core": Role.objects.create(name=data.CORE_ROLE_NAME, color=role_colors[1][0]),
        "leaf": Role.objects.create(name=data.LEAF_ROLE_NAME, color=role_colors[2][0]),
        "arista_leaf": Role.objects.create(name=data.ARISTA_LEAF_ROLE_NAME, color=role_colors[3][0]),
    }
    for role in roles.values():
        role.content_types.set([ContentType.objects.get_for_model(Device)])

    print("Creating Provisioned status...")
    provisioned_status = Status.objects.create(
        name="Provisioned",
        description="Provisioned",
        color=factory.random.randgen.choice(ColorChoices.CHOICES)[0],
    )
    provisioned_status.content_types.set([ContentType.objects.get_for_model(Device)])

    print("Creating 2 Platforms...")
    platforms = {
        "cumulus": Platform.objects.create(name=data.PLATFORM_NAME, napalm_driver="cumulus"),
        "arista": Platform.objects.create(name=data.ARISTA_PLATFORM_NAME, napalm_driver="eos"),
    }

    print("Creating 2 Manufacturers...")
    mfgr_nvidia = Manufacturer.objects.create(name=data.MANUFACTURER_NAME)
    mfgr_arista = Manufacturer.objects.create(name=data.SECOND_MANUFACTURER_NAME)

    print("Creating 2 DeviceTypes...")
    cumulus_type = DeviceType.objects.create(
        manufacturer=mfgr_nvidia,
        model=data.DEVICE_TYPE_MODEL,
        u_height=2,
    )
    arista_type = DeviceType.objects.create(
        manufacturer=mfgr_arista,
        model=data.ARISTA_DEVICE_TYPE_MODEL,
        u_height=1,
    )

    print("Creating 5 Devices...")
    demo_namespace = Namespace.objects.filter(prefixes__network="10.1.0.0").first()
    cumulus_device_names = [data.THIRD_DEVICE_NAME, data.FOURTH_DEVICE_NAME, data.DEVICE_NAME]
    for i, role in enumerate(["spine", "core", "leaf"]):
        create_device_with_ip(
            {
                "name": cumulus_device_names[i],
                "rack": rack2 if role == "core" else rack1,
                "role": roles[role],
                "position": 40 - (i * 8),
                "face": "front",
                "location": module,
                "tenant": tenant,
                "device_type": cumulus_type,
                "status": provisioned_status,
                "platform": platforms["cumulus"],
            },
            f"10.1.0.{i + 1}/24",
            demo_namespace,
        )
    for i in range(2):
        create_device_with_ip(
            {
                "name": [data.ARISTA_DEVICE_NAME, data.SECOND_ARISTA_DEVICE_NAME][i],
                "rack": rack1 if i == 0 else rack2,
                "role": roles["arista_leaf"],
                "position": 42 + (1 * 2),
                "face": "front",
                "location": module,
                "tenant": tenant,
                "device_type": arista_type,
                "status": provisioned_status,
                "platform": platforms["arista"],
            },
            f"10.1.0.{i + 4}/24",
            demo_namespace,
        )

    if with_demo_objects:
        print("Creating 7 demo managed-device objects using config store...")
        devices = Device.objects.all()
        for device in devices:
            create_managed_device_with_config_store(device, device in [devices.first(), devices.last()])
