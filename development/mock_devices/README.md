# Mock Network Devices

Mock network devices for NVIDIA Config Manager sandbox testing. Provides:

1. **Mock Device APIs** — FastAPI servers (HTTPS, self-signed TLS) that emulate Arista EAPI and Cumulus NVUE endpoints, letting you test `NetworkConnection` code changes without real hardware.
2. **Mock DHCP Client** — Sends DHCP DISCOVER/REQUEST packets to the Kea DHCP server using standard UDP sockets, testing the full DHCP flow with devices from the mock topology.
3. **DHCP Config Validator** — Queries the Kea API to verify that DHCP reservations exist for mock devices (no raw sockets needed).
4. **Nautobot Wiring** — Updates each mock device's `primary_ip4` in Nautobot to its Kubernetes Service ClusterIP, so Temporal workflows can reach the mock API pods.
5. **ZTP Validator** — Validates the end-to-end ZTP provisioning chain (DHCP options → boot script → serial check → config fetch).
6. **Temporal Integration** — Makefile targets to trigger Temporal workflows (backup, cable validation) against mock devices.

## Quick Start

### Full Sandbox (Kind + topology + mock devices)

```bash
make sandbox-up
```

This deploys the platform with `mock_devices: false` (via `local-superpod-sandbox.yaml`), creates the mock topology, builds and deploys mock device API pods, and wires their ClusterIPs into Nautobot — all automatically.

> **Note:** `make kind-up` (without sandbox) still uses `local-superpod.yaml` with `mock_devices: true`, which routes workflows through the hardcoded `MockNetworkConnection` stub — useful for fast dev loops that don't need mock device pods.

### Test Workflows

After `sandbox-up`, test workflows directly:

```bash
# Trigger a backup workflow against a mock device (default: a04-u44-p01-tor-01)
make mock-workflow-backup

# Trigger cable validation against a mock device (default: a04-u44-p01-tor-01)
make mock-workflow-cable-validate

# Override the target device (must have a rendered intended config)
make mock-workflow-backup MOCK_BACKUP_DEVICE=a08-u32-p01-cleaf-01
make mock-workflow-cable-validate MOCK_CABLE_DEVICE=a08-u32-p01-cleaf-01
```

### DHCP Testing

```bash
# Validate DHCP config via Kea API — no DHCP packets sent (default: a04-u44-p01-tor-01, serial: 44:38:39:20:00:01)
make mock-dhcp-validate

# Send a real DHCP discover via UDP relay (default: a04-u44-p01-tor-01, serial: 44:38:39:20:00:01)
make mock-dhcp-discover

# Override the target device
make mock-dhcp-validate MOCK_DHCP_DEVICE=a08-u44-p01-mleaf-01 MOCK_DHCP_PLATFORM=cumulus MOCK_DHCP_SERIAL=2C:5E:AB:12:5A:38
make mock-dhcp-discover MOCK_DHCP_DEVICE=a08-u44-p01-mleaf-01 MOCK_DHCP_PLATFORM=cumulus MOCK_DHCP_SERIAL=2C:5E:AB:12:5A:38
```

### ZTP Testing

Validates the end-to-end ZTP provisioning chain: DHCP reservation options, boot script retrieval, serial validation, and config delivery.

```bash
# Run the full ZTP validation chain (default: a04-u44-p01-tor-01, serial: 44:38:39:20:00:01)
make mock-ztp-validate

# Override the target device (must be a device with a DHCP reservation and rendered config)
make mock-ztp-validate MOCK_ZTP_DEVICE=a08-u32-p01-cleaf-01 MOCK_ZTP_PLATFORM=cumulus MOCK_ZTP_SERIAL=7C:8C:09:B9:F8:8E
```

The validation checks four steps in sequence:

1. **DHCP reservation** — queries the Kea API for a matching reservation and verifies `boot-file-name` and `cumulus-provision-url` options are present
2. **Boot script fetch** — calls `GET /v1/device/{uuid}/boot-script` on the ZTP service
3. **Serial validation** — calls `POST /v1/device/{uuid}/validate_serial` to verify the serial matches Nautobot
4. **Config fetch** — calls `GET /v1/device/{uuid}/config/startup.yaml` to verify the config is served from Config Store

