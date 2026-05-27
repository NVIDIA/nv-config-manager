# API Reference

## REST API

Base URL: `/api/plugins/overlays/`

| Endpoint | Methods |
|----------|---------|
| `/overlays/` | GET, POST |
| `/overlays/{id}/` | GET, PUT, PATCH, DELETE |
| `/overlay-assignments/` | GET, POST |
| `/overlay-assignments/{id}/` | GET, PUT, PATCH, DELETE |
| `/vxlans/` | GET, POST |
| `/vxlans/{id}/` | GET, PUT, PATCH, DELETE |
| `/infiniband-pkeys/` | GET, POST |
| `/infiniband-pkeys/{id}/` | GET, PUT, PATCH, DELETE |

## GraphQL

```graphql
query {
  overlays {
    name
    tenant { name }
    location { name }
    isolation_type
    vxlans {
      vnid
      vni_type
      import_targets { name }
      export_targets { name }
    }
    pkeys { pkey }
  }

  vxlans {
    vnid
    name
    vni_type
    vlan { vid }
    vrf { name }
    import_targets { name }
    export_targets { name }
  }

  infiniband_pkeys {
    pkey
    name
    membership_type
  }
}
```

## Models

| Model | Key Fields |
|-------|------------|
| Overlay | name, tenant, location, isolation_type, partition_id |
| OverlayAssignment | overlay, assigned_object, role, guid, membership_type |
| VXLAN | vnid, vni_type, namespace, vlan, vrf, import_targets, export_targets, l3_vlan_id, overlay |
| InfiniBandPKey | pkey, membership_type, qos_config, overlay |

## Isolation Type Constraints

| Isolation Type | Associated Objects | Member Constraints |
|----------------|-------------------|-------------------|
| `vxlan_evpn` | VXLAN VNIs; VRF/VLAN/RT via IPAM and VXLAN links | Device, Interface, Rack |
| `ib_pkey` | InfiniBand PKeys | Interface only (GUID required) |
| `nvlink_partition` | None | Device, Interface, Rack |

## Management Commands

```bash
# Populate test data
nautobot-server populate_overlays

# Superpod-specific data
nautobot-server populate_overlays --superpod
```
