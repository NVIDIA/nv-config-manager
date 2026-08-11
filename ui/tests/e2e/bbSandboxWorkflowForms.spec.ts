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
import { expect, type Page } from "@playwright/test";

import { test } from "./shared/utils";

const choose = async (page: Page, label: string, value: string) => {
  await page.getByRole("button", { name: label }).click();
  await page.getByRole("dialog").last().getByText(value, { exact: true }).click();
};

test("BB drain form loads parameters and submits namespaced input", async ({ page }) => {
  await page.goto("/workflows/bbdraininterfaceworkflow/form");
  await expect(page.getByRole("heading", { name: "BB Sandbox: Drain Interface" })).toBeVisible();
  await choose(page, "Device", "SJC0C-BBR-01");
  await choose(page, "Interface", "et-0/0/0");
  await page.getByLabel("Jira (optional)").fill("BB-123");
  const requestPromise = page.waitForRequest((request) =>
    request.url().includes("/v1/workflow/bb_sandbox/drain_interface")
  );
  await page.getByRole("button", { name: "Review Drain" }).click();
  const request = await requestPromise;
  expect(JSON.parse((await request.postData()) || "{}")).toEqual({
    device: "bb-device-1",
    port: "et-0/0/0",
    jira: "BB-123",
  });
});

test("BB bringup form auto-fills Nautobot allocations and submits intent", async ({ page }) => {
  await page.goto("/workflows/bbinternalbackbonebringupworkflow/form");
  await expect(
    page.getByRole("heading", { name: "BB Sandbox: Internal Backbone Bringup" })
  ).toBeVisible();
  await choose(page, "Circuit", "BB-CIRCUIT-001 (Planned)");
  await page.getByLabel("Jira").fill("BB-456");
  await choose(page, "Local Device", "SJC0C-BBR-01");
  await choose(page, "Remote Device", "SJC0C-BBR-02");
  await choose(page, "Local Ports", "et-0/0/0");
  await choose(page, "Remote Ports", "et-0/0/1");
  await expect(page.getByLabel("LAG Name (optional)")).toHaveValue("ae103");
  await expect(page.getByLabel("IPv4 /31")).toHaveValue("192.0.2.2/31");
  await expect(page.getByLabel("IPv6 /127")).toHaveValue("2001:db8::2/127");

  const requestPromise = page.waitForRequest((request) =>
    request.url().includes("/v1/workflow/bb_sandbox/internal_backbone_bringup")
  );
  await page.getByRole("button", { name: "Start Staged Bringup" }).click();
  const request = await requestPromise;
  expect(JSON.parse((await request.postData()) || "{}")).toMatchObject({
    circuit_id: "BB-CIRCUIT-001",
    jira: "BB-456",
    local_device: "bb-device-1",
    local_ports: ["et-0/0/0"],
    remote_device: "bb-device-2",
    remote_ports: ["et-0/0/1"],
    lag_name: "ae103",
    ipv4_prefix: "192.0.2.2/31",
    ipv6_prefix: "2001:db8::2/127",
    expected_rtt_ms: 10,
    minimum_links: 1,
  });
});
