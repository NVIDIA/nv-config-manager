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
import { Page } from "@playwright/test";

const mockWorkflowWithUnreachableStages = {
  id: "test-unreachable-workflow",
  workflow_type: "Test Workflow",
  status: "COMPLETED",
  workflow_input: {},
  started_by: "test-user",
  start_time: "2025-01-01T00:00:00Z",
  close_time: "2025-01-01T01:00:00Z",
  pending_approval: false,
  search_attributes: {},
  href: "https://test.com/workflow/test-unreachable-workflow",
  result: null,
  stages: [
    {
      name: "stage1",
      description: "Visible Stage 1 - Complete",
      requires_approval: false,
      state: "COMPLETE",
      output: {},
      depends_on: [],
      approvers: [],
      rejecters: [],
      approval_threshold: 0,
      state_history: [
        {
          state: "NOT_STARTED",
          time: "2025-01-01T00:00:00Z",
        },
        {
          state: "IN_PROGRESS",
          time: "2025-01-01T00:10:00Z",
        },
        {
          state: "COMPLETE",
          time: "2025-01-01T00:20:00Z",
        },
      ],
      retryable: true,
      retry_count: 0,
      traceback: null,
      execution_time: 600,
    },
    {
      name: "stage2",
      description: "UNREACHABLE Stage - Should be Hidden",
      requires_approval: false,
      state: "UNREACHABLE",
      output: {},
      depends_on: ["stage1"],
      approvers: [],
      rejecters: [],
      approval_threshold: 0,
      state_history: [
        {
          state: "NOT_STARTED",
          time: "2025-01-01T00:00:00Z",
        },
        {
          state: "UNREACHABLE",
          time: "2025-01-01T00:25:00Z",
        },
      ],
      retryable: false,
      retry_count: 0,
      traceback: null,
      execution_time: null,
    },
    {
      name: "stage3",
      description: "Visible Stage 2 - Failed",
      requires_approval: false,
      state: "FAILED",
      output: {},
      depends_on: ["stage1"],
      approvers: [],
      rejecters: [],
      approval_threshold: 0,
      state_history: [
        {
          state: "NOT_STARTED",
          time: "2025-01-01T00:00:00Z",
        },
        {
          state: "IN_PROGRESS",
          time: "2025-01-01T00:30:00Z",
        },
        {
          state: "FAILED",
          time: "2025-01-01T00:40:00Z",
        },
      ],
      retryable: true,
      retry_count: 1,
      traceback: "Error: Test failure",
      execution_time: 600,
    },
    {
      name: "stage4",
      description: "Another UNREACHABLE Stage - Should be Hidden",
      requires_approval: false,
      state: "UNREACHABLE",
      output: {},
      depends_on: ["stage3"],
      approvers: [],
      rejecters: [],
      approval_threshold: 0,
      state_history: [
        {
          state: "NOT_STARTED",
          time: "2025-01-01T00:00:00Z",
        },
        {
          state: "UNREACHABLE",
          time: "2025-01-01T00:41:00Z",
        },
      ],
      retryable: false,
      retry_count: 0,
      traceback: null,
      execution_time: null,
    },
    {
      name: "stage5",
      description: "Visible Stage 3 - In Progress",
      requires_approval: false,
      state: "IN_PROGRESS",
      output: {},
      depends_on: [],
      approvers: [],
      rejecters: [],
      approval_threshold: 0,
      state_history: [
        {
          state: "NOT_STARTED",
          time: "2025-01-01T00:00:00Z",
        },
        {
          state: "IN_PROGRESS",
          time: "2025-01-01T00:45:00Z",
        },
      ],
      retryable: true,
      retry_count: 0,
      traceback: null,
      execution_time: null,
    },
  ],
};

