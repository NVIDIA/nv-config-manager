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
export const CONFIG_DEPLOY_WORKFLOWS = {
  workflows: [
    {
      id: "9e10d901-6017-4cf6-bd0e-a97a36edf99b",
      workflow_type: "DeployWorkflow",
      workflow_input: {
        device_id: "7ff67cec-4009-44d8-8f28-25e8a26764ec",
      },
      started_by: "joliao",
      start_time: "2025-03-04T02:32:38.087457Z",
      close_time: null,
      status: "RUNNING",
      pending_approval: false,
      search_attributes: {
        Site: ["PDX01"],
        DeviceName: ["LEAF2-GP1-CIN2-PDX01"],
        User: ["joliao"],
        DeviceID: ["7ff67cec-4009-44d8-8f28-25e8a26764ec"],
        BuildIds: [
          "unversioned",
          "unversioned:879c4b06769e4c688df8fc5a3be6937d",
        ],
        DeviceRole: ["cin-leaf"],
        DevicePlatform: ["cumulus-linux"],
      },
      href: "https://dev-ui.test.proxy.nonprod-nvkong.com:443/namespaces/default/workflows/9e10d901-6017-4cf6-bd0e-a97a36edf99b",
    },
  ],
  next_page_token: null,
};
