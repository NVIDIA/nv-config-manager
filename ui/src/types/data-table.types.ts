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
import { Column, ColumnDef } from "@tanstack/react-table";

export const WORKFLOW_STATUS = {
  completed: "COMPLETED",
  running: "RUNNING",
  not_started: "NOT_STARTED",
  pending_approval: "PENDING_APPROVAL",
};

type ISODateTimeString = string; // ISO8601 ex. 2024-05-23T06:31:29.861Z

export type BackupWorkflowInput = {
  device_id: string;
  trigger: "SCHEDULED" | "SYSLOG" | "WORKFLOW" | "API";
  user: string | null;
  user_domain: string;
  workflow_id: string | null;
  intended_config_commit_id: string | null;
};

export type DeployWorkflowInput = {
  device_id: string;
  commit_confirm?: boolean;
};

export type TenantDeployWorkflowInput = {
  device: string;
};

export type DevicePasswordRotationWorkflowInput = {
  device_id: string;
  selected_secret: string;
};
export type ReprovisionWorkflowInput = {
  device_id: string;
};

export type IBValidationWorkflowInput = {
  device_id: string;
};

export type IBOSUpgradeWorkflowInput = {
  device_id: string;
};

export type SwitchOsUpgradeWorkflowInput = {
  device_id: string;
};

export type DeviceCableValidationWorkflowInput = {
  device_id: string;
};

export type ConnectedDeviceMetadataWorkflowInput = {
  device_id: string;
};

export type AIRValidateSiteWorkflowInput = {
  site_name: string;
};

export type AIRCreateSimulationWorkflowInput = {
  name: string;
  topology: object;
};

export type AIRDeleteSimulationWorkflowInput = {
  simulation_id: string;
};

export type PortLLDPInfoWorkflowInput =
  | {
      device_id: string;
      interface: string;
      remote_mac_address?: never;
    }
  | {
      device_id?: never;
      interface?: never;
      remote_mac_address: string;
    };

export type SiteCableValidationWorkflowInput = {
  site: string;
  roles: string[];
  status: string[];
  tenant: string;
  device_type_ids: string[];
  raise_for_invalid: boolean;
};

export type CumulusHardwareValidationWorkflowInput = {
  site: string;
  roles: string[];
  status: string[];
  tenant: string;
  device_type_ids: string[];
  raise_for_invalid: boolean;
};

export type InfinibandCableValidationWorkflowInput = {
  ufm_device_id: string;
  switch_device_ids: string[];
};

export type VPCCreationWorkflowInput = {
  site: string;
  vpc_id: string;
  description: string;
  namespace_tag: string;
  rd_min: number;
  rd_max: number;
};
export interface VPCDeletionWorkflowInput {
  site: string;
  vpc_id: string;
  namespace_tag: string;
}

export type VpcTenantChangeWorkflowInput = {
  vpc_id: string;
  device_id: string;
  port_names: string[];
  site: string;
  namespace_tag?: string;
};

export type MultiDeployWorkflowInput = {
  role: string;
  max_batch_size: number;
  location?: string | null;
  status?: string[] | null;
  tenant?: string | null;
  commit_confirm?: boolean;
};

export type SitePasswordRotationWorkflowInput = {
  location: string;
  selected_secret: string;
  roles: string[];
  tenant: string;
  status: string[];
};

export type DiagnosticsWorkflowInput = {
  device_ids: string[];
  commands: string[];
  ticketing_platform: string; // empty string triggers ticketless mode
  issue_key: string;          // empty string triggers ticketless mode
  include_tech_support: boolean;
  user: string;
};

export type IBPortGuidDiscoveryWorkflowInput = {
  ufm_device_id: string;
  switch_device_ids: string[];
  dry_run: boolean;
};

export type WorkflowStageReview = {
  user: string;
  time: number;
};

export type StateHistory = {
  state:
    | "NOT_STARTED"
    | "IN_PROGRESS"
    | "PENDING_APPROVAL"
    | "COMPLETE"
    | "UNREACHABLE"
    | "FAILED"
    | "REJECTED"
    | "APPROVED";
  time: string;
};

export type WorkflowStage = {
  name: string;
  description: string;
  requires_approval: boolean;
  state: string;
  output: unknown;
  depends_on: string[];
  approvers: WorkflowStageReview[];
  rejecters: WorkflowStageReview[];
  approval_threshold: number;
  state_history: StateHistory[];
  retryable: boolean;
  retry_count: number;
  traceback: string | null;
  execution_time: number | null; // readonly
};

export type Workflow = {
  id: string;
  workflow_type: string;
  workflow_input: unknown;
  started_by: string;
  start_time: ISODateTimeString;
  close_time: ISODateTimeString | null;
  status: string;
  pending_approval: boolean;
  stages: WorkflowStage[];
  result: unknown;
  search_attributes: {
    [key: string]: string[] | number[] | boolean[] | ISODateTimeString[];
  };
  href: string; //readonly
};

export type WorkflowTableProps = {
  title: string;
  //workflowData: Workflow[];
  workflowType: string;
};

export type WorkflowColumns = Workflow;

export interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  //data: TData[];
  workflowType: string;
}

export interface SortableHeaderButtonProps<TData> {
  column: Column<TData>;
  title: string;
}

export interface LinkButtonProps {
  id: string;
}
