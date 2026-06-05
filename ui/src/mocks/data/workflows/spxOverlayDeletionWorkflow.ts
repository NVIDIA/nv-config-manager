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
export const SPX_OVERLAY_DELETION_WORKFLOWS = {
  workflows: [
    {
      id: "6de98ae4-26ff-40a2-b7f2-8ad4c701baf6",
      workflow_type: "SpXOverlayDeletionWorkflow",
      workflow_input: {
        namespace_tag: "spectrumx",
        site: "string",
        overlay_id: "string",
      },
      started_by: "joliao",
      start_time: "2025-03-17T19:15:37.789363Z",
      close_time: "2025-03-17T19:15:38.546903Z",
      status: "COMPLETED",
      pending_approval: false,
      search_attributes: {
        BuildIds: [
          "unversioned",
          "unversioned:879c4b06769e4c688df8fc5a3be6937d",
        ],
        User: ["joliao"],
      },
      href: "https://dev-ui.test.proxy.nonprod-nvkong.com:443/namespaces/default/workflows/6de98ae4-26ff-40a2-b7f2-8ad4c701baf6",
    },
  ],
  next_page_token: null,
};
