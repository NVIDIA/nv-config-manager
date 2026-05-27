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
"""AIR SDK Client wrapper."""

from __future__ import annotations

import socket
import time
from typing import Any

import requests
from air_sdk import AirApi as AirApiV1
from air_sdk.v2 import AirApi
from pydantic import BaseModel

from nv_config_manager.common.config import load_config
from nv_config_manager.common.log import LogCategory, get_logger

logger = get_logger(__name__, category=LogCategory.TEMPORAL_ACTIVITY)


class AirDevice(BaseModel):
    """Model representing an AIR device in a simulation.

    Attributes:
        id: Unique identifier for the device
        name: Name of the device
        worker_ip: IP address of the device's worker
        api_port: Port number for the device's API
    """

    id: str
    name: str
    worker_ip: str
    api_port: int


class Simulation(BaseModel):
    """Model representing an AIR simulation."""

    id: str
    name: str
    state: str


class AirClient:
    """Client wrapper for AIR SDK interactions."""

    def __init__(self) -> None:
        """Initialize the AIR client with authenticated API clients."""
        self.cfg = load_config()
        self.v1_client, self.v2_client = self._get_clients()

    def _resolve_hostname(self, hostname: str) -> str:
        """Resolve a hostname to an IP address if it's not already an IP.

        Args:
            hostname: The hostname or IP address to resolve

        Returns:
            The resolved IP address

        Raises:
            socket.gaierror: If the hostname cannot be resolved
        """
        try:
            # Check if it's already an IP address
            socket.inet_aton(hostname)
            return hostname
        except OSError:
            # If not an IP, resolve the hostname
            return socket.gethostbyname(hostname)

    def _get_clients(self) -> tuple[AirApiV1, AirApi]:
        """Get AIR API clients for both v1 and v2 APIs.

        Returns:
            A tuple containing the v1 and v2 AIR API clients

        Raises:
            requests.exceptions.RequestException: If authentication fails
        """
        ssa_client_id = self.cfg["temporal.air"]["ssa_client_id"]
        ssa_client_secret = self.cfg["temporal.air"]["ssa_client_secret"]
        url = "https://tkpfg13ml3wy1hpcurczo5m2f0qxoxhifu4h7erevvo.ssa.nvidia.com/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {"grant_type": "client_credentials", "scope": "api-access"}
        response = requests.post(
            url, auth=(ssa_client_id, ssa_client_secret), headers=headers, data=data
        )
        response.raise_for_status()
        token = response.json()["access_token"]
        v1_client = AirApiV1(
            api_url=self.cfg["temporal.air"]["air_api_url"],
            username=ssa_client_id,
            bearer_token=token,
        )
        v2_client = AirApi(
            api_url=self.cfg["temporal.air"]["air_api_url"],
            username=ssa_client_id,
            bearer_token=token,
        )
        return v1_client, v2_client

    def create_simulation(self, simulation_name: str, topology: dict[str, Any]) -> str:
        """Create a new AIR simulation with the specified topology.

        Args:
            simulation_name: Name of the simulation
            topology: Topology configuration

        Returns:
            The simulation ID

        Raises:
            air_sdk.exceptions.AirApiError: If simulation creation fails
        """
        org_id = self.cfg["temporal.air"]["org_id"]
        simulation = self.v2_client.simulations.create_from(
            simulation_name,
            "JSON",
            topology,
            org_id,
        )
        return simulation.id  # type: ignore[no-any-return]

    def prepare_simulation_nodes(self, simulation_id: str) -> None:
        """Prepare simulation nodes by creating eth0 interfaces and setting up NVIDIA Config Manager accounts.

        This method:
        1. Creates eth0 outbound interfaces for all nodes that don't have one
        2. Creates NVIDIA Config Manager accounts with default passwords for all nodes
        3. Resets all nodes to apply the changes

        Args:
            simulation_id: ID of the simulation to prepare

        Raises:
            air_sdk.exceptions.AirApiError: If node preparation fails
        """
        # Create Eth0 Outbound interfaces for all nodes
        simulation = self.v2_client.simulations.get(simulation_id)
        for node in self.v2_client.nodes.list(simulation=simulation):
            has_eth0 = False
            for iface in self.v2_client.interfaces.list(node=node):
                if iface.name == "eth0":
                    has_eth0 = True
                    break
            if not has_eth0:
                logger.info(f"Creating eth0 interface for {node.name}")
                self.v2_client.interfaces.create(
                    name="eth0",
                    node=node,
                    interface_type="OOB_INTF",
                    link_up=True,
                    outbound=True,
                )

        # Create NVIDIA Config Manager Account for all nodes
        default_username = self.cfg["temporal.air"]["air_node_user"]
        default_password = self.cfg["temporal.air"]["air_node_password"]
        all_nodes = self.v1_client.simulation_nodes.list(simulation=simulation_id)
        for node in all_nodes:
            node.create_instructions(
                data=f"nv set system aaa user {default_username} password {default_password}",
                executor="shell",
            )
            node.create_instructions(
                data=f"nv set system aaa user {default_username} role system-admin",
                executor="shell",
            )
            node.create_instructions(data="nv config apply -y", executor="shell")
            node.control(action="reset")

    def start_simulation(self, simulation_id: str) -> None:
        """Start a simulation and wait for it to be fully loaded.

        Args:
            simulation_id: ID of the simulation to start

        Raises:
            air_sdk.exceptions.AirApiError: If simulation start fails
        """
        simulation = self.v2_client.simulations.get(simulation_id)
        if simulation.state not in ["LOADING", "LOADED"]:
            self.v1_client.simulation.control(simulation_id, "load")

        while simulation.state != "LOADED":
            time.sleep(5)
            simulation = self.v2_client.simulations.get(simulation_id)

    def create_simulation_node_services(self, simulation_id: str) -> list[AirDevice]:
        """Create HTTPS services for all nodes in a simulation.

        This method:
        1. Creates HTTPS services on eth0 interfaces for all nodes
        2. Resolves hostnames to IP addresses
        3. Returns a list of configured devices with their connection details

        Args:
            simulation_id: ID of the simulation

        Returns:
            List of configured devices with their connection details

        Raises:
            air_sdk.exceptions.AirApiError: If service creation fails
            socket.gaierror: If hostname resolution fails
        """
        service_map = {}
        devices = []
        # Check if any services already exist from previous attempts
        existing_services = self.v1_client.services.list(simulation=simulation_id)
        for service in existing_services:
            service_map[service.interface.id] = service

        for node in self.v2_client.nodes.list(simulation=simulation_id):
            for iface in self.v2_client.interfaces.list(node=node):
                if iface.name == "eth0":
                    service = service_map.get(iface.id)
                    if service is None:
                        service_name = f"{node.name} HTTPS"
                        dest_port = 8765
                        service = self.v2_client.services.create(
                            name=service_name,
                            interface=iface,
                            dest_port=dest_port,
                            service_type="https",
                        )
                    # Resolve the hostname to IP if needed
                    if not service.host:
                        raise ValueError(f"Service {service_name} has no host")
                    worker_ip = self._resolve_hostname(service.host)
                    devices.append(
                        AirDevice(
                            id=node.id,
                            name=node.name,
                            worker_ip=worker_ip,
                            api_port=service.src_port,
                        )
                    )
        return devices

    def wait_for_simulation_node(self, node: AirDevice) -> None:
        """Wait for a simulation node to be ready and accessible.

        This method:
        1. Waits for the node to be in RUNNING state
        2. Attempts to connect to the node's API
        3. Rebuilds the node if connection fails

        Args:
            node: The node to wait for

        Raises:
            requests.exceptions.RequestException: If API connection fails
            air_sdk.exceptions.AirApiError: If node rebuild fails
        """
        default_username = self.cfg["temporal.air"]["air_node_user"]
        default_password = self.cfg["temporal.air"]["air_node_password"]
        session = requests.Session()
        session.auth = (default_username, default_password)
        session.verify = False

        while True:
            air_node = self.v2_client.nodes.get(node.id)
            while air_node.state != "RUNNING":
                logger.info(f"Node {node.name} is not yet running, waiting for 5 seconds")
                time.sleep(5)
                air_node.refresh()
            # Attempt NVUE Query after node has time to build/rebuild
            time.sleep(30)
            try:
                rsp = session.get(
                    f"https://{node.worker_ip}:{node.api_port}/nvue_v1/system/api",
                    timeout=30,
                )
                rsp.raise_for_status()
                return
            except Exception as e:
                logger.warning(f"Error querying {node.name}, rebuilding: {e}")
                # v1_node = self.v1_client.simulation_nodes.get(simulation_node_id=node.id)
                # v1_node.control(action="rebuild")

    def delete_simulation(self, simulation_id: str) -> None:
        """Delete an AIR simulation.

        Args:
            simulation_id: ID of the simulation to delete

        Raises:
            air_sdk.exceptions.AirApiError: If simulation deletion fails
        """
        self.v2_client.simulations.delete(simulation_id)

    def list_simulations(self) -> list[Simulation]:
        """List all simulations managed by NVIDIA Config Manager."""
        simulations = self.v2_client.simulations.list()
        return [
            Simulation(
                id=sim.id,
                name=sim.title,
                state=sim.state,
            )
            for sim in simulations
        ]
