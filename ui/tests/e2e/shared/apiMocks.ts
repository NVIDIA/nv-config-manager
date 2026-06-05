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
import { Page } from "@playwright/test";
import { createGenericWorkflow } from "@/mocks/data/workflows/genericWorkflow";
import {
  SITES_LIST_API_RESPONSE,
  DEVICES_LIST,
  ALL_WORKFLOW_DATA,
  workflowsMockData,
  ROLES_LIST_API_RESPONSE,
  STATUS_LIST_API_RESPONSE,
  TENANT_LIST_API_RESPONSE,
  DEVICE_TYPES_LIST_API_RESPONSE,
  FORBIDDEN_WORKFLOW_ID,
  FORBIDDEN_SITE_ID,
  FORBIDDEN_DEVICE_IDS,
} from "@/mocks/data";

// Mock the runtime config endpoint
export async function mockRuntimeConfigEndpoint(page: Page) {
  await page.route('**/api/config', async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        workflowApiUrl: 'http://localhost:9000',
        configStoreApiUrl: 'http://localhost:9001',
        nautobotUrl: 'https://nautobot.example.com',
        renderServiceUrl: 'http://localhost:9002',
        ztpUrl: 'http://localhost:9003',
        dhcpUrl: 'http://localhost:9004',
      },
    });
  });
}

// Setup all API mocks
export async function setupApiMocks(page: Page) {
  // // Log all requests for debugging
  // page.on("request", (request) => {
  //   console.log(`>> ${request.method()} ${request.url()}`);
  // });

  // page.on("response", (response) => {
  //   console.log(`<< ${response.status()} ${response.url()}`);
  // });

  // Runtime config endpoint (must be first!)
  await mockRuntimeConfigEndpoint(page);
  await mockWhoamiEndpoint(page);

  // Workflow submission endpoints
  await mockSiteCableValidationEndpoint(page);
  await mockVpcCreationEndpoint(page);
  await mockVpcDeletionEndpoint(page);
  await mockBackupEndpoint(page);
  await mockDeployEndpoint(page);
  await mockPortLLDPInfoEndpoint(page);
  await mockConnectedHostMetadataEndpoint(page);
  await mockDeviceCableValidationEndpoint(page);
  await mockDevicePasswordRotationEndpoint(page);
  await mockSitePasswordRotationEndpoint(page);
  await mockIbGetUnhealthyPortsEndpoint(page);
  await mockIbOsUpgradeEndpoint(page);
  await mockInfinibandCableValidationEndpoint(page);
  await mockIbPkeyCreationEndpoint(page);
  await mockIbPkeyMemberAddEndpoint(page);
  await mockIbPkeyMemberDeleteEndpoint(page);
  await mockIbPkeyMemberUpdateEndpoint(page);
  await mockReprovisionEndpoint(page);
  await mockSwitchOsUpgradeEndpoint(page);
  await mockCumulusHardwareValidationEndpoint(page);
  await mockMultiDeployEndpoint(page);

  // Data fetching endpoints
  await mockSitesEndpoint(page);
  await mockRolesEndpoint(page);
  await mockStatusEndpoint(page);
  await mockTenantsEndpoint(page);
  await mockDeviceTypesEndpoint(page);
  await mockDevicesEndpoint(page);
  await mockPasswordUsersEndpoint(page);

  // Workflow listing endpoints
  await mockWorkflowTypesEndpoint(page);
  await mockWorkflowMetadataEndpoint(page);
  await mockWorkflowsListEndpoint(page);
  await mockWorkflowDetailsEndpoint(page);

  // Config Store endpoints
  await mockConfigStoreSearchEndpoint(page);
  await mockConfigStoreDeleteEndpoint(page);
  await mockConfigStoreDeviceConfigsEndpoint(page);
  await mockConfigStoreConfigFileEndpoint(page);

  // Health check
  await mockHealthCheckEndpoint(page);
}

export async function mockWhoamiEndpoint(page: Page) {
  await page.route('**/whoami', async (route) => {
    await route.fulfill({
      status: 200,
      json: {
        user: 'joliao@nvidia.com',
        roles: ['nvcm-network'],
      },
    });
  });
}

export async function mockDevicePasswordRotationEndpoint(page: Page) {
  await page.route(`**/v1/workflow/ngc/device_password_rotation`, async (route) => {
    const request = route.request();
    const body = JSON.parse((await request.postData()) || "{}");

    if (!body.device_id || !body.selected_secret) {
      await route.fulfill({
        status: 400,
        json: { error: "Missing required fields: device_id and selected_secret" },
      });
      return;
    }

    // Check if device is forbidden
    if (Object.values(FORBIDDEN_DEVICE_IDS).includes(body.device_id)) {
      await route.fulfill({
        status: 403,
        json: {
          error: "Forbidden: You do not have permission to rotate passwords on this device",
        },
      });
      return;
    }

    // Simulate processing delay (reduced for faster tests)
    await delay(100);

    // Return success response
    await route.fulfill({
      status: 201,
      json: {
        id: `device-password-rotation-${Date.now()}`,
        href: `https://url-to-temporal.com/namespaces/default/workflows/device-password-rotation-${Date.now()}`,
      },
    });
  });
}

