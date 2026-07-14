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

test.describe("DHCP Dashboard Page", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/dhcp");
  });

  test("displays DHCP lease activity, reservations, and pool usage", async ({
    page,
  }) => {
    const dashboard = page.getByTestId("dhcp-dashboard");
    await expect(
      dashboard.getByRole("heading", { name: "DHCP lease activity" })
    ).toBeVisible({ timeout: TEST_TIMEOUT });
    const activeLeasesMetric = dashboard.getByRole("group", {
      name: "Active leases",
    });
    await expect(
      activeLeasesMetric.getByText("Active leases", { exact: true })
    ).toBeVisible();
    await expect(
      activeLeasesMetric.getByText("2", { exact: true })
    ).toBeVisible();
    await expect(dashboard.getByText("leaf-01")).toBeVisible();
    await expect(
      dashboard
        .getByRole("row")
        .filter({ hasText: "leaf-01" })
        .getByText("10.0.0.0/24", { exact: true })
    ).toBeVisible();
    await expect(
      dashboard.getByText("Config age", { exact: true })
    ).toBeVisible();
    await expect(dashboard.getByText("4m", { exact: true })).toBeVisible();
    await expect(dashboard.getByText("Page 1", { exact: true })).toBeVisible();

    await dashboard.getByRole("tab", { name: "Reservations" }).click();
    await expect(dashboard.getByText("spine-01")).toBeVisible();

    await dashboard.getByRole("tab", { name: "Pool usage" }).click();
    await expect(dashboard.getByText("10.0.0.10-10.0.0.19")).toBeVisible();
    await expect(
      dashboard.getByText("20.0%", { exact: true }).last()
    ).toBeVisible();
  });

  test("clears a DHCP lease after confirmation", async ({ page }) => {
    const dashboard = page.getByTestId("dhcp-dashboard");
    await expect(dashboard.getByText("10.0.0.10")).toBeVisible({
      timeout: TEST_TIMEOUT,
    });

    await dashboard
      .getByRole("button", { name: "Clear lease 10.0.0.10" })
      .click();
    const dialog = page.getByRole("dialog", { name: "Clear DHCP lease?" });
    await expect(dialog).toBeVisible();
    await dialog.getByRole("button", { name: "Clear lease" }).click();

    await expect(
      page.getByText("Lease cleared", { exact: true })
    ).toBeVisible();
    await expect(dashboard.getByText("10.0.0.10")).toHaveCount(0);
  });

  test("shows one fixed-size lease page with previous and next controls", async ({
    page,
  }) => {
    await page.unroute("**/leases?*");
    await page.route("**/leases?*", async (route) => {
      const params = new URL(route.request().url()).searchParams;
      const cursor = params.get("cursor");
      expect(params.get("limit")).toBe("100");
      await route.fulfill({
        status: 200,
        json: {
          leases: [
            {
              ip_address: cursor ? "10.0.0.11" : "10.0.0.10",
              hostname: cursor ? "leaf-02" : "leaf-01",
              hw_address: cursor ? "02:00:00:00:00:11" : "02:00:00:00:00:10",
              subnet: "10.0.0.0/24",
              state: 0,
              cltt: 1783700000,
              valid_lft: 7200,
              expires_at: "2026-07-10T18:00:00Z",
            },
          ],
          next_cursor: cursor ? null : "next-page",
        },
      });
    });
    await page.reload();

    const dashboard = page.getByTestId("dhcp-dashboard");
    const pagination = dashboard.getByRole("navigation", {
      name: "Lease pages",
    });
    await expect(dashboard.getByText("leaf-01")).toBeVisible();
    await expect(dashboard.getByText("leaf-02")).toHaveCount(0);
    await expect(
      pagination.getByRole("button", { name: "Previous" })
    ).toBeDisabled();

    await pagination.getByRole("button", { name: "Next" }).click();
    await expect(dashboard.getByText("leaf-02")).toBeVisible();
    await expect(dashboard.getByText("leaf-01")).toHaveCount(0);
    await expect(pagination.getByText("Page 2", { exact: true })).toBeVisible();
    await expect(
      pagination.getByRole("button", { name: "Next" })
    ).toBeDisabled();

    await pagination.getByRole("button", { name: "Previous" }).click();
    await expect(dashboard.getByText("leaf-01")).toBeVisible();
    await expect(dashboard.getByText("leaf-02")).toHaveCount(0);
    await expect(pagination.getByText("Page 1", { exact: true })).toBeVisible();

    await pagination.getByRole("button", { name: "Next" }).click();
    await expect(dashboard.getByText("leaf-02")).toBeVisible();
    const searchRequestPromise = page.waitForRequest((request) => {
      const url = new URL(request.url());
      return (
        url.pathname === "/leases" && url.searchParams.get("search") === "leaf"
      );
    });
    await dashboard
      .getByRole("searchbox", { name: "Filter displayed DHCP data" })
      .fill("leaf");
    const searchRequest = await searchRequestPromise;
    expect(new URL(searchRequest.url()).searchParams.get("cursor")).toBeNull();
    await expect(pagination.getByText("Page 1", { exact: true })).toBeVisible();
    await expect(dashboard.getByText("leaf-01")).toBeVisible();
  });

  test("keeps lease data available when config age metrics fail", async ({
    page,
  }) => {
    await page.route("**/metrics", async (route) => {
      await route.fulfill({ status: 503, json: { detail: "unavailable" } });
    });
    await page.reload();

    const dashboard = page.getByTestId("dhcp-dashboard");
    await expect(dashboard.getByText("leaf-01")).toBeVisible({
      timeout: TEST_TIMEOUT,
    });
    await expect(
      dashboard.getByText("Config age", { exact: true })
    ).toBeVisible();
    await expect(dashboard.getByText("Unknown", { exact: true })).toBeVisible();
  });

  test("filters displayed DHCP data across tabs", async ({ page }) => {
    const dashboard = page.getByTestId("dhcp-dashboard");
    const search = dashboard.getByRole("searchbox", {
      name: "Filter displayed DHCP data",
    });
    await search.fill("spine-01");

    await expect(
      dashboard.getByText("No active leases match “spine-01”.")
    ).toBeVisible();
    await dashboard.getByRole("tab", { name: "Reservations" }).click();
    await expect(dashboard.getByText("spine-01")).toBeVisible();
    await expect(dashboard.getByText("spine-02")).toHaveCount(0);
  });

  test("matches MAC addresses without separators or in dotted format", async ({
    page,
  }) => {
    const dashboard = page.getByTestId("dhcp-dashboard");
    const search = dashboard.getByRole("searchbox", {
      name: "Filter displayed DHCP data",
    });

    await search.fill("020000000010");
    await expect(dashboard.getByText("leaf-01")).toBeVisible();
    await expect(dashboard.getByText("leaf-02")).toHaveCount(0);

    await search.fill("0200.0000.0010");
    await expect(dashboard.getByText("leaf-01")).toBeVisible();
    await expect(dashboard.getByText("leaf-02")).toHaveCount(0);

    await dashboard.getByRole("tab", { name: "Reservations" }).click();
    await search.fill("020000000001");
    await expect(dashboard.getByText("spine-01")).toBeVisible();
    await expect(dashboard.getByText("spine-02")).toHaveCount(0);

    await search.fill("0200.0000.0001");
    await expect(dashboard.getByText("spine-01")).toBeVisible();
    await expect(dashboard.getByText("spine-02")).toHaveCount(0);
  });
});
