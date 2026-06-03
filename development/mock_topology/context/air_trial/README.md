# DSX Air Trial Mock Topology Context

This context is the source of truth for the DSX Air free trial demo topology and the
Nautobot mock data loaded by the Design Builder mock topology job. The DSX Air sim
generates its temporary DSX Air topology YAML from these device JSON files, so there
is no separate maintained topology export for this built-in demo.

Coverage:

- one `OOB-MLEAF` switch
- five `TAN-HLEAF` switches for multi-deploy testing
- one `oob-mgmt-server`
- OOB-MLEAF DHCP/ZTP over FPP to the server
- TAN leaf `eth0` ports on VLAN 100 behind the OOB-MLEAF
- Config Manager service load balancers on `172.18.255.201` and `172.18.255.202`
- load balancer source ranges for `172.18.0.0/16` and `10.0.0.0/8`
