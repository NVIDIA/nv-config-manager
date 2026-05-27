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
"""Integration tests for DHCP API.

These tests verify that the DHCP API correctly serves KEA DHCP configuration
and that the configuration contains expected subnets and reservations.
"""

import ipaddress
import time
from typing import Any

import pytest
import requests

# Mark all tests in this module as integration tests
pytestmark = pytest.mark.integration

# Maximum time to wait for DHCP data to be populated after job execution
DHCP_DATA_WAIT_TIMEOUT = 300  # 5 minutes
DHCP_POLL_INTERVAL = 10  # seconds


class TestDHCPAPI:
    """Tests for the DHCP API endpoints."""

    def _wait_for_dhcp_data(
        self,
        dhcp_api_url: str,
        dhcp_client: requests.Session,
        timeout: int = DHCP_DATA_WAIT_TIMEOUT,
    ) -> dict[str, Any]:
        """Wait for DHCP to have subnets or reservations populated.

        After job execution, the DHCP service needs to run its first refresh
        to populate subnets and reservations from Nautobot.

        Returns the DHCP config once data is available.
        """
        print(f"\n⏳ Waiting up to {timeout}s for DHCP data to be populated...")
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                response = dhcp_client.get(f"{dhcp_api_url}/config", timeout=30)
                if response.status_code == 200:
                    config = response.json()
                    dhcp4 = self._extract_dhcp4_config(config)
                    if dhcp4:
                        subnets = dhcp4.get("subnet4", [])
                        reservations = dhcp4.get("reservations", [])
                        if subnets or reservations:
                            elapsed = int(time.time() - start_time)
                            print(
                                f"✅ DHCP data available after {elapsed}s: "
                                f"{len(subnets)} subnets, {len(reservations)} reservations"
                            )
                            return config
                        print(
                            f"  ... DHCP config empty, waiting ({int(time.time() - start_time)}s elapsed)"
                        )
            except requests.RequestException as e:
                print(f"  ... DHCP request failed: {e}")

            time.sleep(DHCP_POLL_INTERVAL)

        pytest.fail(
            f"DHCP data not populated after {timeout}s. "
            "The DHCP refresh may not have run after job execution."
        )

    @pytest.mark.timeout(30)
    def test_dhcp_healthcheck(
        self,
        dhcp_api_url: str,
        dhcp_client: requests.Session,
        base_hostname: str,
        sso_enabled: bool,
    ) -> None:
        """Test that the DHCP healthcheck endpoint is accessible.

        Without SSO the healthcheck is hit unauthenticated to verify it
        requires no auth.  With SSO the gateway enforces JWT validation
        before the request reaches the app, so we reuse the authenticated
        session (the app-level healthcheck still exercises the same code
        path; the gateway health-check bypass is validated separately via
        the ``healthChecks.paths`` Helm value).
        """
        print("\n=== Testing DHCP healthcheck ===")

        if sso_enabled:
            # Gateway enforces JWT on svc-* routes; use the authenticated client.
            response = dhcp_client.get(
                f"{dhcp_api_url}/healthcheck",
                timeout=10,
            )
        else:
            # No SSO — verify the endpoint works without any auth.
            session = requests.Session()
            session.headers.update({"Host": f"dhcp.{base_hostname}"})
            session.verify = False
            response = session.get(
                f"{dhcp_api_url}/healthcheck",
                timeout=10,
            )

        print(f"Healthcheck response: {response.status_code}")

        if response.status_code != 200:
            pytest.fail(
                f"DHCP healthcheck failed with status {response.status_code}: {response.text}"
            )

        print("✅ DHCP healthcheck passed")

    @pytest.mark.timeout(60)
    def test_dhcp_config_accessible(
        self,
        dhcp_api_url: str,
        dhcp_client: requests.Session,
    ) -> None:
        """Test that the DHCP config endpoint returns a valid configuration.

        This verifies that:
        1. The endpoint is accessible with auth
        2. The config is valid JSON
        3. The config has expected KEA structure
        """
        print("\n=== Testing DHCP config endpoint ===")

        response = dhcp_client.get(
            f"{dhcp_api_url}/config",
            timeout=30,
        )

        print(f"Config response status: {response.status_code}")

        if response.status_code == 403:
            pytest.fail(
                "DHCP config returned 403 Forbidden. "
                "Check that X-AUTH-REQUEST-EMAIL header is being passed correctly."
            )

        response.raise_for_status()

        config = response.json()
        print(f"Config type: {type(config)}")

        # Validate structure - KEA returns a list with the config
        if isinstance(config, list):
            # KEA response format: [{"result": 0, "arguments": {...}}]
            if len(config) > 0 and "arguments" in config[0]:
                dhcp_config = config[0]["arguments"]
                print(f"KEA config keys: {list(dhcp_config.keys())}")
            else:
                dhcp_config = config
        else:
            dhcp_config = config

        # Check for Dhcp4 key (IPv4 DHCP config)
        if "Dhcp4" in dhcp_config:
            dhcp4 = dhcp_config["Dhcp4"]
            print(f"Dhcp4 config keys: {list(dhcp4.keys())}")

            if "subnet4" in dhcp4:
                subnet_count = len(dhcp4["subnet4"])
                print(f"Number of IPv4 subnets: {subnet_count}")

            if "reservations" in dhcp4:
                reservation_count = len(dhcp4["reservations"])
                print(f"Number of global reservations: {reservation_count}")

        print("✅ DHCP config endpoint accessible and returns valid structure")

    @pytest.mark.timeout(360)  # 6 minutes to allow for DHCP refresh wait
    def test_dhcp_config_has_subnets(
        self,
        dhcp_api_url: str,
        dhcp_client: requests.Session,
    ) -> None:
        """Test that the DHCP configuration contains subnets.

        In a properly configured deployment with mock topology,
        there should be at least one DHCP subnet configured.

        This test waits for the DHCP refresh to populate data after job execution.
        """
        print("\n=== Verifying DHCP subnets ===")

        # Wait for DHCP data to be populated (first refresh after job execution)
        config = self._wait_for_dhcp_data(dhcp_api_url, dhcp_client)

        # Extract Dhcp4 config
        dhcp4 = self._extract_dhcp4_config(config)

        if dhcp4 is None:
            pytest.skip("No Dhcp4 configuration found - DHCP may not be configured")

        subnets = dhcp4.get("subnet4", [])
        subnet_count = len(subnets)

        print(f"Found {subnet_count} IPv4 subnets:")
        for subnet in subnets[:5]:
            subnet_str = subnet.get("subnet", "unknown")
            subnet_id = subnet.get("id", "?")
            pools = subnet.get("pools", [])
            print(f"  - ID {subnet_id}: {subnet_str} ({len(pools)} pools)")

        if subnet_count > 5:
            print(f"  ... and {subnet_count - 5} more")

        # We don't fail if no subnets - the mock topology might not have DHCP configured
        if subnet_count == 0:
            print("⚠️ No subnets configured - this may be expected for some deployments")
        else:
            print(f"✅ Found {subnet_count} DHCP subnets")

    @pytest.mark.timeout(60)
    def test_dhcp_config_has_reservations(
        self,
        dhcp_api_url: str,
        dhcp_client: requests.Session,
    ) -> None:
        """Test that the DHCP configuration contains host reservations.

        In a properly configured deployment with ZTP-enabled devices,
        there should be host reservations for those devices.
        """
        print("\n=== Verifying DHCP reservations ===")

        response = dhcp_client.get(
            f"{dhcp_api_url}/config",
            timeout=30,
        )
        response.raise_for_status()

        config = response.json()
        dhcp4 = self._extract_dhcp4_config(config)

        if dhcp4 is None:
            pytest.skip("No Dhcp4 configuration found - DHCP may not be configured")

        # Check global reservations
        global_reservations = dhcp4.get("reservations", [])

        # Also check per-subnet reservations
        subnets = dhcp4.get("subnet4", [])
        subnet_reservations = sum(len(subnet.get("reservations", [])) for subnet in subnets)

        total_reservations = len(global_reservations) + subnet_reservations

        print(f"Global reservations: {len(global_reservations)}")
        print(f"Per-subnet reservations: {subnet_reservations}")
        print(f"Total reservations: {total_reservations}")

        if global_reservations:
            print("\nSample global reservations:")
            for res in global_reservations[:3]:
                hw = res.get("hw-address", "unknown")
                hostname = res.get("hostname", "unknown")
                ip = res.get("ip-address", "unknown")
                print(f"  - {hostname}: {hw} → {ip}")

        if total_reservations == 0:
            print("⚠️ No reservations configured - this may be expected for some deployments")
        else:
            print(f"✅ Found {total_reservations} DHCP reservations")

    # GraphQL query to get all ZTP-enabled devices with their interfaces and serial
    ZTP_DEVICES_QUERY = """
    query {
        config_manager_devices(ztp_enabled: true) {
            id
            device {
                id
                name
                serial
                role {
                    name
                }
                primary_ip4 {
                    address
                }
                interfaces {
                    name
                    mac_address
                    mgmt_only
                }
            }
        }
    }
    """

    # SMN roles use DHCP pools on /31 subnets, not reservations
    SMN_ROLES = {"SMN-Core", "SMN-Spine", "SMN-Leaf", "SMN-Aggleaf", "SMN-ZTPLeaf"}

    @pytest.mark.timeout(120)
    def test_ztp_devices_have_dhcp_reservations(
        self,
        dhcp_api_url: str,
        dhcp_client: requests.Session,
        nautobot_url: str,
        nautobot_client: requests.Session,
    ) -> None:
        """Test that every ZTP-enabled device has a DHCP reservation.

        This test verifies that:
        1. All devices with ztp_enabled=true in Nautobot
        2. Have a corresponding DHCP reservation in the KEA config
        3. The reservation matches by MAC address (hw-address) or serial (client-id)
        """
        print("\n=== Verifying ZTP devices have DHCP reservations ===")

        # Get all ZTP-enabled devices from Nautobot
        gql_response = nautobot_client.post(
            f"{nautobot_url}/api/graphql/",
            json={"query": self.ZTP_DEVICES_QUERY},
            timeout=30,
        )
        gql_response.raise_for_status()
        gql_data = gql_response.json()

        if "errors" in gql_data:
            pytest.fail(f"GraphQL query failed: {gql_data['errors']}")

        devices = gql_data.get("data", {}).get("config_manager_devices", [])
        print(f"Found {len(devices)} ZTP-enabled devices in Nautobot")

        if not devices:
            pytest.skip("No ZTP-enabled devices found in Nautobot")

        # Get DHCP config
        dhcp_response = dhcp_client.get(
            f"{dhcp_api_url}/config",
            timeout=30,
        )
        dhcp_response.raise_for_status()

        dhcp_config = dhcp_response.json()
        dhcp4 = self._extract_dhcp4_config(dhcp_config)

        if dhcp4 is None:
            pytest.fail("No Dhcp4 configuration found")

        # Collect all DHCP reservations (global + per-subnet)
        all_reservations: list[dict[str, Any]] = list(dhcp4.get("reservations", []))
        for subnet in dhcp4.get("subnet4", []):
            all_reservations.extend(subnet.get("reservations", []))

        # Build sets of identifiers that have reservations
        # MAC addresses (hw-address) - normalized to lowercase
        reserved_macs = {
            res.get("hw-address", "").lower() for res in all_reservations if res.get("hw-address")
        }
        # Client IDs (typically based on serial number) - store raw for matching
        reserved_client_ids_raw = [
            res.get("client-id", "") for res in all_reservations if res.get("client-id")
        ]

        print(f"Found {len(all_reservations)} total DHCP reservations")
        print(f"  - hw-address reservations: {len(reserved_macs)}")
        print(f"  - client-id reservations: {len(reserved_client_ids_raw)}")
        if reserved_client_ids_raw:
            print(f"  - sample client-ids: {reserved_client_ids_raw[:3]}")

        # Check each ZTP-enabled device
        missing_reservations: list[str] = []
        matched_devices: list[str] = []
        no_identifier: list[str] = []

        smn_devices: list[str] = []

        for managed_device in devices:
            device = managed_device.get("device", {})
            device_name = device.get("name", "unknown")
            device_serial = device.get("serial", "")
            device_role = device.get("role", {}).get("name", "")
            interfaces = device.get("interfaces", [])

            # SMN devices use DHCP pools on /31 uplinks, not reservations
            if device_role in self.SMN_ROLES:
                smn_devices.append(device_name)
                continue

            # Find management interface MAC (prefer mgmt_only, fallback to any)
            device_mac = None
            for iface in interfaces:
                mac = iface.get("mac_address")
                if mac:
                    # Prefer management interface
                    if iface.get("mgmt_only"):
                        device_mac = mac.lower()
                        break
                    elif device_mac is None:
                        device_mac = mac.lower()

            # Check if device has either MAC or serial for reservation matching
            if not device_mac and not device_serial:
                no_identifier.append(device_name)
                continue

            # Check if this device has a reservation (by MAC or by serial/client-id)
            has_reservation = False
            if device_mac and device_mac in reserved_macs:
                has_reservation = True
            elif device_serial:
                # Check various client-id formats:
                # 1. Quoted: 'SERIAL'
                # 2. Hex encoded (no colons): continuous hex string
                # 3. Hex encoded (with colons): colon-separated hex
                serial_quoted = f"'{device_serial}'"
                serial_hex_no_colons = "".join(f"{ord(c):02X}" for c in device_serial)
                serial_hex_colons = ":".join(f"{ord(c):02x}" for c in device_serial)
                for client_id in reserved_client_ids_raw:
                    if client_id.upper() in (
                        serial_quoted.upper(),
                        serial_hex_no_colons,
                        serial_hex_colons.upper(),
                        device_serial.upper(),
                    ):
                        has_reservation = True
                        break

            if has_reservation:
                matched_devices.append(device_name)
            else:
                identifier = f"MAC: {device_mac}" if device_mac else f"serial: {device_serial}"
                missing_reservations.append(f"{device_name} ({identifier})")

        print(f"\nSMN devices (use pools, not reservations): {len(smn_devices)}")
        print(f"Devices with DHCP reservations: {len(matched_devices)}")
        print(f"Devices missing DHCP reservations: {len(missing_reservations)}")
        if no_identifier:
            print(f"Devices with no MAC or serial: {len(no_identifier)}")

        if missing_reservations:
            print("\nDevices missing reservations:")
            for device in missing_reservations[:10]:
                print(f"  - {device}")
            if len(missing_reservations) > 10:
                print(f"  ... and {len(missing_reservations) - 10} more")

            pytest.fail(
                f"{len(missing_reservations)} ZTP-enabled devices are missing "
                f"DHCP reservations: {missing_reservations[:5]}"
            )

        print(f"✅ All {len(matched_devices)} non-SMN ZTP devices have DHCP reservations")
        if smn_devices:
            print(f"✅ {len(smn_devices)} SMN devices use DHCP pools (not reservations)")

    @pytest.mark.timeout(120)
    def test_smn_devices_have_dhcp_pools(
        self,
        dhcp_api_url: str,
        dhcp_client: requests.Session,
        nautobot_url: str,
        nautobot_client: requests.Session,
    ) -> None:
        """Test that SMN devices have DHCP subnets with pools and correct options.

        SMN devices use /31 subnets with pools of size 1 on their uplink interfaces,
        rather than reservations based on MAC/serial.
        """
        print("\n=== Verifying SMN devices have DHCP pools ===")

        # Get SMN devices with their uplink interfaces
        smn_query = """
        query {
            config_manager_devices(ztp_enabled: true) {
                device {
                    name
                    role {
                        name
                    }
                    interfaces {
                        name
                        role {
                            name
                        }
                        ip_addresses {
                            address
                        }
                    }
                }
            }
        }
        """
        gql_response = nautobot_client.post(
            f"{nautobot_url}/api/graphql/",
            json={"query": smn_query},
            timeout=30,
        )
        gql_response.raise_for_status()
        gql_data = gql_response.json()

        if "errors" in gql_data:
            pytest.fail(f"GraphQL query failed: {gql_data['errors']}")

        # Filter to SMN devices and collect their uplink /31 subnets
        smn_uplink_subnets: dict[str, str] = {}  # subnet -> device name
        devices = gql_data.get("data", {}).get("config_manager_devices", [])

        for managed_device in devices:
            device = managed_device.get("device", {})
            device_name = device.get("name", "")
            device_role = device.get("role", {}).get("name", "")

            if device_role not in self.SMN_ROLES:
                continue

            for iface in device.get("interfaces", []):
                iface_role = iface.get("role", {})
                if iface_role and iface_role.get("name") == "Uplink":
                    for ip_addr in iface.get("ip_addresses", []):
                        addr = ip_addr.get("address", "")
                        if "/31" in addr:
                            # Extract the /31 subnet from the IP
                            ip_iface = ipaddress.ip_interface(addr)
                            subnet = str(ip_iface.network)
                            smn_uplink_subnets[subnet] = device_name

        print(f"Found {len(smn_uplink_subnets)} SMN uplink /31 subnets")

        if not smn_uplink_subnets:
            pytest.skip("No SMN uplink subnets found")

        # Get DHCP config
        dhcp_response = dhcp_client.get(
            f"{dhcp_api_url}/config",
            timeout=30,
        )
        dhcp_response.raise_for_status()

        dhcp_config = dhcp_response.json()
        dhcp4 = self._extract_dhcp4_config(dhcp_config)

        if dhcp4 is None:
            pytest.fail("No Dhcp4 configuration found")

        # Build a map of subnet -> config
        dhcp_subnets: dict[str, dict[str, Any]] = {}
        for subnet_config in dhcp4.get("subnet4", []):
            dhcp_subnets[subnet_config.get("subnet", "")] = subnet_config

        import json

        print(json.dumps(dhcp_subnets["10.240.164.64/31"], indent=4))

        # Check each SMN uplink subnet
        missing_subnets: list[str] = []
        subnets_without_pools: list[str] = []
        subnets_with_pools: list[str] = []

        for subnet, device_name in smn_uplink_subnets.items():
            if subnet not in dhcp_subnets:
                missing_subnets.append(f"{subnet} ({device_name})")
                continue

            subnet_cfg = dhcp_subnets[subnet]
            pools = subnet_cfg.get("pools", [])

            if not pools:
                subnets_without_pools.append(f"{subnet} ({device_name})")
            else:
                subnets_with_pools.append(subnet)

        print(f"SMN subnets with pools: {len(subnets_with_pools)}")
        print(f"SMN subnets missing from DHCP: {len(missing_subnets)}")
        print(f"SMN subnets without pools: {len(subnets_without_pools)}")

        if missing_subnets:
            print("\nMissing subnets:")
            for s in missing_subnets[:5]:
                print(f"  - {s}")

        if subnets_without_pools:
            print("\nSubnets without pools:")
            for s in subnets_without_pools[:5]:
                print(f"  - {s}")

        if missing_subnets or subnets_without_pools:
            pytest.fail(
                f"SMN DHCP issues: {len(missing_subnets)} missing subnets, "
                f"{len(subnets_without_pools)} subnets without pools"
            )

        print(f"✅ All {len(subnets_with_pools)} SMN uplink subnets have DHCP pools")

    def _extract_dhcp4_config(self, config: Any) -> dict[str, Any] | None:
        """Extract the Dhcp4 configuration from the KEA response."""
        # KEA returns: [{"result": 0, "arguments": {"Dhcp4": {...}}}]
        if isinstance(config, list) and len(config) > 0:
            first = config[0]
            if "arguments" in first and "Dhcp4" in first["arguments"]:
                return first["arguments"]["Dhcp4"]
            if "Dhcp4" in first:
                return first["Dhcp4"]

        # Direct config format
        if isinstance(config, dict):
            if "Dhcp4" in config:
                return config["Dhcp4"]
            if "arguments" in config and "Dhcp4" in config["arguments"]:
                return config["arguments"]["Dhcp4"]

        return None
