# DSX Air Demo Template Plugin

This sample plugin provides template entrypoints for the public DSX Air demo role names:
`OOB-HLEAF`, `OOB-MLEAF`, `TAN-BLEAF`, `TAN-HLEAF`, `TAN-SLEAF`,
`OOB-SPINE`, `TAN-SPINE`, `CIN-LEAF`, and `CIN-SPINE`.

Each role has a dedicated Cumulus Linux 5.16.1 entrypoint for the demo
topology. The templates inherit only from `cumulus-linux/role_common` in
`nv-config-manager` and keep demo-specific interface, bridge, router, and
VRF content inside this plugin.
