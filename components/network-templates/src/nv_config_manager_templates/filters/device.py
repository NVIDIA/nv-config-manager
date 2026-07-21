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
"""Custom Jinja2 Filters for nautobot Device GraphQL data."""

# pylint: disable=too-many-lines
import ipaddress
import re
from typing import Any

from nv_config_manager_dcim import DeviceRenderData, LocationRenderData

from nv_config_manager_templates.dataclasses.bgp import BGPLocalConfig, BGPPeer
from nv_config_manager_templates.dataclasses.consoleport import ConsoleServerPort
from nv_config_manager_templates.dataclasses.interface import ConnectedDevice, Interface
from nv_config_manager_templates.dataclasses.vrf import VRF
from nv_config_manager_templates.filters import FilterException
from nv_config_manager_templates.filters.ip import gateway as gateway_filter


def _inventory(value: DeviceRenderData, key: str, default: Any = None) -> Any:
    """Read one provider-neutral inventory collection."""
    return value.inventory.get(key, default)


def _intent(value: DeviceRenderData, key: str) -> Any:
    """Read one provider-neutral desired-configuration value."""
    return value.intent[key]


def hostname(value: DeviceRenderData) -> str:
    """Return the hostname of the device."""
    return value.identity.name


def site_name(value: DeviceRenderData) -> str:
    """Return the site name for the device."""
    location = value.identity.location
    while location:
        if location.kind == "Site":
            return location.name
        location = location.parent

    raise FilterException("Found no Site location.")


def device_tags(value: DeviceRenderData) -> list[str]:
    """Return the list of tags for this device."""
    return list(value.identity.tags)


def has_tag(value: DeviceRenderData, tag: str) -> bool:
    """Return true if device has the given tag."""
    return tag in device_tags(value)


def interface_has_tag(intf: Interface, tag: str) -> bool:
    """Return true if the interface has *tag* (name match is case-insensitive)."""
    tag_l = tag.lower()
    return any(t.lower() == tag_l for t in intf.tags)


def platform(value: DeviceRenderData) -> str:
    """Return the platform name of this device."""
    return value.identity.platform


def model(value: DeviceRenderData) -> str:
    """Return the model name."""
    return value.identity.model


def role(value: DeviceRenderData) -> str:
    """Return the role name for this device."""
    return value.identity.role


def desired_firmware(value: DeviceRenderData) -> str:
    """Return the desired firmware image version for this device."""
    try:
        return _intent(value, "intended-firmware")["version"]
    except KeyError as exc:
        raise FilterException("No intended firmware image set for device.") from exc


def router_id(value: DeviceRenderData) -> str:
    """Return the router-id of this device."""
    platform_name = platform(value)
    if platform_name == "Cumulus Linux":
        ifname = "lo"
    elif platform_name == "Arista EOS":
        ifname = "Loopback0"
    else:
        raise FilterException(f"Unhandled platform: {platform_name}")

    intf = interface_by_name(value, ifname)
    # Return primary IPv4 with prefix length stripped
    return re.sub(r"\/\d+$", "", intf.primary_ipv4)


def uuid(value: DeviceRenderData) -> str:
    """Return the provider-neutral identifier for the device."""
    return value.identity.id


def asn(value: DeviceRenderData, vrf: str = "default") -> str:
    """Return the ASN for the device."""
    routing_instances = _inventory(value, "bgp_routing_instances", [])
    if routing_instances:
        for instance in routing_instances:
            vrf_entry = instance["router_id"]["interfaces"][0]["vrf"]
            vrf_name = vrf_entry["name"] if vrf_entry else "default"
            if vrf_name == vrf:
                return str(instance["autonomous_system"]["asn"])
    # Fallback to desired configuration intent if no routing data is modeled.
    try:
        # cast to str for consistent return type between asdot and asplain
        return str(_intent(value, "bgp")["asn"])
    except KeyError as exc:
        raise FilterException("No ASN defined for device.") from exc


def interface_by_name(
    value: DeviceRenderData, name: str, fail_if_missing: bool = True
) -> Interface | None:
    """Grab an interface object by interface name."""
    interface_entries = value.interfaces
    try:
        interface_entry = next(
            interface
            for interface in interface_entries
            if interface["name"].lower() == name.lower()
        )
        return Interface.from_render_data(interface_entry)
    except StopIteration as exc:
        if fail_if_missing:
            raise FilterException(f"No interface found with name {name}.") from exc
        return None


def breakout_count(value: DeviceRenderData, interface_name: str) -> int:
    """Return the breakout count for the interface."""
    child_interfaces = interfaces(value, prefix=f"{interface_name}s")
    if len(child_interfaces) == 1 and child_interfaces[0].name == interface_name:
        # No breakout
        return 0

    if len(child_interfaces) <= 2:
        return 2

    if len(child_interfaces) <= 4:
        return 4

    if len(child_interfaces) <= 8:
        return 8

    raise FilterException(f"Detected more than 8 breakouts on {interface_name}.")


