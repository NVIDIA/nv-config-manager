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
"""Nautobot Client for Config Store service.

Provides device metadata caching and bulk device queries for
the config store service. Extends the common aiohttp-based client.
"""

from __future__ import annotations

from configparser import ConfigParser
from typing import Any

from nv_config_manager.common.client import NautobotClient as BaseNautobotClient
from nv_config_manager.common.client import NautobotException
from nv_config_manager.common.log import LogCategory, get_logger

logger = get_logger(__name__, category=LogCategory.NAUTOBOT)


class NautobotError(NautobotException):
    """Exception raised for Nautobot errors in config store."""


class DeviceMetadata:
    """Device metadata from Nautobot."""

    def __init__(
        self,
        device_id: str,
        name: str,
        site: str,
        platform: str | None = None,
        role: str | None = None,
        rack: str | None = None,
        primary_ip4: str | None = None,
        nautobot_url: str | None = None,
    ) -> None:
        """Initialize device metadata."""
        self.device_id = device_id
        self.name = name
        self.site = site
        self.platform = platform
        self.role = role
        self.rack = rack
        self.primary_ip4 = primary_ip4
        self.nautobot_url = nautobot_url

    @staticmethod
    def from_graphql(data: dict[str, Any]) -> DeviceMetadata:
        """Create DeviceMetadata from GraphQL response."""
        # Extract site from location hierarchy
        site = None
        location = data.get("location")
        while location:
            if location.get("location_type", {}).get("name") == "Site":
                site = location["name"]
                break
            location = location.get("parent")

        return DeviceMetadata(
            device_id=data["id"],
            name=data["name"],
            site=site or "Unknown",
            platform=data.get("platform", {}).get("name") if data.get("platform") else None,
            role=data.get("role", {}).get("name") if data.get("role") else None,
            rack=data.get("rack", {}).get("name") if data.get("rack") else None,
            primary_ip4=data.get("primary_ip4", {}).get("host")
            if data.get("primary_ip4")
            else None,
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "device_id": self.device_id,
            "name": self.name,
            "site": self.site,
            "platform": self.platform,
            "role": self.role,
            "rack": self.rack,
            "primary_ip4": self.primary_ip4,
            "nautobot_url": self.nautobot_url,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> DeviceMetadata:
        """Create DeviceMetadata from a dictionary."""
        return DeviceMetadata(
            device_id=data["device_id"],
            name=data["name"],
            site=data["site"],
            platform=data.get("platform"),
            role=data.get("role"),
            rack=data.get("rack"),
            primary_ip4=data.get("primary_ip4"),
            nautobot_url=data.get("nautobot_url"),
        )


class NautobotClient(BaseNautobotClient):
    """Async client for querying Nautobot device metadata.

    Extends the common aiohttp-based NautobotClient with config store
    specific device metadata queries.
    """

    def __init__(
        self,
        nautobot_url: str,
        token: str,
        verify: bool | str = True,
        timeout: int | None = None,
    ) -> None:
        """Initialize the Nautobot client.

        Args:
            nautobot_url: Base URL for Nautobot instance
            token: API token for authentication
            verify: SSL verification - True (default), False (disable), or str (path to CA cert)
            timeout: Request timeout in seconds. ``None`` uses the base default.
        """
        super().__init__(
            nautobot_url=nautobot_url,
            token=token,
            verify=verify,
            timeout=timeout,
        )

    @classmethod
    def from_config(cls, config: ConfigParser) -> NautobotClient:
        """Create NautobotClient from INI configuration.

        Args:
            config: ConfigParser with nautobot section

        Returns:
            Configured NautobotClient instance
        """
        # Lazy import to avoid circular dependency with nv_config_manager.common.config
        from nv_config_manager.common.config import parse_verify_param

        return cls(
            nautobot_url=config.get("nautobot", "server"),
            token=config.get("nautobot", "token"),
            verify=parse_verify_param(config["nautobot"]),
            timeout=cls.timeout_from_config(config),
        )

    async def get_device(self, device_id: str) -> DeviceMetadata | None:
        """Get device metadata by UUID.

        Args:
            device_id: Device UUID

        Returns:
            DeviceMetadata or None if not found
        """
        query = """
            query ($id: ID!) {
              device(id: $id) {
                id
                name
                role {
                  name
                }
                platform {
                  name
                }
                rack {
                  name
                }
                primary_ip4 {
                  host
                }
                location {
                  name
                  location_type {
                    name
                  }
                  parent {
                    name
                    location_type {
                      name
                    }
                    parent {
                      name
                      location_type {
                        name
                      }
                    }
                  }
                }
              }
            }
        """

        try:
            result = await self.graphql_query(query, {"id": device_id})
            device_data = result.get("data", {}).get("device")

            if not device_data:
                logger.warning("Device %s not found in Nautobot", device_id)
                return None

            return DeviceMetadata.from_graphql(device_data)
        except Exception as e:
            logger.error("Failed to get device %s: %s", device_id, e)
            return None

    async def get_all_devices(self, page_size: int = 100) -> list[DeviceMetadata]:
        """Get metadata for all nv-config-manager devices using pagination.

        Args:
            page_size: Number of devices to fetch per page

        Returns:
            List of DeviceMetadata for all nv-config-manager devices
        """
        query = """
            query ($limit: Int!, $offset: Int!) {
              config_manager_devices(limit: $limit, offset: $offset) {
                device {
                  id
                  name
                  role {
                    name
                  }
                  platform {
                    name
                  }
                  rack {
                    name
                  }
                  primary_ip4 {
                    host
                  }
                  location {
                    name
                    location_type {
                      name
                    }
                    parent {
                      name
                      location_type {
                        name
                      }
                      parent {
                        name
                        location_type {
                          name
                        }
                      }
                    }
                  }
                }
              }
            }
        """

        all_devices = []
        offset = 0

        try:
            while True:
                result = await self.graphql_query(query, {"limit": page_size, "offset": offset})
                managed_devices_data = result.get("data", {}).get("config_manager_devices", [])

                if not managed_devices_data:
                    break

                for managed_device in managed_devices_data:
                    device_data = managed_device.get("device")
                    if device_data:
                        try:
                            all_devices.append(DeviceMetadata.from_graphql(device_data))
                        except Exception as e:
                            logger.error("Failed to parse device %s: %s", device_data.get("id"), e)

                logger.info(
                    "Fetched %d devices in current page (offset: %d)",
                    len(managed_devices_data),
                    offset,
                )

                # If we got fewer results than the page size, we're done
                if len(managed_devices_data) < page_size:
                    break

                offset += page_size

            logger.info(
                "Fetched %d total nv-config-manager devices from Nautobot", len(all_devices)
            )
            return all_devices
        except Exception as e:
            logger.error("Failed to get all devices: %s", e)
            return all_devices  # Return whatever we've collected so far
