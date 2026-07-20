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
import { SITES_LIST, SPX_OVERLAY_LIST } from "@/mocks/data";
import { test, TEST_TIMEOUT } from "./shared/utils";

test("tenant change selects from the site's Spectrum-X overlays", async ({
  page,
}) => {
  const overlaysRequest = page.waitForRequest((request) =>
    request.url().includes("/v1/parameter/overlay")
  );

  await page.goto(
    "/workflows/spxoverlaytenantchangeworkflow/form" +
      `?site=${SITES_LIST.pdx01}` +
      `&overlay_id=${SPX_OVERLAY_LIST.primary}`
  );

  const request = await overlaysRequest;
  expect(new URL(request.url()).searchParams.get("location")).toBe(
    SITES_LIST.pdx01
  );
  expect(new URL(request.url()).searchParams.get("isolation_type")).toBe(
    "spectrum_x_vrf"
  );
  await expect(
    page.getByRole("button", {
      name: SPX_OVERLAY_LIST.primary,
      exact: true,
    })
  ).toBeVisible({ timeout: TEST_TIMEOUT });

  await page
    .getByRole("button", {
      name: SPX_OVERLAY_LIST.primary,
      exact: true,
    })
    .click();
  await expect(
    page.getByRole("dialog").getByText(SPX_OVERLAY_LIST.secondary)
  ).toBeVisible();
});