### Deploy Mock Devices to an Existing Cluster

```bash
# Build and deploy mock device pods
make mock-devices-up

# Check status
make mock-devices-status
```

### Remove Mock Devices

```bash
make mock-devices-down
```

## Architecture

### Mock Device API Server

Each mock device runs as a pod with a FastAPI server over self-signed TLS that emulates the device's management API:


| Platform      | API Style     | Default Port | Protocol |
| ------------- | ------------- | ------------ | -------- |
| Cumulus Linux | NVUE REST     | 8765         | HTTPS    |
| NV-OS         | NVUE REST     | 443          | HTTPS    |
| Arista EOS    | EAPI JSON-RPC | 443          | HTTPS    |


TLS is required because Temporal's `AristaConnection` and `CumulusConnection` connect via HTTPS (with `verify=False`). A self-signed cert is generated at Docker build time and bundled into the image.

The API server responds to the same endpoints these clients use in `src/nv_config_manager/temporal/client/device.py`:

- `show running-config`, `show hostname`, `show mac address-table`
- `show ip arp`, `show lldp neighbors detail`, `show interfaces status`
- Config sessions (create, diff, commit, abort)
- NVUE revision lifecycle (create, patch, apply, diff)
- Platform/firmware info, ZTP status, reboot
- Bridge domain MAC tables, ARP neighbor tables

LLDP neighbor data is populated with topology-aware entries so cable validation returns meaningful results.

### Version-Aware Fixtures

API responses are loaded from JSON fixture files organized by platform and OS version, with a fallback to hardcoded defaults. This allows testing version-specific JSON shape differences (e.g., Cumulus 5.11 vs 5.14 `product-release` location, `link.state` vs `link.oper-status`).

```text
fixtures/
  nvue/
    5.11.0/
      system.json          # product-release at root
      interface.json       # link.state (set)
      platform.json
      platform_inventory.json
    5.14.0/
      system.json          # product-release under version.*
      interface.json       # link.oper-status (string)
  eapi/
    4.29.5M/
      show_version.json
      show_interfaces_status.json
      show_mpls_interface.json   # JSON format (text-only on newer EOS)
  devices/                       # per-device overrides (optional)
    a04-u44-p01-tor-01/
      interface.json
```

Resolution order: **device override > version fixture > hardcoded default**.

The OS version is set per-device via the `MOCK_DEVICE_OS_VERSION` environment variable in `manifests/mock-devices.yaml`.

### Nautobot Wiring (`wire` command)

Temporal workflows look up the device's `primary_ip4` from Nautobot and connect to that address. The `wire` command bridges mock devices to Nautobot:

1. Resolves each mock device's Kubernetes Service DNS name to its ClusterIP
2. Creates a "Sandbox" IPAM namespace and a `10.96.0.0/12` prefix (covering the ClusterIP range)
3. Creates an IP address for the ClusterIP, a `mock-mgmt` interface on the device, and links them via the `IPAddressToInterface` relationship
4. Sets the device's `primary_ip4` to the new IP

After wiring, Temporal's `NetworkConnection.from_device_data()` resolves the mock service IP and connects over HTTPS to the mock API pod.

### Mock DHCP Client

The DHCP client uses standard Python UDP sockets for transport and Scapy for BOOTP/DHCP payload encoding/decoding:

- Supports both **hw-address** (MAC) and **client-id** (serial-based) identification
- Acts as a **DHCP relay agent** — auto-detects its pod IP and sets `giaddr` so Kea unicasts responses back, avoiding broadcast routing issues in Kubernetes overlay networks
- Validates DHCP OFFER/ACK responses against expected IPs
- Client-id template: `{{ serial | hex }}`

### DHCP Dev Service

A ClusterIP service (`nv-config-manager-dhcp-dev`) that exposes Kea's UDP port 67 within the cluster. The production Helm chart only exposes UDP 67 via LoadBalancer (MetalLB/NLB), so this dev service enables in-cluster DHCP testing.

