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
import fs from "node:fs/promises";
import path from "node:path";

import { expect, test as base, type Page, type Route } from "@playwright/test";

const SCREENSHOT_DIR = path.resolve(
  process.cwd(),
  "../docs/assets/images/workflows"
);
const CARD_SELECTOR =
  "xpath=ancestor::div[contains(concat(' ', normalize-space(@class), ' '), ' rounded-lg ')][1]";
const AIR_SITE = "TRIAL01 - demo";
const AIR_TAN_LEAF_01_ID = "air-trial-tan-leaf-01";
const PDX_SITE = "PDX01";
const PDX_CUMULUS_ID = "pdx01-cumulus-leaf-01";
const PDX_MLNX_ID = "pdx01-mlx-switch-01";
const PDX_UFM_ID = "pdx01-ufm-01";
const DEMO_VPC_ID = "vpc-demo-101";

type ParameterOption = {
  id: string;
  name: string;
};

type Device = {
  id: string;
  name: string;
  platform: string;
  role: string;
  status: string;
  tenant: string;
};

type QueryValue = string | string[];

type WorkflowScreenshot = {
  fileName: string;
  path: string;
  query?: Record<string, QueryValue>;
  title: string;
};

const DOC_SITES: ParameterOption[] = [
  { id: AIR_SITE, name: AIR_SITE },
  { id: PDX_SITE, name: PDX_SITE },
  { id: "RNO1", name: "RNO1" },
];

const DOC_ROLES: ParameterOption[] = [
  { id: "TAN-HLEAF", name: "TAN-HLEAF" },
  { id: "CIN-Leaf", name: "CIN-Leaf" },
  { id: "CIN-Spine", name: "CIN-Spine" },
  { id: "UFM", name: "UFM" },
  { id: "wan", name: "wan" },
];

const DOC_STATUSES: ParameterOption[] = [
  { id: "Active", name: "Active" },
  { id: "Provisioned", name: "Provisioned" },
  { id: "Provisioning", name: "Provisioning" },
  { id: "Staged", name: "Staged" },
];

const DOC_TENANTS: ParameterOption[] = [
  { id: "NGC", name: "NGC" },
  { id: "TenantA", name: "TenantA" },
  { id: "TenantB", name: "TenantB" },
];

const DOC_DEVICES_BY_SITE: Record<string, Device[]> = {
  [AIR_SITE]: [
    {
      id: AIR_TAN_LEAF_01_ID,
      name: "tan-leaf-01",
      platform: "Cumulus Linux",
      role: "TAN-HLEAF",
      status: "Provisioned",
      tenant: "NGC",
    },
    {
      id: "air-trial-tan-leaf-02",
      name: "tan-leaf-02",
      platform: "Cumulus Linux",
      role: "TAN-HLEAF",
      status: "Provisioned",
      tenant: "NGC",
    },
    {
      id: "air-trial-tan-leaf-03",
      name: "tan-leaf-03",
      platform: "Cumulus Linux",
      role: "TAN-HLEAF",
      status: "Provisioned",
      tenant: "NGC",
    },
    {
      id: "air-trial-tan-leaf-04",
      name: "tan-leaf-04",
      platform: "Cumulus Linux",
      role: "TAN-HLEAF",
      status: "Provisioned",
      tenant: "NGC",
    },
    {
      id: "air-trial-tan-leaf-05",
      name: "tan-leaf-05",
      platform: "Cumulus Linux",
      role: "TAN-HLEAF",
      status: "Provisioned",
      tenant: "NGC",
    },
  ],
  [PDX_SITE]: [
    {
      id: PDX_CUMULUS_ID,
      name: "pdx01-cumulus-leaf-01",
      platform: "Cumulus Linux",
      role: "CIN-Leaf",
      status: "Provisioned",
      tenant: "TenantB",
    },
    {
      id: "pdx01-arista-leaf-01",
      name: "pdx01-arista-leaf-01",
      platform: "Arista EOS",
      role: "CIN-Leaf",
      status: "Active",
      tenant: "TenantA",
    },
    {
      id: PDX_MLNX_ID,
      name: "infiniband-switch1",
      platform: "MLNX-OS",
      role: "CIN-Spine",
      status: "Active",
      tenant: "TenantB",
    },
    {
      id: PDX_UFM_ID,
      name: "pdx01-ufm-01",
      platform: "UFM",
      role: "UFM",
      status: "Active",
      tenant: "TenantB",
    },
  ],
  RNO1: [
    {
      id: "rno1-cumulus-leaf-01",
      name: "rno1-cumulus-leaf-01",
      platform: "Cumulus Linux",
      role: "CIN-Leaf",
      status: "Active",
      tenant: "TenantA",
    },
  ],
};