export async function mockSitePasswordRotationEndpoint(page: Page) {
  await page.route(`**/v1/workflow/ngc/site_password_rotation`, async (route) => {
    const request = route.request();
    const body = JSON.parse((await request.postData()) || "{}");

    if (!body.location || !body.selected_secret || !body.roles || !body.status || !body.tenant) {
      await route.fulfill({
        status: 400,
        json: { error: "Missing required fields" },
      });
      return;
    }

    // Check if site is forbidden
    if (body.location === FORBIDDEN_SITE_ID) {
      await route.fulfill({
        status: 403,
        json: {
          error: "Forbidden: You do not have permission to rotate passwords on this site",
        },
      });
      return;
    }

    // Simulate processing delay (reduced for faster tests)
    await delay(100);

    // Return success response
    await route.fulfill({
      status: 201,
      json: {
        id: `site-password-rotation-${Date.now()}`,
        href: `https://url-to-temporal.com/namespaces/default/workflows/site-password-rotation-${Date.now()}`,
      },
    });
  });
}

export async function mockCumulusHardwareValidationEndpoint(page: Page) {
  await page.route(
    `**/v1/workflow/ngc/cumulus_hardware_validation`,
    async (route) => {
      const request = route.request();
      const body = JSON.parse((await request.postData()) || "{}");

      if (body.site === FORBIDDEN_SITE_ID) {
        await route.fulfill({
          status: 403,
          json: {
            error: "Forbidden: You do not have permission to run this workflow",
          },
        });
        return;
      }

      await delay(100);

      await route.fulfill({
        status: 201,
        json: {
          id: body.site || "site-used-for-id",
          href: `https://url-to-temporal.com/namespaces/default/workflows/${
            body.site || "site-used-for-id"
          }`,
        },
      });
    }
  );
}

export async function mockMultiDeployEndpoint(page: Page) {
  await page.route(`**/v1/workflow/ngc/multi_deploy`, async (route) => {
    const request = route.request();
    const body = JSON.parse((await request.postData()) || "{}");

    // Check for forbidden location
    if (body.location === FORBIDDEN_SITE_ID) {
      await route.fulfill({
        status: 403,
        json: {
          error: "Forbidden: You do not have permission to run this workflow",
        },
      });
      return;
    }

    // Validate required fields
    if (!body.role) {
      await route.fulfill({
        status: 400,
        json: { error: "Role is required" },
      });
      return;
    }

    // Validate batch size
    if (
      body.max_batch_size &&
      (body.max_batch_size < 1 || body.max_batch_size > 100)
    ) {
      await route.fulfill({
        status: 400,
        json: { error: "Invalid batch size: must be between 1 and 100" },
      });
      return;
    }

    await delay(100);

    await route.fulfill({
      status: 201,
      json: {
        id: `multi-deploy-${body.location}`,
        href: `https://url-to-temporal.com/namespaces/default/workflows/multi-deploy-${body.location}`,
        submitted_data: body,
      },
    });
  });
}

// Workflow submission endpoints
export async function mockSiteCableValidationEndpoint(page: Page) {
  await page.route(
    `**/v1/workflow/ngc/site_cable_validation`,
    async (route) => {
      const request = route.request();
      const body = JSON.parse((await request.postData()) || "{}");

      if (body.site === FORBIDDEN_SITE_ID) {
        await route.fulfill({
          status: 403,
          json: {
            error: "Forbidden: You do not have permission to run this workflow",
          },
        });
        return;
      }

      await delay(100);

      await route.fulfill({
        status: 201,
        json: {
          id: body.site || "site-used-for-id",
          href: `https://url-to-temporal.com/namespaces/default/workflows/${
            body.site || "site-used-for-id"
          }`,
        },
      });
    }
  );
}

export async function mockVpcCreationEndpoint(page: Page) {
  await page.route(`**/v1/workflow/ngc/vpc_creation`, async (route) => {
    const request = route.request();
    const body = JSON.parse((await request.postData()) || "{}");

    if (body.site === FORBIDDEN_SITE_ID) {
      await route.fulfill({
        status: 403,
        json: {
          error: "Forbidden: You do not have permission to run this workflow",
        },
      });
      return;
    }

    if (!body.vpc_id || !body.site) {
      await route.fulfill({
        status: 400,
        json: { error: "Missing required fields" },
      });
      return;
    }

    if (body.rd_min >= body.rd_max) {
      await route.fulfill({
        status: 400,
        json: { error: "rd_min must be less than rd_max" },
      });
      return;
    }

    await delay(100);

    await route.fulfill({
      status: 201,
      json: {
        id: body.vpc_id,
        href: `https://url-to-temporal.com/namespaces/default/workflows/${body.vpc_id}`,
        submitted_data: body,
      },
    });
  });
}

