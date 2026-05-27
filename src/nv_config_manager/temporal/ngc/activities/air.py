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
"""AIR Simulation Activities."""

from __future__ import annotations

import hashlib
from io import StringIO
from typing import Any

from pydantic import BaseModel
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError
from temporalio import activity

from nv_config_manager.common.log import LogCategory, get_logger
from nv_config_manager.temporal.client.air import AirClient, AirDevice
from nv_config_manager.temporal.client.device import ConfigSyntaxException, CumulusConnection
from nv_config_manager.temporal.client.nautobot import NautobotClient

logger = get_logger(__name__, category=LogCategory.TEMPORAL_ACTIVITY)


class CreateSimulationInput(BaseModel):
    """Input for create_simulation activity."""

    simulation_name: str
    topology: dict[str, Any]


class CreateSimulationOutput(BaseModel):
    """Output for create_simulation activity."""

    simulation_id: str


class PrepareSimulationNodesInput(BaseModel):
    """Input for prepare_simulation_nodes activity."""

    simulation_id: str


class StartSimulationInput(BaseModel):
    """Input for start_simulation activity."""

    simulation_id: str


class CreateSimulationNodeServicesInput(BaseModel):
    """Input for create_simulation_node_services activity."""

    simulation_id: str


class CreateSimulationNodeServicesOutput(BaseModel):
    """Output for create_simulation_node_services activity."""

    devices: list[AirDevice]


class WaitForSimulationNodeInput(BaseModel):
    """Input for wait_for_simulation_node activity."""

    node: AirDevice


class DeleteSimulationInput(BaseModel):
    """Input for delete_simulation activity."""

    simulation_id: str


@activity.defn
def create_simulation(
    input: CreateSimulationInput,
) -> CreateSimulationOutput:
    """Create a new AIR simulation with the specified topology.

    Args:
        input: CreateSimulationInput containing simulation name and topology

    Returns:
        CreateSimulationOutput containing the simulation ID

    Raises:
        air_sdk.exceptions.AirApiError: If simulation creation fails
    """
    client = AirClient()
    simulation_id = client.create_simulation(input.simulation_name, input.topology)
    return CreateSimulationOutput(simulation_id=simulation_id)


@activity.defn
def prepare_simulation_nodes(input: PrepareSimulationNodesInput) -> None:
    """Prepare simulation nodes by creating eth0 interfaces and setting up NVIDIA Config Manager accounts.

    This activity:
    1. Creates eth0 outbound interfaces for all nodes that don't have one
    2. Creates NVIDIA Config Manager accounts with default passwords for all nodes
    3. Resets all nodes to apply the changes

    Args:
        input: PrepareSimulationNodesInput containing the simulation ID

    Raises:
        air_sdk.exceptions.AirApiError: If node preparation fails
    """
    client = AirClient()
    client.prepare_simulation_nodes(input.simulation_id)


@activity.defn
def start_simulation(input: StartSimulationInput) -> None:
    """Start a simulation and wait for it to be fully loaded.

    Args:
        input: StartSimulationInput containing the simulation ID

    Raises:
        air_sdk.exceptions.AirApiError: If simulation start fails
    """
    client = AirClient()
    client.start_simulation(input.simulation_id)


@activity.defn
def create_simulation_node_services(
    input: CreateSimulationNodeServicesInput,
) -> CreateSimulationNodeServicesOutput:
    """Create HTTPS services for all nodes in a simulation.

    This activity:
    1. Creates HTTPS services on eth0 interfaces for all nodes
    2. Resolves hostnames to IP addresses
    3. Returns a list of configured devices with their connection details

    Args:
        input: CreateSimulationNodeServicesInput containing the simulation ID

    Returns:
        CreateSimulationNodeServicesOutput containing the list of configured devices

    Raises:
        air_sdk.exceptions.AirApiError: If service creation fails
        socket.gaierror: If hostname resolution fails
    """
    client = AirClient()
    devices = client.create_simulation_node_services(input.simulation_id)
    return CreateSimulationNodeServicesOutput(devices=devices)


