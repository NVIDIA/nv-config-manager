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
import { expect } from "@playwright/test";
import { SITES_LIST, DEVICES_LIST, FORBIDDEN_SITE_ID } from "@/mocks/data";
import { test, TEST_TIMEOUT, WORKFLOW_DETAILS_TIMEOUT } from "./utils";

// Define comprehensive configuration interface
interface WorkflowTestConfig {
  formPath: string;
  formTitle: string;
  deviceFilter?: (devices: any[]) => any;
  forbiddenFilter?: (devices: any[]) => any;
  defaultPlatform?: string;
}

export const runWorkflowFormTests = (config: WorkflowTestConfig) => {
  const {
    formPath,
    formTitle,
    deviceFilter = (devices) => devices[0],
    forbiddenFilter = (devices) => {
      const platform =
        config.defaultPlatform ||
        deviceFilter(DEVICES_LIST.PDX01)?.platform ||
        "UFM";

      return devices.find((d) => d.platform === platform) || devices[0];
    },
  } = config;

  test.describe(`${formTitle} Form`, () => {
    test.beforeEach(async ({ page }) => {
      await page.goto(formPath);
    });

    test(`renders ${formTitle} with correct title`, async ({ page }) => {
      const title = await page.getByRole("heading", {
        name: formTitle,
      });
      await expect(title).toBeVisible({ timeout: TEST_TIMEOUT });
    });

    test(`displays validation errors for empty ${formTitle} submission`, async ({
      page,
    }) => {
      await page.getByRole("button", { name: "Submit" }).click();
      await expect(page.getByText("Site is required")).toBeVisible({
        timeout: TEST_TIMEOUT,
      });
      await expect(page.getByText("Device is required")).toBeVisible({
        timeout: TEST_TIMEOUT,
      });
    });

    test(`successfully submits ${formTitle} with valid data and verifies API request`, async ({
      page,
    }) => {
      const site = SITES_LIST.pdx01 as keyof typeof DEVICES_LIST;
      const filteredDevice = deviceFilter(DEVICES_LIST[site]);
      const device = filteredDevice.name;

      await page.getByRole("button", { name: "Site" }).click();
      await page.getByRole("dialog").getByText(site).click();
      await page.getByRole("button", { name: "Device" }).click();
      await page.getByRole("dialog").getByText(device).click();

      await page.getByRole("button", { name: "Submit" }).click();

      await page.waitForURL("**/workflows/**");
      await expect(
        page.getByRole("heading", { name: "Workflow Details" })
      ).toBeVisible({ timeout: WORKFLOW_DETAILS_TIMEOUT });
    });

    test(`${formTitle} device field updates when site changes`, async ({
      page,
    }) => {
      const initialSite = SITES_LIST.pdx01 as keyof typeof DEVICES_LIST;
      const filteredDevice = deviceFilter(DEVICES_LIST[initialSite]);
      const initialDevice = filteredDevice.name;
      const changedSite = SITES_LIST.rno1 as keyof typeof DEVICES_LIST;

      await page.getByRole("button", { name: "Site" }).click();
      await page.getByRole("dialog").getByText(initialSite).click();
      await page.getByRole("button", { name: "Device" }).click();
      await page.getByRole("dialog").getByText(initialDevice).click();

      await page
        .getByRole("button", {
          name: `${initialSite}. Open options`,
          exact: true,
        })
        .first()
        .click();
      await page.getByRole("dialog").getByText(changedSite).click();

      await expect(
        page.getByRole("button", { name: "Select a Device..." })
      ).toBeVisible({ timeout: TEST_TIMEOUT });
    });

    test(`${formTitle} clears device field when site is cleared`, async ({
      page,
    }) => {
      const initialSite = SITES_LIST.pdx01 as keyof typeof DEVICES_LIST;
      const filteredDevice = deviceFilter(DEVICES_LIST[initialSite]);
      const initialDevice = filteredDevice.name;

      // Fill form with initial site and device
      await page.getByRole("button", { name: "Site" }).click();
      await page.getByRole("dialog").getByText(initialSite).click();
      await page.getByRole("button", { name: "Device" }).click();
      await page.getByRole("dialog").getByText(initialDevice).click();

      // Verify selections are visible
      await expect(
        page.getByRole("button", {
          name: `${initialSite}. Open options`,
          exact: true,
        })
      ).toBeVisible();
      await expect(
        page.getByRole("button", {
          name: `${initialDevice}. Open options`,
          exact: true,
        })
      ).toBeVisible();

      // Find the X icon with the specific class inside the button's parent container
      await page
        .locator(".flex.items-center.self-stretch")
        .filter({ has: page.locator("svg.lucide.lucide-x.size-4") })
        .first()
        .click();

      // Verify device field is reset to default state
      await expect(
        page.getByRole("button", { name: "Select a Device..." })
      ).toBeVisible({ timeout: TEST_TIMEOUT });
    });

    test(`${formTitle} resets device field when switching between sites`, async ({
      page,
    }) => {
      // Start with first site selection
      const firstSite = SITES_LIST.pdx01 as keyof typeof DEVICES_LIST;
      const firstDevice = deviceFilter(DEVICES_LIST[firstSite]).name;

      await page.getByRole("button", { name: "Site" }).click();
      await page.getByRole("dialog").getByText(firstSite).click();
      await page.getByRole("button", { name: "Device" }).click();
      await page.getByRole("dialog").getByText(firstDevice).click();

      // Verify first site's selections are visible
      await expect(
        page.getByRole("button", {
          name: `${firstSite}. Open options`,
          exact: true,
        })
      ).toBeVisible();
      await expect(
        page.getByRole("button", {
          name: `${firstDevice}. Open options`,
          exact: true,
        })
      ).toBeVisible();

      // Switch to second site
      const secondSite = SITES_LIST.rno1 as keyof typeof DEVICES_LIST;
      await page
        .getByRole("button", {
          name: `${firstSite}. Open options`,
          exact: true,
        })
        .first()
        .click();
      await page.getByRole("dialog").getByText(secondSite).click();

      // Verify device field is reset
      await expect(
        page.getByRole("button", { name: "Select a Device..." })
      ).toBeVisible({ timeout: TEST_TIMEOUT });

      // Select device for second site
      const secondDevice = deviceFilter(DEVICES_LIST[secondSite]).name;
      await page.getByRole("button", { name: "Device" }).click();
      await page.getByRole("dialog").getByText(secondDevice).click();

      // Verify second site's selections are visible
      await expect(
        page.getByRole("button", {
          name: `${secondSite}. Open options`,
          exact: true,
        })
      ).toBeVisible();
      await expect(
        page.getByRole("button", {
          name: `${secondDevice}. Open options`,
          exact: true,
        })
      ).toBeVisible();

      // Switch back to first site
      await page
        .getByRole("button", {
          name: `${secondSite}. Open options`,
          exact: true,
        })
        .first()
        .click();
      await page.getByRole("dialog").getByText(firstSite).click();

      // Verify device field is reset again
      await expect(
        page.getByRole("button", { name: "Select a Device..." })
      ).toBeVisible({ timeout: TEST_TIMEOUT });
    });

    test(`${formTitle} handles URL parameters correctly and submits with those values`, async ({
      page,
    }) => {
      const site = SITES_LIST.pdx01 as keyof typeof DEVICES_LIST;
      const filteredDevice = deviceFilter(DEVICES_LIST[site]);
      const deviceId = filteredDevice.id;
      const deviceName = filteredDevice.name;

      await page.goto(`${formPath}?site=${site}&device-id=${deviceId}`);

      await expect(
        page.getByRole("button", { name: `${site}. Open options`, exact: true })
      ).toBeVisible({ timeout: TEST_TIMEOUT });
      await expect(
        page.getByRole("button", {
          name: `${deviceName}. Open options`,
          exact: true,
        })
      ).toBeVisible({ timeout: TEST_TIMEOUT });

      await page.getByRole("button", { name: "Submit" }).click();

      await page.waitForURL("**/workflows/**");
      await expect(
        page.getByRole("heading", { name: "Workflow Details" })
      ).toBeVisible({ timeout: WORKFLOW_DETAILS_TIMEOUT });
    });

    test(`disables ${formTitle} during submission`, async ({ page }) => {
      const site = SITES_LIST.pdx01 as keyof typeof DEVICES_LIST;
      const filteredDevice = deviceFilter(DEVICES_LIST[site]);
      const device = filteredDevice.name;

      await page.getByRole("button", { name: "Site" }).click();
      await page.getByRole("dialog").getByText(site).click();
      await page.getByRole("button", { name: "Device" }).click();
      await page.getByRole("dialog").getByText(device).click();

      await page.getByRole("button", { name: "Submit" }).click();

      await expect(
        page.getByRole("button", { name: `${site}. Open options`, exact: true })
      ).toBeDisabled();
      await expect(
        page.getByRole("button", {
          name: `${device}. Open options`,
          exact: true,
        })
      ).toBeDisabled();
      await expect(
        page.getByRole("button", { name: "Submitting..." })
      ).toBeDisabled();
    });
  });

  test.describe(`${formTitle} - Error Scenarios`, () => {
    test.beforeEach(async ({ page }) => {
      await page.goto(formPath);
    });

    test("displays forbidden error notification when submitting with forbidden values", async ({
      page,
    }) => {
      await page.getByRole("button", { name: "Site" }).click();
      await page.getByRole("dialog").getByText(FORBIDDEN_SITE_ID).click();

      const forbiddenDevice = forbiddenFilter(DEVICES_LIST[FORBIDDEN_SITE_ID]);

      await page.getByRole("button", { name: "Device" }).click();
      await page.getByRole("dialog").getByText(forbiddenDevice.name).click();

      await page.getByRole("button", { name: "Submit" }).click();

      // NOTE: While not ideal, firefox has a weird bug where the toast notification is not visible unless we force a viewport adjustment.
      const errorTitle = page.locator("div.text-sm.font-semibold", {
        hasText: "Workflow Failed",
      });
      const errorMessage = page.locator("div.text-sm.opacity-90", {
        hasText: "Forbidden: You do not have permission to run this workflow",
      });

      await expect(errorTitle).toBeVisible({ timeout: TEST_TIMEOUT });
      await expect(errorMessage).toBeVisible({ timeout: TEST_TIMEOUT });
      await expect(page.getByRole("button", { name: "Submit" })).toBeEnabled();
    });
  });
};
