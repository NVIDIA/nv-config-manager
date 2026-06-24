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

const FORM_TITLE = "InfiniBand PKey Creation Workflow";
const FORM_PATH = "/workflows/ibpkeycreationworkflow/form";
const ENDPOINT = "/v1/workflow/ngc/ib_pkey_creation";

test.describe("IB PKey Creation Form", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(FORM_PATH);
  });

  test("renders form with correct title", async ({ page }) => {
    await expect(
      page.getByRole("heading", { name: FORM_TITLE }),
    ).toBeVisible({ timeout: TEST_TIMEOUT });
  });

  test("requires host before submit", async ({ page }) => {
    await page.getByRole("button", { name: "Create PKey" }).click();
    await expect(page.getByText("Host is required")).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
  });

  test("prefills from URL params and submits with them", async ({ page }) => {
    const requestPromise = page.waitForRequest((r) =>
      r.url().includes(ENDPOINT),
    );

    await page.goto(`${FORM_PATH}?host=ufm.example.com&pkey=0x0100`);

    await expect(page.getByLabel("UFM Host")).toHaveValue("ufm.example.com");
    await expect(page.getByLabel("PKey (optional)")).toHaveValue("0x0100");

    await page.getByRole("button", { name: "Create PKey" }).click();

    const request = await requestPromise;
    const body = JSON.parse((await request.postData()) || "{}");
    expect(body).toEqual({
      host: "ufm.example.com",
      pkey: "0x0100",
    });

    await expect(
      page.getByRole("heading", { name: "Workflow Details" }),
    ).toBeVisible({ timeout: WORKFLOW_DETAILS_TIMEOUT });
  });

  test("omits empty optional fields from the request body", async ({
    page,
  }) => {
    const requestPromise = page.waitForRequest((r) =>
      r.url().includes(ENDPOINT),
    );

    await page.getByLabel("UFM Host").fill("ufm-1.lab");
    await page.getByRole("button", { name: "Create PKey" }).click();

    const request = await requestPromise;
    const body = JSON.parse((await request.postData()) || "{}");
    expect(body).toEqual({ host: "ufm-1.lab" });

    await expect(
      page.getByRole("heading", { name: "Workflow Details" }),
    ).toBeVisible({ timeout: WORKFLOW_DETAILS_TIMEOUT });
  });

  test("shows hint when pkey is non-canonical and lets server decide", async ({
    page,
  }) => {
    await page.getByLabel("UFM Host").fill("ufm-1.lab");
    await page.getByLabel("PKey (optional)").fill("not-a-pkey");

    await expect(
      page.getByText(/Expected format: 0x followed by 1-4 hex digits/i),
    ).toBeVisible({ timeout: TEST_TIMEOUT });

    await page.getByRole("button", { name: "Create PKey" }).click();

    const errorTitle = page.locator("div.text-sm.font-semibold", {
      hasText: "Workflow Failed",
    });
    await expect(errorTitle).toBeVisible({ timeout: TEST_TIMEOUT });
  });
});