export async function mockVpcDeletionEndpoint(page: Page) {
  await page.route(`**/v1/workflow/ngc/vpc_deletion`, async (route) => {
    const request = route.request();
    const body = JSON.parse((await request.postData()) || "{}");

    if (body.site === FORBIDDEN_SITE_ID) {
      await route.fulfill({
        status: 403,
        json: {
          error: "Forbidden: You do not have permission to run this workflow",
        },
      });
      return;
    }

    if (!body.vpc_id || !body.site) {
      await route.fulfill({
        status: 400,
        json: { error: "Missing required fields" },
      });
      return;
    }

    await delay(100);

    await route.fulfill({
      status: 200,
      json: {
        id: body.vpc_id,
        href: `https://url-to-temporal.com/namespaces/default/workflows/${body.vpc_id}`,
        submitted_data: body,
      },
    });
  });
}

export async function mockBackupEndpoint(page: Page) {
  await page.route(`**/v1/workflow/ngc/backup`, async (route) => {
    const request = route.request();
    const body = JSON.parse((await request.postData()) || "{}");

    if (
      body.site === FORBIDDEN_SITE_ID ||
      Object.values(FORBIDDEN_DEVICE_IDS).includes(body.device_id)
    ) {
      await route.fulfill({
        status: 403,
        json: {
          error: "Forbidden: You do not have permission to run this workflow",
        },
      });
      return;
    }

    if (!body.device_id) {
      await route.fulfill({
        status: 400,
        json: { error: "Missing required fields" },
      });
      return;
    }

    await delay(100);

    await route.fulfill({
      status: 201,
      json: {
        id: body.device_id,
        href: `https://url-to-temporal.com/namespaces/default/workflows/${body.device_id}`,
        submitted_data: body,
      },
    });
  });
}

export async function mockDeployEndpoint(page: Page) {
  await page.route(`**/v1/workflow/ngc/deploy`, async (route) => {
    const request = route.request();
    const body = JSON.parse((await request.postData()) || "{}");

    if (
      body.site === FORBIDDEN_SITE_ID ||
      Object.values(FORBIDDEN_DEVICE_IDS).includes(body.device_id)
    ) {
      await route.fulfill({
        status: 403,
        json: {
          error: "Forbidden: You do not have permission to run this workflow",
        },
      });
      return;
    }

    if (!body.device_id) {
      await route.fulfill({
        status: 400,
        json: { error: "Missing required fields" },
      });
      return;
    }

    await delay(100);

    await route.fulfill({
      status: 201,
      json: {
        id: body.device_id,
        href: `https://url-to-temporal.com/namespaces/default/workflows/${body.device_id}`,
        submitted_data: body,
      },
    });
  });
}

export async function mockPortLLDPInfoEndpoint(page: Page) {
  await page.route(`**/v1/workflow/ngc/port_lldp_info`, async (route) => {
    const request = route.request();
    const body = JSON.parse((await request.postData()) || "{}");

    if (
      body.site === FORBIDDEN_SITE_ID ||
      Object.values(FORBIDDEN_DEVICE_IDS).includes(body.device_id)
    ) {
      await route.fulfill({
        status: 403,
        json: {
          error: "Forbidden: You do not have permission to run this workflow",
        },
      });
      return;
    }

    await delay(100);

    await route.fulfill({
      status: 201,
      json: {
        id: body.device_id || "mac-address-used-for-id",
        href: `https://url-to-temporal.com/namespaces/default/workflows/${
          body.device_id || "mac-address-used-for-id"
        }`,
        submitted_data: body,
      },
    });
  });
}

export async function mockConnectedHostMetadataEndpoint(page: Page) {
  await page.route(
    `**/v1/workflow/ngc/connected_host_metadata`,
    async (route) => {
      const request = route.request();
      const body = JSON.parse((await request.postData()) || "{}");

      if (
        body.site === FORBIDDEN_SITE_ID ||
        Object.values(FORBIDDEN_DEVICE_IDS).includes(body.device_id)
      ) {
        await route.fulfill({
          status: 403,
          json: {
            error: "Forbidden: You do not have permission to run this workflow",
          },
        });
        return;
      }

      await delay(100);

      await route.fulfill({
        status: 201,
        json: {
          id: body.device_id || "device-id-used-for-id",
          href: `https://url-to-temporal.com/namespaces/default/workflows/${
            body.device_id || "device-id-used-for-id"
          }`,
          submitted_data: body,
        },
      });
    }
  );
}

