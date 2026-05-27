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
import { test, TEST_TIMEOUT } from "./shared/utils";
import { runWorkflowFormTests } from "./shared/workflowFormTests";

// Run the standard workflow form tests
runWorkflowFormTests({
  formPath: "/workflows/backupworkflow/form",
  formTitle: "New Config Backup Workflow",
  defaultPlatform: "Arista EOS", // Assuming backup works primarily with Arista devices
});

// Add additional tests specific to the backup workflow
test.describe("Backup Config Form - Additional Tests", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/workflows/backupworkflow/form");
  });

  test("submits correct data to the API", async ({ page }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/backup");
    });

    // Fill form with specific test values
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();
    await page.getByRole("button", { name: "Device" }).click();
    await page
      .getByRole("dialog")
      .getByText(DEVICES_LIST[SITES_LIST.pdx01][0].name)
      .click();

    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data
    expect(requestData).toEqual({
      device_id: DEVICES_LIST[SITES_LIST.pdx01][0].id,
      intended_config_commit_id: "",
      trigger: "API",
      user: "",
      user_domain: "nvidia.com",
      workflow_id: "",
    });

    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("loads form with URL parameters and performs manual changes", async ({
    page,
  }) => {
    // Navigate to the form with URL parameters
    const siteName = SITES_LIST.pdx01;
    const deviceId = DEVICES_LIST[siteName][0].id;
    const deviceName = DEVICES_LIST[siteName][0].name;
    await page.goto(
      `/workflows/backupworkflow/form?site=${siteName}&device-id=${deviceId}`
    );

    // Verify the form is pre-populated with URL parameter values
    await expect(page.getByRole("button").getByText(siteName)).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
    await expect(page.getByRole("button").getByText(deviceName)).toBeVisible({
      timeout: TEST_TIMEOUT,
    });

    // Change the values manually
    const newSiteName = SITES_LIST.rno1;
    await page.getByRole("button").getByText(siteName, { exact: true }).click();
    await page.getByRole("dialog").getByText(newSiteName).click();

    // Select a new device from the new site
    const newDeviceName = DEVICES_LIST[newSiteName][0].name;
    await page.getByRole("button", { name: "Select a Device" }).click();
    await page.getByRole("dialog").getByText(newDeviceName).click();

    // Verify the form is updated with the new values
    await expect(
      page.getByRole("button").getByText(newSiteName, { exact: true })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
    await expect(
      page.getByRole("button").getByText(newDeviceName, { exact: true })
    ).toBeVisible({ timeout: TEST_TIMEOUT });

    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/backup");
    });

    // Submit the form with the manually changed values
    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data contains the manually changed values, not the URL parameter values
    expect(requestData).toEqual({
      device_id: DEVICES_LIST[newSiteName][0].id,
      intended_config_commit_id: "",
      trigger: "API",
      user: "",
      user_domain: "nvidia.com",
      workflow_id: "",
    });

    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("submits form directly from URL parameters without changes", async ({
    page,
  }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/backup");
    });

    // Navigate to the form with URL parameters
    const siteName = SITES_LIST.pdx01;
    const deviceId = DEVICES_LIST[siteName][0].id;
    const deviceName = DEVICES_LIST[siteName][0].name;
    await page.goto(
      `/workflows/backupworkflow/form?site=${siteName}&device-id=${deviceId}`
    );

    // Verify the form is pre-populated with URL parameter values
    await expect(page.getByRole("button").getByText(siteName)).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
    await expect(page.getByRole("button").getByText(deviceName)).toBeVisible({
      timeout: TEST_TIMEOUT,
    });

    // Submit the form directly without making any changes
    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data contains the URL parameter values
    expect(requestData).toEqual({
      device_id: deviceId,
      intended_config_commit_id: "",
      trigger: "API",
      user: "",
      user_domain: "nvidia.com",
      workflow_id: "",
    });

    // Wait for navigation to confirm submission completed
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("displays forbidden error notification when submitting with forbidden values", async ({
    page,
  }) => {
    // Use the Arista EOS specific forbidden device
    const forbiddenDevice = DEVICES_LIST[FORBIDDEN_SITE_ID].find(
      (device) => device.id === FORBIDDEN_DEVICE_IDS.ARISTA
    );

    // Fill form with forbidden site and device
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(FORBIDDEN_SITE_ID).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New Config Backup Workflow" })
      .click();

    await page.getByRole("button", { name: "Device" }).click();
    await page
      .getByRole("dialog")
      .getByText(forbiddenDevice?.name || "")
      .click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New Config Backup Workflow" })
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
});