const AIR_DEVICE_QUERY = {
  "device-id": AIR_TAN_LEAF_01_ID,
  site: AIR_SITE,
};
const PDX_MLNX_QUERY = {
  "device-id": PDX_MLNX_ID,
  site: PDX_SITE,
};
const SITE_SCOPE_QUERY = {
  role: "TAN-HLEAF",
  site: AIR_SITE,
  status: "Provisioned",
  tenant: "NGC",
};

const WORKFLOW_SCREENSHOTS: WorkflowScreenshot[] = [
  {
    fileName: "backupworkflow-form.png",
    path: "/workflows/backupworkflow/form",
    query: AIR_DEVICE_QUERY,
    title: "New Config Backup Workflow",
  },
  {
    fileName: "connectedhostmetadataworkflow-form.png",
    path: "/workflows/connectedhostmetadataworkflow/form",
    query: AIR_DEVICE_QUERY,
    title: "Connected Host Metadata Workflow",
  },
  {
    fileName: "cumulushardwarevalidationworkflow-form.png",
    path: "/workflows/cumulushardwarevalidationworkflow/form",
    query: SITE_SCOPE_QUERY,
    title: "Cumulus Hardware Validation Workflow Form",
  },
  {
    fileName: "deployworkflow-form.png",
    path: "/workflows/deployworkflow/form",
    query: AIR_DEVICE_QUERY,
    title: "Config Deploy Workflow",
  },
  {
    fileName: "devicecablevalidationworkflow-form.png",
    path: "/workflows/devicecablevalidationworkflow/form",
    query: AIR_DEVICE_QUERY,
    title: "Device Cable Validation Workflow",
  },
  {
    fileName: "devicepasswordrotationworkflow-form.png",
    path: "/workflows/devicepasswordrotationworkflow/form",
    query: {
      device: AIR_TAN_LEAF_01_ID,
      selected_secret: "cumulus",
      site: AIR_SITE,
    },
    title: "Device Password Rotation Workflow",
  },
  {
    fileName: "diagnosticsworkflow-form.png",
    path: "/workflows/diagnosticsworkflow/form",
    title: "Diagnostics Workflow",
  },
  {
    fileName: "ibportguiddiscoveryworkflow-form.png",
    path: "/workflows/ibportguiddiscoveryworkflow/form",
    title: "IB Port GUID Discovery",
  },
  {
    fileName: "infinibandcablevalidationworkflow-form.png",
    path: "/workflows/infinibandcablevalidationworkflow/form",
    query: {
      role: ["UFM", "CIN-Spine"],
      site: PDX_SITE,
      status: "Active",
      tenant: "TenantB",
    },
    title: "Infiniband Cable Validation Workflow Form",
  },
  {
    fileName: "infinibandgetunhealthyportsworkflow-form.png",
    path: "/workflows/infinibandgetunhealthyportsworkflow/form",
    query: PDX_MLNX_QUERY,
    title: "IB Get Unhealthy Ports Workflow",
  },
  {
    fileName: "infinibandmlnxosupgradeworkflow-form.png",
    path: "/workflows/infinibandmlnxosupgradeworkflow/form",
    query: PDX_MLNX_QUERY,
    title: "IB MLNX OS Upgrade Workflow",
  },
  {
    fileName: "multideployworkflow-form.png",
    path: "/workflows/multideployworkflow/form",
    query: {
      location: AIR_SITE,
      max_batch_size: "5",
      role: "TAN-HLEAF",
      status: "Provisioned",
    },
    title: "Multi-Deploy Workflow Form",
  },
  {
    fileName: "portlldpinfoworkflow-form.png",
    path: "/workflows/portlldpinfoworkflow/form",
    title: "Port LLDP Info Workflow Form",
  },
  {
    fileName: "reprovisionworkflow-form.png",
    path: "/workflows/reprovisionworkflow/form",
    query: AIR_DEVICE_QUERY,
    title: "Reprovision Workflow",
  },
  {
    fileName: "sitecablevalidationworkflow-form.png",
    path: "/workflows/sitecablevalidationworkflow/form",
    query: SITE_SCOPE_QUERY,
    title: "New Site Cable Validation Workflow Form",
  },
  {
    fileName: "sitepasswordrotationworkflow-form.png",
    path: "/workflows/sitepasswordrotationworkflow/form",
    query: {
      location: AIR_SITE,
      role: "TAN-HLEAF",
      selected_secret: "cumulus",
      status: "Provisioned",
      tenant: "NGC",
    },
    title: "Site Password Rotation Workflow",
  },
  {
    fileName: "switchosupgradeworkflow-form.png",
    path: "/workflows/switchosupgradeworkflow/form",
    query: AIR_DEVICE_QUERY,
    title: "Switch OS Upgrade Workflow",
  },
  {
    fileName: "tenantdeployworkflow-form.png",
    path: "/workflows/tenantdeployworkflow/form",
    query: AIR_DEVICE_QUERY,
    title: "Tenant Deploy Workflow",
  },
  {
    fileName: "vpccreationworkflow-form.png",
    path: "/workflows/vpccreationworkflow/form",
    query: {
      description: "Demo tenant network",
      namespace: "spectrumx",
      rd_max: "65010",
      rd_min: "65000",
      site: PDX_SITE,
      vpc: DEMO_VPC_ID,
    },
    title: "VPC Creation Workflow Form",
  },
  {
    fileName: "vpcdeletionworkflow-form.png",
    path: "/workflows/vpcdeletionworkflow/form",
    query: {
      namespace: "spectrumx",
      site: PDX_SITE,
      vpc: DEMO_VPC_ID,
    },
    title: "VPC Deletion Workflow Form",
  },
  {
    fileName: "vpctenantchangeworkflow-form.png",
    path: "/workflows/vpctenantchangeworkflow/form",
    query: {
      "device-id": PDX_CUMULUS_ID,
      namespace: "spectrumx",
      port_names: "swp1, swp2",
      site: PDX_SITE,
      vpc: DEMO_VPC_ID,
    },
    title: "VPC Tenant Change Workflow Form",
  },
];

