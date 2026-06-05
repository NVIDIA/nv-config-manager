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
import { test } from "./shared/utils";

test.describe("Workflows Page", () => {
  test("logout uses a relative provider logout redirect", async ({ request }) => {
    const response = await request.get("/auth/logout", { maxRedirects: 0 });

    expect(response.status()).toBe(302);
    expect(response.headers().location).toBe("/oauth2/logout");
  });

  test("renders a unified metadata-backed workflow table", async ({ page }) => {
    await page.goto("/workflows?workflow_type=DeployWorkflow");

    await expect(
      page.getByRole("heading", { name: "Workflows" })
    ).toBeVisible();
    await expect(
      page.getByText("New Workflow", { exact: true })
    ).toHaveCount(0);

    await expect(
      page.getByRole("cell", { name: "Configuration Deploy" })
    ).toBeVisible();
    await expect(page.getByText("LEAF2-GP1-CIN2-PDX01")).toBeVisible();
    const tableHeader = page.locator("thead");
    await expect(tableHeader.getByText("Roles")).toHaveCount(0);
    await expect(tableHeader.getByText("Device ID")).toHaveCount(0);
    await expect(tableHeader.getByText("Device Role")).toHaveCount(0);
    await expect(tableHeader.getByText("Device Platform")).toHaveCount(0);

    await page.getByRole("button", { name: "Columns" }).click();
    await page
      .getByRole("checkbox", { name: "Toggle Device ID column" })
      .click();
    await expect(tableHeader.getByText("Device ID")).toBeVisible();
  });

  test("shows user roles and disables workflows the user cannot execute", async ({
    page,
  }) => {
    await page.goto("/workflows?workflow_type=DeployWorkflow");

    await page.getByRole("button", { name: "User roles" }).click();
    await expect(page.getByText("Username", { exact: true })).toBeVisible();
    await expect(page.getByText("joliao@nvidia.com")).toBeVisible();
    await expect(page.getByText("Roles", { exact: true })).toBeVisible();
    await expect(page.getByText("nvcm-network")).toBeVisible();
    await expect(page.getByRole("link", { name: "Logout" })).toHaveAttribute(
      "href",
      "/auth/logout"
    );

    await page.getByRole("button", { name: "New workflow" }).click();
    await expect(
      page.getByRole("link", { name: "Config Deploy" })
    ).toBeVisible();
    await expect(page.getByRole("link", { name: "Multi-Deploy" })).toHaveCount(0);

    await page.getByText("Multi-Deploy").hover();
    await expect(
      page.getByRole("tooltip", {
        name: "Required execute roles: nvcm-admin",
      })
    ).toBeVisible();
  });

  test("keeps rows visible when loading the next backend page", async ({
    page,
  }) => {
    await page.goto("/workflows");

    await expect(page.getByText("LEAF1-GP1-CIN2-PDX01").first()).toBeVisible();
    await page.getByRole("button", { exact: true, name: "Next" }).click();

    await expect(page.getByText("Page 2")).toBeVisible();
    await expect(page.getByText("More pages available")).toBeVisible();
    await expect(page.getByText("Port LLDP Info").first()).toBeVisible();
  });

  test("supports value filter icons through workflow list filters", async ({
    page,
  }) => {
    await page.goto("/workflows?workflow_type=DeployWorkflow");

    await page
      .getByRole("link", {
        name: "Filter by Device Name: LEAF2-GP1-CIN2-PDX01",
      })
      .click();

    await expect(page).toHaveURL(/device_name=LEAF2-GP1-CIN2-PDX01/);
    await expect(page.getByText("LEAF2-GP1-CIN2-PDX01")).toBeVisible();

    await expect(
      page.getByRole("link", {
        name: "Filter by Device Name: LEAF2-GP1-CIN2-PDX01",
      })
    ).toHaveCSS("border-bottom-width", "0px");
  });

  test("hydrates status filters from the URL", async ({ page }) => {
    await page.goto("/workflows?status=FAILED");

    await expect(page.getByText("Device Cable Validation")).toBeVisible();
    await expect(page.getByText("LEAF2-GP1-CIN3-PDX01")).toBeVisible();
    await expect(
      page.locator("tbody").getByText("Failed", { exact: true })
    ).toBeVisible();
  });

  test("supports dropdown filters and clearing all filters", async ({ page }) => {
    await page.goto("/workflows");

    await page
      .locator("thead")
      .getByRole("cell", { name: /Status/ })
      .getByRole("combobox")
      .click();
    await page.getByRole("option", { name: "Failed" }).click();

    await expect(page.getByText("Device Cable Validation")).toBeVisible();
    await expect(page.getByText("LEAF2-GP1-CIN3-PDX01")).toBeVisible();

    await page.getByRole("button", { name: "Clear All Filters" }).click();
    await expect(page.getByText("LEAF1-GP1-CIN2-PDX01").first()).toBeVisible();

    const pendingApprovalResponse = page.waitForResponse((response) => {
      const url = new URL(response.url());

      return (
        url.pathname.endsWith("/v1/workflow/") &&
        url.searchParams.get("status") === "RUNNING" &&
        url.searchParams.get("pending_approval") === "true"
      );
    });
    await page
      .locator("thead")
      .getByRole("cell", { name: /Status/ })
      .getByRole("combobox")
      .click();
    await page.getByRole("option", { name: "Pending Approval" }).click();
    await pendingApprovalResponse;

    await page.getByRole("button", { name: "Clear All Filters" }).click();
    await expect(page.getByText("LEAF1-GP1-CIN2-PDX01").first()).toBeVisible();

    await page.goto("/workflows?status=FAILED");
    await expect(page.getByText("Device Cable Validation")).toBeVisible();
    await page.getByRole("button", { name: "Clear All Filters" }).click();

    await expect(page).toHaveURL(/\/workflows$/);
    await expect(page.getByText("LEAF1-GP1-CIN2-PDX01").first()).toBeVisible();
  });

  test("supports top-level workflow timeframe filters", async ({ page }) => {
    await page.goto("/workflows");

    await expect(page.getByText("LEAF1-GP1-CIN2-PDX01").first()).toBeVisible();

    const tableHeader = page.locator("thead");
    await expect(
      tableHeader
        .locator("th")
        .filter({ hasText: "Start Time" })
        .getByRole("textbox")
    ).toHaveCount(0);
    await expect(
      tableHeader
        .locator("th")
        .filter({ hasText: "End Time" })
        .getByRole("textbox")
    ).toHaveCount(0);

    const timeframe = await page.evaluate(() => {
      const pad = (value: number) => String(value).padStart(2, "0");
      const formatLocalDateTime = (value: string) => {
        const date = new Date(value);

        return {
          date: `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(
            date.getDate()
          )}`,
          time: `${pad(date.getHours())}:${pad(date.getMinutes())}`,
        };
      };

      return {
        end: formatLocalDateTime("2025-03-04T02:34:00Z"),
        start: formatLocalDateTime("2025-03-04T02:32:00Z"),
      };
    });

    await page.getByLabel("Start date").fill(timeframe.start.date);
    await page.getByLabel("Start time").fill(timeframe.start.time);
    await page.getByLabel("End date").fill(timeframe.end.date);
    await page.getByLabel("End time").fill(timeframe.end.time);

    await expect(page.getByText("Connected Host Metadata")).toBeVisible();
    await expect(
      page.getByRole("cell", { name: "Configuration Backup" })
    ).toHaveCount(0);
    await expect(page.getByRole("cell", { name: "VPC Creation" })).toHaveCount(0);
  });

  test("keeps workflow id column width stable with no results", async ({
    page,
  }) => {
    await page.goto("/workflows");

    const workflowIdHeader = page.locator("thead th").first();
    await expect(page.getByText("LEAF1-GP1-CIN2-PDX01").first()).toBeVisible();
    await expect(workflowIdHeader).toBeVisible();

    const initialBox = await workflowIdHeader.boundingBox();
    const initialWidth = initialBox?.width ?? 0;
    expect(initialWidth).toBeGreaterThan(280);

    await page
      .locator("thead")
      .getByRole("textbox", { name: "Search..." })
      .first()
      .fill("not-a-real-workflow-id");
    await expect(page.getByText("No results.")).toBeVisible();

    const emptyBox = await workflowIdHeader.boundingBox();
    expect(emptyBox?.width ?? 0).toBeCloseTo(initialWidth, 0);

    await page.getByRole("button", { name: "Clear All Filters" }).click();
    await expect(page.getByText("LEAF1-GP1-CIN2-PDX01").first()).toBeVisible();

    const restoredBox = await workflowIdHeader.boundingBox();
    expect(restoredBox?.width ?? 0).toBeCloseTo(initialWidth, 0);
  });

  test("persists the selected row count", async ({ page }) => {
    await page.goto("/workflows");

    await expect(page.getByText("LEAF1-GP1-CIN2-PDX01").first()).toBeVisible();

    await page.getByRole("combobox").filter({ hasText: "10 Rows" }).click();
    await page.getByRole("option", { name: "50 Rows" }).click();
    await expect(
      page.getByRole("combobox").filter({ hasText: "50 Rows" })
    ).toBeVisible();

    await page.reload();

    await expect(
      page.getByRole("combobox").filter({ hasText: "50 Rows" })
    ).toBeVisible();
  });
});
