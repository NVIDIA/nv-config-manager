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
  formPath: "/workflows/infinibandgetunhealthyportsworkflow/form",
  formTitle: "New InfiniBand Get Unhealthy Ports Workflow",
  deviceFilter: (devices) =>
    devices.find((d) => d.platform === "UFM") || devices[0],
  forbiddenFilter: (devices) =>
    devices.find((d) => Object.values(FORBIDDEN_DEVICE_IDS).includes(d.id)) ||
    devices[0],
});

// Add additional tests specific to the New InfiniBand Get Unhealthy Ports Workflow
test.describe("IB Validation Form - Additional Tests", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/workflows/infinibandgetunhealthyportsworkflow/form");
  });

  test("only shows UFM devices in the device dropdown", async ({ page }) => {
    // Select a site that has UFM devices
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "New InfiniBand Get Unhealthy Ports Workflow",
      })
      .click();

    // Open the device dropdown
    await page.getByRole("button", { name: "Device" }).click();

    // Get all device options in the dropdown
    const deviceOptions = page.getByRole("dialog").getByRole("option");

    // Check that each device in the dropdown has platform=UFM
    const ufmDevices = DEVICES_LIST[SITES_LIST.pdx01].filter(
      (device) => device.platform === "UFM"
    );

    // Verify the correct number of devices is shown
    await expect(deviceOptions).toHaveCount(ufmDevices.length);

    // Verify that only UFM devices are listed
    for (const ufmDevice of ufmDevices) {
      await expect(
        page.getByRole("dialog").getByText(ufmDevice.name)
      ).toBeVisible();
    }

    // Close the dropdown
    await page
      .getByRole("heading", {
        name: "New InfiniBand Get Unhealthy Ports Workflow",
      })
      .click();
  });

  test("submits correct data to the API", async ({ page }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request
        .url()
        .includes("/v1/workflow/ngc/infiniband_get_unhealthy_ports");
    });

    // Find a site with UFM devices
    const site = SITES_LIST.pdx01;
    const ufmDevices = DEVICES_LIST[site].filter(
      (device) => device.platform === "UFM"
    );
    const ufmDevice = ufmDevices[0];

    // Fill form with specific test values
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(site).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "New InfiniBand Get Unhealthy Ports Workflow",
      })
      .click();

    await page.getByRole("button", { name: "Device" }).click();
    await page.getByRole("dialog").getByText(ufmDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "New InfiniBand Get Unhealthy Ports Workflow",
      })
      .click();

    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data
    expect(requestData).toEqual({
      device_id: ufmDevice.id,
    });

    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("loads form with URL parameters and performs manual changes", async ({
    page,
  }) => {
    // Find sites with UFM devices
    const initialSite = SITES_LIST.pdx01;
    const newSite = SITES_LIST.rno1;

    const initialUfmDevices = DEVICES_LIST[initialSite].filter(
      (device) => device.platform === "UFM"
    );
    const newUfmDevices = DEVICES_LIST[newSite].filter(
      (device) => device.platform === "UFM"
    );

    const initialDevice = initialUfmDevices[0];
    const newDevice = newUfmDevices[0];

    // Navigate to the form with URL parameters
    await page.goto(
      `/workflows/infinibandgetunhealthyportsworkflow/form?site=${initialSite}&device-id=${initialDevice.id}`
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
      .getByRole("heading", {
        name: "New InfiniBand Get Unhealthy Ports Workflow",
      })
      .click();

    // Select a new device from the new site
    await page.getByRole("button", { name: "Select a Device" }).click();
    await page.getByRole("dialog").getByText(newDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "New InfiniBand Get Unhealthy Ports Workflow",
      })
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
        .includes("/v1/workflow/ngc/infiniband_get_unhealthy_ports");
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
    // Find a site with UFM devices
    const site = SITES_LIST.pdx01;
    const ufmDevices = DEVICES_LIST[site].filter(
      (device) => device.platform === "UFM"
    );
    const ufmDevice = ufmDevices[0];

    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request
        .url()
        .includes("/v1/workflow/ngc/infiniband_get_unhealthy_ports");
    });

    // Navigate to the form with URL parameters
    await page.goto(
      `/workflows/infinibandgetunhealthyportsworkflow/form?site=${site}&device-id=${ufmDevice.id}`
    );

    // Verify the form is pre-populated with URL parameter values
    await expect(page.getByRole("button", { name: site })).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
    await expect(
      page.getByRole("button", { name: ufmDevice.name })
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
      device_id: ufmDevice.id,
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
      .getByRole("heading", {
        name: "New InfiniBand Get Unhealthy Ports Workflow",
      })
      .click();

    // Select device
    const ufmDevices = DEVICES_LIST[SITES_LIST.pdx01].filter(
      (device) => device.platform === "UFM"
    );
    await page.getByRole("button", { name: "Device" }).click();
    await page.getByRole("dialog").getByText(ufmDevices[0].name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "New InfiniBand Get Unhealthy Ports Workflow",
      })
      .click();

    // Verify device is selected
    await expect(
      page.getByRole("button", { name: ufmDevices[0].name })
    ).toBeVisible();

    // Change site
    await page.getByRole("button", { name: SITES_LIST.pdx01 }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.rno1).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "New InfiniBand Get Unhealthy Ports Workflow",
      })
      .click();

    // Verify device field has been cleared
    await expect(
      page.getByRole("button", { name: "Select a Device" })
    ).toBeVisible();
  });

  test("disables form during submission", async ({ page }) => {
    // Find a site with UFM devices
    const site = SITES_LIST.pdx01;
    const ufmDevices = DEVICES_LIST[site].filter(
      (device) => device.platform === "UFM"
    );
    const ufmDevice = ufmDevices[0];

    // Fill form with specific test values
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(site).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "New InfiniBand Get Unhealthy Ports Workflow",
      })
      .click();

    await page.getByRole("button", { name: "Device" }).click();
    await page.getByRole("dialog").getByText(ufmDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "New InfiniBand Get Unhealthy Ports Workflow",
      })
      .click();

    await page.getByRole("button", { name: "Submit" }).click();

    // Verify fields are disabled during submission
    await expect(page.getByRole("button", { name: site })).toBeDisabled();
    await expect(
      page.getByRole("button", { name: ufmDevice.name })
    ).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Submitting..." })
    ).toBeDisabled();
  });

  test("shows API validation details and allows resubmission", async ({ page }) => {
    let submissionCount = 0;
    await page.route(
      "**/v1/workflow/ngc/infiniband_get_unhealthy_ports",
      async (route) => {
        submissionCount += 1;
        await route.fulfill({
          status: 422,
          json: { detail: "Device identifier must be a valid UUID" },
        });
      }
    );

    const site = SITES_LIST.pdx01;
    const ufmDevice = DEVICES_LIST[site].find(
      (device) => device.platform === "UFM"
    );
    expect(ufmDevice).toBeDefined();

    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(site).click();
    await page.getByRole("button", { name: "Device" }).click();
    await page.getByRole("dialog").getByText(ufmDevice!.name).click();

    await page.getByRole("button", { name: "Submit" }).click();

    await expect(
      page.getByText(
        "Failed to create workflow: Error: Device identifier must be a valid UUID",
        { exact: true }
      )
    ).toBeVisible({ timeout: TEST_TIMEOUT });
    await expect(page.getByRole("button", { name: "Submit" })).toBeEnabled();

    await page.getByRole("button", { name: "Submit" }).click();
    await expect.poll(() => submissionCount).toBe(2);
  });

  test("displays forbidden error notification when submitting with forbidden values", async ({
    page,
  }) => {
    // Fill form with forbidden site
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(FORBIDDEN_SITE_ID).click();

    // Find the forbidden device
    const forbiddenDevice = DEVICES_LIST[FORBIDDEN_SITE_ID].filter(
      (device) => device.platform === "UFM"
    )[0];

    // Select the forbidden device
    await page.getByRole("button", { name: "Device" }).click();
    await page.getByRole("dialog").getByText(forbiddenDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "New InfiniBand Get Unhealthy Ports Workflow",
      })
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
