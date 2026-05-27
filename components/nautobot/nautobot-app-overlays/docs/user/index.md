# User Guide

The Overlays app provides data models for multi-tenant network isolation across
multiple fabric types.

## Models

- **[Overlay](overlays.md)** - Tenant network segment within a location
- **[VXLAN](vxlan.md)** - VNI tracking for L2/L3 VXLAN/EVPN overlays
- **[InfiniBand PKey](infiniband-pkey.md)** - IB partition key management and UFM integration
- **[InfiniBand MKey](infiniband-mkey.md)** - IB management key tracking
- **Overlay Assignment** - Associates resources (devices, interfaces, racks) with overlays

## Quick Start

### VXLAN/EVPN

1. Create an **Overlay** with isolation type **VXLAN/EVPN**
2. In IPAM, define **VRFs**, **VLANs**, and **Route Targets** as needed for your design (route targets are shared objects used by both VRFs and VXLANs).
3. Create **VXLANs** for VNI mappings. For **L2 VNIs**, set **import/export route targets** on the VXLAN when you need EVPN RTs for that segment; for **L3 VNIs**, RD/RT usually remain on the **VRF**, with the VXLAN linked to that VRF.
4. Add **Overlay Assignments** (devices, interfaces, racks) as needed

### InfiniBand PKey

1. Create an **Overlay** with isolation type **IB PKey**
2. Create an **InfiniBand PKey** linked to that overlay
3. Add **Overlay Assignments** for IB interfaces — each requires a GUID

### InfiniBand MKey

1. Create an **Overlay** with isolation type **IB MKey**
2. Create an **InfiniBand MKey** linked to that overlay
3. Add **Overlay Assignments** for IB interfaces

### NVLink Partition / Spectrum X

1. Create an **Overlay** with isolation type **NVLink Partition** or **Spectrum X**
2. Set the optional `partition_id` if required by the fabric controller
3. Add **Overlay Assignments** (devices, interfaces, racks) as needed
