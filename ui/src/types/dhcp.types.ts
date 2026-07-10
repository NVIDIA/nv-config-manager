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

export interface DhcpLease {
  ip_address: string;
  hostname: string;
  hw_address?: string | null;
  client_id?: string | null;
  subnet_id: number;
  state: number;
  cltt: number;
  valid_lft: number;
  expires_at?: string | null;
}

export interface DhcpReservation {
  ip_address?: string | null;
  hostname: string;
  identifier_type?: string | null;
  identifier?: string | null;
  subnet_id?: number | null;
}

export interface DhcpPoolUsage {
  subnet_id: number;
  subnet: string;
  pool: string;
  assigned: number;
  total: number;
  utilization: number;
}

export interface DhcpLeaseDashboard {
  active_lease_count: number;
  reservation_count: number;
  assigned_address_count: number;
  pool_address_count: number;
  leases_truncated: boolean;
  reservations_truncated: boolean;
  leases: DhcpLease[];
  reservations: DhcpReservation[];
  pools: DhcpPoolUsage[];
}