export async function mockDeviceCableValidationEndpoint(page: Page) {
  await page.route(
    `**/v1/workflow/ngc/device_cable_validation`,
    async (route) => {
      const request = route.request();
      const body = JSON.parse((await request.postData()) || "{}");

      if (
        body.site === FORBIDDEN_SITE_ID ||
        Object.values(FORBIDDEN_DEVICE_IDS).includes(body.device_id)
      ) {
        await route.fulfill({
          status: 403,
          json: {
            error: "Forbidden: You do not have permission to run this workflow",
          },
        });
        return;
      }

      if (!body.device_id) {
        await route.fulfill({
          status: 400,
          json: { error: "Missing required fields" },
        });
        return;
      }

      await delay(100);

      await route.fulfill({
        status: 201,
        json: {
          id: body.device_id,
          href: `https://url-to-temporal.com/namespaces/default/workflows/${body.device_id}`,
          submitted_data: body,
        },
      });
    }
  );
}

export async function mockIbGetUnhealthyPortsEndpoint(page: Page) {
  await page.route(
    `**/v1/workflow/ngc/infiniband_get_unhealthy_ports`,
    async (route) => {
      const request = route.request();
      const body = JSON.parse((await request.postData()) || "{}");

      if (
        body.site === FORBIDDEN_SITE_ID ||
        Object.values(FORBIDDEN_DEVICE_IDS).includes(body.device_id)
      ) {
        await route.fulfill({
          status: 403,
          json: {
            error: "Forbidden: You do not have permission to run this workflow",
          },
        });
        return;
      }

      if (!body.device_id) {
        await route.fulfill({
          status: 400,
          json: { error: "Missing required fields" },
        });
        return;
      }

      await delay(100);

      await route.fulfill({
        status: 201,
        json: {
          id: body.device_id,
          href: `https://url-to-temporal.com/namespaces/default/workflows/${body.device_id}`,
          submitted_data: body,
        },
      });
    }
  );
}

export async function mockIbOsUpgradeEndpoint(page: Page) {
  await page.route(
    `**/v1/workflow/ngc/infiniband_mlnx_os_upgrade`,
    async (route) => {
      const request = route.request();
      const body = JSON.parse((await request.postData()) || "{}");

      if (
        body.site === FORBIDDEN_SITE_ID ||
        Object.values(FORBIDDEN_DEVICE_IDS).includes(body.device_id)
      ) {
        await route.fulfill({
          status: 403,
          json: {
            error: "Forbidden: You do not have permission to run this workflow",
          },
        });
        return;
      }

      if (!body.device_id) {
        await route.fulfill({
          status: 400,
          json: { error: "Missing required fields" },
        });
        return;
      }

      await delay(100);

      const workflowId = `infiniband-mlnx-os-upgrade-${Date.now()}`;

      await route.fulfill({
        status: 201,
        json: {
          id: workflowId,
          href: `https://url-to-temporal.com/namespaces/default/workflows/${workflowId}`,
          submitted_data: body,
        },
      });
    }
  );
}

export async function mockInfinibandCableValidationEndpoint(page: Page) {
  await page.route(
    `**/v1/workflow/ngc/infiniband_cable_validation`,
    async (route) => {
      const request = route.request();
      const body = JSON.parse((await request.postData()) || "{}");

      if (
        !body.ufm_device_id ||
        !body.switch_device_ids ||
        body.switch_device_ids.length === 0
      ) {
        await route.fulfill({
          status: 400,
          json: { error: "Missing required fields" },
        });
        return;
      }

      // Check if UFM device is forbidden
      if (Object.values(FORBIDDEN_DEVICE_IDS).includes(body.ufm_device_id)) {
        await route.fulfill({
          status: 403,
          json: {
            error:
              "Forbidden: You do not have permission to use this UFM device",
          },
        });
        return;
      }

      // Check if any switch device is forbidden
      const hasForbiddenSwitches = body.switch_device_ids.some((id: string) =>
        Object.values(FORBIDDEN_DEVICE_IDS).includes(id)
      );

      if (hasForbiddenSwitches) {
        await route.fulfill({
          status: 403,
          json: {
            error:
              "Forbidden: You do not have permission to use one or more switch devices",
          },
        });
        return;
      }

      await delay(100);

      await route.fulfill({
        status: 201,
        json: {
          id: body.ufm_device_id,
          href: `https://url-to-temporal.com/namespaces/default/workflows/${body.ufm_device_id}`,
          submitted_data: body,
        },
      });
    }
  );
}

const IB_PKEY_PATTERN = /^0[xX][0-9a-fA-F]{1,4}$/;
const IB_GUID_PATTERN = /^0x[0-9a-fA-F]{16}$/;

