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
import useSWRInfinite from "swr/infinite";

import { sanitizeUrl } from "@/lib/utils";
import type {
  DhcpLeasePage,
  DhcpPoolPage,
  DhcpReservationPage,
  DhcpSummary,
} from "@/types/dhcp.types";

const CONFIG_SYNC_TIMESTAMP_METRIC =
  "nv_config_manager_dhcp_cache_last_refresh_timestamp_seconds";
const REQUEST_TIMEOUT_MS = 30000;
const DHCP_COLLECTION_PAGE_SIZE = 100;

/** Fetch and validate the dashboard response from the DHCP API. */
async function dhcpFetcher<T>(url: string): Promise<T> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(url, {
      credentials: "include",
      mode: "cors",
      signal: controller.signal,
    });
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new Error(
        body?.detail || body?.error || "DHCP lease data is unavailable"
      );
    }
    return response.json();
  } finally {
    clearTimeout(timeout);
  }
}

/** Read the latest configuration sync timestamp from Prometheus text. */
async function configSyncTimestampFetcher(url: string): Promise<number | null> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(url, {
      credentials: "include",
      mode: "cors",
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error("DHCP config sync age is unavailable");
    }

    const metrics = await response.text();
    const sample = metrics
      .split("\n")
      .find(
        (line) =>
          line.startsWith(`${CONFIG_SYNC_TIMESTAMP_METRIC}{`) &&
          line.includes('ip_version="4"')
      );
    if (!sample) return null;

    const value = Number(sample.trim().split(/\s+/)[1]);
    return Number.isFinite(value) ? value : null;
  } finally {
    clearTimeout(timeout);
  }
}

/** Subscribe to DHCP summary data. */
export function useDhcpSummary(dhcpUrl: string) {
  const url = dhcpUrl ? sanitizeUrl(`${dhcpUrl}/summary?ip_version=4`) : null;
  return useSWR<DhcpSummary>(url, dhcpFetcher, {
    refreshInterval: 30000,
    revalidateOnFocus: true,
  });
}

interface DhcpCursorPage {
  next_cursor?: string | null;
}

/** Preserve API order while removing rows repeated across changing cursor pages. */
function uniqueBy<T>(items: T[], key: (item: T) => string): T[] {
  const uniqueItems = new Map<string, T>();
  for (const item of items) {
    const itemKey = key(item);
    if (!uniqueItems.has(itemKey)) uniqueItems.set(itemKey, item);
  }
  return [...uniqueItems.values()];
}

/** Subscribe to cursor-paginated DHCP collection pages as an infinite list. */
function useDhcpCollectionPages<T extends DhcpCursorPage>(
  dhcpUrl: string,
  path: string,
  search: string,
  enabled = true
) {
  return useSWRInfinite<T>(
    (pageIndex, previousPageData) => {
      if (!dhcpUrl || !enabled) return null;
      if (pageIndex > 0 && !previousPageData?.next_cursor) return null;

      const query = new URLSearchParams({
        limit: String(DHCP_COLLECTION_PAGE_SIZE),
      });
      if (search) query.set("search", search);
      if (previousPageData?.next_cursor) {
        query.set("cursor", previousPageData.next_cursor);
      }
      return sanitizeUrl(`${dhcpUrl}/${path}?${query}`);
    },
    dhcpFetcher,
    {
      keepPreviousData: true,
      refreshInterval: 30000,
      revalidateOnFocus: true,
    }
  );
}

/** Subscribe to the loaded cursor-paginated lease pages. */
export function useDhcpLeases(dhcpUrl: string, search: string) {
  const response = useDhcpCollectionPages<DhcpLeasePage>(
    dhcpUrl,
    "lease",
    search
  );
  const pages = response.data ?? [];
  const lastPage = pages.at(-1);

  return {
    ...response,
    hasMore: lastPage?.next_cursor != null,
    leases: uniqueBy(
      pages.flatMap((page) => page.leases),
      (lease) => lease.ip_address
    ),
    loadMore: () => response.setSize((size) => size + 1),
  };
}

/** Subscribe to the loaded cursor-paginated reservation pages. */
export function useDhcpReservations(
  dhcpUrl: string,
  search: string,
  enabled: boolean
) {
  const response = useDhcpCollectionPages<DhcpReservationPage>(
    dhcpUrl,
    "reservation",
    search,
    enabled
  );
  const pages = response.data ?? [];
  const lastPage = pages.at(-1);

  return {
    ...response,
    hasMore: lastPage?.next_cursor != null,
    loadMore: () => response.setSize((size) => size + 1),
    reservations: uniqueBy(
      pages.flatMap((page) => page.reservations),
      (reservation) =>
        `${reservation.ip_address ?? ""}:${reservation.hostname ?? ""}:${
          reservation.identifier_type ?? ""
        }:${reservation.identifier ?? ""}:${reservation.subnet ?? ""}`
    ),
    totalCount: lastPage?.total_count ?? 0,
  };
}

/** Subscribe to the loaded cursor-paginated configured pool pages. */
export function useDhcpPools(
  dhcpUrl: string,
  search: string,
  enabled: boolean
) {
  const response = useDhcpCollectionPages<DhcpPoolPage>(
    dhcpUrl,
    "pool",
    search,
    enabled
  );
  const pages = response.data ?? [];
  const lastPage = pages.at(-1);

  return {
    ...response,
    hasMore: lastPage?.next_cursor != null,
    loadMore: () => response.setSize((size) => size + 1),
    pools: uniqueBy(
      pages.flatMap((page) => page.pools),
      (pool) => `${pool.subnet}:${pool.pool}`
    ),
    totalCount: lastPage?.total_count ?? 0,
  };
}

/** Subscribe to the last successful configuration sync timestamp. */
export function useDhcpConfigSyncTimestamp(dhcpUrl: string) {
  const url = dhcpUrl ? sanitizeUrl(`${dhcpUrl}/metrics`) : null;
  return useSWR<number | null>(url, configSyncTimestampFetcher, {
    refreshInterval: 30000,
    revalidateOnFocus: true,
  });
}

/** Delete an active lease through the DHCP API. */
export async function clearDhcpLease(
  dhcpUrl: string,
  ipAddress: string
): Promise<void> {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(
      sanitizeUrl(`${dhcpUrl}/lease/${encodeURIComponent(ipAddress)}`),
      {
        credentials: "include",
        method: "DELETE",
        mode: "cors",
        signal: controller.signal,
      }
    );
    if (!response.ok) {
      const body = await response.json().catch(() => null);
      throw new Error(body?.detail || body?.error || "Failed to clear lease");
    }
  } finally {
    clearTimeout(timeout);
  }
}
