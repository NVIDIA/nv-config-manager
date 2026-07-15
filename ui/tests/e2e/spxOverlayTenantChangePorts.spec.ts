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
import { DEVICES_LIST, SITES_LIST } from "@/mocks/data";
import { test, TEST_TIMEOUT } from "./shared/utils";

test("queries the selected device ports and supports multiple selections", async ({
  page,
}) => {
  await page.goto("/workflows/spxoverlaytenantchangeworkflow/form");

  await page.getByRole("button", { name: "Site" }).click();
  await page.getByRole("dialog").getByText(SITES_LIST.pdx01).click();

  const firstDevice = DEVICES_LIST.PDX01[0];
  const interfaceRequest = page.waitForRequest((request) =>
    request.url().includes(`/v1/parameter/device/${firstDevice.id}/interfaces`)
  );
  await page.getByRole("button", { name: "Device" }).click();
  await page.getByRole("dialog").getByText(firstDevice.name).click();
  await interfaceRequest;

  await page.getByRole("button", { name: "Ports" }).click();
  await page.getByRole("dialog").getByText("swp1").click();
  await page.getByRole("dialog").getByText("swp2").click();

  const ports = page.getByRole("button", { name: /swp1.*swp2/ });
  await expect(ports).toContainText("swp1", { timeout: TEST_TIMEOUT });
  await expect(ports).toContainText("swp2");
  await expect(page.getByRole("button", { name: "Submit" })).toBeEnabled();

  await page.getByRole("heading", {
    name: "New SpX Overlay Tenant Change Workflow",
  }).click();
  await page.getByRole("button", { name: firstDevice.name }).click();
  await page.getByRole("dialog").getByText(DEVICES_LIST.PDX01[1].name).click();

  await expect(page.getByRole("button", { name: "Submit" })).toBeDisabled();
});

test("loads device and port selections from URL parameters", async ({ page }) => {
  const device = DEVICES_LIST.PDX01[0];
  await page.goto(
    "/workflows/spxoverlaytenantchangeworkflow/form" +
      `?site=${SITES_LIST.pdx01}` +
      `&device-id=${device.id}` +
      "&port_names=swp1%2Cswp2"
  );

  await expect(
    page.getByRole("button", { name: device.name })
  ).toBeVisible({ timeout: TEST_TIMEOUT });
  await expect(
    page.getByRole("button", { name: /swp1.*swp2/ })
  ).toBeVisible({ timeout: TEST_TIMEOUT });
  await expect(page.getByRole("button", { name: "Submit" })).toBeEnabled();
});

test("rejects URL port selections that are not on the device", async ({ page }) => {
  const device = DEVICES_LIST.PDX01[0];
  await page.goto(
    "/workflows/spxoverlaytenantchangeworkflow/form" +
      `?site=${SITES_LIST.pdx01}` +
      `&device-id=${device.id}` +
      "&port_names=not-a-device-port"
  );

  await expect(
    page.getByRole("button", { name: device.name })
  ).toBeVisible({ timeout: TEST_TIMEOUT });
  await expect(page.getByRole("button", { name: "Submit" })).toBeDisabled();
  await expect(page.getByText("not-a-device-port")).toHaveCount(0);
});