function validateIbPkeyMembershipBody(body: {
  host?: string;
  pkey?: string;
  interfaces?: { device?: string; interface?: string }[];
  guids?: string[];
}): { status: number; json: { error: string } } | null {
  if (!body.host) {
    return { status: 400, json: { error: "Missing required field: host" } };
  }
  if (!body.pkey) {
    return { status: 400, json: { error: "Missing required field: pkey" } };
  }
  if (!IB_PKEY_PATTERN.test(body.pkey)) {
    return {
      status: 400,
      json: { error: "pkey must match /^0[xX][0-9a-fA-F]{1,4}$/" },
    };
  }
  const hasInterfaces = (body.interfaces?.length ?? 0) > 0;
  const hasGuids = (body.guids?.length ?? 0) > 0;
  if (hasInterfaces === hasGuids) {
    return {
      status: 400,
      json: { error: "Provide exactly one of 'interfaces' or 'guids'" },
    };
  }
  if (hasGuids && body.guids!.some((g) => !IB_GUID_PATTERN.test(g))) {
    return {
      status: 400,
      json: { error: "Each guid must match 0x + 16 hex digits" },
    };
  }
  return null;
}

async function registerIbPkeyMembershipRoute(
  page: Page,
  endpoint: string,
  workflowKind: string,
) {
  await page.route(`**${endpoint}`, async (route) => {
    const body = JSON.parse((await route.request().postData()) || "{}");
    const err = validateIbPkeyMembershipBody(body);
    if (err) {
      await route.fulfill({ status: err.status, json: err.json });
      return;
    }
    await delay(100);
    const workflowId = `${workflowKind}-${Date.now()}`;
    await route.fulfill({
      status: 201,
      json: {
        id: workflowId,
        href: `https://url-to-temporal.com/namespaces/default/workflows/${workflowId}`,
        submitted_data: body,
      },
    });
  });
}

export async function mockIbPkeyMemberAddEndpoint(page: Page) {
  await registerIbPkeyMembershipRoute(
    page,
    "/v1/workflow/ngc/ib_pkey_member_add",
    "ib-pkey-member-add",
  );
}

export async function mockIbPkeyMemberDeleteEndpoint(page: Page) {
  await registerIbPkeyMembershipRoute(
    page,
    "/v1/workflow/ngc/ib_pkey_member_delete",
    "ib-pkey-member-delete",
  );
}

export async function mockIbPkeyMemberUpdateEndpoint(page: Page) {
  await registerIbPkeyMembershipRoute(
    page,
    "/v1/workflow/ngc/ib_pkey_member_update",
    "ib-pkey-member-update",
  );
}

export async function mockIbPkeyCreationEndpoint(page: Page) {
  const PKEY_PATTERN = /^0[xX][0-9a-fA-F]{1,4}$/;

  await page.route(`**/v1/workflow/ngc/ib_pkey_creation`, async (route) => {
    const request = route.request();
    const body = JSON.parse((await request.postData()) || "{}");

    if (!body.host) {
      await route.fulfill({
        status: 400,
        json: { error: "Missing required field: host" },
      });
      return;
    }

    if (body.pkey && !PKEY_PATTERN.test(body.pkey)) {
      await route.fulfill({
        status: 400,
        json: { error: "pkey must match /^0[xX][0-9a-fA-F]{1,4}$/" },
      });
      return;
    }

    await delay(100);

    const workflowId = `ib-pkey-creation-${Date.now()}`;
    await route.fulfill({
      status: 201,
      json: {
        id: workflowId,
        href: `https://url-to-temporal.com/namespaces/default/workflows/${workflowId}`,
        submitted_data: body,
      },
    });
  });
}

export async function mockReprovisionEndpoint(page: Page) {
  await page.route(`**/v1/workflow/ngc/reprovision`, async (route) => {
    const request = route.request();
    const body = JSON.parse((await request.postData()) || "{}");

    if (
      body.site === FORBIDDEN_SITE_ID ||
      Object.values(FORBIDDEN_DEVICE_IDS).includes(body.device_id)
    ) {
      await route.fulfill({
        status: 403,
        json: {
          error: "Forbidden: You do not have permission to run this workflow",
        },
      });
      return;
    }

    if (!body.device_id) {
      await route.fulfill({
        status: 400,
        json: { error: "Missing required fields" },
      });
      return;
    }

    await delay(100);

    await route.fulfill({
      status: 201,
      json: {
        id: body.device_id,
        href: `https://url-to-temporal.com/namespaces/default/workflows/${body.device_id}`,
        submitted_data: body,
      },
    });
  });
}

