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

test.describe("Config File Page", () => {
  test.beforeEach(async ({ page }) => {
    // Navigate directly to config file page
    await page.goto("/device/device-uuid-1/running-config.txt?file_type=intended");
  });

  test("renders config file page with Download button", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: "running-config.txt", level: 1 })
    ).toBeVisible({ timeout: TEST_TIMEOUT });

    await expect(page.getByRole("button", { name: "Download" })).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
  });

  test("downloads single config file when clicking Download", async ({
    page,
  }) => {
    await expect(page.getByRole("button", { name: "Download" })).toBeVisible({
      timeout: TEST_TIMEOUT,
    });

    const [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 15000 }),
      page.getByRole("button", { name: "Download" }).click(),
    ]);
    expect(download.suggestedFilename()).toBe("spine-001_running-config.txt");
  });
});