@activity.defn
def wait_for_simulation_node(input: WaitForSimulationNodeInput) -> None:
    """Wait for a simulation node to be ready and accessible.

    This activity:
    1. Waits for the node to be in RUNNING state
    2. Attempts to connect to the node's API
    3. Rebuilds the node if connection fails

    Args:
        input: WaitForSimulationNodeInput containing the node to wait for

    Raises:
        requests.exceptions.RequestException: If API connection fails
        air_sdk.exceptions.AirApiError: If node rebuild fails
    """
    client = AirClient()
    client.wait_for_simulation_node(input.node)


@activity.defn
def delete_simulation(input: DeleteSimulationInput) -> None:
    """Delete an AIR simulation.

    Args:
        input: DeleteSimulationInput containing the simulation ID

    Raises:
        air_sdk.exceptions.AirApiError: If simulation deletion fails
    """
    client = AirClient()
    client.delete_simulation(input.simulation_id)


class ConfigTestInput(BaseModel):
    """Input for test_configuration_against_air_device activity."""

    node: AirDevice
    config: str


class ConfigTestOutput(BaseModel):
    """Output for test_configuration_against_air_device activity."""

    error: str | None


def _sanitize_config(config: str, air_user: str, air_password: str) -> str:
    """Sanitize a configuration string by removing sensitive information."""
    # NVUE (cumulus/nvos) only for now
    # Communication with AIR does not happen over our private VPN tunnels
    # nor do we have a way to validate that the node we're sending config to
    # is genuinely from AIR, therefore we should strip any production secrets
    # prior to testing the configuration against the node
    try:
        config_obj = YAML().load(config)
        # Replace any passwords or hashed passwords with dummy data
        dummy_password = "DuMMyP4SSW0RD!"
        dummy_hash = hashlib.sha512(dummy_password.encode()).hexdigest()

        def _replace_passwords(obj: dict[str, Any] | list[Any]) -> None:
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if key in ["password", "hashed-password", "secret"]:
                        obj[key] = dummy_hash if key == "hashed-password" else dummy_password
                    elif isinstance(value, dict | list):
                        _replace_passwords(value)
            elif isinstance(obj, list):
                for item in obj:
                    if isinstance(item, dict | list):
                        _replace_passwords(item)

        _replace_passwords(config_obj)

        # Blow away any local user accounts
        # and replace with air user
        if config_obj[0]["set"]["system"]["aaa"]["user"]:
            config_obj[0]["set"]["system"]["aaa"]["user"] = {
                air_user: {
                    "password": air_password,
                    "role": "system-admin",
                }
            }

        yaml_config_stream = StringIO()
        YAML().dump(config_obj, yaml_config_stream)
        return yaml_config_stream.getvalue()
    except (KeyError, IndexError, YAMLError) as exc:
        raise ConfigSyntaxException("Invalid yaml loaded from the Config Store.") from exc


@activity.defn
def validate_configuration_against_air_device(
    input: ConfigTestInput,
) -> ConfigTestOutput:
    """Test a configuration against an AIR device."""
    # For now we're only supporting Cumulus
    client = AirClient()
    air_user = client.cfg["temporal.air"]["air_node_user"]
    air_password = client.cfg["temporal.air"]["air_node_password"]
    connection = CumulusConnection(
        input.node.worker_ip, input.node.api_port, air_user, air_password
    )
    sanitized_config = _sanitize_config(input.config, air_user, air_password)
    error = None
    try:
        connection.perform_candidate_diff(sanitized_config)
    except Exception as e:
        error = str(e)
    return ConfigTestOutput(error=error)


