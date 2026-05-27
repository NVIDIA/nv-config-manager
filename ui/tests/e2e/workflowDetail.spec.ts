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
import { FORBIDDEN_WORKFLOW_ID } from "@/mocks/data";

test.describe("Workflow Detail Page", () => {
  test("Test workflow detail page loads correctly", async ({ page }) => {
    await page.goto("/workflows/some-workflow-id");

    // Check for the main heading
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible();

    // Check for the Stages section by text content
    await expect(page.getByText("Stages")).toBeVisible();

    // Check for the stage details in the table using role
    const stageCell = page.getByRole("cell", {
      name: /Get the list of devices to validate for this site/,
    });
    await expect(stageCell).toBeVisible();

    // Check for the stage status badge within the cell
    await expect(
      stageCell.getByText("COMPLETE", { exact: true })
    ).toBeVisible();
  });

  test("displays stage details correctly", async ({ page }) => {
    await page.goto("/workflows/some-workflow-id");

    // Check the stage table structure
    const stageTable = page.getByRole("table");
    await expect(stageTable).toBeVisible();

    // Verify stage description in table cell
    const stageCell = page.getByRole("cell", {
      name: /Get the list of devices to validate for this site/,
    });
    await expect(stageCell).toBeVisible();

    // Verify stage status within the cell
    const statusBadge = stageCell.getByText("COMPLETE", { exact: true });
    await expect(statusBadge).toBeVisible();
  });

  test("displays forbidden error page when accessing unauthorized workflow", async ({
    page,
  }) => {
    await page.goto(`/workflows/${FORBIDDEN_WORKFLOW_ID}`);

    // Check for error heading in the card
    await expect(
      page.getByRole("heading", { name: "Access Denied", level: 3 })
    ).toBeVisible();

    // Check for alert section with error content
    const alert = page.getByRole("alert").filter({
      has: page.getByText(
        "You do not have permission to access this resource."
      ),
    });
    await expect(alert).toBeVisible();

    // Check alert contents
    await expect(
      alert.getByRole("heading", { name: "Access Denied", level: 5 })
    ).toBeVisible();
    await expect(
      alert.getByText("You do not have permission to access this resource.")
    ).toBeVisible();

    // Check for action buttons
    const tryAgainButton = page.getByRole("button", { name: "Try Again" });
    await expect(tryAgainButton).toBeVisible();
    await expect(tryAgainButton).toHaveClass(/bg-primary/);

    // Check for workflows link
    const workflowsLink = page.getByRole("link", { name: "Go to Workflows" });
    await expect(workflowsLink).toBeVisible();
    await expect(workflowsLink).toHaveAttribute("href", "/workflows");

    // Click try again and verify we're still on error page (since it's forbidden)
    await tryAgainButton.click();
    await expect(
      page.getByRole("heading", { name: "Access Denied", level: 3 })
    ).toBeVisible();
  });
});
