/*
 * SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
export const INFINIBAND_GET_UNHEALTHY_PORTS_WORKFLOWS = {
  workflows: [
    {
      id: "48dd896f-b2e9-44ca-aa43-58e30f00c5d1",
      workflow_type: "InfinibandGetUnhealthyPortsWorkflow",
      workflow_input: {
        device_type_ids: [],
        raise_for_invalid: true,
        roles: ["TenantA Device", "CIN-Spine", "TAN-Core"],
        site: "PDX01",
        status: ["Active", "Provisioned"],
        tenant: "TenantA",
      },
      started_by: "joliao",
      start_time: "2025-03-04T02:33:52.785347Z",
      close_time: "2025-03-04T02:34:03.871234Z",
      status: "COMPLETED",
      pending_approval: false,
      search_attributes: {
        Site: ["PDX01"],
        BuildIds: [
          "unversioned",
          "unversioned:879c4b06769e4c688df8fc5a3be6937d",
        ],
        User: ["joliao"],
      },
      href: "https://dev-ui.test.proxy.nonprod-nvkong.com:443/namespaces/default/workflows/48dd896f-b2e9-44ca-aa43-58e30f00c5d1",
    },
  ],
  next_page_token: null,
};