def loopback_prefix(value: DeviceRenderData) -> str:
    """Return the parent prefix for an interface IP."""
    try:
        interface_entries = value.interfaces
        interface_entry = next(
            interface for interface in interface_entries if interface["name"] == "lo"
        )
        try:
            return interface_entry["ip_addresses"][0]["parent"]["parent"]["prefix"]
        except KeyError as exc:
            raise FilterException("Unable to calculate loopback prefix.") from exc
    except StopIteration as exc:
        raise FilterException("No interface found with name lo.") from exc


def interfaces(  # pylint: disable=too-many-arguments,too-many-branches
    value: DeviceRenderData,
    prefix: str = None,
    contains: str = None,
    vrf: str = None,
    interface_role: str | list[str] | None = None,
    peer_role: str | list[str] | None = None,
    include_mgmt: bool = True,
    bgp_peers_only: bool = False,
    tags: list[str] | None = None,
) -> list[Interface]:
    """Return a list of interface objects with optional filtering."""
    interface_records = []
    for interface_entry in value.interfaces:
        if include_mgmt or not interface_entry["mgmt_only"]:
            interface_records.append(Interface.from_render_data(interface_entry))

    if prefix:
        interface_records = [
            interface
            for interface in interface_records
            if interface.name.lower().startswith(prefix.lower())
        ]

    if contains:
        interface_records = [
            interface for interface in interface_records if contains in interface.name
        ]

    if vrf:
        interface_records = [interface for interface in interface_records if interface.vrf == vrf]

    if interface_role:
        if isinstance(interface_role, str):
            interface_records = [
                interface for interface in interface_records if interface.role == interface_role
            ]
        elif isinstance(interface_role, list):
            interface_records = [
                interface for interface in interface_records if interface.role in interface_role
            ]

    if peer_role:
        if isinstance(peer_role, str):
            interface_records = [
                interface
                for interface in interface_records
                if interface.connected_interface
                and (interface.connected_interface.device.role.lower() == peer_role.lower())
            ]
        elif isinstance(peer_role, list):
            peer_role_list = [role.lower() for role in peer_role]
            interface_records = [
                interface
                for interface in interface_records
                if interface.connected_interface
                and interface.connected_interface.device.role.lower() in peer_role_list
            ]

    if bgp_peers_only:
        interface_records = [
            interface for interface in interface_records if interface.has_bgp_peer()
        ]

    if tags:
        interface_records = [
            interface
            for interface in interface_records
            if any(tag in interface.tags for tag in tags)
        ]
    return sorted(interface_records, key=interface_natural_sort_key)


def management_interface(value: DeviceRenderData) -> Interface:
    """Return the management interface for the given device."""
    if platform(value) in ["Cumulus Linux", "MLNX-OS"]:
        try:
            return interface_by_name(value, "eth0")
        except FilterException as exc:
            # Some IPMI devices will use loopback instead
            if "smn" not in role(value).lower() and "ipmi" not in role(value).lower():
                raise exc
            return interface_by_name(value, "lo")

    if platform(value) == "Arista EOS":
        management_interfaces = interfaces(value, prefix="Management")
        if len(management_interfaces) == 1:
            return management_interfaces[0]

        if not management_interfaces:
            raise FilterException("No Management interface found.")
        raise FilterException("Multiple management interfaces defined.")
    raise FilterException(f"No Management Interface lookup implemnented for {platform(value)}")


def default_gateways(value: DeviceRenderData, version: int = 4) -> list[str]:
    """Return a list of default gateway IPs for the given device."""
    if "smn" in role(value).lower() or "uc" in role(value).lower():
        # For the SMN routers, pull the IP
        # for each uplink interface
        uplink_interfaces = interfaces(value, interface_role="Uplink")
        result = []
        for interface in uplink_interfaces:
            try:
                if version == 4 and interface.connected_interface.device.peer_ipv4:
                    result.append(interface.connected_interface.device.peer_ipv4)
                elif version == 6 and interface.connected_interface.device.peer_ipv6:
                    result.append(interface.connected_interface.device.peer_ipv6)
            except AttributeError:
                continue
        if not result:
            raise FilterException("Must have at least one default gateway.")
        return result
    mgmt_interface = management_interface(value)
    if version == 4:
        return [gateway_filter(mgmt_interface.primary_ipv4)]
    return [gateway_filter(mgmt_interface.primary_ipv6)]


def attached_vrfs(value: DeviceRenderData) -> list[VRF]:
    """Return the list of attached VRFs."""
    vrfs = set()
    for interface in value.interfaces:
        if interface["vrf"]:
            vrf = VRF.from_render_data(interface["vrf"])
            if vrf:
                vrfs.add(vrf)
    return sorted(list(vrfs), key=lambda x: x.name)


