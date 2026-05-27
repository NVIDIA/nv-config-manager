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
import { delay, http, HttpResponse } from "msw";
import { sanitizeUrl } from "@/lib/utils";
import { mockApiURL as apiURL } from "@/config/mockApiUrl";
import { workflowsMockData } from "@/mocks/data";
import { FORBIDDEN_WORKFLOW_ID } from "@/mocks/data/formData";
import { createGenericWorkflow } from "@/mocks/data/workflows/genericWorkflow";

export const workflowTypes = [
  "BackupWorkflow",
  "ConnectedHostMetadataWorkflow",
  "DeployWorkflow",
  "MultiDeployWorkflow",
  "DeviceCableValidationWorkflow",
  "HelloWorld",
  "HelloWorldApproval",
  "PortLLDPInfoWorkflow",
  "RedfishProvisioningWorkflow",
  "SiteCableValidationWorkflow",
  "VpcCreationWorkflow",
  "VpcDeletionWorkflow",
  "InfinibandGetUnhealthyPortsWorkflow",
  "InfinibandCableValidationWorkflow",
  "InfinibandMlnxOSUpgradeWorkflow",
  "ReprovisionWorkflow",
  "SwitchOsUpgradeWorkflow",
  "CumulusHardwareValidationWorkflow",
  "AIRCreateSimulationWorkflow",
  "AIRValidateSiteWorkflow",
  "AIRDeleteSimulationWorkflow",
];

export const workflowFetchingHandlers = [
  http.get(sanitizeUrl(`${apiURL}/v1/workflow/types`), async () => {
    return HttpResponse.json(workflowTypes, { status: 200 });
  }),
  http.get(sanitizeUrl(`${apiURL}/v1/workflow`), async ({ request }) => {
    const url = new URL(request.url);
    const workflowType = url.searchParams.get("workflow_type");
    const nextPageToken = url.searchParams.get("next_page_token");
    const limit = url.searchParams.get("limit");

    const pageSize = limit ? parseInt(limit) : 10;
    const page = nextPageToken ? parseInt(nextPageToken) : 0;

    const workflows =
      workflowsMockData[workflowType as keyof typeof workflowsMockData]
        .workflows || [];
    const paginatedWorkflows = workflows.slice(
      page * pageSize,
      (page + 1) * pageSize
    );
    const hasMore = (page + 1) * pageSize < workflows.length;

    await delay(2500);

    return HttpResponse.json(
      {
        workflows: paginatedWorkflows,
        next_page_token: hasMore ? (page + 1).toString() : null,
      },
      { status: 200 }
    );
  }),
  http.get(sanitizeUrl(`${apiURL}/v1/workflow/:id`), async ({ params }) => {
    const { id } = params;

    if (id === FORBIDDEN_WORKFLOW_ID) {
      return HttpResponse.json(
        {
          error: "Forbidden: You do not have permission to view this workflow",
        },
        { status: 403 }
      );
    }

    await delay(2500);

    return HttpResponse.json(createGenericWorkflow(String(id)));
  }),
];
