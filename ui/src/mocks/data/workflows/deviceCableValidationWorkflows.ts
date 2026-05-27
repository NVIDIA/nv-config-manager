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
export const DEVICE_CABLE_VALIDATION_WORKFLOWS = {
  workflows: [
    {
      id: "4860ce4a-8742-4198-8d26-60cc7151cf4e",
      workflow_type: "DeviceCableValidationWorkflow",
      workflow_input: {
        device: null,
        device_id: "76984a54-3188-418b-8e03-0489355e19fc",
      },
      started_by: "joliao",
      start_time: "2025-03-04T02:33:00.874675Z",
      close_time: "2025-03-04T02:33:11.556508Z",
      status: "FAILED",
      pending_approval: false,
      search_attributes: {
        Site: ["PDX01"],
        DeviceName: ["LEAF2-GP1-CIN3-PDX01"],
        User: ["joliao"],
        DeviceID: ["76984a54-3188-418b-8e03-0489355e19fc"],
        BuildIds: [
          "unversioned",
          "unversioned:879c4b06769e4c688df8fc5a3be6937d",
        ],
        DeviceRole: ["cin-leaf"],
        DevicePlatform: ["cumulus-linux"],
      },
      href: "https://dev-ui.test.proxy.nonprod-nvkong.com:443/namespaces/default/workflows/4860ce4a-8742-4198-8d26-60cc7151cf4e",
    },
  ],
  next_page_token: null,
};
