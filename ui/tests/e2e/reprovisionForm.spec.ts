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
import {
  SITES_LIST,
  DEVICES_LIST,
  FORBIDDEN_SITE_ID,
  FORBIDDEN_DEVICE_IDS,
} from "@/mocks/data";
import { test, TEST_TIMEOUT, WORKFLOW_DETAILS_TIMEOUT } from "./shared/utils";
import { runWorkflowFormTests } from "./shared/workflowFormTests";

// Run the standard workflow form tests with a device filter for Cumulus Linux devices
runWorkflowFormTests({
  formPath: "/workflows/reprovisionworkflow/form",
  formTitle: "New Reprovision Workflow",
  deviceFilter: (devices) =>
    devices.find((d) => d.platform === "Cumulus Linux") || devices[0],
  defaultPlatform: "Cumulus Linux",
});

// Add additional tests specific to the reprovision workflow
test.describe("New Reprovision Workflow Form - Additional Tests", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/workflows/reprovisionworkflow/form");
  });

  test("shows a destructive workflow warning", async ({ page }) => {
    await expect(
      page.getByRole("alert").filter({
        hasText: "This workflow is destructive",
      })
    ).toHaveText(
      "This workflow is destructive. It will replace all existing configuration on the device with the intended configuration."
    );
  });

  test("only shows Cumulus Linux devices in the device dropdown", async ({
    page,
  }) => {
    // Select a site that has Cumulus Linux devices
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New Reprovision Workflow" })
      .click();

    // Open the device dropdown
    await page.getByRole("button", { name: "Device" }).click();

    // Get all device options in the dropdown
    const deviceOptions = page.getByRole("dialog").getByRole("option");

    // Check that each device in the dropdown has platform=Cumulus Linux
    const cumulusDevices = DEVICES_LIST[SITES_LIST.pdx01].filter(
      (device) => device.platform === "Cumulus Linux"
    );

    // Verify the correct number of devices is shown
    await expect(deviceOptions).toHaveCount(cumulusDevices.length);

    // Verify that only Cumulus Linux devices are listed
    for (const cumulusDevice of cumulusDevices) {
      await expect(
        page.getByRole("dialog").getByText(cumulusDevice.name)
      ).toBeVisible();
    }

    // Close the dropdown
    await page
      .getByRole("heading", { name: "New Reprovision Workflow" })
      .click();
  });

  test("submits correct data to the API", async ({ page }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/reprovision");
    });

    // Find a site with Cumulus Linux devices
    const site = SITES_LIST.pdx01;
    const cumulusDevices = DEVICES_LIST[site].filter(
      (device) => device.platform === "Cumulus Linux"
    );
    const cumulusDevice = cumulusDevices[0];

    // Fill form with specific test values
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(site).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New Reprovision Workflow" })
      .click();

    await page.getByRole("button", { name: "Device" }).click();
    await page.getByRole("dialog").getByText(cumulusDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New Reprovision Workflow" })
      .click();

    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data
    expect(requestData).toEqual({
      device_id: cumulusDevice.id,
    });

    await page.waitForURL("**/workflows/**");
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: WORKFLOW_DETAILS_TIMEOUT });
  });

  test("loads form with URL parameters and performs manual changes", async ({
    page,
  }) => {
    // Find sites with Cumulus Linux devices
    const initialSite = SITES_LIST.pdx01;
    const newSite = SITES_LIST.rno1;

    const initialCumulusDevices = DEVICES_LIST[initialSite].filter(
      (device) => device.platform === "Cumulus Linux"
    );
    const newCumulusDevices = DEVICES_LIST[newSite].filter(
      (device) => device.platform === "Cumulus Linux"
    );

    const initialDevice = initialCumulusDevices[0];
    const newDevice = newCumulusDevices[0];

    // Navigate to the form with URL parameters
    await page.goto(
      `/workflows/reprovisionworkflow/form?site=${initialSite}&device-id=${initialDevice.id}`
    );

    // Verify the form is pre-populated with URL parameter values
    await expect(page.getByRole("button", { name: initialSite })).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
    await expect(
      page.getByRole("button", { name: initialDevice.name })
    ).toBeVisible({
      timeout: TEST_TIMEOUT,
    });

    // Change the values manually
    await page.getByRole("button", { name: initialSite }).click();
    await page.getByRole("dialog").getByText(newSite).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New Reprovision Workflow" })
      .click();

    // Select a new device from the new site
    await page.getByRole("button", { name: "Select a Device" }).click();
    await page.getByRole("dialog").getByText(newDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New Reprovision Workflow" })
      .click();

    // Verify the form is updated with the new values
    await expect(page.getByRole("button", { name: newSite })).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
    await expect(
      page.getByRole("button", { name: newDevice.name })
    ).toBeVisible({ timeout: TEST_TIMEOUT });

    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/reprovision");
    });

    // Submit the form with the manually changed values
    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data contains the manually changed values, not the URL parameter values
    expect(requestData).toEqual({
      device_id: newDevice.id,
    });

    await page.waitForURL("**/workflows/**");
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: WORKFLOW_DETAILS_TIMEOUT });
  });

  test("submits form directly from URL parameters without changes", async ({
    page,
  }) => {
    // Find a site with Cumulus Linux devices
    const site = SITES_LIST.pdx01;
    const cumulusDevices = DEVICES_LIST[site].filter(
      (device) => device.platform === "Cumulus Linux"
    );
    const cumulusDevice = cumulusDevices[0];

    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/reprovision");
    });

    // Navigate to the form with URL parameters
    await page.goto(
      `/workflows/reprovisionworkflow/form?site=${site}&device-id=${cumulusDevice.id}`
    );

    // Verify the form is pre-populated with URL parameter values
    await expect(page.getByRole("button", { name: site })).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
    await expect(
      page.getByRole("button", { name: cumulusDevice.name })
    ).toBeVisible({
      timeout: TEST_TIMEOUT,
    });

    // Submit the form directly without making any changes
    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data contains the URL parameter values
    expect(requestData).toEqual({
      device_id: cumulusDevice.id,
    });

    await page.waitForURL("**/workflows/**");
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: WORKFLOW_DETAILS_TIMEOUT });
  });

  test("displays forbidden error notification when submitting with forbidden values", async ({
    page,
  }) => {
    // Use the Cumulus Linux specific forbidden device ID
    const forbiddenCumulusDevice = DEVICES_LIST[FORBIDDEN_SITE_ID].find(
      (device) => device.id === FORBIDDEN_DEVICE_IDS.CUMULUS
    );

    // Fill form with forbidden site and device
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(FORBIDDEN_SITE_ID).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New Reprovision Workflow" })
      .click();

    await page.getByRole("button", { name: "Device" }).click();
    await page
      .getByRole("dialog")
      .getByText(forbiddenCumulusDevice?.name || "")
      .click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New Reprovision Workflow" })
      .click();

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
  });

  test("disables form during submission", async ({ page }) => {
    // Find a site with Cumulus Linux devices
    const site = SITES_LIST.pdx01;
    const cumulusDevices = DEVICES_LIST[site].filter(
      (device) => device.platform === "Cumulus Linux"
    );
    const cumulusDevice = cumulusDevices[0];

    // Fill form with specific test values
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(site).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New Reprovision Workflow" })
      .click();

    await page.getByRole("button", { name: "Device" }).click();
    await page.getByRole("dialog").getByText(cumulusDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New Reprovision Workflow" })
      .click();

    await page.getByRole("button", { name: "Submit" }).click();

    // Verify fields are disabled during submission
    await expect(page.getByRole("button", { name: site })).toBeDisabled();
    await expect(
      page.getByRole("button", { name: cumulusDevice.name })
    ).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Submitting..." })
    ).toBeDisabled();
  });
});
