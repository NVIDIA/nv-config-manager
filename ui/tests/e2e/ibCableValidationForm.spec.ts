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

// Add additional tests specific to the Infiniband Cable Validation Workflow
test.describe("Infiniband Cable Validation Form", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/workflows/infinibandcablevalidationworkflow/form");
  });

  test("renders form with correct title", async ({ page }) => {
    const title = await page.getByRole("heading", {
      name: "Infiniband Cable Validation Workflow Form",
    });
    await expect(title).toBeVisible({ timeout: TEST_TIMEOUT });
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
    await expect(page.getByText("Device IDs is required")).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
  });

  test("successfully submits form with valid data and verifies API request", async ({
    page,
  }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request
        .url()
        .includes("/v1/workflow/ngc/infiniband_cable_validation");
    });

    // Find a site with UFM and MLNX-OS devices
    const site = SITES_LIST.pdx01;
    const ufmDevices = DEVICES_LIST[site].filter(
      (device) => device.platform === "UFM"
    );
    const mlnxDevices = DEVICES_LIST[site].filter(
      (device) => device.platform === "MLNX-OS"
    );
    const ufmDevice = ufmDevices[0];
    const mlnxDevice = mlnxDevices[0];

    // Fill form with specific test values
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(site).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    await page.getByRole("button", { name: "Select a Device..." }).click();
    await page.getByRole("dialog").getByText(ufmDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    // Select a MLNX-OS device for the deviceIds field
    await page.getByRole("button", { name: "Select a Device IDs..." }).click();
    await page.getByRole("dialog").getByText(mlnxDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data
    expect(requestData).toEqual({
      ufm_device_id: ufmDevice.id,
      switch_device_ids: [mlnxDevice.id],
    });

    // Wait for navigation to confirm submission completed
    await page.waitForURL("**/workflows/**");
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("device field updates when site changes", async ({ page }) => {
    // Find two different sites with devices
    const initialSite = SITES_LIST.pdx01;
    const changedSite = SITES_LIST.rno1;

    const initialUfmDevices = DEVICES_LIST[initialSite].filter(
      (device) => device.platform === "UFM"
    );
    const initialMlnxDevices = DEVICES_LIST[initialSite].filter(
      (device) => device.platform === "MLNX-OS"
    );

    const initialUfmDevice = initialUfmDevices[0];
    const initialMlnxDevice = initialMlnxDevices[0];

    // Fill form with initial site and selections
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(initialSite).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    await page.getByRole("button", { name: "Select a Device..." }).click();
    await page.getByRole("dialog").getByText(initialUfmDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    await page.getByRole("button", { name: "Select a Device IDs..." }).click();
    await page.getByRole("dialog").getByText(initialMlnxDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    // Verify initial selections are visible
    await expect(
      page.getByRole("button").getByText(initialUfmDevice.name)
    ).toBeVisible();

    // Use a more specific selector for the MLNX device
    // Look for the chip/tag that contains the selected device name
    await expect(
      page.locator(".flex-wrap").getByText(initialMlnxDevice.name)
    ).toBeVisible();

    // Change to a new site
    await page.getByRole("button").getByText(initialSite).click();
    await page.getByRole("dialog").getByText(changedSite).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    // Verify device and device IDs selections are cleared
    // The test name says "device field updates" but we actually test that both device and deviceIds are cleared
    await expect(
      page.getByRole("button").getByText("Select a Device...")
    ).toBeVisible();
    await expect(
      page.getByRole("button").getByText("Select a Device IDs...")
    ).toBeVisible();

    // Verify that the device IDs list no longer shows the previously selected value
    await expect(
      page.locator(".flex-wrap").getByText(initialMlnxDevice.name)
    ).not.toBeVisible();
  });

  test("handles URL parameters correctly and submits with those values", async ({
    page,
  }) => {
    // Find a site with UFM and MLNX-OS devices
    const site = SITES_LIST.pdx01;
    const ufmDevices = DEVICES_LIST[site].filter(
      (device) => device.platform === "UFM"
    );
    const mlnxDevices = DEVICES_LIST[site].filter(
      (device) => device.platform === "MLNX-OS"
    );
    const ufmDevice = ufmDevices[0];
    const mlnxDevice = mlnxDevices[0];

    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request
        .url()
        .includes("/v1/workflow/ngc/infiniband_cable_validation");
    });

    // Navigate to the form with URL parameters
    await page.goto(
      `/workflows/infinibandcablevalidationworkflow/form?site=${site}&device=${ufmDevice.id}&device-id=${mlnxDevice.id}`
    );

    // Verify the form is pre-populated with URL parameter values
    await expect(page.getByRole("button").getByText(site)).toBeVisible({
      timeout: TEST_TIMEOUT,
    });

    await expect(
      page.getByRole("button").getByText(ufmDevice.name)
    ).toBeVisible({
      timeout: TEST_TIMEOUT,
    });

    await expect(page.getByText(mlnxDevice.name)).toBeVisible({
      timeout: TEST_TIMEOUT,
    });

    // Submit the form directly without making any changes
    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data contains the URL parameter values
    expect(requestData).toEqual({
      ufm_device_id: ufmDevice.id,
      switch_device_ids: [mlnxDevice.id],
    });

    // Wait for navigation to confirm submission completed
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("handles invalid URL parameters by keeping form blank", async ({
    page,
  }) => {
    // Navigate to the form with invalid URL parameters
    const invalidSite = "NONEXISTENT_SITE";
    const invalidDeviceId = "invalid-device-id-123";
    const invalidDeviceIds = ["invalid-device-id-456"];

    await page.goto(
      `/workflows/infinibandcablevalidationworkflow/form?site=${invalidSite}&device=${invalidDeviceId}&device-id=${invalidDeviceIds.join(
        ","
      )}`
    );

    // Wait for the form to load and process URL params
    await expect(
      page.getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
    ).toBeVisible({ timeout: TEST_TIMEOUT });

    // Verify that the form fields remain blank/default after processing invalid URL parameters
    // Site field should be empty
    await expect(page.getByRole("button", { name: "Site" })).toBeVisible();

    // Device field should be empty/default
    await expect(
      page.getByRole("button", { name: "Select a Device..." })
    ).toBeVisible();

    // Device IDs field should be empty/default
    await expect(
      page.getByRole("button", { name: "Select a Device IDs..." })
    ).toBeVisible();

    // Verify that clicking submit shows validation errors
    await page.getByRole("button", { name: "Submit" }).click();

    // Check for validation errors
    await expect(page.getByText("Site is required")).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
    await expect(page.getByText("Device is required")).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
    await expect(page.getByText("Device IDs is required")).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
  });

  test("disables form during submission", async ({ page }) => {
    // Find a site with UFM and MLNX-OS devices
    const site = SITES_LIST.pdx01;
    const ufmDevices = DEVICES_LIST[site].filter(
      (device) => device.platform === "UFM"
    );
    const mlnxDevices = DEVICES_LIST[site].filter(
      (device) => device.platform === "MLNX-OS"
    );
    const ufmDevice = ufmDevices[0];
    const mlnxDevice = mlnxDevices[0];

    // Fill form with specific test values
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(site).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    await page.getByRole("button", { name: "Select a Device..." }).click();
    await page.getByRole("dialog").getByText(ufmDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    // Select a MLNX-OS device for the deviceIds field
    await page.getByRole("button", { name: "Select a Device IDs..." }).click();
    await page.getByRole("dialog").getByText(mlnxDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    await page.getByRole("button", { name: "Submit" }).click();

    // Check that form elements are disabled during submission
    await expect(
      page.getByRole("button", { name: site, exact: true })
    ).toBeDisabled();
    await expect(
      page.getByRole("button", { name: ufmDevice.name, exact: true })
    ).toBeDisabled();
    // Check for the "Submitting..." button
    await expect(
      page.getByRole("button", { name: "Submitting..." })
    ).toBeDisabled();
  });

  test("clearing site resets device and device IDs fields to default state", async ({
    page,
  }) => {
    // Find a site with devices
    const site = SITES_LIST.pdx01;
    const ufmDevices = DEVICES_LIST[site].filter(
      (device) => device.platform === "UFM"
    );
    const mlnxDevices = DEVICES_LIST[site].filter(
      (device) => device.platform === "MLNX-OS"
    );
    const ufmDevice = ufmDevices[0];
    const mlnxDevice = mlnxDevices[0];

    // Fill form with initial site and selections
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(site).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    await page.getByRole("button", { name: "Select a Device..." }).click();
    await page.getByRole("dialog").getByText(ufmDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    await page.getByRole("button", { name: "Select a Device IDs..." }).click();
    await page.getByRole("dialog").getByText(mlnxDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    // Verify initial selections are visible
    await expect(
      page.getByRole("button").getByText(ufmDevice.name)
    ).toBeVisible();

    // Use a more specific selector for the MLNX device
    await expect(
      page.locator(".flex-wrap").getByText(mlnxDevice.name)
    ).toBeVisible();

    // Find the X icon with the specific class inside the button's parent container
    await page
      .locator(".flex.items-center.self-stretch")
      .filter({ has: page.locator("svg.lucide.lucide-x.size-4") })
      .first()
      .click();

    // Verify device and device IDs dropdowns are reset to their default state
    await expect(
      page.getByRole("button").getByText("Select a Device...")
    ).toBeVisible();

    await expect(
      page.getByRole("button").getByText("Select a Device IDs...")
    ).toBeVisible();

    // Verify that the device IDs list no longer shows the previously selected value
    await expect(
      page.locator(".flex-wrap").getByText(mlnxDevice.name)
    ).not.toBeVisible();
  });
});

test.describe("Infiniband Cable Validation Form - Error Scenarios", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/workflows/infinibandcablevalidationworkflow/form");
  });

  test("displays forbidden error notification when submitting with forbidden values", async ({
    page,
  }) => {
    // Find a forbidden UFM device and an MLNX-OS device
    const forbiddenUfmDevice = DEVICES_LIST[FORBIDDEN_SITE_ID].find(
      (device) =>
        device.platform === "UFM" &&
        Object.values(FORBIDDEN_DEVICE_IDS).includes(device.id)
    );

    // Find a regular MLNX-OS device for the deviceIds field
    const mlnxDevice = DEVICES_LIST[FORBIDDEN_SITE_ID].find(
      (device) => device.platform === "MLNX-OS"
    );

    // Skip the test if we can't find the required devices
    if (!forbiddenUfmDevice || !mlnxDevice) {
      console.log(
        "Skipping test: Required test devices not found in mock data"
      );
      return;
    }

    // Select the forbidden site
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(FORBIDDEN_SITE_ID).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    // Select the forbidden UFM device
    await page.getByRole("button", { name: "Select a Device..." }).click();
    await page.getByRole("dialog").getByText(forbiddenUfmDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    // Select an MLNX-OS device
    await page.getByRole("button", { name: "Select a Device IDs..." }).click();
    await page.getByRole("dialog").getByText(mlnxDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    await page.getByRole("button", { name: "Submit" }).click();

    // Check for the error notification
    const errorTitle = page.locator("div.text-sm.font-semibold", {
      hasText: "Workflow Failed",
    });
    const errorMessage = page.locator("div.text-sm.opacity-90", {
      hasText: "Forbidden: You do not have permission",
    });

    await expect(errorTitle).toBeVisible({ timeout: TEST_TIMEOUT });
    await expect(errorMessage).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("forbidden MLNX-OS device for Device IDs shows error", async ({
    page,
  }) => {
    // Find a regular UFM device
    const site = FORBIDDEN_SITE_ID;
    const ufmDevice = DEVICES_LIST[site].find(
      (device) =>
        device.platform === "UFM" &&
        !Object.values(FORBIDDEN_DEVICE_IDS).includes(device.id)
    );

    // Find a forbidden MLNX-OS device
    const forbiddenMlnxDevice = DEVICES_LIST[site].find(
      (device) =>
        device.platform === "MLNX-OS" &&
        Object.values(FORBIDDEN_DEVICE_IDS).includes(device.id)
    );

    // Skip the test if we can't find the required devices
    if (!ufmDevice || !forbiddenMlnxDevice) {
      console.log(
        "Skipping test: Required test devices not found in mock data"
      );
      return;
    }

    // Select the site
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(site).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    // Select the UFM device
    await page.getByRole("button", { name: "Select a Device..." }).click();
    await page.getByRole("dialog").getByText(ufmDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    // Select the forbidden MLNX-OS device
    await page.getByRole("button", { name: "Select a Device IDs..." }).click();
    await page.getByRole("dialog").getByText(forbiddenMlnxDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    await page.getByRole("button", { name: "Submit" }).click();

    // Check for the error notification
    const errorTitle = page.locator("div.text-sm.font-semibold", {
      hasText: "Workflow Failed",
    });
    const errorMessage = page.locator("div.text-sm.opacity-90", {
      hasText: "Forbidden: You do not have permission",
    });

    await expect(errorTitle).toBeVisible({ timeout: TEST_TIMEOUT });
    await expect(errorMessage).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("only shows UFM devices in the device dropdown", async ({ page }) => {
    // Select a site that has UFM devices
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    // Open the device dropdown - use more specific selector
    await page.getByRole("button", { name: "Select a Device..." }).click();

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
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();
  });

  test("only shows MLNX-OS devices in the Device IDs dropdown", async ({
    page,
  }) => {
    // Select a site that has MLNX-OS devices
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    // Open the device IDs dropdown - use more specific selector
    await page.getByRole("button", { name: "Select a Device IDs..." }).click();

    // Get all device options in the dropdown
    const deviceIdOptions = page.getByRole("dialog").getByRole("option");

    // Check that each device in the dropdown has platform=MLNX-OS
    const mlnxDevices = DEVICES_LIST[SITES_LIST.pdx01].filter(
      (device) => device.platform === "MLNX-OS"
    );

    // Verify the correct number of devices is shown
    await expect(deviceIdOptions).toHaveCount(mlnxDevices.length);

    // Verify that only MLNX-OS devices are listed
    for (const mlnxDevice of mlnxDevices) {
      await expect(
        page.getByRole("dialog").getByText(mlnxDevice.name)
      ).toBeVisible();
    }

    // Close the dropdown
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();
  });

  test("selecting multiple devices for Device IDs", async ({ page }) => {
    // Find a site with multiple MLNX-OS devices
    const site = SITES_LIST.pdx01;
    const ufmDevices = DEVICES_LIST[site].filter(
      (device) => device.platform === "UFM"
    );
    const mlnxDevices = DEVICES_LIST[site].filter(
      (device) => device.platform === "MLNX-OS"
    );

    // Ensure we have at least two MLNX-OS devices for testing
    expect(mlnxDevices.length).toBeGreaterThanOrEqual(2);

    const ufmDevice = ufmDevices[0];
    const mlnxDevice1 = mlnxDevices[0];
    const mlnxDevice2 = mlnxDevices[1];

    // Fill form with specific test values
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(site).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    await page.getByRole("button", { name: "Select a Device..." }).click();
    await page.getByRole("dialog").getByText(ufmDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    // Select multiple MLNX-OS devices for the deviceIds field
    await page.getByRole("button", { name: "Select a Device IDs..." }).click();
    await page.getByRole("dialog").getByText(mlnxDevice1.name).click();
    await page.getByRole("dialog").getByText(mlnxDevice2.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request
        .url()
        .includes("/v1/workflow/ngc/infiniband_cable_validation");
    });

    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data includes multiple device IDs
    expect(requestData).toEqual({
      ufm_device_id: ufmDevice.id,
      switch_device_ids: [mlnxDevice1.id, mlnxDevice2.id],
    });

    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("loads form with URL parameters and performs manual changes", async ({
    page,
  }) => {
    // Find sites with UFM and MLNX-OS devices
    const initialSite = SITES_LIST.pdx01;
    const newSite = SITES_LIST.rno1;

    const initialUfmDevices = DEVICES_LIST[initialSite].filter(
      (device) => device.platform === "UFM"
    );
    const initialMlnxDevices = DEVICES_LIST[initialSite].filter(
      (device) => device.platform === "MLNX-OS"
    );

    const newUfmDevices = DEVICES_LIST[newSite].filter(
      (device) => device.platform === "UFM"
    );
    const newMlnxDevices = DEVICES_LIST[newSite].filter(
      (device) => device.platform === "MLNX-OS"
    );

    const initialUfmDevice = initialUfmDevices[0];
    const initialMlnxDevice = initialMlnxDevices[0];

    const newUfmDevice = newUfmDevices[0];
    const newMlnxDevice = newMlnxDevices[0];

    // Navigate to the form with URL parameters
    await page.goto(
      `/workflows/infinibandcablevalidationworkflow/form?site=${initialSite}&device=${initialUfmDevice.id}&device-id=${initialMlnxDevice.id}`
    );

    // Verify the form is pre-populated with URL parameter values
    await expect(page.getByRole("button").getByText(initialSite)).toBeVisible({
      timeout: TEST_TIMEOUT,
    });

    await expect(
      page.getByRole("button").getByText(initialUfmDevice.name)
    ).toBeVisible({
      timeout: TEST_TIMEOUT,
    });

    await expect(page.getByText(initialMlnxDevice.name)).toBeVisible({
      timeout: TEST_TIMEOUT,
    });

    // Change the values manually
    await page
      .getByRole("button")
      .getByText(initialSite, { exact: true })
      .click();
    await page.getByRole("dialog").getByText(newSite).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    // Select a new UFM device from the new site
    await page.getByRole("button", { name: "Select a Device..." }).click();
    await page.getByRole("dialog").getByText(newUfmDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    // Select a new MLNX-OS device from the new site
    await page.getByRole("button", { name: "Select a Device IDs..." }).click();
    await page.getByRole("dialog").getByText(newMlnxDevice.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Infiniband Cable Validation Workflow Form",
      })
      .click();

    // Verify the form is updated with the new values
    await expect(
      page.getByRole("button").getByText(newSite, { exact: true })
    ).toBeVisible({ timeout: TEST_TIMEOUT });

    await expect(
      page.getByRole("button").getByText(newUfmDevice.name, { exact: true })
    ).toBeVisible({ timeout: TEST_TIMEOUT });

    await expect(
      page.locator(".flex-wrap").getByText(newMlnxDevice.name)
    ).toBeVisible();

    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request
        .url()
        .includes("/v1/workflow/ngc/infiniband_cable_validation");
    });

    // Submit the form with the manually changed values
    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data contains the manually changed values, not the URL parameter values
    expect(requestData).toEqual({
      ufm_device_id: newUfmDevice.id,
      switch_device_ids: [newMlnxDevice.id],
    });

    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });
});