const test = base.extend<{ page: Page }>({
  page: async ({ browser }, run) => {
    const context = await browser.newContext({
      serviceWorkers: "block",
      viewport: { width: 1280, height: 900 },
    });
    const page = await context.newPage();

    await setupDocsMocks(page);
    await page.addInitScript(() => {
      window.BYPASS_MSW = true;
    });

    await run(page);
    await context.close();
  },
});

test.describe("workflow form docs screenshots", () => {
  test.beforeAll(async () => {
    await fs.mkdir(SCREENSHOT_DIR, { recursive: true });
  });

  for (const workflow of WORKFLOW_SCREENSHOTS) {
    test(`captures ${workflow.title}`, async ({ page }) => {
      await page.goto(routeWithQuery(workflow.path, workflow.query));
      await page.waitForLoadState("networkidle");

      const heading = page.getByRole("heading", { name: workflow.title });
      await expect(heading).toBeVisible();
      await settleFonts(page);
      await screenshotWorkflowCard(page, workflow);
    });
  }
});

async function setupDocsMocks(page: Page): Promise<void> {
  await page.route("**/api/config", async (route) => {
    await fulfillJson(route, {
      configStoreApiUrl: "http://localhost:9001",
      dhcpUrl: "http://localhost:9004",
      nautobotUrl: "https://nautobot.nvcm.air",
      renderServiceUrl: "http://localhost:9002",
      workflowApiUrl: "http://localhost:9000",
      ztpUrl: "http://localhost:9003",
    });
  });

  await page.route("**/v1/parameter/location*", async (route) => {
    await fulfillJson(route, DOC_SITES);
  });

  await page.route(/.*\/v1\/parameter\/role/, async (route) => {
    await fulfillJson(route, DOC_ROLES);
  });

  await page.route(/.*\/v1\/parameter\/status/, async (route) => {
    await fulfillJson(route, DOC_STATUSES);
  });

  await page.route(/.*\/v1\/parameter\/tenant/, async (route) => {
    await fulfillJson(route, DOC_TENANTS);
  });

  await page.route(/^.*\/v1\/parameter\/device(\?.*)?$/, async (route) => {
    const url = new URL(route.request().url());
    await fulfillJson(route, filterDevices(url));
  });

  await page.route("**/v1/parameter/device/*/password_users", async (route) => {
    await fulfillJson(route, [
      { description: "Cumulus Linux demo user", name: "cumulus" },
      { description: "Administrator demo user", name: "admin" },
    ]);
  });

  await page.route("**/v1/parameter/diagnostics/commands*", async (route) => {
    await fulfillJson(route, [
      { description: "Collect interface state", name: "show interface" },
      { description: "Collect LLDP neighbors", name: "show lldp neighbor" },
    ]);
  });
}

