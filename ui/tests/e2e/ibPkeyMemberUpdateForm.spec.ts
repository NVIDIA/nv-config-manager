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
import { test, TEST_TIMEOUT, WORKFLOW_DETAILS_TIMEOUT } from "./shared/utils";

const FORM_TITLE = "Replace PKey Membership";
const FORM_PATH = "/workflows/ibpkeymemberupdateworkflow/form";
const ENDPOINT = "/v1/workflow/ngc/ib_pkey_member_update";

test.describe("IB PKey Member Update Form", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(FORM_PATH);
  });

  test("renders form with destructive warning", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: FORM_TITLE }),
    ).toBeVisible({ timeout: TEST_TIMEOUT });
    await expect(
      page.getByText(/reconciles PKey membership/i),
    ).toBeVisible({ timeout: TEST_TIMEOUT });
    await expect(page.getByText(/Removals require approval/i)).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
  });

  test("submits with interfaces and full membership_type", async ({ page }) => {
    const requestPromise = page.waitForRequest(
      (r) => r.url().includes(ENDPOINT) && r.method() === "POST",
    );

    await page.getByLabel("UFM Host").fill("ufm-1.lab");
    await page.getByLabel("PKey").fill("0x8001");
    await page.getByPlaceholder("device (e.g. hca01)").fill("hca01");
    await page.getByPlaceholder("interface (e.g. mlx5_0)").fill("mlx5_0");

    await page.getByRole("button", { name: "Replace Members" }).click();

    const request = await requestPromise;
    const body = JSON.parse((await request.postData()) || "{}");
    expect(body).toEqual({
      host: "ufm-1.lab",
      pkey: "0x8001",
      interfaces: [{ device: "hca01", interface: "mlx5_0" }],
      membership_type: "full",
    });

    await expect(
      page.getByRole("heading", { name: "Workflow Details" }),
    ).toBeVisible({ timeout: WORKFLOW_DETAILS_TIMEOUT });
  });
});
