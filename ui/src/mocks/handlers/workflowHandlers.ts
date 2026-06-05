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
import { ALL_WORKFLOW_DATA, workflowsMockData } from "@/mocks/data";
import { FORBIDDEN_WORKFLOW_ID } from "@/mocks/data/formData";
import { createGenericWorkflow } from "@/mocks/data/workflows/genericWorkflow";

export const workflowTypes = [
  "BackupWorkflow",
  "ConnectedHostMetadataWorkflow",
  "DeployWorkflow",
  "TenantDeployWorkflow",
  "MultiDeployWorkflow",
  "DeviceCableValidationWorkflow",
  "DevicePasswordRotationWorkflow",
  "HelloWorld",
  "HelloWorldApproval",
  "PortLLDPInfoWorkflow",
  "RedfishProvisioningWorkflow",
  "SiteCableValidationWorkflow",
  "SitePasswordRotationWorkflow",
  "VpcCreationWorkflow",
  "VpcDeletionWorkflow",
  "VpcTenantChangeWorkflow",
  "InfinibandGetUnhealthyPortsWorkflow",
  "InfinibandCableValidationWorkflow",
  "InfinibandMlnxOSUpgradeWorkflow",
  "ReprovisionWorkflow",
  "SwitchOsUpgradeWorkflow",
  "CumulusHardwareValidationWorkflow",
  "IBPKeyCreationWorkflow",
  "IBPKeyMemberAddWorkflow",
  "IBPKeyMemberUpdateWorkflow",
  "IBPKeyMemberDeleteWorkflow",
  "DiagnosticsWorkflow",
  "IBPortGuidDiscoveryWorkflow",
];

const workflowDisplayNames: Record<string, string> = {
  BackupWorkflow: "Configuration Backup",
  ConnectedHostMetadataWorkflow: "Connected Host Metadata",
  DeployWorkflow: "Configuration Deploy",
  TenantDeployWorkflow: "Tenant Deploy",
  MultiDeployWorkflow: "Multi-Deploy",
  DeviceCableValidationWorkflow: "Device Cable Validation",
  DevicePasswordRotationWorkflow: "Device Password Rotation",
  PortLLDPInfoWorkflow: "Port LLDP Info",
  SiteCableValidationWorkflow: "Site Cable Validation",
  SitePasswordRotationWorkflow: "Site Password Rotation",
  VpcCreationWorkflow: "VPC Creation",
  VpcDeletionWorkflow: "VPC Deletion",
  VpcTenantChangeWorkflow: "VPC Tenant Change",
  InfinibandGetUnhealthyPortsWorkflow: "InfiniBand Get Unhealthy Ports",
  InfinibandCableValidationWorkflow: "InfiniBand Cable Validation",
  InfinibandMlnxOSUpgradeWorkflow: "InfiniBand MLNX OS Upgrade",
  ReprovisionWorkflow: "Reprovision",
  SwitchOsUpgradeWorkflow: "Switch OS Upgrade",
  CumulusHardwareValidationWorkflow: "Cumulus Hardware Validation",
  IBPKeyCreationWorkflow: "IB PKey Creation",
  IBPKeyMemberAddWorkflow: "IB PKey Member Add",
  IBPKeyMemberUpdateWorkflow: "IB PKey Member Update",
  IBPKeyMemberDeleteWorkflow: "IB PKey Member Delete",
  DiagnosticsWorkflow: "Diagnostics",
  IBPortGuidDiscoveryWorkflow: "IB Port GUID Discovery",
};

const getWorkflowExecuteRoles = (workflowType: string) =>
  workflowType === "MultiDeployWorkflow" ? ["nvcm-admin"] : ["all"];

export const workflowMetadata = {
  workflows: workflowTypes.map((workflowType) => ({
    name: workflowType,
    display_name: workflowDisplayNames[workflowType] ?? workflowType,
    description: `${workflowDisplayNames[workflowType] ?? workflowType} workflow`,
    endpoint: `/ngc/${workflowType.toLowerCase()}`,
    namespace: "ngc",
    cli_name: workflowType.toLowerCase(),
    input_class: `${workflowType}Input`,
    read_roles: ["all"],
    execute_roles: getWorkflowExecuteRoles(workflowType),
  })),
};

const getFirstSearchAttribute = (workflow: unknown, key: string): string => {
  const workflowRecord = workflow as {
    search_attributes?: Record<string, Array<string | number | boolean>>;
  };
  return String(workflowRecord.search_attributes?.[key]?.[0] ?? "");
};

const getWorkflowStartTimestamp = (workflow: unknown): number => {
  const workflowRecord = workflow as { start_time?: string };
  return Date.parse(workflowRecord.start_time ?? "");
};

const filterWorkflows = (workflows: unknown[], url: URL) => {
  const searchAttributeFilters = [
    ["device_id", "DeviceID"],
    ["device_name", "DeviceName"],
    ["device_platform", "DevicePlatform"],
    ["device_role", "DeviceRole"],
    ["site", "Site"],
    ["user", "User"],
  ];

  return workflows.filter((workflow) => {
    const workflowRecord = workflow as { status?: string; workflow_type?: string };
    const workflowType = url.searchParams.get("workflow_type");
    const status = url.searchParams.get("status");
    const startTimeFilter = Date.parse(url.searchParams.get("start_time") ?? "");
    const endTimeFilter = Date.parse(url.searchParams.get("end_time") ?? "");

    if (workflowType && workflowRecord.workflow_type !== workflowType) {
      return false;
    }
    if (status && workflowRecord.status !== status) {
      return false;
    }
    if (!Number.isNaN(startTimeFilter) || !Number.isNaN(endTimeFilter)) {
      const workflowStartTime = getWorkflowStartTimestamp(workflow);

      if (Number.isNaN(workflowStartTime)) {
        return false;
      }
      if (!Number.isNaN(startTimeFilter) && workflowStartTime < startTimeFilter) {
        return false;
      }
      if (!Number.isNaN(endTimeFilter) && workflowStartTime > endTimeFilter) {
        return false;
      }
    }

    return searchAttributeFilters.every(([param, attribute]) => {
      const value = url.searchParams.get(param);
      if (!value) {
        return true;
      }
      return getFirstSearchAttribute(workflow, attribute)
        .toLowerCase()
        .includes(value.toLowerCase());
    });
  });
};

export const workflowFetchingHandlers = [
  http.get(sanitizeUrl(`${apiURL}/whoami`), async () => {
    return HttpResponse.json(
      { user: "joliao@nvidia.com", roles: ["nvcm-network"] },
      { status: 200 }
    );
  }),
  http.get(sanitizeUrl(`${apiURL}/v1/workflow/types`), async () => {
    return HttpResponse.json(workflowTypes, { status: 200 });
  }),
  http.get(sanitizeUrl(`${apiURL}/v1/workflow/metadata`), async () => {
    return HttpResponse.json(workflowMetadata, { status: 200 });
  }),
  http.get(sanitizeUrl(`${apiURL}/v1/workflow`), async ({ request }) => {
    const url = new URL(request.url);
    const workflowType = url.searchParams.get("workflow_type");
    const nextPageToken = url.searchParams.get("next_page_token");
    const limit = url.searchParams.get("limit");

    const pageSize = limit ? parseInt(limit) : 10;
    const page = nextPageToken ? parseInt(nextPageToken) : 0;

    const workflows = filterWorkflows(
      workflowType
        ? workflowsMockData[workflowType as keyof typeof workflowsMockData]
            ?.workflows || []
        : ALL_WORKFLOW_DATA.workflows,
      url
    );
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