@activity.defn
def generate_air_topology_for_location(location_id: str) -> dict[str, Any]:
    """Generate AIR topology for a location."""
    # TODO: GraphQL query to get requisite data
    return {
        "oob": False,
        "nodes": {
            "aggleaf1-gp1-smn1-sitea": {
                "memory": 4096,
                "os": "cumulus-vx-5.11.0",
                "cpu": 2,
            },
            "core1-cp1-smn1-sitea": {
                "memory": 4096,
                "os": "cumulus-vx-5.11.0",
                "cpu": 2,
            },
            "leaf1-cp1-smn1-sitea": {
                "memory": 4096,
                "os": "cumulus-vx-5.11.0",
                "cpu": 2,
            },
            "spine1-cp1-smn1-sitea": {
                "memory": 4096,
                "os": "cumulus-vx-5.11.0",
                "cpu": 2,
            },
        },
        "links": [
            [{"node": "aggleaf1-gp1-smn1-sitea", "interface": "swp1"}, "unconnected"],
            [{"node": "aggleaf1-gp1-smn1-sitea", "interface": "swp2"}, "unconnected"],
            [{"node": "aggleaf1-gp1-smn1-sitea", "interface": "swp3"}, "unconnected"],
            [{"node": "aggleaf1-gp1-smn1-sitea", "interface": "swp4"}, "unconnected"],
            [{"node": "aggleaf1-gp1-smn1-sitea", "interface": "swp5"}, "unconnected"],
            [{"node": "aggleaf1-gp1-smn1-sitea", "interface": "swp6"}, "unconnected"],
            [{"node": "aggleaf1-gp1-smn1-sitea", "interface": "swp7"}, "unconnected"],
            [{"node": "aggleaf1-gp1-smn1-sitea", "interface": "swp8"}, "unconnected"],
            [{"node": "aggleaf1-gp1-smn1-sitea", "interface": "swp9"}, "unconnected"],
            [{"node": "aggleaf1-gp1-smn1-sitea", "interface": "swp10"}, "unconnected"],
            [{"node": "aggleaf1-gp1-smn1-sitea", "interface": "swp11"}, "unconnected"],
            [{"node": "aggleaf1-gp1-smn1-sitea", "interface": "swp12"}, "unconnected"],
            [{"node": "core1-cp1-smn1-sitea", "interface": "swp1"}, "unconnected"],
            [{"node": "core1-cp1-smn1-sitea", "interface": "swp2"}, "unconnected"],
            [{"node": "core1-cp1-smn1-sitea", "interface": "swp3"}, "unconnected"],
            [{"node": "core1-cp1-smn1-sitea", "interface": "swp4"}, "unconnected"],
            [{"node": "core1-cp1-smn1-sitea", "interface": "swp5"}, "unconnected"],
            [{"node": "core1-cp1-smn1-sitea", "interface": "swp6"}, "unconnected"],
            [{"node": "core1-cp1-smn1-sitea", "interface": "swp7"}, "unconnected"],
            [{"node": "core1-cp1-smn1-sitea", "interface": "swp8"}, "unconnected"],
            [{"node": "core1-cp1-smn1-sitea", "interface": "swp9"}, "unconnected"],
            [{"node": "core1-cp1-smn1-sitea", "interface": "swp10"}, "unconnected"],
            [{"node": "core1-cp1-smn1-sitea", "interface": "swp11"}, "unconnected"],
            [{"node": "core1-cp1-smn1-sitea", "interface": "swp12"}, "unconnected"],
            [{"node": "leaf1-cp1-smn1-sitea", "interface": "swp1"}, "unconnected"],
            [{"node": "leaf1-cp1-smn1-sitea", "interface": "swp2"}, "unconnected"],
            [{"node": "leaf1-cp1-smn1-sitea", "interface": "swp3"}, "unconnected"],
            [{"node": "leaf1-cp1-smn1-sitea", "interface": "swp4"}, "unconnected"],
            [{"node": "leaf1-cp1-smn1-sitea", "interface": "swp5"}, "unconnected"],
            [{"node": "leaf1-cp1-smn1-sitea", "interface": "swp6"}, "unconnected"],
            [{"node": "leaf1-cp1-smn1-sitea", "interface": "swp7"}, "unconnected"],
            [{"node": "leaf1-cp1-smn1-sitea", "interface": "swp8"}, "unconnected"],
            [{"node": "leaf1-cp1-smn1-sitea", "interface": "swp9"}, "unconnected"],
            [{"node": "leaf1-cp1-smn1-sitea", "interface": "swp10"}, "unconnected"],
            [{"node": "leaf1-cp1-smn1-sitea", "interface": "swp11"}, "unconnected"],
            [{"node": "leaf1-cp1-smn1-sitea", "interface": "swp12"}, "unconnected"],
            [{"node": "spine1-cp1-smn1-sitea", "interface": "swp1"}, "unconnected"],
            [{"node": "spine1-cp1-smn1-sitea", "interface": "swp2"}, "unconnected"],
            [{"node": "spine1-cp1-smn1-sitea", "interface": "swp3"}, "unconnected"],
            [{"node": "spine1-cp1-smn1-sitea", "interface": "swp4"}, "unconnected"],
            [{"node": "spine1-cp1-smn1-sitea", "interface": "swp5"}, "unconnected"],
            [{"node": "spine1-cp1-smn1-sitea", "interface": "swp6"}, "unconnected"],
            [{"node": "spine1-cp1-smn1-sitea", "interface": "swp7"}, "unconnected"],
            [{"node": "spine1-cp1-smn1-sitea", "interface": "swp8"}, "unconnected"],
            [{"node": "spine1-cp1-smn1-sitea", "interface": "swp9"}, "unconnected"],
            [{"node": "spine1-cp1-smn1-sitea", "interface": "swp10"}, "unconnected"],
            [{"node": "spine1-cp1-smn1-sitea", "interface": "swp11"}, "unconnected"],
            [{"node": "spine1-cp1-smn1-sitea", "interface": "swp12"}, "unconnected"],
        ],
    }


