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

/** Active lease returned by the DHCP lease API. */
export interface DhcpLease {
  ip_address: string;
  hostname: string;
  hw_address?: string | null;
  client_id?: string | null;
  duid?: string | null;
  subnet?: string | null;
  state: number;
  cltt: number;
  valid_lft: number;
  expires_at?: string | null;
}

/** Cursor-paginated active leases returned by the DHCP API. */
export interface DhcpLeasePage {
  leases: DhcpLease[];
  next_cursor?: string | null;
}

/** Static reservation returned by the DHCP API. */
export interface DhcpReservation {
  ip_address?: string | null;
  hostname: string;
  identifier_type?: string | null;
  identifier?: string | null;
  subnet?: string | null;
}

/** Cursor-paginated reservations returned by the DHCP API. */
export interface DhcpReservationPage {
  reservations: DhcpReservation[];
  total_count: number;
  next_cursor?: string | null;
}

/** Configured address pool returned by the DHCP API. */
export interface DhcpPool {
  subnet: string;
  pool: string;
}

/** Cursor-paginated configured pools returned by the DHCP API. */
export interface DhcpPoolPage {
  pools: DhcpPool[];
  total_count: number;
  next_cursor?: string | null;
}

/** Aggregated lease and configuration counts returned by the DHCP API. */
export interface DhcpSummary {
  active_lease_count: number;
  reservation_count: number;
  pool_count: number;
}
