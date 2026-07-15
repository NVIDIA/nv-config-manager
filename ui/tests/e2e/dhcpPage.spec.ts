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

  test("displays DHCP lease activity, reservations, and pools", async ({
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
    const unconfiguredSubnet = dashboard
      .getByRole("row")
      .filter({ hasText: "leaf-02" })
      .getByText("Removed", { exact: true });
    await expect(unconfiguredSubnet).toBeVisible();
    await expect(unconfiguredSubnet).toHaveAttribute(
      "title",
      "This lease's subnet ID is not present in the current DHCP configuration."
    );
    await expect(
      dashboard.getByText("Config age", { exact: true })
    ).toBeVisible();
    await expect(dashboard.getByText("4m", { exact: true })).toBeVisible();
    await expect(
      dashboard.getByText("Loaded 2 active leases · All active leases loaded", {
        exact: true,
      })
    ).toBeVisible();

    await dashboard.getByRole("tab", { name: "Reservations" }).click();
    await expect(dashboard.getByText("spine-01")).toBeVisible();
    await expect(
      dashboard.getByText("Loaded 2 of 2 reservations", { exact: true })
    ).toBeVisible();

    await dashboard.getByRole("tab", { name: "Pools" }).click();
    await expect(dashboard.getByText("10.0.0.10-10.0.0.19")).toBeVisible();
    await expect(
      dashboard.getByText("Loaded 1 of 1 pools", { exact: true })
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

  test("loads additional lease pages on scroll and resets cursors for search", async ({
    page,
  }) => {
    let releaseNextPage!: () => void;
    const nextPageGate = new Promise<void>((resolve) => {
      releaseNextPage = resolve;
    });
    await page.unroute("**/lease?*");
    await page.route("**/lease?*", async (route) => {
      const params = new URL(route.request().url()).searchParams;
      const cursor = params.get("cursor");
      const search = params.get("search");
      expect(params.get("limit")).toBe("100");
      if (cursor) await nextPageGate;
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
          next_cursor: search || cursor ? null : "next-page",
        },
      });
    });
    await page.reload();

    const dashboard = page.getByTestId("dhcp-dashboard");
    await expect(dashboard.getByText("leaf-01")).toBeVisible();
    const activeLeasesMetric = dashboard.getByRole("group", {
      name: "Active leases",
    });
    await expect(
      activeLeasesMetric.getByText("2", { exact: true })
    ).toBeVisible();
    await expect(
      activeLeasesMetric.getByText("Current active allocations", {
        exact: true,
      })
    ).toBeVisible();
    releaseNextPage();
    await expect(dashboard.getByText("leaf-02")).toBeVisible();
    await expect(
      activeLeasesMetric.getByText("2", { exact: true })
    ).toBeVisible();
    await expect(
      activeLeasesMetric.getByText("Current active allocations", {
        exact: true,
      })
    ).toBeVisible();
    await expect(
      dashboard.getByText("Loaded 2 active leases · All active leases loaded", {
        exact: true,
      })
    ).toBeVisible();
    const searchRequestPromise = page.waitForRequest((request) => {
      const url = new URL(request.url());
      return (
        url.pathname === "/lease" && url.searchParams.get("search") === "leaf"
      );
    });
    await dashboard
      .getByRole("searchbox", { name: "Filter displayed DHCP data" })
      .fill("leaf");
    const searchRequest = await searchRequestPromise;
    expect(new URL(searchRequest.url()).searchParams.get("cursor")).toBeNull();
    await expect(dashboard.getByText("leaf-01")).toBeVisible();
    await expect(
      dashboard.getByText(
        "Loaded 1 matching active leases · All matches loaded",
        {
          exact: true,
        }
      )
    ).toBeVisible();
  });

  test("infinitely loads reservations and pools with exact totals", async ({
    page,
  }) => {
    await page.unroute("**/reservations?*");
    await page.route("**/reservations?*", async (route) => {
      const params = new URL(route.request().url()).searchParams;
      const cursor = params.get("cursor");
      expect(params.get("limit")).toBe("100");
      await route.fulfill({
        status: 200,
        json: {
          reservations: [
            {
              ip_address: cursor ? "10.0.0.3" : "10.0.0.2",
              hostname: cursor ? "spine-02" : "spine-01",
              identifier_type: "hw-address",
              identifier: cursor ? "02:00:00:00:00:02" : "02:00:00:00:00:01",
            },
          ],
          total_count: 2,
          next_cursor: cursor ? null : "next-reservation-page",
        },
      });
    });
    await page.unroute("**/pools?*");
    await page.route("**/pools?*", async (route) => {
      const params = new URL(route.request().url()).searchParams;
      const cursor = params.get("cursor");
      expect(params.get("limit")).toBe("100");
      await route.fulfill({
        status: 200,
        json: {
          pools: [
            {
              subnet: cursor ? "10.0.1.0/24" : "10.0.0.0/24",
              pool: cursor ? "10.0.1.10-10.0.1.19" : "10.0.0.10-10.0.0.19",
            },
          ],
          total_count: 2,
          next_cursor: cursor ? null : "next-pool-page",
        },
      });
    });

    const dashboard = page.getByTestId("dhcp-dashboard");
    await dashboard.getByRole("tab", { name: "Reservations" }).click();
    await expect(dashboard.getByText("spine-01")).toBeVisible();
    await expect(dashboard.getByText("spine-02")).toBeVisible();
    await expect(
      dashboard.getByText("Loaded 2 of 2 reservations", { exact: true })
    ).toBeVisible();

    await dashboard.getByRole("tab", { name: "Pools" }).click();
    await expect(dashboard.getByText("10.0.0.10-10.0.0.19")).toBeVisible();
    await expect(dashboard.getByText("10.0.1.10-10.0.1.19")).toBeVisible();
    await expect(
      dashboard.getByText("Loaded 2 of 2 pools", { exact: true })
    ).toBeVisible();
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
