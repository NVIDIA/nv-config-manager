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

// Sample VPC data for testing
const VPC_DATA = {
  vpc_id: "test-vpc-1",
  namespace_tag: "spectrumx-diff",
  site: SITES_LIST.pdx01,
};

test.describe("SpX Overlay Deletion Workflow Form", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/workflows/spxoverlaydeletionworkflow/form");
  });

  test("renders form with correct title", async ({ page }) => {
    const title = await page.getByRole("heading", {
      name: "SpX Overlay Deletion Workflow Form",
    });
    await expect(title).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("displays validation errors for empty submission", async ({ page }) => {
    // Clear the default values that are auto-populated
    const namespaceInput = page.getByLabel("Namespace");
    await expect(
      page.getByRole("button", { name: "Select a Site..." })
    ).toBeEnabled({
      timeout: TEST_TIMEOUT,
    });
    await expect(namespaceInput).toHaveValue("spectrumx", {
      timeout: TEST_TIMEOUT,
    });
    await expect
      .poll(
        async () => {
          await namespaceInput.fill("");
          return namespaceInput.inputValue();
        },
        { timeout: TEST_TIMEOUT }
      )
      .toBe("");

    await page.getByRole("button", { name: "Submit" }).click();

    // Check for all required field validations
    await expect(page.getByText("Site is required")).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
    await expect(page.getByText("VPC is required")).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
    await expect(page.getByText("Namespace is required")).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
  });
});

// Tests that handle their own navigation with URL parameters
test.describe("SpX Overlay Deletion Workflow Form - URL Parameters", () => {
  test("handles URL parameters correctly and submits with those values", async ({
    page,
  }) => {
    // Navigate with all URL parameters
    await page.goto(
      "/workflows/spxoverlaydeletionworkflow/form" +
        `?site=${SITES_LIST.pdx01}` +
        `&vpc=${VPC_DATA.vpc_id}` +
        `&namespace=${VPC_DATA.namespace_tag}`
    );

    // Verify all fields are pre-populated
    await expect(
      page.getByRole("button", { name: SITES_LIST.pdx01, exact: true })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
    await expect(page.getByLabel("VPC")).toHaveValue(VPC_DATA.vpc_id);
    await expect(page.getByLabel("Namespace")).toHaveValue(
      VPC_DATA.namespace_tag
    );

    // Set up a listener for the request (after page is loaded)
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/spx_overlay_deletion");
    });

    // Submit the form with the URL parameters
    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data matches the URL parameters
    expect(requestData).toEqual({
      site: SITES_LIST.pdx01,
      vpc_id: VPC_DATA.vpc_id,
      namespace_tag: VPC_DATA.namespace_tag,
    });

    // Wait for navigation to confirm submission completed
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("loads from URL parameters then do manual changes before submission", async ({
    page,
  }) => {
    // Navigate with initial URL parameters
    await page.goto(
      "/workflows/spxoverlaydeletionworkflow/form" +
        `?site=${SITES_LIST.pdx01}` +
        `&vpc=${VPC_DATA.vpc_id}` +
        `&namespace=${VPC_DATA.namespace_tag}`
    );

    // Verify initial values are pre-populated
    await expect(
      page.getByRole("button", { name: SITES_LIST.pdx01, exact: true })
    ).toBeVisible({ timeout: TEST_TIMEOUT });

    // Change the site
    await page.getByRole("button", { name: SITES_LIST.pdx01 }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.rno1).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "SpX Overlay Deletion Workflow Form" })
      .click();

    // Change the VPC ID
    await page.getByLabel("VPC").fill("modified-vpc");

    // Change the namespace
    await page.getByLabel("Namespace").fill("modified-namespace");

    // Set up a listener for the request (after page is loaded)
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/spx_overlay_deletion");
    });

    // Submit the form with the modified values
    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data matches the manually changed values
    expect(requestData).toEqual({
      site: SITES_LIST.rno1,
      vpc_id: "modified-vpc",
      namespace_tag: "modified-namespace",
    });

    // Wait for navigation to confirm submission completed
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });
});

// Tests that use beforeEach navigation
test.describe("SpX Overlay Deletion Workflow Form - Standard Tests", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/workflows/spxoverlaydeletionworkflow/form");
  });

  test("submits correct data to the API", async ({ page }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/spx_overlay_deletion");
    });

    // Fill form with specific test values
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "SpX Overlay Deletion Workflow Form" })
      .click();

    await page.getByLabel("VPC").fill("test-vpc-submission");
    await page.getByLabel("Namespace").fill("test-namespace");

    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data
    expect(requestData).toEqual({
      site: SITES_LIST.pdx01,
      vpc_id: "test-vpc-submission",
      namespace_tag: "test-namespace",
    });

    // Wait for navigation to confirm submission completed
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test(`disables form during submission`, async ({ page }) => {
    // Fill form with specific test values
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();
    // Click outside to close any dropdown that might be open
    await page
      .getByRole("heading", { name: "SpX Overlay Deletion Workflow Form" })
      .click();

    await page.getByLabel("VPC").fill("test-vpc-submission");
    await page.getByLabel("Namespace").fill("test-namespace");

    await page.getByRole("button", { name: "Submit" }).click();

    // Verify all form elements are disabled during submission
    await expect(
      page.getByRole("button", { name: SITES_LIST.pdx01, exact: true })
    ).toBeDisabled();
    await expect(page.getByLabel("VPC")).toBeDisabled();
    await expect(page.getByLabel("Namespace")).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Submitting..." })
    ).toBeDisabled();
  });

  test("displays forbidden error notification when submitting with forbidden values", async ({
    page,
  }) => {
    // Fill form with forbidden site and other required fields
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(FORBIDDEN_SITE_ID).click();

    await page.getByLabel("VPC").fill("test-vpc");
    await page.getByLabel("Namespace").fill("test-namespace");

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

// Test that needs to be in URL Parameters group
test.describe("SpX Overlay Deletion Workflow Form - URL Parameters 2", () => {
  test("submits form directly from URL parameters without changes", async ({
    page,
  }) => {
    // Navigate with all URL parameters
    await page.goto(
      "/workflows/spxoverlaydeletionworkflow/form" +
        `?site=${SITES_LIST.pdx01}` +
        `&vpc=${VPC_DATA.vpc_id}` +
        `&namespace=${VPC_DATA.namespace_tag}`
    );

    // Verify all fields are pre-populated
    await expect(
      page.getByRole("button", { name: SITES_LIST.pdx01, exact: true })
    ).toBeVisible({ timeout: TEST_TIMEOUT });

    // Set up a listener for the request (after page is loaded)
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/spx_overlay_deletion");
    });

    // Submit the form directly without making any changes
    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data contains the URL parameter values
    expect(requestData).toEqual({
      site: SITES_LIST.pdx01,
      vpc_id: VPC_DATA.vpc_id,
      namespace_tag: VPC_DATA.namespace_tag,
    });

    // Wait for navigation to confirm submission completed
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("populates default values for namespace", async ({ page }) => {
    // Navigate to the form without any URL parameters
    await page.goto("/workflows/spxoverlaydeletionworkflow/form");

    // Verify that namespace has the default value "spectrumx"
    await expect(page.getByLabel("Namespace")).toHaveValue("spectrumx");

    // Verify that Site and VPC are empty (no defaults)
    await expect(page.getByRole("button", { name: "Site" })).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
    await expect(page.getByLabel("VPC")).toHaveValue("");
  });
});
