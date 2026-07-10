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

/** Subscribe to refreshed DHCP dashboard data for the splash page. */
export function useDhcpDashboard(dhcpUrl: string) {
  const url = dhcpUrl
    ? sanitizeUrl(`${dhcpUrl}/lease-dashboard?limit=100`)
    : null;
  return useSWR<DhcpLeaseDashboard>(url, dhcpFetcher, {
    refreshInterval: 30000,
    revalidateOnFocus: true,
  });
}

/** Delete an active IPv4 lease through the restricted DHCP proxy. */
export async function clearDhcpLease(
  dhcpUrl: string,
  ipAddress: string,
): Promise<void> {
  const response = await fetch(sanitizeUrl(`${dhcpUrl}/lease`), {
    body: JSON.stringify({
      command: "lease4-del",
      service: ["dhcp4"],
      arguments: { "ip-address": ipAddress },
    }),
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    method: "POST",
    mode: "cors",
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    throw new Error(body?.detail || body?.error || "Failed to clear lease");
  }
  const result = Array.isArray(body) ? body[0] : body;
  if (result?.result !== 0) {
    throw new Error(result?.text || "KEA did not clear the lease");
  }
}
