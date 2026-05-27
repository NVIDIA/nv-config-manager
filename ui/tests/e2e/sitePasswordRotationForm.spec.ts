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
import { SITES_LIST } from "@/mocks/data";

test.describe("Site Password Rotation Form", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/workflows/sitepasswordrotationworkflow/form");
  });

  test("renders form with correct title", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Site Password Rotation Workflow" })
    ).toBeVisible();
  });

  test("secret field requires location selection first", async ({ page }) => {
    // Secret field should be disabled initially
    await expect(
      page.getByRole("button", { name: /select location first/i })
    ).toBeDisabled();

    // Fill in location
    await page.getByRole("button", { name: /Select a Location/i }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.rno1).click();
    await page
      .getByRole("heading", { name: "Site Password Rotation Workflow" })
      .click();

    // Wait for devices to load and secret field to become available
    await page.waitForTimeout(3000);
    await expect(
      page.getByRole("button", { name: /Secret to Rotate/i })
    ).toBeEnabled();
  });

  test("shows device count feedback", async ({ page }) => {
    // Fill in location
    await page.getByRole("button", { name: /Select a Location/i }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.rno1).click();
    await page
      .getByRole("heading", { name: "Site Password Rotation Workflow" })
      .click();

    // Should show device count feedback
    await expect(
      page.getByText(/Found \d+ matching device/)
    ).toBeVisible({ timeout: 5000 });
  });
});
