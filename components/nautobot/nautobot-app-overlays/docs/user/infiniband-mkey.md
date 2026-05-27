# InfiniBand MKey Management

The InfiniBand MKey model tracks Management Keys for IB subnet management protection.

## Overview

An MKey is a 64-bit authentication token that protects InfiniBand subnet management
operations (SMPs/MADs). Unlike PKeys, MKeys are not exposed via the UFM REST API.
MKey parameters are applied by SCP-delivering a generated `opensm.conf` to the UFM
server device followed by an OpenSM reload.

## Model Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| Name | String | Yes | Descriptive name |
| MKey Value | String | Yes | 64-bit hex management key (e.g., `0x0000000000a12c30`) |
| MKey Per Port | Boolean | No | Derive a unique MKey per HCA port instead of a global key (default: `false`) |
| MKey Lease Period | Integer | No | Lease period in seconds — `0` = infinite, 1–65535 (default: `60`) |
| Protect Bits | Integer | No | Protection enforcement level: `0`/`1` = partial, `2`/`3` = full (default: `0`) |
| MKey Global Seed | String | No | 64-bit hex seed used for per-port derivation when `mkey_per_port` is `true` |
| UFM Device | ForeignKey | No | The Nautobot Device representing the UFM server that receives the `opensm.conf` |
| Overlay | ForeignKey | No | Associated overlay (must have isolation type **IB MKey**) |
| Tenant | ForeignKey | No | Owning tenant |
| Status | Status | Yes | Active, Reserved, etc. |

!!! note "Overlay Constraint"
    InfiniBand MKeys can only be associated with Overlays that have isolation type **IB MKey**. The overlay dropdown in the UI is filtered to only show compatible overlays.

## Protection Bits

| Value | Enforcement |
|-------|-------------|
| 0 | No enforcement (MKey ignored) |
| 1 | Partial enforcement |
| 2 | Full enforcement |
| 3 | Full enforcement (reserved for future use) |

## Per-Port MKey Derivation

When `mkey_per_port` is enabled, a unique MKey is derived for each HCA port using the
`mkey_global_seed` as input. This provides stronger isolation at the cost of more
complex OpenSM configuration.

## Interface Membership

IB MKey overlays track interface membership via Overlay Assignments. Each assigned
interface requires a **GUID** (InfiniBand port identifier, e.g., `0x0002c9030012abcd`).

## Creating MKeys

**Web UI:** Navigate to **Multi-Tenancy > InfiniBand MKeys > Add**

**REST API:**

```bash
curl -X POST "https://nautobot.example.com/api/plugins/overlays/mkeys/" \
  -H "Authorization: Token $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "subnet-mgmt-mkey",
    "mkey_value": "0x0000000000a12c30",
    "mkey_lease_period": 60,
    "protect_bits": 2,
    "status": {"name": "Active"}
  }'
```
