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
export type SiteConfig = typeof siteConfig;

export const siteConfig = {
  name: "NVIDIA Config Manager",
  description: "Network automation and configuration management.",
  mainNav: [
    {
      title: "Workflows",
      href: "/workflows",
    },
    {
      title: "Configs",
      href: "/configs",
    },
  ],
  workflows: [
    {
      title: "Config Backup",
      slug: "backupworkflow",
      enabled: true,
    },
    {
      title: "Connected Host Metadata",
      slug: "connectedhostmetadataworkflow",
      enabled: true,
    },
    {
      title: "Config Deploy",
      slug: "deployworkflow",
      enabled: true,
    },
    {
      title: "Tenant Deploy",
      slug: "tenantdeployworkflow",
      enabled: true,
    },
    {
      title: "Multi-Deploy",
      slug: "multideployworkflow",
      enabled: true,
    },
    {
      title: "Device Cable Validation",
      slug: "devicecablevalidationworkflow",
      enabled: true,
    },
    {
      title: "Site Cable Validation",
      slug: "sitecablevalidationworkflow",
      enabled: true,
    },
    {
      title: "Port LLDP Info Workflow",
      slug: "portlldpinfoworkflow",
      enabled: true,
    },
    {
      title: "Redfish Provisioning",
      slug: "redfishprovisioningworkflow",
      enabled: false,
    },
    {
      title: "VPC Creation",
      slug: "vpccreationworkflow",
      enabled: true,
    },
    {
      title: "VPC Deletion",
      slug: "vpcdeletionworkflow",
      enabled: true,
    },
    {
      title: "VPC Tenant Change",
      slug: "vpctenantchangeworkflow",
      enabled: true,
    },
    {
      title: "IB Get Unhealthy Ports",
      slug: "infinibandgetunhealthyportsworkflow",
      enabled: true,
    },
    {
      title: "IB Cable Validation",
      slug: "infinibandcablevalidationworkflow",
      enabled: true,
    },
    {
      title: "IB MLNX OS Upgrade",
      slug: "infinibandmlnxosupgradeworkflow",
      enabled: true,
    },
    {
      title: "Reprovision",
      slug: "reprovisionworkflow",
      enabled: true,
    },
    {
      title: "Switch OS Upgrade",
      slug: "switchosupgradeworkflow",
      enabled: true,
    },
    {
      title: "Cumulus Hardware Validation",
      slug: "cumulushardwarevalidationworkflow",
      enabled: true,
    },
    {
      title: "Device Password Rotation",
      slug: "devicepasswordrotationworkflow",
      enabled: true,
    },
    {
      title: "Site Password Rotation",
      slug: "sitepasswordrotationworkflow",
      enabled: true,
    },
    { // NOSONAR
      title: "Diagnostics",
      slug: "diagnosticsworkflow",
      enabled: true,
    },
    {
      title: "IB Port GUID Discovery",
      slug: "ibportguiddiscoveryworkflow",
      enabled: true,
    },
  ],
};