### Sandbox Kea Configuration

Local Kind deployments require one Kea configuration override (set automatically in `values-local-small.yaml` / `values-local-medium.yaml`):

- **`networkDhcp.kea.dhcpSocketType: "udp"`** — switches Kea from raw sockets (L2) to kernel UDP sockets (L3), which work reliably in Kubernetes overlay networks.

The sandbox pod network subnet (`10.244.0.0/16`) is configured as a Nautobot config context with the `nv-config-manager-kea-static-data` schema, created automatically by `make topology`. This lets the DHCP confgen pick it up through its standard static data path, so DHCP packets from mock client pods match a Kea subnet.

### End-to-End Workflow Testing

With mock devices wired into Nautobot, the full pipeline looks like:

```text
make mock-topology    →  Nautobot (device data)
make mock-devices-up  →  Mock API pods (NVUE/eAPI)
make mock-wire-devices →  Nautobot primary_ip4 → mock ClusterIP
make mock-workflow-*  →  Temporal → NetworkConnection → mock pods
```

Testable workflows with current mock APIs:


| Workflow                | Feasibility | Notes                                                                     |
| ----------------------- | ----------- | ------------------------------------------------------------------------- |
| Backup                  | High        | `get_running_configuration` fully mocked                                  |
| Cable Validation        | High        | LLDP neighbors + interface status + MAC/ARP mocked                        |
| Config Deploy (diff)    | Medium      | Requires a rendered config in Config Store                                |
| Config Deploy (commit)  | Medium      | Mock commit succeeds but simplified state machine                         |
| ZTP Validation          | High        | `make mock-ztp-validate` checks DHCP options, boot script, serial, config |
| OS Upgrade / ZTP (full) | Low         | Full DORA+fetch+reboot cycle needs stateful ZTP mock and firmware stubs   |
| Hardware Validation     | Medium      | Platform/inventory stubs exist but may need shape fixes                   |


## Sandbox vs. Production

The sandbox runs all the same services as production (Nautobot, Render, Temporal, Config Store, Kea, NATS) but with several differences:


| Aspect                  | Production                                                           | Sandbox                                                                                                             |
| ----------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| **Network devices**     | Real switches (Arista, Cumulus) with management IPs                  | FastAPI pods emulating EAPI/NVUE over self-signed TLS                                                               |
| **Device connectivity** | Temporal connects to real management IPs via HTTPS                   | `wire` command maps `primary_ip4` to Kubernetes ClusterIPs                                                          |
| **DHCP transport**      | Kea uses raw sockets (L2 broadcast)                                  | Kea uses kernel UDP sockets (L3); mock client sets `giaddr` to simulate relay                                       |
| **DHCP subnets**        | Real management subnets from site IPAM                               | Pod network subnet (`10.244.0.0/16`) added via Nautobot config context (`nv-config-manager-kea-static-data` schema)              |
| **Secrets**             | HashiCorp Vault (production secrets, SPIFFE mTLS)                    | `--sites DC01` generates mock K8s secrets (`root_password_r1`, etc.)                                                |
| **TLS certificates**    | Proper CA-signed certs                                               | Self-signed certs generated at Docker build time (`verify=False`)                                                   |
| **Topology**            | Real devices discovered/imported into Nautobot                       | Design Builder job creates devices from JSON fixtures                                                               |
| **Config rendering**    | Templates render for all devices with full Vault secrets             | Only devices with matching templates render; some roles (e.g. UFM) may lack templates                               |
| **ZTP device auth**     | IP-based: ZTP verifies request comes from the device's management IP | Mock auth headers (`X-Auth-Request-Email`) via `localDev.mockAuth`, same pattern as all sandbox services            |
| **Mock API fidelity**   | N/A                                                                  | Version-aware JSON fixtures with hardcoded fallbacks; responses are structurally correct per OS version              |
| **Cluster**             | Multi-node EKS with NLB, MetalLB, SPIFFE                             | Single-node Kind with NodePort, no SPIFFE                                                                           |


