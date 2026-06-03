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

from typing import Any

from nautobot.apps.jobs import StringVar, register_jobs
from nautobot_design_builder.choices import DesignModeChoices
from nautobot_design_builder.contrib.ext import CableConnectionExtension, LookupExtension
from nautobot_design_builder.design_job import DesignJob

from ..context import BaseContext, get_mock_topology_context_class

name = "Mock Topology"


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
        return super().run(*args, **kwargs)

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
