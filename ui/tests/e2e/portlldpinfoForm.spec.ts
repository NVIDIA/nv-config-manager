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

// Sample MAC address for testing
const SAMPLE_MAC_ADDRESS = "00:11:22:33:44:55";
const SAMPLE_INTERFACE = "Ethernet1/1";

test.describe("Port LLDP Info Workflow Form", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/workflows/portlldpinfoworkflow/form");
  });

  test("renders form with correct title", async ({ page }) => {
    const title = await page.getByRole("heading", {
      name: "Port LLDP Info Workflow Form",
    });
    await expect(title).toBeVisible();
  });

  test("displays validation error when no fields are filled", async ({
    page,
  }) => {
    await page.getByRole("button", { name: "Submit" }).click();

    await expect(
      page.getByText(
        "Please provide either all device information or a MAC address"
      )
    ).toBeVisible();
  });

  test("displays validation error when form information is incomplete", async ({
    page,
  }) => {
    // Fill only site field
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "Port LLDP Info Workflow Form" })
      .click();

    await page.getByRole("button", { name: "Submit" }).click();

    // Check for validation errors
    await expect(
      page.getByText("Device is required when providing device information")
    ).toBeVisible();
    await expect(
      page.getByText("Interface is required when providing device information")
    ).toBeVisible();

    // Clear and fill only device field
    await page.reload();
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "Port LLDP Info Workflow Form" })
      .click();

    await page.getByRole("button", { name: "Device" }).click();
    await page
      .getByRole("dialog")
      .getByText(DEVICES_LIST[SITES_LIST.pdx01][0].name)
      .click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "Port LLDP Info Workflow Form" })
      .click();

    await page.getByRole("button", { name: "Submit" }).click();

    // Check for validation error
    await expect(
      page.getByText("Interface is required when providing device information")
    ).toBeVisible();
  });

  test("disables device fields when MAC address is entered", async ({
    page,
  }) => {
    // Fill MAC address
    const macAddressInput = page.getByLabel("MAC Address");
    await macAddressInput.waitFor({ state: "visible" });
    await macAddressInput.fill(SAMPLE_MAC_ADDRESS);
    await expect(macAddressInput).toHaveValue(SAMPLE_MAC_ADDRESS, {
      timeout: TEST_TIMEOUT,
    });

    // Verify device fields are disabled
    await expect(
      page.getByRole("button", { name: "Select a Site" })
    ).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Select a Device" })
    ).toBeDisabled();
    await expect(page.getByLabel("Interface")).toBeDisabled();
  });

  test("disables MAC address field when device information is entered", async ({
    page,
  }) => {
    // Fill site field
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "Port LLDP Info Workflow Form" })
      .click();

    // Verify MAC address field is disabled
    await expect(page.getByLabel("MAC Address")).toBeDisabled();
  });

  test("clears device fields when MAC address is entered", async ({ page }) => {
    // Fill device information first
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "Port LLDP Info Workflow Form" })
      .click();

    await page.getByRole("button", { name: "Device" }).click();
    await page
      .getByRole("dialog")
      .getByText(DEVICES_LIST[SITES_LIST.pdx01][0].name)
      .click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "Port LLDP Info Workflow Form" })
      .click();

    await page.getByLabel("Interface").fill(SAMPLE_INTERFACE);

    // Reload the page to reset the form state
    await page.reload();

    // Now fill MAC address
    await page.getByLabel("MAC Address").fill(SAMPLE_MAC_ADDRESS);

    // Verify device fields are empty and disabled
    await expect(page.getByRole("button", { name: "Site" })).toBeDisabled();
    await expect(page.getByRole("button", { name: "Device" })).toBeDisabled();
    await expect(page.getByLabel("Interface")).toBeDisabled();
    await expect(page.getByLabel("Interface")).toHaveValue("");
  });

  test("clears MAC address when device information is entered", async ({
    page,
  }) => {
    // Fill MAC address first
    await page.getByLabel("MAC Address").fill(SAMPLE_MAC_ADDRESS);

    // Reload the page to reset the form state
    await page.reload();

    // Now fill device information
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "Port LLDP Info Workflow Form" })
      .click();

    // Verify MAC address field is empty and disabled
    await expect(page.getByLabel("MAC Address")).toBeDisabled();
    await expect(page.getByLabel("MAC Address")).toHaveValue("");
  });

  test("submits form with device information correctly", async ({ page }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/port_lldp_info");
    });

    // Fill device information
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "Port LLDP Info Workflow Form" })
      .click();

    await page.getByRole("button", { name: "Device" }).click();
    await page
      .getByRole("dialog")
      .getByText(DEVICES_LIST[SITES_LIST.pdx01][0].name)
      .click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "Port LLDP Info Workflow Form" })
      .click();

    await page.getByLabel("Interface").fill(SAMPLE_INTERFACE);

    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data
    expect(requestData).toEqual({
      device_id: DEVICES_LIST[SITES_LIST.pdx01][0].id,
      interface: SAMPLE_INTERFACE,
    });

    // Wait for navigation to confirm submission completed
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("submits form with MAC address correctly", async ({ page }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/port_lldp_info");
    });

    // Fill MAC address
    await page.getByLabel("MAC Address").waitFor({ state: "visible" });
    await page.getByLabel("MAC Address").fill(SAMPLE_MAC_ADDRESS);

    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data
    expect(requestData).toEqual({
      remote_mac_address: SAMPLE_MAC_ADDRESS,
    });

    // Wait for navigation to confirm submission completed
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("loads device information from URL parameters", async ({ page }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/port_lldp_info");
    });

    // Navigate with device information URL parameters
    const siteName = SITES_LIST.pdx01;
    const deviceId = DEVICES_LIST[siteName][0].id;
    const deviceName = DEVICES_LIST[siteName][0].name;
    await page.goto(
      `/workflows/portlldpinfoworkflow/form?site=${siteName}&device-id=${deviceId}&interface=${SAMPLE_INTERFACE}`
    );

    // Verify the form is pre-populated with URL parameter values
    await expect(page.getByRole("button").getByText(siteName)).toBeVisible();
    await expect(page.getByRole("button").getByText(deviceName)).toBeVisible();
    await expect(page.getByLabel("Interface")).toHaveValue(SAMPLE_INTERFACE);
    await expect(page.getByLabel("MAC Address")).toBeDisabled();

    // Submit the form directly without making any changes
    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data contains the URL parameter values
    expect(requestData).toEqual({
      device_id: deviceId,
      interface: SAMPLE_INTERFACE,
    });

    // Wait for navigation to confirm submission completed
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("loads MAC address from URL parameters", async ({ page }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/port_lldp_info");
    });

    // Navigate with MAC address URL parameter
    await page.goto(
      `/workflows/portlldpinfoworkflow/form?remote_mac_address=${SAMPLE_MAC_ADDRESS}`
    );

    // Verify the form is pre-populated with URL parameter values
    await expect(page.getByLabel("MAC Address")).toHaveValue(
      SAMPLE_MAC_ADDRESS
    );
    await expect(page.getByRole("button", { name: "Site" })).toBeDisabled();
    await expect(page.getByRole("button", { name: "Device" })).toBeDisabled();
    await expect(page.getByLabel("Interface")).toBeDisabled();

    // Submit the form directly without making any changes
    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data contains the URL parameter values
    expect(requestData).toEqual({
      remote_mac_address: SAMPLE_MAC_ADDRESS,
    });

    // Wait for navigation to confirm submission completed
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("prioritizes MAC address when both device info and MAC address are provided in URL parameters", async ({
    page,
  }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/port_lldp_info");
    });

    // Navigate with both device info and MAC address URL parameters
    const siteName = SITES_LIST.pdx01;
    const deviceId = DEVICES_LIST[siteName][0].id;
    await page.goto(
      `/workflows/portlldpinfoworkflow/form?site=${siteName}&device-id=${deviceId}&interface=${SAMPLE_INTERFACE}&remote_mac_address=${SAMPLE_MAC_ADDRESS}`
    );

    // Verify the form is pre-populated with MAC address and device fields are disabled
    await expect(page.getByLabel("MAC Address")).toHaveValue(
      SAMPLE_MAC_ADDRESS
    );
    await expect(page.getByRole("button", { name: "Site" })).toBeDisabled();
    await expect(page.getByRole("button", { name: "Device" })).toBeDisabled();
    await expect(page.getByLabel("Interface")).toBeDisabled();

    // Submit the form directly without making any changes
    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data contains only the MAC address
    expect(requestData).toEqual({
      remote_mac_address: SAMPLE_MAC_ADDRESS,
    });

    // Wait for navigation to confirm submission completed
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("disables form during submission when using device information", async ({
    page,
  }) => {
    // Fill device information
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "Port LLDP Info Workflow Form" })
      .click();

    await page.getByRole("button", { name: "Device" }).click();
    await page
      .getByRole("dialog")
      .getByText(DEVICES_LIST[SITES_LIST.pdx01][0].name)
      .click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "Port LLDP Info Workflow Form" })
      .click();

    await page.getByLabel("Interface").fill(SAMPLE_INTERFACE);

    await page.getByRole("button", { name: "Submit" }).click();

    // Verify all form elements are disabled during submission
    await expect(
      page.getByRole("button", { name: SITES_LIST.pdx01, exact: true })
    ).toBeDisabled();
    await expect(
      page.getByRole("button", {
        name: DEVICES_LIST[SITES_LIST.pdx01][0].name,
        exact: true,
      })
    ).toBeDisabled();
    await expect(page.getByLabel("Interface")).toBeDisabled();
    await expect(page.getByLabel("MAC Address")).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Submitting..." })
    ).toBeDisabled();
  });

  test("automatically clears device info when MAC address is entered and submits with only MAC address", async ({
    page,
  }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/port_lldp_info");
    });

    // Fill device information first
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "Port LLDP Info Workflow Form" })
      .click();

    await page.getByRole("button", { name: "Device" }).click();
    await page
      .getByRole("dialog")
      .getByText(DEVICES_LIST[SITES_LIST.pdx01][0].name)
      .click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "Port LLDP Info Workflow Form" })
      .click();

    await page.getByLabel("Interface").fill(SAMPLE_INTERFACE);

    // Now fill MAC address - this should clear and disable device fields
    await page.evaluate(() => {
      const macInput = document.querySelector(
        'input[name="remote_mac_address"]'
      );
      if (macInput) {
        macInput.removeAttribute("disabled");
      }
    });
    await page.getByLabel("MAC Address").fill(SAMPLE_MAC_ADDRESS);

    // Verify device fields are cleared and disabled
    await expect(page.getByRole("button", { name: "Site" })).toBeDisabled();
    await expect(page.getByRole("button", { name: "Device" })).toBeDisabled();
    await expect(page.getByLabel("Interface")).toBeDisabled();

    // Submit the form
    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data contains ONLY the MAC address
    expect(requestData).toEqual({
      remote_mac_address: SAMPLE_MAC_ADDRESS,
    });
    expect(requestData).not.toHaveProperty("device_id");
    expect(requestData).not.toHaveProperty("interface");

    // Wait for navigation to confirm submission completed
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("disables form during submission when using MAC address", async ({
    page,
  }) => {
    // Fill MAC address
    await page.getByLabel("MAC Address").waitFor({ state: "visible" });
    await page.getByLabel("MAC Address").fill(SAMPLE_MAC_ADDRESS);

    await page.getByRole("button", { name: "Submit" }).click();

    // Verify all form elements are disabled during submission
    await expect(page.getByRole("button", { name: "Site" })).toBeDisabled();
    await expect(page.getByRole("button", { name: "Device" })).toBeDisabled();
    await expect(page.getByLabel("Interface")).toBeDisabled();
    await expect(page.getByLabel("MAC Address")).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Submitting..." })
    ).toBeDisabled();
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
      .getByRole("heading", { name: "Port LLDP Info Workflow" })
      .click();

    await page.getByRole("button", { name: "Device" }).click();
    await page
      .getByRole("dialog")
      .getByText(forbiddenDevice?.name || "")
      .click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "Port LLDP Info Workflow" })
      .click();
    await page.getByLabel("Interface").fill(SAMPLE_INTERFACE);

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

  test("clears site field when an invalid site is provided in URL params", async ({
    page,
  }) => {
    // Navigate with an invalid site parameter
    const invalidSite = "nonexistent-site";
    await page.goto(`/workflows/portlldpinfoworkflow/form?site=${invalidSite}`);

    // Allow time for validation logic to run
    await page.waitForTimeout(500);

    // Check that site field is empty (cleared)
    await expect(
      page.getByRole("button", { name: "Select a Site" })
    ).toBeVisible();

    // Verify site dropdown works properly after clearing invalid value
    await page.getByRole("button", { name: "Site" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();

    // Verify the site was selected correctly
    await expect(
      page.getByRole("button", { name: SITES_LIST.pdx01 })
    ).toBeVisible();
  });

  test("clears both site and device fields when invalid site and device are provided in URL params", async ({
    page,
  }) => {
    // Navigate with invalid site and device parameters
    const invalidSite = "nonexistent-site";
    const invalidDevice = "nonexistent-device";
    await page.goto(
      `/workflows/portlldpinfoworkflow/form?site=${invalidSite}&device-id=${invalidDevice}`
    );

    // Allow time for validation logic to run
    await page.waitForTimeout(500);

    // Check that both site and device fields are empty (cleared)
    await expect(
      page.getByRole("button", { name: "Select a Site" })
    ).toBeVisible();
    await expect(
      page.getByRole("button", { name: "Select a Device" })
    ).toBeVisible();

    // Verify both dropdowns work properly after clearing invalid values
    await page.getByRole("button", { name: "Site" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();

    // Wait for devices to load
    await page.waitForTimeout(500);

    await page.getByRole("button", { name: "Device" }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
  });

  test("keeps valid site but clears invalid device from URL params", async ({
    page,
  }) => {
    // Navigate with valid site but invalid device parameters
    const validSite = SITES_LIST.pdx01;
    const invalidDevice = "nonexistent-device";
    await page.goto(
      `/workflows/portlldpinfoworkflow/form?site=${validSite}&device-id=${invalidDevice}`
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
    await page
      .getByRole("dialog")
      .getByText(DEVICES_LIST[validSite][0].name)
      .click();

    // Verify the device was selected correctly
    await expect(
      page.getByRole("button", { name: DEVICES_LIST[validSite][0].name })
    ).toBeVisible();
  });

  test("automatically clears device field when site field is cleared", async ({
    page,
  }) => {
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.forbidden).click();

    // Wait for devices to load
    await page.waitForTimeout(500);

    await page.getByRole("button", { name: "Device" }).click();
    await page
      .getByRole("dialog")
      .getByText(DEVICES_LIST[SITES_LIST.forbidden][0].name)
      .click();

    await page.waitForTimeout(500);

    // Verify both fields are properly populated
    await expect(
      page.getByRole("button", { name: SITES_LIST.forbidden })
    ).toBeVisible({ timeout: 5000 });
    await expect(
      page.getByRole("button", {
        name: DEVICES_LIST[SITES_LIST.forbidden][0].name,
      })
    ).toBeVisible({ timeout: 5000 });

    // Now clear the site by selecting it and clicking a different option
    await page.getByRole("button", { name: SITES_LIST.forbidden }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();

    // Verify site field is cleared
    await expect(
      page.getByRole("button", { name: SITES_LIST.pdx01 })
    ).toBeVisible();

    // Verify device field is also automatically cleared
    await expect(
      page.getByRole("button", { name: "Select a Device" })
    ).toBeVisible();
  });

  test("automatically clears device field when site is changed after populating from URL params", async ({
    page,
  }) => {
    // Navigate with valid site and device parameters
    const validSite = SITES_LIST.pdx01;
    const validDevice = DEVICES_LIST[validSite][0].id;
    await page.goto(
      `/workflows/portlldpinfoworkflow/form?site=${validSite}&device-id=${validDevice}`
    );

    // Allow time for fields to populate
    await page.waitForTimeout(500);

    // Verify both fields are properly populated from URL params
    await expect(page.getByRole("button", { name: validSite })).toBeVisible();
    await expect(
      page.getByRole("button", { name: DEVICES_LIST[validSite][0].name })
    ).toBeVisible();

    // Now change the site to a different valid site
    await page.getByRole("button", { name: validSite }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.rno1).click();

    // Verify site field changed to new value
    await expect(
      page.getByRole("button", { name: SITES_LIST.rno1 })
    ).toBeVisible();

    // Verify device field is automatically cleared
    await expect(
      page.getByRole("button", { name: "Select a Device" })
    ).toBeVisible();
  });

  test("clearing site resets device and interface fields to default state", async ({
    page,
  }) => {
    // Find a site with devices
    const site = SITES_LIST.pdx01;
    const device = DEVICES_LIST[site][0];

    // Fill form with initial site and selections
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(site).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Port LLDP Info Workflow Form",
      })
      .click();

    await page.getByRole("button", { name: "Device" }).click();
    await page.getByRole("dialog").getByText(device.name).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", {
        name: "Port LLDP Info Workflow Form",
      })
      .click();

    // Verify initial selections are visible
    await expect(page.getByRole("button").getByText(device.name)).toBeVisible();

    // Find the X icon with the specific class inside the button's parent container
    await page
      .locator(".flex.items-center.self-stretch")
      .filter({ has: page.locator("svg.lucide.lucide-x.size-4") })
      .first()
      .click();

    // Verify device and interface fields are reset to their default state
    await expect(
      page.getByRole("button").getByText("Select a Device")
    ).toBeVisible();
  });
});