export async function mockSwitchOsUpgradeEndpoint(page: Page) {
  await page.route(`**/v1/workflow/ngc/switch_os_upgrade`, async (route) => {
    const request = route.request();
    const body = JSON.parse((await request.postData()) || "{}");

    if (Object.values(FORBIDDEN_DEVICE_IDS).includes(body.device_id)) {
      await route.fulfill({
        status: 403,
        json: {
          error: "Forbidden: You do not have permission to run this workflow",
        },
      });
      return;
    }

    if (!body.device_id) {
      await route.fulfill({
        status: 400,
        json: { error: "Missing required fields" },
      });
      return;
    }

    await delay(100);

    await route.fulfill({
      status: 201,
      json: {
        id: body.device_id,
        href: `https://url-to-temporal.com/namespaces/default/workflows/${body.device_id}`,
        submitted_data: body,
      },
    });
  });
}

// Data fetching endpoints
export async function mockSitesEndpoint(page: Page) {
  await page.route(`**/v1/parameter/location*`, async (route) => {
    await route.fulfill({
      status: 200,
      json: SITES_LIST_API_RESPONSE,
    });
  });
}

export async function mockRolesEndpoint(page: Page) {
  await page.route(/.*\/v1\/parameter\/role/, async (route) => {
    await route.fulfill({
      status: 200,
      json: ROLES_LIST_API_RESPONSE,
    });
  });
}

export async function mockStatusEndpoint(page: Page) {
  await page.route(/.*\/v1\/parameter\/status/, async (route) => {
    await route.fulfill({
      status: 200,
      json: STATUS_LIST_API_RESPONSE,
    });
  });
}

export async function mockTenantsEndpoint(page: Page) {
  await page.route(/.*\/v1\/parameter\/tenant/, async (route) => {
    await route.fulfill({
      status: 200,
      json: TENANT_LIST_API_RESPONSE,
    });
  });
}

export async function mockDeviceTypesEndpoint(page: Page) {
  await page.route(`**/v1/parameter/devicetypeid`, async (route) => {
    await route.fulfill({
      status: 200,
      json: DEVICE_TYPES_LIST_API_RESPONSE,
    });
  });
}

export async function mockDevicesEndpoint(page: Page) {
  // Use a more specific route pattern with regex to avoid matching devicetypeid
  await page.route(/^.*\/v1\/parameter\/device(\?.*)?$/, async (route) => {
    const url = new URL(route.request().url());
    const site = url.searchParams.get("site") || "PDX01";

    // Get all devices for the requested site
    let devices = DEVICES_LIST[site as keyof typeof DEVICES_LIST] || [];

    // Process all filter parameters
    url.searchParams.forEach((value, key) => {
      if (key === "site") return; // Already handled above

      // Filter devices based on the parameter
      devices = devices.filter((device) => {
        // Handle multi-value parameters (arrays)
        if (url.searchParams.getAll(key).length > 1) {
          const allowedValues = url.searchParams.getAll(key);
          return allowedValues.includes(
            String(device[key as keyof typeof device])
          );
        }

        // Handle single value parameters
        // Case insensitive matching and partial matching for string values
        const deviceValue = device[key as keyof typeof device];
        if (typeof deviceValue === "string" && typeof value === "string") {
          return deviceValue.toLowerCase().includes(value.toLowerCase());
        }

        // Exact matching for non-string values
        return device[key as keyof typeof device] === value;
      });
    });

    await delay(100);

    await route.fulfill({
      status: 200,
      json: devices,
    });
  });
}

export async function mockPasswordUsersEndpoint(page: Page) {
  await page.route(`**/v1/parameter/device/*/password_users`, async (route) => {
    const url = route.request().url();
    const deviceId = url.match(/\/device\/([^\/]+)\/password_users/)?.[1];

    // Mock password users data for different devices
    const passwordUsers = [
      { name: "admin", description: "Administrator account" },
      { name: "cumulus", description: "Cumulus user account" },
    ];

    // Check if device is forbidden
    if (deviceId && Object.values(FORBIDDEN_DEVICE_IDS).includes(deviceId)) {
      await route.fulfill({
        status: 403,
        json: {
          error: "Forbidden: You do not have permission to access this device",
        },
      });
      return;
    }

    await route.fulfill({
      status: 200,
      json: passwordUsers,
    });
  });
}

// Workflow listing endpoints
export async function mockWorkflowTypesEndpoint(page: Page) {
  const workflowTypes = [
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
    "DiagnosticsWorkflow",
    "IBPortGuidDiscoveryWorkflow",
  ];

  await page.route(`**/v1/workflow/types`, async (route) => {
    await route.fulfill({
      status: 200,
      json: workflowTypes,
    });
  });
}