def has_vrf(value: DeviceRenderData, vrf_name: str) -> bool:
    """Return True if the device has the given VRF."""
    return vrf_name in [vrf.name for vrf in attached_vrfs(value)]


def console_server_ports(
    value: DeviceRenderData, connected_only: bool = False
) -> list[ConsoleServerPort]:
    """Return list of console server ports optionally filtered by connection status."""
    ports = [
        ConsoleServerPort.from_render_data(entry)
        for entry in _inventory(value, "console_server_ports", [])
    ]
    if connected_only:
        ports = [port for port in ports if port.connected]
    return ports


# pylint: disable=too-many-locals,too-many-branches,too-many-nested-blocks
# pylint: disable=too-many-statements
def bgp_routing_instance(value: DeviceRenderData, vrf: str = "default") -> BGPLocalConfig:
    """Return a local BGP configuration with its peers."""
    routing_instances = _inventory(value, "bgp_routing_instances", [])
    if routing_instances:
        for instance in routing_instances:
            peers = []
            for endpoint in instance.get("endpoints", []):
                source_vrf = "default"

                if endpoint.get("source_interface", {}).get("vrf"):
                    source_vrf = endpoint["source_interface"]["vrf"]["name"]
                    # Strip off site name and fabric if _ present
                    # to account for uniqueness constraints
                    # and Cumulus VRF name limitations
                    # e.g. SITEA-TAN1_SCP1 -> SCP1
                    # we should evaluate modeling this in NB long term
                    if "_" in source_vrf:
                        source_vrf = source_vrf.split("_")[1]

                if source_vrf != vrf:
                    continue

                peer_group = None
                ttl = None
                # Use peer_group from the endpoint if available
                if endpoint.get("peer_group") and endpoint["peer_group"].get("name"):
                    peer_group = endpoint["peer_group"]["name"]
                    peer_group_data = endpoint["peer_group"]
                    extra_attrs = peer_group_data.get("extra_attributes")
                    if isinstance(extra_attrs, dict) and "ttl" in extra_attrs:
                        ttl = extra_attrs["ttl"]
                    elif ttl is None:
                        pg_tpl = peer_group_data.get("peergroup_template") or {}
                        tpl_attrs = pg_tpl.get("extra_attributes")
                        if isinstance(tpl_attrs, dict) and "ttl" in tpl_attrs:
                            ttl = tpl_attrs["ttl"]

                peer = endpoint.get("peer")
                if peer:
                    v4_address = next(
                        (
                            ip_address["address"].replace("/32", "").replace("/31", "")
                            for ip_address in peer["source_interface"]["ip_addresses"]
                            if ip_address["ip_version"] == 4
                        ),
                        None,
                    )
                    v6_address = next(
                        (
                            ip_address["address"].replace("/128", "")
                            for ip_address in peer["source_interface"]["ip_addresses"]
                            if ip_address["ip_version"] == 6
                        ),
                        None,
                    )
                    # Use the peer device role if peer_group is not set
                    peer_routing_instance = peer["routing_instance"]
                    if not peer_group:
                        peer_group = peer_routing_instance["device"]["role"]["name"].upper()

                    peer_source_interface = None
                    if peer.get("source_interface") and peer["source_interface"].get("name"):
                        peer_source_interface = peer["source_interface"]["name"]

                    peers.append(
                        {
                            "name": peer_routing_instance["device"]["name"],
                            "status": peer_routing_instance["status"]["name"],
                            "description": peer_routing_instance["device"]["name"],
                            "peer_group": peer_group,
                            "peer_role": (peer_routing_instance["device"]["role"]["name"]),
                            "asn": peer_routing_instance["autonomous_system"]["asn"],
                            "peer_ipv4": v4_address,
                            "peer_ipv6": v6_address,
                            "source_interface": peer_source_interface,
                            "source_vrf": source_vrf,
                            "ttl": ttl,
                        }
                    )
            if peers:
                # We found peers within this VRF
                local_config = {
                    "status": instance["status"]["name"],
                    "asn": instance["autonomous_system"]["asn"],
                    "interface": instance["router_id"]["interfaces"][0]["name"],
                    "vrf": vrf,
                    "peers": [BGPPeer(**peer) for peer in peers],
                }
                return BGPLocalConfig(**local_config)

        if vrf == "default" and len(routing_instances) == 1:
            instance = routing_instances[0]
            # No matches found within the BGP plugin data
            # But we can still return the local BGP data with an
            # empty list of peers
            local_config = {
                "status": instance["status"]["name"],
                "asn": instance["autonomous_system"]["asn"],
                "interface": instance["router_id"]["interfaces"][0]["name"],
                "vrf": vrf,
                "peers": [],
            }
            return BGPLocalConfig(**local_config)
        raise FilterException(
            f"Routing instance for VRF {vrf} not found on device {hostname(value)}."
        )

    # Fallback for providers that express BGP only as configuration intent.
    instance_asn = _intent(value, "bgp")["asn"]
    instance_status = "Active"
    if platform(value) == "Cumulus Linux":
        lo_if = interface_by_name(value, "lo")
    elif platform(value) == "Arista EOS":
        lo_if = interface_by_name(value, "Loopback0")
    else:
        raise FilterException(f"Unsupported platform: {platform(value)}")
    peers = []
    interface = lo_if.name

    local_config = {
        "status": instance_status,
        "asn": instance_asn,
        "interface": interface,
        "vrf": vrf,
        "peers": [BGPPeer(**peer) for peer in peers],
    }
    return BGPLocalConfig(**local_config)


