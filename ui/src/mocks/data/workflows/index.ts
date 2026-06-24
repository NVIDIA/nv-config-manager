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
import { CONFIG_BACKUP_WORKFLOWS } from "./configBackupWorkflows";
import { CONNECTED_HOST_METADATA_WORKFLOWS } from "./connectedHostMetadataWorkflows";
import { CONFIG_DEPLOY_WORKFLOWS } from "./configDeployWorkflows";
import { DEVICE_CABLE_VALIDATION_WORKFLOWS } from "./deviceCableValidationWorkflows";
import { SITE_CABLE_VALIDATION_WORKFLOWS } from "./siteCableValidationWorkflows";
import { PORT_LLDP_INFO_WORKFLOWS } from "./portLldpInfoWorkflows";
import { SPX_OVERLAY_CREATION_WORKFLOWS } from "./spxOverlayCreationWorkflows";
import { SPX_OVERLAY_DELETION_WORKFLOWS } from "./spxOverlayDeletionWorkflow";
import { INFINIBAND_GET_UNHEALTHY_PORTS_WORKFLOWS } from "./infinibandGetUnhealthyWorkflows";
import { REPROVISION_WORKFLOWS } from "./reprovisionWorkflow";

export const ALL_WORKFLOW_DATA = {
  workflows: [
    ...CONFIG_BACKUP_WORKFLOWS.workflows,
    ...CONNECTED_HOST_METADATA_WORKFLOWS.workflows,
    ...CONFIG_DEPLOY_WORKFLOWS.workflows,
    ...DEVICE_CABLE_VALIDATION_WORKFLOWS.workflows,
    ...SITE_CABLE_VALIDATION_WORKFLOWS.workflows,
    ...PORT_LLDP_INFO_WORKFLOWS.workflows,
    ...SPX_OVERLAY_CREATION_WORKFLOWS.workflows,
    ...SPX_OVERLAY_DELETION_WORKFLOWS.workflows,
    ...INFINIBAND_GET_UNHEALTHY_PORTS_WORKFLOWS.workflows,
    ...REPROVISION_WORKFLOWS.workflows,
  ],
  next_page_token: null,
};

export const workflowsMockData = {
  BackupWorkflow: CONFIG_BACKUP_WORKFLOWS,
  ConnectedHostMetadataWorkflow: CONNECTED_HOST_METADATA_WORKFLOWS,
  DeployWorkflow: CONFIG_DEPLOY_WORKFLOWS,
  DeviceCableValidationWorkflow: DEVICE_CABLE_VALIDATION_WORKFLOWS,
  SiteCableValidationWorkflow: SITE_CABLE_VALIDATION_WORKFLOWS,
  PortLLDPInfoWorkflow: PORT_LLDP_INFO_WORKFLOWS,
  SpXOverlayCreationWorkflow: SPX_OVERLAY_CREATION_WORKFLOWS,
  SpXOverlayDeletionWorkflow: SPX_OVERLAY_DELETION_WORKFLOWS,
  InfinibandGetUnhealthyPortsWorkflow: INFINIBAND_GET_UNHEALTHY_PORTS_WORKFLOWS,
  ReprovisionWorkflow: REPROVISION_WORKFLOWS,
};
