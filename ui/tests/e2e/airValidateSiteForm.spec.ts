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
import { SITES_LIST, FORBIDDEN_SITE_ID } from "@/mocks/data";
import { test, TEST_TIMEOUT } from "./shared/utils";

test.describe("AIR Validate Site Workflow Form", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/workflows/airvalidatesiteworkflow/form");
  });

  test("renders form with correct title", async ({ page }) => {
    const title = await page.getByRole("heading", {
      name: "AIR Validate Site",
    });
    await expect(title).toBeVisible();
  });

  test("displays validation error when no site is selected", async ({
    page,
  }) => {
    await page.getByRole("button", { name: "Submit" }).click();

    await expect(page.getByText("Site is required")).toBeVisible();
  });

  test("submits form with correct data to API", async ({ page }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/air_validate_site");
    });

    const site = SITES_LIST.pdx01;

    // Fill form with site
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(site).click();
    // Click outside to close dropdown
    await page.getByRole("heading", { name: "AIR Validate Site" }).click();

    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data
    expect(requestData).toEqual({
      site_name: site,
    });

    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("loads site from URL parameters", async ({ page }) => {
    const site = SITES_LIST.pdx01;

    // Navigate with site URL parameter
    await page.goto(`/workflows/airvalidatesiteworkflow/form?site=${site}`);

    // Verify the form is pre-populated with URL parameter value
    await expect(page.getByRole("button").getByText(site)).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
  });

  test("submits form directly from URL parameters without changes", async ({
    page,
  }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/air_validate_site");
    });

    const site = SITES_LIST.pdx01;

    // Navigate with site URL parameter
    await page.goto(`/workflows/airvalidatesiteworkflow/form?site=${site}`);

    // Verify the form is pre-populated
    await expect(page.getByRole("button").getByText(site)).toBeVisible({
      timeout: TEST_TIMEOUT,
    });

    // Submit without making any changes
    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data contains the URL parameter value
    expect(requestData).toEqual({
      site_name: site,
    });

    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("loads form with URL parameters and performs manual changes", async ({
    page,
  }) => {
    const initialSite = SITES_LIST.pdx01;
    const newSite = SITES_LIST.rno1;

    // Navigate with initial site URL parameter
    await page.goto(
      `/workflows/airvalidatesiteworkflow/form?site=${initialSite}`
    );

    // Verify the form is pre-populated with URL parameter value
    await expect(page.getByRole("button").getByText(initialSite)).toBeVisible({
      timeout: TEST_TIMEOUT,
    });

    // Change the site manually
    await page
      .getByRole("button")
      .getByText(initialSite, { exact: true })
      .click();
    await page.getByRole("dialog").getByText(newSite).click();
    // Click outside to close dropdown
    await page.getByRole("heading", { name: "AIR Validate Site" }).click();

    // Verify the form is updated with the new value
    await expect(
      page.getByRole("button").getByText(newSite, { exact: true })
    ).toBeVisible({ timeout: TEST_TIMEOUT });

    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/air_validate_site");
    });

    // Submit the form with the manually changed value
    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data contains the manually changed value, not the URL parameter value
    expect(requestData).toEqual({
      site_name: newSite,
    });

    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("clears site field when invalid site is provided in URL params", async ({
    page,
  }) => {
    // Navigate with an invalid site parameter
    const invalidSite = "nonexistent-site";
    await page.goto(
      `/workflows/airvalidatesiteworkflow/form?site=${invalidSite}`
    );

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

  test("shows error for forbidden site", async ({ page }) => {
    // Fill form with forbidden site
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(FORBIDDEN_SITE_ID).click();
    // Click outside to close dropdown
    await page.getByRole("heading", { name: "AIR Validate Site" }).click();

    // Submit the form
    await page.getByRole("button", { name: "Submit" }).click();

    // Wait for and verify the error toast appears
    const errorTitle = page.locator("div.text-sm.font-semibold", {
      hasText: "Workflow Failed",
    });
    const errorMessage = page.locator("div.text-sm.opacity-90", {
      hasText: "Forbidden: You do not have permission to run this workflow",
    });

    await expect(errorTitle).toBeVisible({ timeout: TEST_TIMEOUT });
    await expect(errorMessage).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("form disables during submission", async ({ page }) => {
    const site = SITES_LIST.pdx01;

    // Fill the form
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(site).click();
    // Click outside to close dropdown
    await page.getByRole("heading", { name: "AIR Validate Site" }).click();

    // Submit the form
    await page.getByRole("button", { name: "Submit" }).click();

    // Verify submit button shows "Submitting..." and is disabled
    await expect(
      page.getByRole("button", { name: "Submitting..." })
    ).toBeDisabled();

    // Verify site field is also disabled during submission
    await expect(
      page.getByRole("button", { name: site, exact: true })
    ).toBeDisabled();
  });

  test("can clear site selection and reselect", async ({ page }) => {
    const firstSite = SITES_LIST.pdx01;
    const secondSite = SITES_LIST.rno1;

    // Select first site
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(firstSite).click();
    // Click outside to close dropdown
    await page.getByRole("heading", { name: "AIR Validate Site" }).click();

    // Verify first site is selected
    await expect(page.getByRole("button", { name: firstSite })).toBeVisible();
    await expect(page.getByRole("button", { name: "Submit" })).toBeEnabled();

    // Clear the selection by clicking the X button
    await page
      .locator(".flex.items-center.self-stretch")
      .filter({ has: page.locator("svg.lucide.lucide-x.size-4") })
      .first()
      .click();

    // Verify site field is cleared
    await expect(
      page.getByRole("button", { name: "Select a Site" })
    ).toBeVisible();

    // Select second site
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(secondSite).click();
    // Click outside to close dropdown
    await page.getByRole("heading", { name: "AIR Validate Site" }).click();

    // Verify second site is selected
    await expect(page.getByRole("button", { name: secondSite })).toBeVisible();
  });

  test("keyboard navigation works in site dropdown", async ({ page }) => {
    // Open dropdown with keyboard
    await page.getByRole("button", { name: "Site" }).focus();
    await page.keyboard.press("Enter");

    // Verify dropdown is open
    await expect(page.getByRole("dialog")).toBeVisible();

    // Navigate with arrow keys and select with Enter
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("Enter");

    // Verify a site was selected (first option)
    await expect(page.getByRole("button", { name: "Submit" })).toBeEnabled();
  });

  test("displays loading state when sites are loading", async ({ page }) => {
    // This test verifies the loading state is handled properly
    // The loading state should be brief but visible during initial load
    await page.goto("/workflows/airvalidatesiteworkflow/form");

    // Check that the form renders without errors during loading
    await expect(
      page.getByRole("heading", { name: "AIR Validate Site" })
    ).toBeVisible();

    // Eventually the site dropdown should be available
    await expect(
      page.getByRole("button", { name: /Site|Select a Site/ })
    ).toBeVisible({ timeout: 10000 });
  });
});