def dns_servers(value: DeviceRenderData, optional: bool = True) -> list[str]:
    """Return a list of DNS servers for the device."""
    try:
        return _intent(value, "dns")["ipv4"]
    except KeyError as exc:
        if optional:
            return []
        raise FilterException(f"No DNS servers defined for site {site_name(value)}.") from exc


def ntp_servers(value: DeviceRenderData, optional: bool = True) -> list[str]:
    """Return a list of NTP servers for the device."""
    try:
        return _intent(value, "ntp")["ipv4"]
    except KeyError as exc:
        if optional:
            return []
        raise FilterException(f"No NTP servers defined for site {site_name(value)}.") from exc


def syslog_servers(value: DeviceRenderData, optional: bool = True) -> list[str]:
    """Return a list of Syslog servers for the device."""
    try:
        return _intent(value, "syslog")["ipv4"]
    except KeyError as exc:
        if optional:
            return []
        raise FilterException(f"No Syslog servers defined for site {site_name(value)}.") from exc


def tacacs_servers(value: DeviceRenderData, optional: bool = True) -> list[str]:
    """Return a list of TACACS+ servers for the device."""
    try:
        return _intent(value, "tacacs")["ipv4"]
    except KeyError as exc:
        if optional:
            return []
        raise FilterException(f"No tacacs servers defined for site {site_name(value)}.") from exc


def ztp_servers(value: DeviceRenderData) -> list[str]:
    """Return a list of ZTP servers for the device."""
    try:
        return _intent(value, "ztp")["ipv4"]
    except KeyError as exc:
        raise FilterException(f"No ZTP servers defined for site {site_name(value)}.") from exc


def firmware_cache(value: DeviceRenderData) -> list[str]:
    """Return a list of firmware cache servers, fall back to ZTP servers."""
    try:
        return _intent(value, "firmware_cache")["ipv4"]
    except KeyError:
        # Fallback to ZTP servers if firmware_cache is not present
        return ztp_servers(value)


def nvlink_topology(value: DeviceRenderData) -> str:
    """Return the NVLink topology for the device."""
    try:
        return _inventory(value, "nvlink_domain", [])[0]["topology"].lower()
    except KeyError as exc:
        raise FilterException(f"No NVLink topology defined for device {hostname(value)}.") from exc


def firmware_bundle_version(value: DeviceRenderData) -> str:
    """Return the firmware bundle version for this device."""
    try:
        return _intent(value, "firmware_bundle_version")
    except KeyError:
        # Default to 1.2.0 if not specified for backward compatibility
        return "1.2.0"


def firmware_bundles(value: DeviceRenderData) -> dict[str, Any]:
    """Return the firmware bundles mapping from normalized intent."""
    try:
        return _intent(value, "firmware_bundles")
    except KeyError as exc:
        raise FilterException(
            f"No firmware_bundles defined in intent for device {hostname(value)}."
        ) from exc


def firmware_bundle(value: DeviceRenderData, bundle_version: str = None) -> dict[str, Any]:
    """Return the specific firmware bundle configuration."""
    if bundle_version is None:
        bundle_version = firmware_bundle_version(value)

    bundles = firmware_bundles(value)
    if bundle_version not in bundles:
        raise FilterException(
            f"Firmware bundle version '{bundle_version}' "
            "not found in firmware_bundles. "
            f"Available versions: {list(bundles.keys())}"
        )

    return bundles[bundle_version]


def firmware_overrides(value: DeviceRenderData) -> dict[str, Any]:
    """Return firmware overrides for this device."""
    try:
        return _intent(value, "firmware_overrides")
    except KeyError:
        # Return empty overrides if not specified
        return {"skip_components": [], "custom_components": {}}


