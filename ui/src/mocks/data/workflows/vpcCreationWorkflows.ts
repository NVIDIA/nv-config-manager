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
export const VPC_CREATION_WORKFLOWS = {
  workflows: [
    {
      id: "a809c86a-790f-49cd-a5e1-ae84f20d0c21",
      workflow_type: "VpcCreationWorkflow",
      workflow_input: {
        namespace_tag: "spectrumx",
        description: "TenantB Tenant",
        rd_max: 65000,
        rd_min: 60000,
        site: "RNO1",
        vpc_id: "1234",
      },
      started_by: "joliao",
      start_time: "2025-03-04T02:55:39.440019Z",
      close_time: null,
      status: "RUNNING",
      pending_approval: false,
      search_attributes: {
        BuildIds: [
          "unversioned",
          "unversioned:879c4b06769e4c688df8fc5a3be6937d",
        ],
        User: ["joliao"],
      },
      href: "https://dev-ui.test.proxy.nonprod-nvkong.com:443/namespaces/default/workflows/a809c86a-790f-49cd-a5e1-ae84f20d0c21",
    },
  ],
  next_page_token: null,
};
