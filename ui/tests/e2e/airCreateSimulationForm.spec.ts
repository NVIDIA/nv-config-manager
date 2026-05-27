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
import { test, TEST_TIMEOUT } from "./shared/utils";
import { FORBIDDEN_SITE_ID } from "@/mocks/data";

// Sample data for testing
const SAMPLE_NAME = "test-simulation";
const SAMPLE_TOPOLOGY = JSON.stringify({
  devices: [
    {
      name: "device1",
      type: "switch",
      interfaces: ["Ethernet1/1", "Ethernet1/2"],
    },
  ],
});

test.describe("AIR Create Simulation Workflow Form", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/workflows/aircreatesimulationworkflow/form");
  });

  test("renders form with correct title", async ({ page }) => {
    const title = await page.getByRole("heading", {
      name: "AIR Create Simulation",
    });
    await expect(title).toBeVisible();
  });

  test("displays validation error when no fields are filled", async ({
    page,
  }) => {
    await page.getByRole("button", { name: "Submit" }).click();

    await expect(page.getByText("Name is required")).toBeVisible();
    await expect(page.getByText("Topology JSON is required")).toBeVisible();
  });

  test("displays validation error when form information is incomplete", async ({
    page,
  }) => {
    // Fill only name field
    await page.getByLabel("Simulation Name").fill(SAMPLE_NAME);
    await page.getByRole("button", { name: "Submit" }).click();

    // Check for validation error
    await expect(page.getByText("Topology JSON is required")).toBeVisible();

    // Clear and fill only topology field
    await page.reload();
    await page.locator('textarea[name="topology"]').fill(SAMPLE_TOPOLOGY);
    await page.getByRole("button", { name: "Submit" }).click();

    // Check for validation error
    await expect(page.getByText("Name is required")).toBeVisible();
  });

  test("displays validation error for invalid JSON", async ({ page }) => {
    // Fill form with invalid JSON
    await page.getByLabel("Simulation Name").fill(SAMPLE_NAME);
    await page.locator('textarea[name="topology"]').fill("invalid json");

    await page.getByRole("button", { name: "Submit" }).click();

    // Check for validation error
    await expect(page.getByText("Must be valid JSON")).toBeVisible();
  });

  test("formats valid JSON when format button is clicked", async ({ page }) => {
    // Fill form with unformatted JSON
    const unformattedJSON =
      '{"devices":[{"name":"device1","type":"switch","interfaces":["Ethernet1/1","Ethernet1/2"]}]}';
    await page.locator('textarea[name="topology"]').fill(unformattedJSON);

    // Click format button
    await page.getByRole("button", { name: "Format JSON" }).click();

    // NOTE: While not ideal, firefox has a weird bug where the toast notification is not visible unless we force a viewport adjustment.
    const successTitle = page.locator("div.text-sm.font-semibold", {
      hasText: "JSON Formatted",
    });
    const successMessage = page.locator("div.text-sm.opacity-90", {
      hasText: "Your JSON has been prettified!",
    });

    await expect(successTitle).toBeVisible({ timeout: TEST_TIMEOUT });
    await expect(successMessage).toBeVisible({ timeout: TEST_TIMEOUT });

    // Verify JSON is formatted
    const formattedValue = await page
      .locator('textarea[name="topology"]')
      .inputValue();
    expect(formattedValue).toBe(
      JSON.stringify(JSON.parse(unformattedJSON), null, 2)
    );
  });

  test("verifies JSON formatting preserves data structure", async ({
    page,
  }) => {
    // Create a complex JSON structure
    const complexJSON = {
      devices: [
        {
          name: "device1",
          type: "switch",
          interfaces: ["Ethernet1/1", "Ethernet1/2"],
          config: {
            hostname: "switch1",
            vlans: [1, 2, 3],
            features: {
              lldp: true,
              cdp: false,
            },
          },
        },
        {
          name: "device2",
          type: "router",
          interfaces: ["GigabitEthernet0/1", "GigabitEthernet0/2"],
          config: {
            hostname: "router1",
            routing: {
              ospf: true,
              bgp: false,
            },
          },
        },
      ],
      topology: {
        connections: [
          {
            from: "device1.Ethernet1/1",
            to: "device2.GigabitEthernet0/1",
          },
        ],
      },
    };

    // Fill form with unformatted JSON
    const unformattedJSON = JSON.stringify(complexJSON);
    await page.locator('textarea[name="topology"]').fill(unformattedJSON);

    // Click format button
    await page.getByRole("button", { name: "Format JSON" }).click();

    // NOTE: While not ideal, firefox has a weird bug where the toast notification is not visible unless we force a viewport adjustment.
    const successTitle = page.locator("div.text-sm.font-semibold", {
      hasText: "JSON Formatted",
    });
    const successMessage = page.locator("div.text-sm.opacity-90", {
      hasText: "Your JSON has been prettified!",
    });

    await expect(successTitle).toBeVisible({ timeout: TEST_TIMEOUT });
    await expect(successMessage).toBeVisible({ timeout: TEST_TIMEOUT });

    // Get the formatted value
    const formattedValue = await page
      .locator('textarea[name="topology"]')
      .inputValue();

    // Parse both the original and formatted JSON to verify they are equivalent
    const originalParsed = JSON.parse(unformattedJSON);
    const formattedParsed = JSON.parse(formattedValue);

    // Verify the data structure is preserved
    expect(formattedParsed).toEqual(originalParsed);

    // Verify the formatting (should have proper indentation)
    expect(formattedValue).toContain('  "devices": [');
    expect(formattedValue).toContain('    "name": "device1"');
    expect(formattedValue).toContain('      "config": {');
    expect(formattedValue).toContain('        "hostname": "switch1"');
  });

  test("shows error toast when formatting invalid JSON", async ({ page }) => {
    // Fill form with invalid JSON
    const topologyInput = page.locator('textarea[name="topology"]');
    await expect(topologyInput).toBeVisible({ timeout: TEST_TIMEOUT });
    await topologyInput.fill("invalid json");
    await expect(topologyInput).toHaveValue("invalid json", {
      timeout: TEST_TIMEOUT,
    });

    // Click format button
    await page.getByRole("button", { name: "Format JSON" }).click();

    // NOTE: While not ideal, firefox has a weird bug where the toast notification is not visible unless we force a viewport adjustment.
    const errorTitle = page.locator("div.text-sm.font-semibold", {
      hasText: "Invalid JSON",
    });
    const errorMessage = page.locator("div.text-sm.opacity-90", {
      hasText: "Cannot format invalid JSON. Please check your syntax.",
    });

    await expect(errorTitle).toBeVisible({ timeout: TEST_TIMEOUT });
    await expect(errorMessage).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("submits form with valid data correctly", async ({ page }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/air_create_simulation");
    });

    // Fill form with valid data
    await page.getByLabel("Simulation Name").fill(SAMPLE_NAME);
    await page.locator('textarea[name="topology"]').fill(SAMPLE_TOPOLOGY);

    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data
    expect(requestData).toEqual({
      name: SAMPLE_NAME,
      topology: JSON.parse(SAMPLE_TOPOLOGY),
    });

    // Wait for navigation to confirm submission completed
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("loads form data from URL parameters", async ({ page }) => {
    // Navigate with URL parameters
    await page.goto(
      `/workflows/aircreatesimulationworkflow/form?name=${SAMPLE_NAME}&topology=${encodeURIComponent(
        SAMPLE_TOPOLOGY
      )}`
    );

    // Verify the form is pre-populated with URL parameter values
    await expect(page.getByLabel("Simulation Name")).toHaveValue(SAMPLE_NAME);
    await expect(page.locator('textarea[name="topology"]')).toHaveValue(
      SAMPLE_TOPOLOGY
    );
  });

  test("disables form during submission", async ({ page }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/air_create_simulation");
    });

    // Fill form with valid data
    await page.getByLabel("Simulation Name").fill(SAMPLE_NAME);
    await page.locator('textarea[name="topology"]').fill(SAMPLE_TOPOLOGY);

    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data
    expect(requestData).toEqual({
      name: SAMPLE_NAME,
      topology: JSON.parse(SAMPLE_TOPOLOGY),
    });

    // Verify all form elements are disabled during submission
    await expect(page.getByLabel("Simulation Name")).toBeDisabled();
    await expect(page.locator('textarea[name="topology"]')).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Format JSON" })
    ).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Submitting..." })
    ).toBeDisabled();
  });

  test("displays error toast when workflow is forbidden", async ({ page }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/air_create_simulation");
    });

    // Fill form with valid data
    const nameInput = page.getByLabel("Simulation Name");
    const topologyInput = page.locator('textarea[name="topology"]');
    await expect(nameInput).toBeVisible({ timeout: TEST_TIMEOUT });
    await nameInput.fill(FORBIDDEN_SITE_ID);
    await topologyInput.fill(SAMPLE_TOPOLOGY);
    await expect(nameInput).toHaveValue(FORBIDDEN_SITE_ID, {
      timeout: TEST_TIMEOUT,
    });
    await expect(topologyInput).toHaveValue(SAMPLE_TOPOLOGY, {
      timeout: TEST_TIMEOUT,
    });

    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data
    expect(requestData).toEqual({
      name: FORBIDDEN_SITE_ID,
      topology: JSON.parse(SAMPLE_TOPOLOGY),
    });

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

  test("handles empty JSON string in format function", async ({ page }) => {
    // Clear the topology field
    await page.locator('textarea[name="topology"]').fill("");

    // Click format button
    await page.getByRole("button", { name: "Format JSON" }).click();

    // Verify no toast is shown and field remains empty
    await expect(
      page.getByText("Your JSON has been prettified!")
    ).not.toBeVisible();
    await expect(page.locator('textarea[name="topology"]')).toHaveValue("");
  });
});