def firmware_component(
    value: DeviceRenderData, component: str, bundle_version: str = None
) -> dict[str, Any] | None:
    """Return firmware configuration for a specific component."""
    bundle = firmware_bundle(value, bundle_version)
    overrides = firmware_overrides(value)

    # Check if component should be skipped
    if component in overrides.get("skip_components", []):
        return None

    # Check for custom component override
    custom_components = overrides.get("custom_components", {})
    if component in custom_components:
        return custom_components[component]

    # Return component from bundle
    firmware = bundle.get("firmware", {})
    return firmware.get(component)


def has_firmware_bundle(value: DeviceRenderData) -> bool:
    """Return True if device has firmware bundle configuration."""
    try:
        firmware_bundles(value)
        return True
    except FilterException:
        return False


def nv_os_version(value: DeviceRenderData, bundle_version: str = None) -> str:
    """Return the NV-OS version for the specified firmware bundle."""
    bundle = firmware_bundle(value, bundle_version)
    nv_os = bundle.get("nv_os", {})
    return nv_os.get("version", "")


def nv_os_image_file(value: DeviceRenderData, bundle_version: str = None) -> str:
    """Return the NV-OS image file name for the specified firmware bundle."""
    bundle = firmware_bundle(value, bundle_version)
    nv_os = bundle.get("nv_os", {})
    return nv_os.get("image_file", "")


def interface_natural_sort_key(interface: Interface) -> tuple[str, list[int]]:
    """
    Create a sort key for interface names that handles various vendor formats.

    Supports formats like:
    - swp1, swp2, swp3
    - swp1s1, swp1s2, swp2s1, swp2s2
    - Ethernet1, Ethernet1/1, Ethernet1/1/1
    - ge-1/1/1, xe-1/1/1
    - swp49.4001, swp50.4001

    Returns a tuple of (prefix, [numeric_parts]) for proper sorting.
    """
    pattern = r"^([\w\-]+?)(\d+(?:[\/s\.]\d+)*)?$"
    match = re.match(pattern, interface.name)
    if not match:
        return (interface.name, [])

    prefix, numeric_part = match.groups()

    numeric_parts = []
    if numeric_part:
        parts = re.split(r"[\/s\.]", numeric_part)
        numeric_parts = [int(part) for part in parts if part.isdigit()]

    return (prefix, numeric_parts)


def helper_addresses_by_vlan(
    value: DeviceRenderData, location_value: LocationRenderData
) -> dict[int, list[str]]:
    """Return mapping of VLAN IDs to helper addresses for VLANs present on device."""
    vlan_interfaces = interfaces(value, prefix="vlan")
    device_vlan_ids = {intf.vlan_number for intf in vlan_interfaces if intf.vlan_number}
    result: dict[int, list[str]] = {}

    # From location: vlans with rel_vlan_to_helper_address
    if "vlans" in location_value.inventory:
        for vlan in location_value.inventory["vlans"]:
            vlan_id = vlan["vid"]
            if vlan_id in device_vlan_ids:
                helpers = set()
                for helper in vlan.get("rel_vlan_to_helper_address", []):
                    if "host" in helper:
                        helpers.add(helper["host"])
                if helpers:
                    result[vlan_id] = sorted(list(helpers), key=ipaddress.ip_address)

    return result


def helper_addresses_by_vrf(
    value: DeviceRenderData,
    location_value: LocationRenderData,
) -> dict[str, dict[str, list]]:
    """Return mapping of VRFs to their VLANs and helper addresses.

    Args:
        value: Provider-neutral device render data
        location_value: Provider-neutral location render data

    Returns:
        Dictionary mapping VRF names to dicts with 'vlans' and 'helpers' keys:
        {
            "default": {
                "vlans": [900, 901, 998],
                "helpers": ["10.48.175.141", "10.48.175.211"]
            }
        }
    """
    # Get all helper addresses for VLANs on this device
    all_vlan_helpers = helper_addresses_by_vlan(value, location_value)

    # Get all VLAN interfaces and group by VRF
    vlan_interfaces = interfaces(value, prefix="vlan")

    # Build mapping of VRF -> {vlans: [], helpers: []}
    result = {}
    for intf in vlan_interfaces:
        vlan_id = intf.vlan_number
        if vlan_id and vlan_id in all_vlan_helpers:
            vrf_name = intf.vrf
            if vrf_name not in result:
                result[vrf_name] = {"vlans": [], "helpers": set()}

            result[vrf_name]["vlans"].append(vlan_id)
            # Add all helpers for this VLAN to the VRF's helper set
            result[vrf_name]["helpers"].update(all_vlan_helpers[vlan_id])

    # Convert helper sets to sorted lists
    for vrf_config in result.values():
        vrf_config["helpers"] = sorted(list(vrf_config["helpers"]), key=ipaddress.ip_address)

    return result