export async function mockWorkflowMetadataEndpoint(page: Page) {
  const workflowTypes = [
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
    DiagnosticsWorkflow: "Diagnostics",
    IBPortGuidDiscoveryWorkflow: "IB Port GUID Discovery",
  };
  const getWorkflowExecuteRoles = (workflowType: string) =>
    workflowType === "MultiDeployWorkflow" ? ["nvcm-admin"] : ["all"];
  const workflowMetadata = {
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

  await page.route(`**/v1/workflow/metadata`, async (route) => {
    await route.fulfill({
      status: 200,
      json: workflowMetadata,
    });
  });
}

export async function mockWorkflowsListEndpoint(page: Page) {
  await page.route(/.*\/v1\/workflow\/?(\?.*)?$/, async (route) => {
    const url = new URL(route.request().url());
    // Skip if this is a specific workflow ID request
    if (!url.pathname.endsWith("/v1/workflow") && !url.pathname.endsWith("/v1/workflow/")) {
      return route.fallback();
    }

    const workflowType = url.searchParams.get("workflow_type");
    const nextPageToken = url.searchParams.get("next_page_token");
    const limit = url.searchParams.get("limit");

    const pageSize = limit ? parseInt(limit) : 10;
    const page = nextPageToken ? parseInt(nextPageToken) : 0;

    const searchAttributeFilters = [
      ["device_id", "DeviceID"],
      ["device_name", "DeviceName"],
      ["device_platform", "DevicePlatform"],
      ["device_role", "DeviceRole"],
      ["site", "Site"],
      ["user", "User"],
    ];
    const workflows = (
      workflowType
        ? workflowsMockData[workflowType as keyof typeof workflowsMockData]
            ?.workflows || []
        : ALL_WORKFLOW_DATA.workflows
    ).filter((workflow) => {
      if (workflowType && workflow.workflow_type !== workflowType) {
        return false;
      }

      const status = url.searchParams.get("status");
      if (status && workflow.status !== status) {
        return false;
      }

      const startTimeFilter = Date.parse(url.searchParams.get("start_time") ?? "");
      const endTimeFilter = Date.parse(url.searchParams.get("end_time") ?? "");
      if (!Number.isNaN(startTimeFilter) || !Number.isNaN(endTimeFilter)) {
        const workflowStartTime = Date.parse(workflow.start_time);

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

        const searchAttributes = workflow.search_attributes as Record<
          string,
          Array<string | number | boolean> | undefined
        >;
        const attributeValue = String(searchAttributes[attribute]?.[0] ?? "").toLowerCase();
        return attributeValue.includes(value.toLowerCase());
      });
    });
    const paginatedWorkflows = workflows.slice(
      page * pageSize,
      (page + 1) * pageSize
    );
    const hasMore = (page + 1) * pageSize < workflows.length;

    await delay(100);

    await route.fulfill({
      status: 200,
      json: {
        workflows: paginatedWorkflows,
        next_page_token: hasMore ? (page + 1).toString() : null,
      },
    });
  });
}

export async function mockWorkflowDetailsEndpoint(page: Page) {
  // Use a regex pattern to match any workflow ID
  await page.route(/.*\/v1\/workflow\/([^/?]+)(\?.*)?$/, async (route) => {
    const url = new URL(route.request().url());
    if (
      url.pathname.endsWith("/v1/workflow") ||
      url.pathname.endsWith("/v1/workflow/") ||
      url.pathname.endsWith("/v1/workflow/types") ||
      url.pathname.endsWith("/v1/workflow/metadata")
    ) {
      return route.fallback();
    }
    const id = url.pathname.split("/").pop();

    console.log(`Workflow details requested for ID: ${id}`);

    if (id === FORBIDDEN_WORKFLOW_ID) {
      await route.fulfill({
        status: 403,
        json: {
          error:
            "Forbidden: You do not have permission to access this resource",
        },
      });
      return;
    }

    await delay(100);

    await route.fulfill({
      status: 200,
      json: createGenericWorkflow(id!),
    });
  });
}

// Health check
export async function mockHealthCheckEndpoint(page: Page) {
  await page.route(`**/healthcheck`, async (route) => {
    await route.fulfill({
      status: 200,
      json: { status: "ok" },
    });
  });
}

// ========================================
// Config Store API Mocks
// ========================================

// Mock device data for config store
const CONFIG_STORE_DEVICES = [
  {
    uuid: "device-uuid-1",
    name: "pdx01-spine-001",
    site: "PDX01",
    latest_update: new Date().toISOString(),
    latest_author: "admin",
    latest_message: "Updated routing config",
    active: true,
  },
  {
    uuid: "device-uuid-2",
    name: "pdx01-leaf-001",
    site: "PDX01",
    latest_update: new Date(Date.now() - 3600000).toISOString(),
    latest_author: "automation",
    latest_message: "BGP peer configuration",
    active: true,
  },
  {
    uuid: "device-uuid-3",
    name: "rno1-core-001",
    site: "RNO1",
    latest_update: new Date(Date.now() - 86400000).toISOString(),
    latest_author: "admin",
    latest_message: "Initial config backup",
    active: true,
  },
  {
    uuid: "device-uuid-4",
    name: "pdx01-decomm-001",
    site: "PDX01",
    latest_update: new Date(Date.now() - 604800000).toISOString(),
    latest_author: "admin",
    latest_message: "Last config before decommission",
    active: false,
  },
];

