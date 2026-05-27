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
import { test as base } from "@playwright/test";
import { setupApiMocks } from "./apiMocks";

/**
 * Default timeout for test assertions in milliseconds.
 * Used for waiting for elements, navigation, etc.
 * Set to 10 seconds as a reasonable balance between:
 * - Fast failure detection in automated tests
 * - Enough time for real application operations
 */
export const TEST_TIMEOUT = 10000;

/**
 * Timeout for the "Workflow Details" heading after form submission.
 * Post-submit navigation and API responses can be slow in CI.
 */
export const WORKFLOW_DETAILS_TIMEOUT = 20000;

// Define a custom fixture with service workers disabled
export const test = base.extend({
  page: async ({ browser }, use) => {
    // Create a new context with service workers disabled
    const context = await browser.newContext({
      serviceWorkers: "block",
    });

    // Create a page from this context
    const page = await context.newPage();

    // Set up all API mocks
    await setupApiMocks(page);

    // Add this to bypass MSW initialization error
    await page.addInitScript(() => {
      window.BYPASS_MSW = true;
    });

    // Use this page for all tests
    await use(page);

    // Clean up after tests
    await context.close();
  },
});