// Mock workflow with all stages UNREACHABLE
const mockWorkflowAllUnreachable = {
  ...mockWorkflowWithUnreachableStages,
  id: "test-all-unreachable-workflow",
  stages: mockWorkflowWithUnreachableStages.stages.map((stage) => ({
    ...stage,
    state: "UNREACHABLE",
    state_history: [
      {
        state: "NOT_STARTED",
        time: "2025-01-01T00:00:00Z",
      },
      {
        state: "UNREACHABLE",
        time: "2025-01-01T00:10:00Z",
      },
    ],
  })),
};

async function mockWorkflowEndpoint(page: Page, workflowData: any) {
  await page.route(`**/v1/workflow/${workflowData.id}`, async (route) => {
    await route.fulfill({
      status: 200,
      json: workflowData,
    });
  });
}

test.describe("Stage List - UNREACHABLE State Filtering", () => {
  test("should hide stages with UNREACHABLE state", async ({ page }) => {
    // Set up mock for workflow with mixed states
    await mockWorkflowEndpoint(page, mockWorkflowWithUnreachableStages);

    // Navigate to the workflow detail page
    await page.goto(`/workflows/${mockWorkflowWithUnreachableStages.id}`);

    // Wait for the page to load
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible();

    // Check that visible stages are displayed
    await expect(
      page.getByRole("cell", { name: /Visible Stage 1 - Complete/ })
    ).toBeVisible();
    await expect(
      page.getByRole("cell", { name: /Visible Stage 2 - Failed/ })
    ).toBeVisible();
    await expect(
      page.getByRole("cell", { name: /Visible Stage 3 - In Progress/ })
    ).toBeVisible();

    // Verify that UNREACHABLE stages are NOT displayed
    await expect(
      page.getByRole("cell", { name: /UNREACHABLE Stage - Should be Hidden/ })
    ).not.toBeVisible();
    await expect(
      page.getByRole("cell", {
        name: /Another UNREACHABLE Stage - Should be Hidden/,
      })
    ).not.toBeVisible();

    // Verify status badges for visible stages
    const completeStageCell = page.getByRole("cell", {
      name: /Visible Stage 1 - Complete/,
    });
    await expect(
      completeStageCell.getByText("COMPLETE", { exact: true })
    ).toBeVisible();

    const failedStageCell = page.getByRole("cell", {
      name: /Visible Stage 2 - Failed/,
    });
    await expect(
      failedStageCell.getByText("FAILED", { exact: true })
    ).toBeVisible();

    const inProgressStageCell = page.getByRole("cell", {
      name: /Visible Stage 3 - In Progress/,
    });
    await expect(
      inProgressStageCell.getByText("IN_PROGRESS", { exact: true })
    ).toBeVisible();
  });

  test("should display 'No Stages' when all stages are UNREACHABLE", async ({
    page,
  }) => {
    // Set up mock for workflow with all UNREACHABLE stages
    await mockWorkflowEndpoint(page, mockWorkflowAllUnreachable);

    // Navigate to the workflow detail page
    await page.goto(`/workflows/${mockWorkflowAllUnreachable.id}`);

    // Wait for the page to load
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible();

    // Check that "No Stages" message is displayed in the left panel
    await expect(page.getByRole("cell", { name: "No Stages" })).toBeVisible();

    // Verify that no stage descriptions are visible (look for actual stage names)
    await expect(
      page.getByRole("cell", { name: /Visible Stage/ })
    ).not.toBeVisible();

    // Check that the right panel shows "No Stages Available"
    await expect(
      page.getByRole("heading", { name: "No Stages Available" })
    ).toBeVisible();
  });

  test("should handle stage selection correctly with filtered stages", async ({
    page,
  }) => {
    // Set up mock for workflow with mixed states
    await mockWorkflowEndpoint(page, mockWorkflowWithUnreachableStages);

    // Navigate to the workflow detail page
    await page.goto(`/workflows/${mockWorkflowWithUnreachableStages.id}`);

    // Wait for the page to load
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible();

    // Wait for initial selection to be applied (should be IN_PROGRESS stage based on getInitialStage priority)
    const inProgressStageCell = page.getByRole("cell", {
      name: /Visible Stage 3 - In Progress/,
    });
    const inProgressStageRow = page
      .getByRole("row")
      .filter({ has: inProgressStageCell });

    // Verify initial selection is on IN_PROGRESS stage
    await page.waitForTimeout(500);
    const initialRowClasses = await inProgressStageRow.getAttribute("class");
    expect(initialRowClasses).toContain("bg-blue-100");

    // Click on the Failed stage
    const failedStageCell = page.getByRole("cell", {
      name: /Visible Stage 2 - Failed/,
    });
    await failedStageCell.click();

    // Wait for the selection to update
    await page.waitForTimeout(200);

    // Verify that the clicked stage has the selected styling (blue background)
    const failedStageRow = page
      .getByRole("row")
      .filter({ has: failedStageCell });
    const failedRowClasses = await failedStageRow.getAttribute("class");
    expect(failedRowClasses).toContain("bg-blue-100");

    // Verify previous selection is no longer highlighted
    const inProgressRowClassesAfter = await inProgressStageRow.getAttribute(
      "class"
    );
    expect(inProgressRowClassesAfter).not.toContain("bg-blue-100");

    // Click on the Complete stage
    const completeStageCell = page.getByRole("cell", {
      name: /Visible Stage 1 - Complete/,
    });
    await completeStageCell.click();

    // Wait for the selection to update
    await page.waitForTimeout(200);

    // Verify selection moved to the complete stage
    const completeStageRow = page
      .getByRole("row")
      .filter({ has: completeStageCell });
    const completeRowClasses = await completeStageRow.getAttribute("class");
    expect(completeRowClasses).toContain("bg-blue-100");

    // Verify previous selection is no longer highlighted
    const failedRowClassesAfter = await failedStageRow.getAttribute("class");
    expect(failedRowClassesAfter).not.toContain("bg-blue-100");
  });

  test("should correctly count only visible stages", async ({ page }) => {
    // Set up mock for workflow with mixed states
    await mockWorkflowEndpoint(page, mockWorkflowWithUnreachableStages);

    // Navigate to the workflow detail page
    await page.goto(`/workflows/${mockWorkflowWithUnreachableStages.id}`);

    // Wait for the page to load
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible();

    // Count the number of stage rows (should be 3, not 5)
    const stageCells = page
      .getByRole("cell")
      .filter({ hasText: /Visible Stage/ });
    await expect(stageCells).toHaveCount(3);

    // Verify no UNREACHABLE text is visible anywhere in the stages table
    const stageTable = page.getByRole("table");
    await expect(stageTable).not.toContainText("UNREACHABLE");
  });

  test("should not display UNREACHABLE stage details in right panel", async ({
    page,
  }) => {
    // Set up mock for workflow with mixed states
    await mockWorkflowEndpoint(page, mockWorkflowWithUnreachableStages);

    // Navigate to the workflow detail page
    await page.goto(`/workflows/${mockWorkflowWithUnreachableStages.id}`);

    // Wait for the page to load
    await expect(
      page.getByRole("heading", { name: "Workflow Details" })
    ).toBeVisible();

    // Verify the right panel shows details of a visible stage, not an UNREACHABLE one
    const rightPanel = page.locator(".justify-center.p-6");

    // Check that the right panel doesn't contain UNREACHABLE stage descriptions
    await expect(rightPanel).not.toContainText(
      "UNREACHABLE Stage - Should be Hidden"
    );
    await expect(rightPanel).not.toContainText(
      "Another UNREACHABLE Stage - Should be Hidden"
    );

    // Verify that the state badge in the right panel is not UNREACHABLE
    const stateBadges = rightPanel.locator(".badge");
    for (const badge of await stateBadges.all()) {
      const text = await badge.textContent();
      expect(text).not.toBe("UNREACHABLE");
    }
  });
});