### What the sandbox tests well

- End-to-end service orchestration (Nautobot -> Render -> Config Store -> Temporal -> device)
- API contract compatibility (correct endpoints, request/response shapes, auth headers)
- DHCP reservation generation and subnet matching
- ZTP provisioning chain (DHCP options -> boot script -> serial validation -> config delivery)
- Nautobot IPAM and device data pipeline
- Helm chart configuration and service wiring

### What requires production or dedicated test environments

- Real device behavior (firmware upgrades, reboot cycles, ZTP state machines)
- Network performance and timeouts under load
- Vault/SPIFFE integration and secret rotation
- Multi-node scheduling, pod anti-affinity, autoscaling
- LoadBalancer and NLB connectivity for DHCP/ZTP

## Deployed Mock Devices

The default manifests deploy devices matching the superpod mock topology:


| Service              | Device                   | Platform | Role             | Serial (DHCP/ZTP)       | Port |
| -------------------- | ------------------------ | -------- | ---------------- | ----------------------- | ---- |
| mock-sp-tor-01       | a04-u44-p01-tor-01       | Cumulus  | OOB-Leaf         | `44:38:39:20:00:01`     | 8765 |
| mock-sp-oobspine-01  | a08-u28-p01-oobspine-01  | Cumulus  | OOB-Spine        | `54:9B:24:41:33:12`     | 8765 |
| mock-sp-cleaf-01     | a08-u32-p01-cleaf-01     | Cumulus  | In-Band-Leaf     | `7C:8C:09:B9:F8:8E`     | 8765 |
| mock-sp-mleaf-01     | a08-u44-p01-mleaf-01     | Cumulus  | Mgmt-Leaf        | `2C:5E:AB:12:5A:38`     | 8765 |
| mock-sp-bleaf-01     | a09-u28-p01-bleaf-01     | Cumulus  | Border-Leaf      | `E8:9E:49:CF:4E:90`     | 8765 |
| mock-sp-sleaf-01     | a09-u32-p01-sleaf-01     | Cumulus  | Storage-Leaf     | `7C:8C:09:B9:F8:9E`     | 8765 |
| mock-sp-spine-01     | a09-u36-p01-spine-01     | Cumulus  | Converged-Spine  | `7C:8C:09:B9:F8:A6`     | 8765 |
| mock-sp-pleaf-01     | a09-u44-p01-pleaf-01     | Cumulus  | Power-Leaf       | `2C:5E:AB:12:5A:68`     | 8765 |


The two MLNX-OS UFM devices (`a09-u23-p01-ufm-01`, `b09-u23-p01-ufm-02`) are not mocked — they have no `intended-firmware` and no supported mock API implementation.


After `make mock-wire-devices`, each device's `primary_ip4` in Nautobot points to the Service ClusterIP so Temporal workflows can reach the mock API pod.

To add more devices, copy a deployment block in `manifests/mock-devices.yaml`, update the env vars with data from `development/mock_topology/context/superpod/devices/`, and add a matching entry to `DEFAULT_DEVICE_MAP` in `mock_device/wire_nautobot.py`.

## CLI Usage

The mock device CLI provides the following commands:

### `serve` — Run the mock device API

```bash
uv run mock-device serve \
    --name a04-u44-p01-tor-01 \
    --platform cumulus \
    --serial 44:38:39:20:00:01 \
    --os-version 5.13.1 \
    --port 8765
```

The `--os-version` flag controls which fixture files are loaded (e.g. `fixtures/nvue/5.11.0/`). If omitted, it defaults to the `MOCK_DEVICE_OS_VERSION` environment variable.

### `wire` — Wire mock device IPs into Nautobot

```bash
uv run mock-device wire \
    --nautobot-url http://nv-config-manager-nautobot.nv-config-manager.svc:80 \
    --nautobot-token <token>
```

Resolves each mock device's Kubernetes Service ClusterIP and updates the device's `primary_ip4` in Nautobot. This is typically run as a Kubernetes Job via `make mock-wire-devices`.