def users(value: DeviceRenderData) -> list[dict[str, str]]:
    """Return username/role/password_key for each user."""
    try:
        user_mappings = _intent(value, "password_mappings")
    except KeyError as err:
        raise FilterException(f"Error accessing password mappings: {err}") from err

    if not user_mappings:
        raise FilterException(f"password_mappings is empty for device {hostname(value)}")

    result = []
    for username, user_config in user_mappings.items():
        for key in ("password", "rotation"):
            if key not in user_config:
                raise FilterException(
                    f"password_mappings: user '{username}' is missing required "
                    f"key '{key}' (device {hostname(value)})"
                )
        result.append(
            {
                "username": username,
                "role": (user_config.get("role") or "").strip(),
                "password_key": f"{user_config['password']}_{user_config['rotation']}",
            }
        )
    return sorted(result, key=lambda x: x["username"])


def _vrf_name_matches(actual: str | None, expected: Any) -> bool:
    """Match Nautobot VRF names, tolerating site-prefixed names used for uniqueness."""
    if not actual:
        return False

    expected_name = str(expected)
    return actual == expected_name or actual.split("_", 1)[-1] == expected_name


def _device_has_vrf(value: DeviceRenderData, vrf_name: Any) -> bool:
    """Return true if the device render data has the requested VRF attached."""
    for vrf in _inventory(value, "vrfs", []):
        if _vrf_name_matches(vrf.get("name"), vrf_name):
            return True

    for interface in value.interfaces:
        vrf = interface.get("vrf")
        if vrf and _vrf_name_matches(vrf.get("name"), vrf_name):
            return True
    return False


def l3vni_mappings(value: DeviceRenderData, vrf_name: Any) -> str:
    """Return the L3 VLAN value for a VRF from overlay plugin VXLAN data."""
    device_name = value.identity.name
    for vxlan in _inventory(value, "vxlans", []):
        if str(vxlan.get("vni_type", "")).lower() != "l3":
            continue

        vrf = vxlan.get("vrf") or {}
        if _vrf_name_matches(vrf.get("name"), vrf_name):
            l3_vlan = vxlan.get("l3_vlan_id")
            if l3_vlan in (None, ""):
                return ""
            return str(l3_vlan)

    if _device_has_vrf(value, vrf_name):
        return ""

    raise FilterException(
        f"VRF '{vrf_name}' not found in overlay VXLAN data for device {device_name}"
    )


def vni_mappings(value: DeviceRenderData, vlan_id: Any) -> str:
    """Return the VNI value for a VLAN from overlay plugin VXLAN data."""
    device_name = value.identity.name
    try:
        vlan_key = int(vlan_id)
    except (TypeError, ValueError) as exc:
        raise FilterException(
            f"Invalid VLAN ID '{vlan_id}' for overlay VXLAN lookup on device {device_name}"
        ) from exc

    for vxlan in _inventory(value, "vxlans", []):
        if str(vxlan.get("vni_type", "")).lower() != "l2":
            continue

        vlan = vxlan.get("vlan") or {}
        if vlan.get("vid") == vlan_key:
            vnid = vxlan.get("vnid")
            if vnid in (None, ""):
                raise FilterException(
                    f"No VNID found for VLAN {vlan_id} in overlay VXLAN data "
                    f"for device {device_name}"
                )
            return str(vnid)

    raise FilterException(
        f"VLAN {vlan_id} not found in overlay VXLAN data for device {device_name}"
    )


def evpn_esi_mac(value: DeviceRenderData, local_id: int | str) -> str:
    """Compute EVPN ESI MAC address from evpn_esi_base_mac and bond local-id."""
    hostname_val = value.identity.name
    try:
        base_mac = _intent(value, "evpn_esi_base_mac")
    except (KeyError, TypeError) as exc:
        raise FilterException(
            f"No evpn_esi_base_mac found in intent for device {hostname_val}"
        ) from exc
    try:
        octets = base_mac.split(":")
        if len(octets) != 6:
            raise ValueError("MAC address must contain six octets.")
        base_mac_int = int("".join(f"{int(octet, 16):02x}" for octet in octets), 16)
        esi_mac_int = base_mac_int + int(local_id)
    except (AttributeError, TypeError, ValueError) as exc:
        raise FilterException(
            f"Invalid EVPN ESI MAC inputs for device {hostname_val}: "
            f"base_mac={base_mac}, local_id={local_id}"
        ) from exc

    if esi_mac_int > 0xFFFFFFFFFFFF:
        raise FilterException(
            f"EVPN ESI MAC overflow for device {hostname_val}: "
            f"base_mac={base_mac}, local_id={local_id}"
        )

    return ":".join(f"{(esi_mac_int >> offset) & 0xFF:02x}" for offset in range(40, -1, -8))


