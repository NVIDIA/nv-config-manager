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

// Sample data for testing - matching what's available in the mock
const SAMPLE_SIMULATION_ID = "test-simulation-123";
const SAMPLE_SIMULATION_NAME = "Test Simulation 123";
const FORBIDDEN_SIMULATION_NAME = "Forbidden Simulation";

test.describe("AIR Delete Simulation Workflow Form", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/workflows/airdeletesimulationworkflow/form");
  });

  test("renders form with correct title", async ({ page }) => {
    const title = await page.getByRole("heading", {
      name: "AIR Delete Simulation",
    });
    await expect(title).toBeVisible();
  });

  test("displays validation error when no simulation is selected", async ({
    page,
  }) => {
    await page.getByRole("button", { name: "Submit" }).click();

    await expect(page.getByText("Simulation ID is required")).toBeVisible();
  });

  test("submits form with valid simulation selection correctly", async ({
    page,
  }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/air_delete");
    });

    // Wait for simulations to load and select one
    await page.getByRole("button", { name: "Select a Simulation..." }).click();
    await page.getByRole("option", { name: SAMPLE_SIMULATION_NAME }).click();

    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data
    expect(requestData).toEqual({
      simulation_id: SAMPLE_SIMULATION_ID,
    });

    // Wait for navigation to confirm submission completed
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("loads form data from URL parameters", async ({ page }) => {
    // Navigate with URL parameters
    await page.goto(
      `/workflows/airdeletesimulationworkflow/form?simulation_id=${SAMPLE_SIMULATION_ID}`
    );

    // Wait for the form to load and check that the correct simulation is selected
    await expect(page.getByText(SAMPLE_SIMULATION_NAME)).toBeVisible();
  });

  test("disables form during submission", async ({ page }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/air_delete");
    });

    // Wait for simulations to load and select one
    await page.getByRole("button", { name: "Select a Simulation..." }).click();
    await page.getByRole("option", { name: SAMPLE_SIMULATION_NAME }).click();

    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data
    expect(requestData).toEqual({
      simulation_id: SAMPLE_SIMULATION_ID,
    });

    // Verify submit button shows submitting state
    await expect(
      page.getByRole("button", { name: "Submitting..." })
    ).toBeDisabled();
  });

  test("displays error toast when workflow is forbidden", async ({ page }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/air_delete");
    });

    // Wait for simulations to load and select the forbidden one
    await page.getByRole("button", { name: "Select a Simulation..." }).click();
    await page.getByRole("option", { name: FORBIDDEN_SIMULATION_NAME }).click();

    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data
    expect(requestData).toEqual({
      simulation_id: FORBIDDEN_SITE_ID,
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

  test("submits form with URL parameters without changes", async ({ page }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/air_delete");
    });

    // Navigate with URL parameters
    await page.goto(
      `/workflows/airdeletesimulationworkflow/form?simulation_id=${SAMPLE_SIMULATION_ID}`
    );

    // Wait for the correct simulation to be pre-selected
    await expect(page.getByText(SAMPLE_SIMULATION_NAME)).toBeVisible();

    // Submit the form directly without making any changes
    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data contains the URL parameter values
    expect(requestData).toEqual({
      simulation_id: SAMPLE_SIMULATION_ID,
    });

    // Wait for navigation to confirm submission completed
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("loads from URL parameters then do manual changes before submission", async ({
    page,
  }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/air_delete");
    });

    // Navigate with initial URL parameters
    await page.goto(
      `/workflows/airdeletesimulationworkflow/form?simulation_id=${SAMPLE_SIMULATION_ID}`
    );

    // Wait for the initial selection to load
    await expect(page.getByText(SAMPLE_SIMULATION_NAME)).toBeVisible();

    // Change the simulation selection
    await page.getByRole("button", { name: SAMPLE_SIMULATION_NAME }).click();
    await page
      .getByRole("option", { name: "SITEA Validation" })
      .click();

    // Submit the form with the modified values
    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data matches the manually changed values
    expect(requestData).toEqual({
      simulation_id: "4dce8367-aaea-4965-924e-34647be0a630",
    });

    // Wait for navigation to confirm submission completed
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("can search and filter simulations in dropdown", async ({ page }) => {
    // Open the dropdown
    await page.getByRole("button", { name: "Select a Simulation..." }).click();

    // Type in the search box to filter
    await page.getByPlaceholder("Search Simulation").fill("SITEA");

    // Verify that only matching items are shown
    await expect(
      page.getByRole("option", { name: "SITEA Validation" })
    ).toBeVisible();
    await expect(
      page.getByRole("option", { name: SAMPLE_SIMULATION_NAME })
    ).not.toBeVisible();

    // Clear search and verify all options are back
    await page.getByPlaceholder("Search Simulation").fill("");
    await expect(
      page.getByRole("option", { name: SAMPLE_SIMULATION_NAME })
    ).toBeVisible();
    await expect(
      page.getByRole("option", { name: "SITEA Validation" })
    ).toBeVisible();
  });
});
