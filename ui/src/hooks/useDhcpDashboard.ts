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

import useSWR from "swr";

import { sanitizeUrl } from "@/lib/utils";
import type { DhcpLeaseDashboard } from "@/types/dhcp.types";

const CONFIG_REFRESH_METRIC =
  "nv_config_manager_dhcp_cache_last_refresh_timestamp_seconds";
const REQUEST_TIMEOUT_MS = 30000;

/** Fetch and validate the dashboard response from the DHCP API. */
async function dhcpFetcher(url: string): Promise<DhcpLeaseDashboard> {
  const response = await fetch(url, {
    credentials: "include",
    mode: "cors",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail || body?.error || "DHCP lease data is unavailable");
  }
  return response.json();
}

/** Read the latest configuration refresh timestamp from Prometheus text. */
async function configRefreshFetcher(url: string): Promise<number | null> {
  const response = await fetch(url, {
    credentials: "include",
    mode: "cors",
  });
  if (!response.ok) {
    throw new Error("DHCP configuration age is unavailable");
  }

  const metrics = await response.text();
  const sample = metrics.split("\n").find(
    (line) =>
      line.startsWith(`${CONFIG_REFRESH_METRIC}{`) &&
      line.includes('ip_version="4"'),
  );
  if (!sample) return null;

  const value = Number(sample.trim().split(/\s+/)[1]);
  return Number.isFinite(value) ? value : null;
}

/** Subscribe to refreshed DHCP dashboard data for the splash page. */
export function useDhcpDashboard(dhcpUrl: string) {
  const url = dhcpUrl
    ? sanitizeUrl(`${dhcpUrl}/lease-dashboard?ip_version=4&limit=100`)
    : null;
  return useSWR<DhcpLeaseDashboard>(url, dhcpFetcher, {
    refreshInterval: 30000,
    revalidateOnFocus: true,
  });
}

/** Subscribe to the last successful configuration refresh timestamp. */
export function useDhcpConfigRefreshTimestamp(dhcpUrl: string) {
  const url = dhcpUrl ? sanitizeUrl(`${dhcpUrl}/metrics`) : null;
  return useSWR<number | null>(url, configRefreshFetcher, {
    refreshInterval: 30000,
    revalidateOnFocus: true,
  });
}

/** Delete an active lease through the DHCP API. */
export async function clearDhcpLease(
  dhcpUrl: string,
  ipAddress: string,
): Promise<void> {
  const query = new URLSearchParams({
    ip_address: ipAddress,
    ip_version: "4",
  });
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(sanitizeUrl(`${dhcpUrl}/lease?${query}`), {
      credentials: "include",
      method: "DELETE",
      mode: "cors",
      signal: controller.signal,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new Error(body?.detail || body?.error || "Failed to clear lease");
    }
  } finally {
    clearTimeout(timeout);
  }
}