### `dhcp` — Send DHCP requests

```bash
uv run mock-device dhcp \
    --name a04-u44-p01-tor-01 \
    --platform cumulus \
    --serial 44:38:39:20:00:01 \
    --dhcp-server nv-config-manager-dhcp-dev.nv-config-manager.svc.cluster.local \
    --client-id-template '{{ serial | hex }}'
```

The client auto-detects its pod IP for the relay `giaddr`. To override, pass `--relay-gateway <ip>`.

### `validate` — Check DHCP config via API

```bash
uv run mock-device validate \
    --name a04-u44-p01-tor-01 \
    --platform cumulus \
    --serial 44:38:39:20:00:01 \
    --client-id-template '{{ serial | hex }}' \
    --dhcp-api-url http://nv-config-manager-dhcp-internal.nv-config-manager.svc:9000
```

### `ztp-validate` — Validate ZTP provisioning chain

```bash
uv run mock-device ztp-validate \
    --name a04-u44-p01-tor-01 \
    --platform cumulus \
    --serial 44:38:39:20:00:01 \
    --client-id-template '{{ serial | hex }}' \
    --dhcp-api-url http://nv-config-manager-dhcp-internal.nv-config-manager.svc:9000 \
    --ztp-api-url http://nv-config-manager-ztp-api.nv-config-manager.svc:9000
```

Validates: DHCP reservation has `boot-file-name`, ZTP serves the boot script, serial matches Nautobot, and startup config is available. Typically run as a Kubernetes Job via `make mock-ztp-validate`.

### `generate-fixtures` — Generate fixture files from topology data

```bash
# Generate from a single device JSON
uv run mock-device generate-fixtures \
    development/mock_topology/context/superpod/devices/a04-u44-p01-tor-01.json

# Generate from an entire topology directory
uv run mock-device generate-fixtures \
    development/mock_topology/context/superpod/devices/

# Include per-device override fixtures (LLDP neighbors, etc.)
uv run mock-device generate-fixtures \
    development/mock_topology/context/superpod/devices/ \
    --device-overrides

# Write to a custom output directory
uv run mock-device generate-fixtures \
    development/mock_topology/context/superpod/devices/ \
    --output-dir /tmp/fixtures
```

Reads each device's platform and `config_context.intended-firmware.version` from the topology JSON and writes version-specific fixture files to `fixtures/{platform}/{version}/`. The generator is version-aware: Cumulus 5.14+ fixtures use `link.oper-status` and nested `version.product-release`, while 5.11 fixtures use `link.state` (set) and root-level `product-release`.

## Extending

### Adding a new device

1. Find the device JSON in `development/mock_topology/context/superpod/devices/`
2. Add a Deployment + Service to `manifests/mock-devices.yaml`
3. Set `MOCK_DEVICE_NAME`, `MOCK_DEVICE_PLATFORM`, `MOCK_DEVICE_SERIAL`, and `MOCK_DEVICE_OS_VERSION` (e.g. `5.13.1` for Cumulus)
4. Add an entry to `DEFAULT_DEVICE_MAP` in `mock_device/wire_nautobot.py` so the `wire` command knows about it
5. Optionally generate per-device fixture overrides:
   ```bash
   uv run mock-device generate-fixtures \
       development/mock_topology/context/superpod/devices/<device>.json \
       --device-overrides
   ```
6. Rebuild the image to pick up new fixtures: `make mock-devices-up`

### Adding new API responses

- **Via fixtures (preferred):** Add a `.json` file under `fixtures/{platform}/{version}/` using the endpoint key as filename (e.g. `show_version.json` for eAPI, `system.json` for NVUE). The `FixtureLoader` will pick it up automatically.
- **Via generator:** Extend `mock_device/fixture_generator.py` to emit the new fixture from topology data, then re-run `generate-fixtures`.
- **Hardcoded fallback:** For responses that don't vary by version, edit `mock_device/device_api/eapi.py` (`_dispatch_command()`) or `mock_device/device_api/nvue.py` (route handlers) directly. The fixture loader falls through to these defaults when no file is found.
