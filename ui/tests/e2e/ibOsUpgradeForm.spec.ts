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
  formPath: "/workflows/infinibandmlnxosupgradeworkflow/form",
  formTitle: "New InfiniBand MLNX-OS Upgrade Workflow",
  deviceFilter: (devices) =>
    devices.find((d) => d.platform === "MLNX-OS") || devices[0],
  forbiddenFilter: (devices) =>
    devices.find(
      (d) =>
        d.platform === "MLNX-OS" &&
        Object.values(FORBIDDEN_DEVICE_IDS).includes(d.id)
    ) || devices[0],
});

// Add additional tests specific to the IB OS Upgrade Workflow
test.describe("IB OS Upgrade Form - Additional Tests", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/workflows/infinibandmlnxosupgradeworkflow/form");
  });

  test("only shows MLNX-OS devices in the device dropdown", async ({
    page,
  }) => {
    // Select a site that has MLNX-OS devices
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New InfiniBand MLNX-OS Upgrade Workflow" })
      .click();

    // Open the device dropdown
    await page.getByRole("button", { name: "Device" }).click();

    // Get all device options in the dropdown
    const deviceOptions = page.getByRole("dialog").getByRole("option");

    // Check that each device in the dropdown has platform=MLNX-OS
    const mlnxDevices = DEVICES_LIST[SITES_LIST.pdx01].filter(
      (device) => device.platform === "MLNX-OS"
    );

    // Verify the correct number of devices is shown
    await expect(deviceOptions).toHaveCount(mlnxDevices.length);

    // Verify that only MLNX-OS devices are listed
    for (const mlnxDevice of mlnxDevices) {
      await expect(
        page.getByRole("dialog").getByText(mlnxDevice.name)
      ).toBeVisible();
    }

    // Close the dropdown
    await page
      .getByRole("heading", { name: "New InfiniBand MLNX-OS Upgrade Workflow" })
      .click();
  });

  test("submits correct data to the API", async ({ page }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request
        .url()
        .includes("/v1/workflow/ngc/infiniband_mlnx_os_upgrade");
    });

    // Find a site with MLNX-OS devices
    const site = SITES_LIST.pdx01;
    const mlnxDevices = DEVICES_LIST[site].filter(
      (device) => device.platform === "MLNX-OS"
    );
    const mlnxDevice = mlnxDevices[0];

    // Fill form with specific test values
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(site).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New InfiniBand MLNX-OS Upgrade Workflow" })
      .click();

    await page.getByRole("button", { name: "Device" }).click();
    await page.getByRole("dialog").getByText(mlnxDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New InfiniBand MLNX-OS Upgrade Workflow" })
      .click();

    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data
    expect(requestData).toEqual({
      device_id: mlnxDevice.id,
    });

    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("loads form with URL parameters and performs manual changes", async ({
    page,
  }) => {
    // Find sites with MLNX-OS devices
    const initialSite = SITES_LIST.pdx01;
    const newSite = SITES_LIST.rno1;

    const initialMlnxDevices = DEVICES_LIST[initialSite].filter(
      (device) => device.platform === "MLNX-OS"
    );
    const newMlnxDevices = DEVICES_LIST[newSite].filter(
      (device) => device.platform === "MLNX-OS"
    );

    const initialDevice = initialMlnxDevices[0];
    const newDevice = newMlnxDevices[0];

    // Navigate to the form with URL parameters
    await page.goto(
      `/workflows/infinibandmlnxosupgradeworkflow/form?site=${initialSite}&device-id=${initialDevice.id}`
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
      .getByRole("heading", { name: "New InfiniBand MLNX-OS Upgrade Workflow" })
      .click();

    // Select a new device from the new site
    await page.getByRole("button", { name: "Select a Device" }).click();
    await page.getByRole("dialog").getByText(newDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New InfiniBand MLNX-OS Upgrade Workflow" })
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
      return request
        .url()
        .includes("/v1/workflow/ngc/infiniband_mlnx_os_upgrade");
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

    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("submits form directly from URL parameters without changes", async ({
    page,
  }) => {
    // Find a site with MLNX-OS devices
    const site = SITES_LIST.pdx01;
    const mlnxDevices = DEVICES_LIST[site].filter(
      (device) => device.platform === "MLNX-OS"
    );
    const mlnxDevice = mlnxDevices[0];

    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request
        .url()
        .includes("/v1/workflow/ngc/infiniband_mlnx_os_upgrade");
    });

    // Navigate to the form with URL parameters
    await page.goto(
      `/workflows/infinibandmlnxosupgradeworkflow/form?site=${site}&device-id=${mlnxDevice.id}`
    );

    // Verify the form is pre-populated with URL parameter values
    await expect(page.getByRole("button", { name: site })).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
    await expect(
      page.getByRole("button", { name: mlnxDevice.name })
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
      device_id: mlnxDevice.id,
    });

    // Wait for navigation to confirm submission completed
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("displays validation errors for empty submission", async ({ page }) => {
    // Click submit without filling any fields
    await page.getByRole("button", { name: "Submit" }).click();

    // Check for validation errors
    await expect(page.getByText("Site is required")).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
    await expect(page.getByText("Device is required")).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
  });

  test("clears device field when site is changed", async ({ page }) => {
    // Initial site selection
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New InfiniBand MLNX-OS Upgrade Workflow" })
      .click();

    // Select device
    const mlnxDevices = DEVICES_LIST[SITES_LIST.pdx01].filter(
      (device) => device.platform === "MLNX-OS"
    );
    await page.getByRole("button", { name: "Device" }).click();
    await page.getByRole("dialog").getByText(mlnxDevices[0].name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New InfiniBand MLNX-OS Upgrade Workflow" })
      .click();

    // Verify device is selected
    await expect(
      page.getByRole("button", { name: mlnxDevices[0].name })
    ).toBeVisible();

    // Change site
    await page.getByRole("button", { name: SITES_LIST.pdx01 }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.rno1).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New InfiniBand MLNX-OS Upgrade Workflow" })
      .click();

    // Verify device field has been cleared
    await expect(
      page.getByRole("button", { name: "Select a Device" })
    ).toBeVisible();
  });

  test("disables form during submission", async ({ page }) => {
    // Find a site with MLNX-OS devices
    const site = SITES_LIST.pdx01;
    const mlnxDevices = DEVICES_LIST[site].filter(
      (device) => device.platform === "MLNX-OS"
    );
    const mlnxDevice = mlnxDevices[0];

    // Fill form with specific test values
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(site).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New InfiniBand MLNX-OS Upgrade Workflow" })
      .click();

    await page.getByRole("button", { name: "Device" }).click();
    await page.getByRole("dialog").getByText(mlnxDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New InfiniBand MLNX-OS Upgrade Workflow" })
      .click();

    await page.getByRole("button", { name: "Submit" }).click();

    // Verify fields are disabled during submission
    await expect(page.getByRole("button", { name: site })).toBeDisabled();
    await expect(
      page.getByRole("button", { name: mlnxDevice.name })
    ).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Submitting..." })
    ).toBeDisabled();
  });

  test("displays forbidden error notification when submitting with forbidden values", async ({
    page,
  }) => {
    // Fill form with forbidden site
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(FORBIDDEN_SITE_ID).click();

    // Find the forbidden MLNX-OS device
    const forbiddenDevice = DEVICES_LIST[FORBIDDEN_SITE_ID].filter(
      (device) => device.platform === "MLNX-OS"
    )[0];

    // Select the forbidden device
    await page.getByRole("button", { name: "Device" }).click();
    await page.getByRole("dialog").getByText(forbiddenDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "New InfiniBand MLNX-OS Upgrade Workflow" })
      .click();

    await page.getByRole("button", { name: "Submit" }).click();

    // Check for the error notification
    const errorTitle = page.locator("div.text-sm.font-semibold", {
      hasText: "Workflow Failed",
    });
    const errorMessage = page.locator("div.text-sm.opacity-90", {
      hasText: "Forbidden: You do not have permission to run this workflow",
    });

    await expect(errorTitle).toBeVisible({ timeout: TEST_TIMEOUT });
    await expect(errorMessage).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("keeps valid site but clears invalid device from URL params", async ({
    page,
  }) => {
    // Navigate with valid site but invalid device parameters
    const validSite = SITES_LIST.pdx01;
    const invalidDevice = "nonexistent-device";
    await page.goto(
      `/workflows/infinibandmlnxosupgradeworkflow/form?site=${validSite}&device-id=${invalidDevice}`
    );

    // Allow time for validation logic and device data to load
    await page.waitForTimeout(1000);

    // Check that site field is populated but device field is empty
    await expect(page.getByRole("button", { name: validSite })).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Select a Device" })
    ).toBeVisible();

    // Verify device dropdown works properly after clearing invalid value
    await page.getByRole("button", { name: "Device" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();

    // Find the first MLNX-OS device for the site
    const mlnxDevices = DEVICES_LIST[validSite].filter(
      (device) => device.platform === "MLNX-OS"
    );

    await page.getByRole("dialog").getByText(mlnxDevices[0].name).click();

    // Verify the device was selected correctly
    await expect(
      page.getByRole("button", { name: mlnxDevices[0].name })
    ).toBeVisible();
  });

  test("handles URL parameters correctly and submits with those values", async ({
    page,
  }) => {
    // Find a site with MLNX-OS devices
    const site = SITES_LIST.pdx01;
    const mlnxDevices = DEVICES_LIST[site].filter(
      (device) => device.platform === "MLNX-OS"
    );
    const mlnxDevice = mlnxDevices[0];

    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request
        .url()
        .includes("/v1/workflow/ngc/infiniband_mlnx_os_upgrade");
    });

    // Navigate to the form with URL parameters
    await page.goto(
      `/workflows/infinibandmlnxosupgradeworkflow/form?site=${site}&device-id=${mlnxDevice.id}`
    );

    // Verify the form is pre-populated with URL parameter values
    await expect(page.getByRole("button", { name: site })).toBeVisible({
      timeout: TEST_TIMEOUT,
    });

    await expect(
      page.getByRole("button", { name: mlnxDevice.name })
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
      device_id: mlnxDevice.id,
    });

    // Wait for navigation to confirm submission completed
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });
});