function filterDevices(url: URL): Device[] {
  const site = url.searchParams.get("site") || AIR_SITE;
  let devices = [...(DOC_DEVICES_BY_SITE[site] || [])];

  for (const key of new Set(url.searchParams.keys())) {
    if (key === "site") {
      continue;
    }
    const values = url.searchParams.getAll(key);
    devices = devices.filter((device) =>
      values.some((value) => fieldMatches(device, key, value))
    );
  }

  return devices;
}

function fieldMatches(device: Device, key: string, value: string): boolean {
  const fieldValue = device[key as keyof Device];
  if (!fieldValue) {
    return false;
  }
  return fieldValue.toLowerCase().includes(value.toLowerCase());
}

async function fulfillJson(route: Route, json: unknown): Promise<void> {
  await route.fulfill({
    json,
    status: 200,
  });
}

async function settleFonts(page: Page): Promise<void> {
  await page.evaluate(async () => {
    await document.fonts.ready;
  });
}

async function screenshotWorkflowCard(
  page: Page,
  workflow: WorkflowScreenshot
): Promise<void> {
  const outputPath = path.join(SCREENSHOT_DIR, workflow.fileName);

  for (let attempt = 1; attempt <= 3; attempt += 1) {
    const heading = page.getByRole("heading", { name: workflow.title });
    const card = heading.locator(CARD_SELECTOR);
    await expect(card).toBeVisible();
    await page.waitForTimeout(250);

    try {
      await card.screenshot({ path: outputPath });
      return;
    } catch (error) {
      if (attempt === 3) {
        throw error;
      }
      await page.waitForTimeout(500);
    }
  }
}

function routeWithQuery(
  routePath: string,
  query?: Record<string, QueryValue>
): string {
  if (!query) {
    return routePath;
  }

  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    const values = Array.isArray(value) ? value : [value];
    for (const item of values) {
      params.append(key, item);
    }
  }

  return `${routePath}?${params.toString()}`;
}