export async function mockConfigStoreSearchEndpoint(page: Page) {
  await page.route('**/v1/admin/devices/search*', async (route) => {
    const url = new URL(route.request().url());
    const query = url.searchParams.get('q') || '';
    const includeInactive = url.searchParams.get('include_inactive') === 'true';
    
    let results = CONFIG_STORE_DEVICES;

    if (!includeInactive) {
      results = results.filter(d => d.active);
    }
    
    if (query) {
      const lowerQuery = query.toLowerCase();
      results = results.filter(d => 
        d.name.toLowerCase().includes(lowerQuery) ||
        d.site.toLowerCase().includes(lowerQuery) ||
        d.uuid.toLowerCase().includes(lowerQuery)
      );
    }

    await delay(100);

    await route.fulfill({
      status: 200,
      json: results,
    });
  });
}

export async function mockConfigStoreDeleteEndpoint(page: Page) {
  await page.route(/\/v1\/admin\/devices\/[^/]+$/, async (route) => {
    if (route.request().method() !== 'DELETE') {
      return route.fallback();
    }

    const url = route.request().url();
    const uuidMatch = url.match(/\/v1\/admin\/devices\/([^?]+)/);
    const deviceUuid = uuidMatch?.[1] || '';

    await delay(100);

    await route.fulfill({
      status: 200,
      json: {
        device_uuid: deviceUuid,
        deleted_versions: 3,
        message: "Permanently deleted 3 config version(s)",
      },
    });
  });
}

export async function mockConfigStoreDeviceConfigsEndpoint(page: Page) {
  // Use regex to explicitly match /v1/config/device/:uuid (not config file path)
  await page.route(/\/v1\/config\/device\/[^/]+(\?|$)/, async (route) => {
    const url = route.request().url();
    const uuidMatch = url.match(/\/v1\/config\/device\/([^?]+)/);
    const deviceUuid = uuidMatch?.[1];

    const configs = [
      {
        id: `${deviceUuid}-config-1`,
        device_uuid: deviceUuid,
        filename: "running-config.txt",
        file_type: "intended",
        version: 3,
        content: "! Sample running config\nhostname pdx01-spine-001\n",
        content_hash: "abc123",
        author: "admin",
        commit_message: "Updated hostname",
        created_at: new Date().toISOString(),
        device: {
          name: "pdx01-spine-001",
          site: "PDX01",
          platform: "Cumulus Linux",
          role: "spine",
          rack: "A01",
          primary_ip4: "10.0.0.1",
          nautobot_url: "https://nautobot.example.com/devices/1",
          last_updated: new Date().toISOString(),
        },
      },
      {
        id: `${deviceUuid}-config-2`,
        device_uuid: deviceUuid,
        filename: "frr.conf",
        file_type: "intended",
        version: 2,
        content: "! FRR configuration\nrouter bgp 65001\n",
        content_hash: "def456",
        author: "automation",
        commit_message: "BGP config update",
        created_at: new Date().toISOString(),
      },
    ];

    await delay(100);

    await route.fulfill({
      status: 200,
      json: configs,
    });
  });
}

export async function mockConfigStoreConfigFileEndpoint(page: Page) {
  // Match config file requests: /v1/config/:uuid/:filename (exclude device list)
  await page.route(/\/v1\/config\/[^/]+\/[^/]+(\?|$)/, async (route) => {
    const url = route.request().url();

    // Skip device config list: /v1/config/device/uuid
    if (/\/v1\/config\/device\/[^/]+(\?|$)/.test(url)) {
      return route.continue();
    }

    const configFile = {
      id: "config-file-1",
      device_uuid: "device-uuid-1",
      filename: "running-config.txt",
      file_type: "intended",
      version: 3,
      content: "! Sample running config\nhostname pdx01-spine-001\ninterface eth0\n  ip address 10.0.0.1/24\n",
      content_hash: "abc123",
      author: "admin",
      commit_message: "Updated hostname",
      created_at: new Date().toISOString(),
      device: {
        name: "pdx01-spine-001",
        site: "PDX01",
        platform: "Cumulus Linux",
        role: "spine",
        rack: "A01",
        primary_ip4: "10.0.0.1",
        nautobot_url: "https://nautobot.example.com/devices/1",
        last_updated: new Date().toISOString(),
      },
    };

    await delay(100);

    await route.fulfill({
      status: 200,
      json: configFile,
    });
  });
}

// Helper function to simulate delay
async function delay(ms: number): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, ms));
}