def global_fabric_mac(value: DeviceRenderData, fail_if_missing: bool = True) -> str:
    """Get global fabric MAC address from device intent."""
    try:
        fabric_mac = _intent(value, "fabric-mac")
        return fabric_mac if fabric_mac is not None else ""
    except (KeyError, TypeError) as exc:
        if fail_if_missing:
            hostname_val = value.identity.name
            raise FilterException(
                f"No fabric-mac found in intent for device {hostname_val}"
            ) from exc
        return ""


def evpn_df_preference(value: DeviceRenderData) -> int:
    """Return EVPN df-preference from intent, defaulting to 50000."""
    try:
        result = _intent(value, "evpn")["df-preference"]
    except (KeyError, TypeError):
        result = 50000
    return result


def spx_subnets(value: DeviceRenderData, ip_version: int = 4) -> list[dict[str, str]]:
    """List Spectrum-X /31 downlink subnets with their rail prefix."""
    results = []
    for intf in value.interfaces:
        if not intf["role"] or intf["role"]["name"] != "Downlink":
            continue
        if not intf["ip_addresses"]:
            continue

        for ip_entry in intf["ip_addresses"]:
            if ip_entry["ip_version"] != ip_version:
                continue

            try:
                subnet = ip_entry["parent"]["prefix"]
                rail_prefix = ip_entry["parent"]["parent"]["parent"]["prefix"]
            except (KeyError, TypeError) as exc:
                raise FilterException(
                    f"Incomplete parent hierarchy for interface {intf['name']}. "
                    f"Expected /31 -> device prefix -> rail prefix structure."
                ) from exc

            rail_network = ipaddress.ip_network(rail_prefix)
            if rail_network.prefixlen not in [16, 17]:
                raise FilterException(
                    f"Invalid rail prefix length /{rail_network.prefixlen} for "
                    f"{rail_prefix}. Expected /16 (4-rail) or /17 (8-rail)."
                )

            results.append({"subnet": subnet, "rail_prefix": rail_prefix})

    return results


def get_vrf(
    value: DeviceRenderData, vrf_name: str = "", startswith: str = ""
) -> VRF | None | list[VRF]:
    """Return the VRF object for the given VRF name or matching startswith pattern."""
    if vrf_name:
        return next((vrf for vrf in attached_vrfs(value) if vrf.name == vrf_name), None)
    if startswith:
        return [vrf for vrf in attached_vrfs(value) if vrf.name.startswith(startswith)]
    return None


def has_vrf_interfaces(value: DeviceRenderData) -> bool:
    """Return True if the device has any interfaces in non-default VRFs."""
    for interface in value.interfaces:
        if interface["vrf"] and interface["vrf"]["name"].lower() != "default":
            return True
    return False


def device_aggregate(
    value: DeviceRenderData, peer_role: str, ip_version: int = 4, allow_multiple=False
) -> str | list[str]:
    """Aggregate all p2p interfaces."""
    supernets = set()
    for intf in value.interfaces:
        if not intf["role"] or intf["role"]["name"] != "Downlink":
            continue
        if not intf["ip_addresses"]:
            continue
        supernets.update(
            {
                ipaddress.ip_network(ip_entry["parent"]["parent"]["prefix"])
                for ip_entry in intf["ip_addresses"]
                if ip_entry["ip_version"] == ip_version
            }
        )

    if not supernets:
        raise FilterException("Found zero P2P aggregates on downlinks.")
    if len(supernets) > 1 and not allow_multiple:
        raise FilterException(f"Found multiple P2P aggregates on downlinks: {supernets}")

    peer_interfaces = [
        intf
        for intf in interfaces(value)
        if intf.connected_interface
        and intf.connected_interface.device.role.lower() == peer_role.lower()
    ]
    for peer_intf in peer_interfaces:
        peer_net_if = (
            ipaddress.ip_interface(peer_intf.primary_ipv4)
            if ip_version == 4
            else ipaddress.ip_interface(peer_intf.primary_ipv6)
        )
        contained = False
        for supernet in supernets:
            if peer_net_if.network.subnet_of(supernet):
                contained = True
        if not contained:
            raise FilterException(
                f"IP {peer_net_if} on {peer_intf.name} "
                f"is not contained in {[str(s) for s in supernets]}."
            )

    if allow_multiple:
        return [str(supernet) for supernet in sorted(supernets)]
    return str(supernets.pop())


def connected_devices(
    value: DeviceRenderData, peer_role: str | None = None
) -> set[ConnectedDevice]:
    """Return all devices connected to this device."""
    devices = {
        intf.connected_interface.device for intf in interfaces(value) if intf.connected_interface
    }
    if peer_role:
        devices = {device for device in devices if device.role == peer_role}
    return devices


