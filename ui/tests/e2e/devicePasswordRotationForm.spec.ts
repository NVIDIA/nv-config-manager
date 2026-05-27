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
import { SITES_LIST, DEVICES_LIST } from "@/mocks/data";

test.describe("Device Password Rotation Form", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/workflows/devicepasswordrotationworkflow/form");
  });

  test("renders form with correct title", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "Device Password Rotation Workflow" })
    ).toBeVisible();
  });

  test("submits correct data to the API with secret selection", async ({ page }) => {
    // Set up a listener for the request
    const requestPromise = page.waitForRequest((request) => {
      return request.url().includes("/v1/workflow/ngc/device_password_rotation");
    });

    // Fill form with specific test values
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.rno1).click();
    await page
      .getByRole("heading", { name: "Device Password Rotation Workflow" })
      .click();

    await page.getByRole("button", { name: "Device" }).click();
    await page
      .getByRole("dialog")
      .getByText(DEVICES_LIST.RNO1[0].name)
      .click();
    await page
      .getByRole("heading", { name: "Device Password Rotation Workflow" })
      .click();

    // Select secret (unique to password rotation workflow)
    await page.getByRole("button", { name: /Secret/i }).click();
    await page.getByRole("dialog").getByText("admin", { exact: true }).click();
    await page
      .getByRole("heading", { name: "Device Password Rotation Workflow" })
      .click();

    await page.getByRole("button", { name: "Submit" }).click();

    // Get the request before navigation completes
    const request = await requestPromise;
    const requestData = JSON.parse((await request.postData()) || "{}");

    // Verify the request data includes both device_id and selected_secret
    expect(requestData).toEqual({
      device_id: DEVICES_LIST.RNO1[0].id,
      selected_secret: "admin",
    });

    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("secret field requires device selection", async ({ page }) => {
    // Secret field should be disabled initially
    await expect(
      page.getByRole("button", { name: /Secret/i })
    ).toBeDisabled();

    // Fill in site
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.rno1).click();

    // Secret should still be disabled
    await expect(
      page.getByRole("button", { name: /Secret/i })
    ).toBeDisabled();

    // Fill in device
    await page.getByRole("button", { name: "Device" }).click();
    await page
      .getByRole("dialog")
      .getByText(DEVICES_LIST.RNO1[0].name)
      .click();

    // Secret field should now be enabled
    await expect(
      page.getByRole("button", { name: /Secret/i })
    ).toBeEnabled();
  });

  test("submit button requires all three fields", async ({ page }) => {
    // Submit button should be disabled initially
    await expect(page.getByRole("button", { name: "Submit" })).toBeDisabled();

    // Fill site and device
    await page.getByRole("button", { name: "Site" }).click();
    await page.getByRole("dialog").getByText(SITES_LIST.rno1).click();

    await page.getByRole("button", { name: "Device" }).click();
    await page
      .getByRole("dialog")
      .getByText(DEVICES_LIST.RNO1[0].name)
      .click();

    // Fill secret to enable submit
    await page.getByRole("button", { name: /Secret/i }).click();
    await page.getByRole("dialog").getByText("admin", { exact: true }).click();
    
    // Now submit should be enabled
    await expect(page.getByRole("button", { name: "Submit" })).toBeEnabled();
  });
});