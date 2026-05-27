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
export const CONNECTED_HOST_METADATA_WORKFLOWS = {
  workflows: [
    {
      id: "4aab170f-a682-47d6-8f13-0e721af4c696",
      workflow_type: "ConnectedHostMetadataWorkflow",
      workflow_input: {
        device_id: "ca22595f-7044-46d1-b760-63cac2f947b3",
      },
      started_by: "joliao",
      start_time: "2025-03-04T02:32:13.777899Z",
      close_time: "2025-03-04T02:32:24.394660Z",
      status: "COMPLETED",
      pending_approval: false,
      search_attributes: {
        Site: ["RNO1"],
        DeviceName: ["rno1-m04-c10-core1-cg1-tan-lab1"],
        User: ["joliao"],
        DeviceID: ["ca22595f-7044-46d1-b760-63cac2f947b3"],
        BuildIds: [
          "unversioned",
          "unversioned:879c4b06769e4c688df8fc5a3be6937d",
        ],
        DeviceRole: ["tan-core"],
        DevicePlatform: ["cumulus-linux"],
      },
      href: "https://dev-ui.test.proxy.nonprod-nvkong.com:443/namespaces/default/workflows/4aab170f-a682-47d6-8f13-0e721af4c696",
    },
  ],
  next_page_token: null,
};