def peer_group_ttl(value: DeviceRenderData, peer_group: str, vrf: str = "default") -> int | None:
    """Return the TTL for the first peer in the given BGP peer group, or None."""
    instance = bgp_routing_instance(value, vrf=vrf)
    for peer in instance.peers:
        if peer.peer_group == peer_group:
            return peer.ttl
    return None


def isis_metric(value: DeviceRenderData, interface_name: str) -> int | None:
    """Retrieve the ISIS metric for the given interface."""
    isis_interfaces = _intent(value, "isis")["interfaces"]
    return isis_interfaces.get(interface_name)


def dhcp_servers(value: DeviceRenderData, provider: str, optional: bool = True) -> list[str]:
    """Return a list of DHCP servers for the device."""
    try:
        return _intent(value, "dhcp")[provider]["ipv4"]
    except KeyError as exc:
        if optional:
            return []
        raise FilterException(
            f"No {provider} DHCP servers defined for site {site_name(value)}."
        ) from exc


def management_prefixes(value: DeviceRenderData) -> list[str]:
    """Return a list of remote prefixes for management traffic."""
    try:
        return _intent(value, "management_prefixes")["ipv4"]
    except KeyError as exc:
        raise FilterException(
            f"No management prefixes defined for site {site_name(value)}."
        ) from exc


def provisioning_servers(value: DeviceRenderData, fail_if_missing: bool = True) -> list[str]:
    """Return a list of provisioning servers."""
    try:
        return _intent(value, "provisioning_servers")["ipv4"]
    except KeyError as exc:
        if fail_if_missing:
            raise FilterException(
                f"No provisioning servers defined for site {site_name(value)}."
            ) from exc
        return []


def _is_device_overlay_assignment(entry: dict[str, Any]) -> bool:
    """Return true if an overlay assignment points at a Nautobot device."""
    object_type = entry.get("assigned_object_type")
    if not object_type:
        return True
    return (
        object_type.get("app_label") == "dcim" and object_type.get("model", "").lower() == "device"
    )


def _vxlan_route_targets(
    overlay: dict[str, Any], vxlan: dict[str, Any]
) -> tuple[list[str], list[str]]:
    """Return export/import route target names for an L2 VXLAN overlay."""
    export_targets = [target["name"] for target in vxlan.get("export_targets", [])]
    import_targets = [target["name"] for target in vxlan.get("import_targets", [])]
    if export_targets or import_targets:
        return export_targets, import_targets

    vxlan_id = vxlan.get("id")
    for assignment in overlay.get("assignments", []):
        if assignment.get("assigned_object_id") != vxlan_id:
            continue
        return (
            [target["name"] for target in assignment.get("export_targets", [])],
            [target["name"] for target in assignment.get("import_targets", [])],
        )

    return [], []


def _overlay_vxlan_assignment(overlay: dict[str, Any]) -> dict[str, Any] | None:
    """Return the VXLAN object assignment for an overlay entry."""
    assignments = overlay.get("assignments", [])
    for assignment in assignments:
        object_type = assignment.get("assigned_object_type") or {}
        if object_type.get("app_label") == "nautobot_app_overlays" and (
            object_type.get("model", "").lower() == "vxlan"
        ):
            return assignment

    return next(
        (
            assignment
            for assignment in assignments
            if assignment.get("export_targets") or assignment.get("import_targets")
        ),
        None,
    )


def l2vni_vrfs(value: DeviceRenderData) -> list[dict[str, Any]]:
    """Return per-LG L2VNI overlays for the device, sourced from the overlays plugin."""
    data = value.inventory
    l2_vxlans_by_id = {}
    l2_vxlans_by_overlay = {}
    for vxlan in data.get("vxlans", []):
        if str(vxlan.get("vni_type", "")).lower() != "l2":
            continue

        vxlan_id = vxlan.get("id")
        if vxlan_id:
            l2_vxlans_by_id[vxlan_id] = vxlan

        overlay_name = (vxlan.get("overlay") or {}).get("name")
        if overlay_name:
            l2_vxlans_by_overlay[overlay_name] = vxlan

    result = []
    for entry in data.get("overlay_assignments", []):
        if not _is_device_overlay_assignment(entry):
            continue

        overlay = entry.get("overlay") or {}
        overlay_name = overlay.get("name", "")
        vxlan = l2_vxlans_by_overlay.get(overlay_name)
        if not vxlan:
            vxlan_assignment = _overlay_vxlan_assignment(overlay)
            if vxlan_assignment:
                vxlan = l2_vxlans_by_id.get(vxlan_assignment.get("assigned_object_id"))
        if not vxlan:
            continue

        export_targets, import_targets = _vxlan_route_targets(overlay, vxlan)
        result.append(
            {
                "name": overlay_name,
                "vni": str(vxlan.get("vnid", "")),
                "export_targets": export_targets,
                "import_targets": import_targets,
            }
        )
    return sorted(result, key=lambda x: x["name"])
