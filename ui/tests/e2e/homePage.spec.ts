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

test.describe("Home Page (Splash Page)", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/");
  });

  test("renders the NVIDIA Config Manager home page with correct title", async ({
    page,
  }) => {
    await expect(
      page.getByRole("heading", { name: "NVIDIA Config Manager", level: 1 })
    ).toBeVisible({ timeout: TEST_TIMEOUT });

    await expect(
      page.getByText("Network automation and configuration management platform")
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("displays User Interfaces section with Workflows and Device Configs links", async ({
    page,
  }) => {
    // Check section heading
    await expect(
      page.getByRole("heading", { name: "User Interfaces", level: 2 })
    ).toBeVisible({ timeout: TEST_TIMEOUT });

    // Check Workflows card exists (look for card with heading, not nav link)
    const workflowsHeading = page.getByRole("heading", { name: "Workflows" });
    await expect(workflowsHeading).toBeVisible({ timeout: TEST_TIMEOUT });

    // Check Device Configs card exists (look for card with heading)
    const configsHeading = page.getByRole("heading", { name: "Device Configs" });
    await expect(configsHeading).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("displays External Services section with Nautobot link", async ({
    page,
  }) => {
    await expect(
      page.getByRole("heading", { name: "External Services", level: 2 })
    ).toBeVisible({ timeout: TEST_TIMEOUT });

    // Check Nautobot card (external link)
    const nautobotLink = page.locator(
      "a[href='https://nautobot.example.com']"
    );
    await expect(nautobotLink).toBeVisible({ timeout: TEST_TIMEOUT });
    await expect(nautobotLink.getByText("Nautobot")).toBeVisible();
    await expect(
      nautobotLink.getByText("Network Source of Truth")
    ).toBeVisible();
  });

  test("displays API Documentation section with all API links", async ({
    page,
  }) => {
    await expect(
      page.getByRole("heading", { name: "API Documentation", level: 2 })
    ).toBeVisible({ timeout: TEST_TIMEOUT });

    // Check API cards are visible (use heading role for card titles)
    await expect(
      page.getByRole("heading", { name: "Workflow API" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
    await expect(
      page.getByRole("heading", { name: "Config Store API" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
    await expect(
      page.getByRole("heading", { name: "Render Service API" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
    await expect(
      page.getByRole("heading", { name: "ZTP API" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
    await expect(
      page.getByRole("heading", { name: "DHCP API" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("navigates to Workflows page when clicking Workflows card", async ({
    page,
  }) => {
    // Click the Workflows heading/card in the main content area
    const workflowsHeading = page.getByRole("heading", { name: "Workflows" });
    await workflowsHeading.click();

    await page.waitForURL("**/workflows");
    await expect(page).toHaveURL(/\/workflows$/);
  });

  test("navigates to Configs page when clicking Device Configs card", async ({
    page,
  }) => {
    // Click the Device Configs heading/card in the main content area
    const configsHeading = page.getByRole("heading", { name: "Device Configs" });
    await configsHeading.click();

    await page.waitForURL("**/configs");
    await expect(page).toHaveURL(/\/configs$/);
  });
});

