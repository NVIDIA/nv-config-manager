<!--
SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
SPDX-License-Identifier: Apache-2.0

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# DSX Air Simulation Configs

Pre-built simulation configs for testing specific workflows against a simulated
network topology using [NVIDIA DSX Air](https://air.nvidia.com).

## Available Configs

| File | Purpose |
|------|---------|
| `air_trial.yaml` | Resource-capped demo for DSX Air free trial accounts |
| `spx-overlay-demo.yaml` | SpX Overlay workflow end-to-end testing |

## SpX Overlay Demo (`spx-overlay-demo.yaml`)

Tests the four SpX Overlay workflows (creation, deletion, assignment, tenant
change) against a simulated SuperPOD topology.

### Prerequisites

- DSX Air account with an active subscription
- NGC API key with DSX Air access
- `sshpass` installed locally (`brew install sshpass`)

### Deploy

```bash
uv run --project installer nv-config-manager-installer air-sim deploy \
  -c development/air_sim/configs/spx-overlay-demo.yaml
```

Set your `org_id` and `ngc_api_key` in the config or via environment variables
before running. Use `use_internal: true` if deploying against an internal Air
instance.

### Post-Deploy Nautobot Setup

The mock topology job runs automatically and sets up devices, network context,
the `spectrumx` namespace tag, and the namespace site location. No manual setup
is required — the SpX Overlay workflows will work immediately after deploy.

### Running the Workflows

Once deploy completes, open `https://nvcm.air` and navigate to any SpX Overlay
workflow. Use the following test values:

| Field | Value |
|-------|-------|
| Site | `SPO01` |
| Tenant | `Public Demo` |
| Overlay ID | any unique string, e.g. `demo-overlay-001` |
| Namespace | `spectrumx` |
| RD Min / Max | defaults (60000 / 65000) |

After creation, verify the Overlay and VXLAN objects appear in Nautobot at
`https://nautobot.nvcm.air/plugins/overlays/`.