class MinimalTopologyInput(BaseModel):
    """Minimal Topology Input."""

    site_name: str


class MinimalTopologyOutput(BaseModel):
    topology: dict[str, Any]
    node_map: dict[str, str]


@activity.defn
async def generate_minimal_topology_for_site(
    activity_input: MinimalTopologyInput,
) -> MinimalTopologyOutput:
    """Generate minimal topology for a site."""
    managed_devices = []
    query = """
query($location: [String]!) {
  devices(nv_config_manager_device_status: true, platform: "Cumulus Linux", location: $location) {
    id
    name
    config_context
    role {
      name
    }
    device_type {
      model
    }
    interfaces {
      name
      type
    }
    configmanagerdevicestatus {
      intended_config {
        path
      }
    }
  }
}
"""
    client = NautobotClient()
    async with client:
        response = await client.graphql_query(
            query, {"location": [activity_input.site_name]}, timeout=30
        )
    for device in response["data"]["devices"]:
        if not device["configmanagerdevicestatus"]["intended_config"]:
            continue
        # Virtual interfaces are not needed for the topology
        # We want eth0 to be created as part of the simulation bringup
        # to set it up properly as the outbound interface for landing
        # the API service
        physical_interfaces = {
            interface["name"]
            for interface in device["interfaces"]
            if interface["type"] != "VIRTUAL" and interface["name"] != "eth0"
        }
        managed_devices.append(
            {
                "id": device["id"],
                "name": device["name"],
                "role": device["role"]["name"],
                "image": device["config_context"]["intended-firmware"]["version"],
                "model": device["device_type"]["model"],
                "interfaces": physical_interfaces,
            }
        )

    # Group devices to smallest set of AIR nodes
    device_groups = {}
    node_map = {}
    for device in managed_devices:
        key = "-".join((device["model"], device["role"], device["image"])).replace(".", "-")
        if key not in device_groups:
            device_groups[key] = {
                "interfaces": set(),
                "image": device["image"],
                "devices": [],
            }
        device_groups[key]["interfaces"] |= device["interfaces"]
        device_groups[key]["devices"].append(device)
        node_map[device["id"]] = key
    topology: dict[str, Any] = {"oob": False, "nodes": {}, "links": []}

    # Create a node for each device group
    for group_key, group_data in device_groups.items():
        # Create a representative node name from the group key
        node_name = group_key

        # Add node with specified resources
        mem = 4 * 1024
        topology["nodes"][node_name] = {
            "memory": mem,
            "cpu": 4,
            "os": f"cumulus-vx-{group_data['image']}",
        }

        # Add unconnected interfaces for each interface in the group
        for interface in group_data["interfaces"]:
            topology["links"].append([{"node": node_name, "interface": interface}, "unconnected"])

    return MinimalTopologyOutput(topology=topology, node_map=node_map)
