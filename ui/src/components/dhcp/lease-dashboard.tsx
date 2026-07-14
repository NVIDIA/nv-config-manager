"use client";
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

import { useState } from "react";
import {
  Activity,
  CalendarClock,
  Clock3,
  Database,
  Network,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
} from "lucide-react";

import {
  clearDhcpLease,
  useDhcpConfigRefreshTimestamp,
  useDhcpDashboard,
} from "@/hooks/useDhcpDashboard";
import type { DhcpLease } from "@/types/dhcp.types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { useToast } from "@/components/ui/use-toast";

interface LeaseDashboardProps {
  readonly dhcpUrl: string;
}

interface MetricProps {
  readonly icon: React.ReactNode;
  readonly label: string;
  readonly value: string;
  readonly detail: string;
}

/** Render one summary metric in the DHCP dashboard header. */
function Metric({ icon, label, value, detail }: MetricProps) {
  return (
    <div
      role="group"
      aria-label={label}
      className="rounded-lg border bg-background/60 p-4"
    >
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-muted-foreground">{label}</p>
        <div className="rounded-md bg-primary/10 p-2 text-primary">{icon}</div>
      </div>
      <p className="mt-3 text-2xl font-semibold tracking-tight">{value}</p>
      <p className="mt-1 text-xs text-muted-foreground">{detail}</p>
    </div>
  );
}

/** Render a consistent empty state for a dashboard tab. */
function EmptyState({ message }: Readonly<{ message: string }>) {
  return (
    <div className="flex min-h-32 items-center justify-center rounded-md border border-dashed p-6 text-sm text-muted-foreground">
      {message}
    </div>
  );
}

/** Format a nullable lease expiry for the operator's locale. */
function formatExpiry(expiresAt?: string | null): string {
  if (!expiresAt) return "Never";
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(expiresAt));
}

/** Format a Prometheus refresh timestamp as a compact age. */
function formatConfigAge(timestamp?: number | null): string {
  if (timestamp == null) return "Unknown";
  const ageSeconds = Math.max(0, Math.floor(Date.now() / 1000 - timestamp));
  if (ageSeconds < 60) return `${ageSeconds}s`;
  if (ageSeconds < 3600) return `${Math.floor(ageSeconds / 60)}m`;
  if (ageSeconds < 86400) return `${Math.floor(ageSeconds / 3600)}h`;
  return `${Math.floor(ageSeconds / 86400)}d`;
}

/** Normalize a complete 48-bit MAC address across common separator styles. */
function normalizeMacAddress(value: string): string | null {
  const compactValue = value.replaceAll(/[:.-]/g, "").toLowerCase();
  return /^[0-9a-f]{12}$/.test(compactValue) ? compactValue : null;
}

/** Return whether any display value contains the query or the same MAC address. */
function matchesSearch(
  values: Array<string | number | null | undefined>,
  query: string,
): boolean {
  const normalizedMacQuery = normalizeMacAddress(query);
  return values.some((value) => {
    const normalizedValue = String(value ?? "").toLowerCase();
    return (
      normalizedValue.includes(query) ||
      (normalizedMacQuery !== null &&
        normalizeMacAddress(normalizedValue) === normalizedMacQuery)
    );
  });
}

/** Render a utilization bar using warning colors near pool capacity. */
function PoolBar({ utilization }: Readonly<{ utilization: number }>) {
  const color =
    utilization >= 90
      ? "bg-destructive"
      : utilization >= 70
        ? "bg-amber-500"
        : "bg-primary";
  return (
    <div className="h-2 w-28 overflow-hidden rounded-full bg-muted" aria-hidden="true">
      <div
        className={`h-full rounded-full ${color}`}
        style={{ width: `${Math.min(utilization, 100)}%` }}
      />
    </div>
  );
}

/** Render live DHCP lease, reservation, and pool activity. */
export function LeaseDashboard({ dhcpUrl }: LeaseDashboardProps) {
  const { data, error, isLoading, isValidating, mutate } = useDhcpDashboard(dhcpUrl);
  const {
    data: configRefreshTimestamp,
    isValidating: isConfigAgeValidating,
    mutate: mutateConfigRefreshTimestamp,
  } = useDhcpConfigRefreshTimestamp(dhcpUrl);
  const { toast } = useToast();
  const [leaseToClear, setLeaseToClear] = useState<DhcpLease | null>(null);
  const [isClearing, setIsClearing] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");

  const refresh = () => {
    void Promise.allSettled([mutate(), mutateConfigRefreshTimestamp()]);
  };

  const clearLease = async () => {
    if (!leaseToClear) return;
    setIsClearing(true);
    try {
      await clearDhcpLease(dhcpUrl, leaseToClear.ip_address);
      toast({
        title: "Lease cleared",
        description: `${leaseToClear.ip_address} is available for reassignment.`,
      });
      setLeaseToClear(null);
      await mutate();
    } catch (clearError) {
      toast({
        title: "Unable to clear lease",
        description:
          clearError instanceof Error ? clearError.message : "The request failed.",
        variant: "destructive",
      });
    } finally {
      setIsClearing(false);
    }
  };

  if (isLoading) {
    return (
      <Card data-testid="dhcp-dashboard-loading">
        <CardHeader>
          <Skeleton className="h-7 w-48" />
          <Skeleton className="h-4 w-72" />
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          {[0, 1, 2, 3, 4].map((item) => (
            <Skeleton key={item} className="h-28" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card className="border-dashed" data-testid="dhcp-dashboard-error">
        <CardHeader className="flex-row items-start justify-between space-y-0">
          <div className="space-y-1.5">
            <CardTitle className="flex items-center gap-2 text-xl">
              <Network className="h-5 w-5" /> DHCP leases
            </CardTitle>
            <CardDescription>
              {error instanceof Error ? error.message : "Lease data is unavailable."}
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={refresh}>
            <RefreshCw className="mr-2 h-4 w-4" /> Retry
          </Button>
        </CardHeader>
      </Card>
    );
  }

  const utilization = data.pool_address_count
    ? (data.assigned_address_count / data.pool_address_count) * 100
    : 0;
  const normalizedSearch = searchQuery.trim().toLowerCase();
  const filteredLeases = normalizedSearch
    ? data.leases.filter((lease) =>
        matchesSearch(
          [
            lease.ip_address,
            lease.hostname,
            lease.hw_address,
            lease.client_id,
            lease.duid,
            lease.subnet,
          ],
          normalizedSearch,
        ),
      )
    : data.leases;
  const filteredReservations = normalizedSearch
    ? data.reservations.filter((reservation) =>
        matchesSearch(
          [
            reservation.ip_address,
            reservation.hostname,
            reservation.identifier_type,
            reservation.identifier,
            reservation.subnet,
          ],
          normalizedSearch,
        ),
      )
    : data.reservations;
  const filteredPools = normalizedSearch
    ? data.pools.filter((pool) =>
        matchesSearch(
          [pool.subnet, pool.pool],
          normalizedSearch,
        ),
      )
    : data.pools;

  return (
    <Card className="overflow-hidden" data-testid="dhcp-dashboard">
      <CardHeader className="border-b bg-card/70">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-2xl">
              <Network className="h-6 w-6 text-primary" /> DHCP lease activity
            </CardTitle>
            <CardDescription className="mt-2">
              Live address allocations, configured reservations, and pool capacity.
            </CardDescription>
          </div>
          <Button
            aria-label="Refresh DHCP lease data"
            variant="outline"
            size="sm"
            onClick={refresh}
            disabled={isValidating || isConfigAgeValidating}
          >
            <RefreshCw
              className={`mr-2 h-4 w-4 ${isValidating || isConfigAgeValidating ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Metric
            icon={<Activity className="h-4 w-4" />}
            label="Active leases"
            value={data.active_lease_count.toLocaleString()}
            detail={data.leases_truncated ? `Showing first ${data.leases.length}` : "Current assignments"}
          />
          <Metric
            icon={<ShieldCheck className="h-4 w-4" />}
            label="Reservations"
            value={data.reservation_count.toLocaleString()}
            detail="Configured static addresses"
          />
          <Metric
            icon={<Database className="h-4 w-4" />}
            label="Pool capacity"
            value={data.pool_address_count.toLocaleString()}
            detail={`${data.assigned_address_count.toLocaleString()} addresses assigned`}
          />
          <Metric
            icon={<CalendarClock className="h-4 w-4" />}
            label="Pool utilization"
            value={`${utilization.toFixed(1)}%`}
            detail={`${data.pools.length} configured pool${data.pools.length === 1 ? "" : "s"}`}
          />
          <Metric
            icon={<Clock3 className="h-4 w-4" />}
            label="Config age"
            value={formatConfigAge(configRefreshTimestamp)}
            detail={
              configRefreshTimestamp == null
                ? "Refresh metric unavailable"
                : "Since last successful refresh"
            }
          />
        </div>
      </CardHeader>
      <CardContent className="p-6">
        <div className="relative mb-4 max-w-xl">
          <Search
            className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
            aria-hidden="true"
          />
          <Input
            type="search"
            aria-label="Filter displayed DHCP data"
            placeholder="Filter by IP, hostname, identifier, or subnet"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            className="pl-9"
          />
        </div>
        <Tabs defaultValue="leases">
          <TabsList className="grid w-full grid-cols-3 sm:w-auto">
            <TabsTrigger value="leases">Active leases</TabsTrigger>
            <TabsTrigger value="reservations">Reservations</TabsTrigger>
            <TabsTrigger value="pools">Pool usage</TabsTrigger>
          </TabsList>

          <TabsContent value="leases" className="mt-4">
            {filteredLeases.length === 0 ? (
              <EmptyState
                message={
                  normalizedSearch
                    ? `No active leases match “${searchQuery.trim()}”.`
                    : "No active leases."
                }
              />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>IP address</TableHead>
                    <TableHead>Device</TableHead>
                    <TableHead>Identifier</TableHead>
                    <TableHead>Subnet</TableHead>
                    <TableHead>Expires</TableHead>
                    <TableHead className="w-14"><span className="sr-only">Actions</span></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredLeases.map((lease) => (
                    <TableRow key={lease.ip_address}>
                      <TableCell className="font-mono font-medium">{lease.ip_address}</TableCell>
                      <TableCell>{lease.hostname || "Unknown device"}</TableCell>
                      <TableCell className="font-mono text-xs">
                        {lease.hw_address || lease.client_id || lease.duid || "—"}
                      </TableCell>
                      <TableCell>
                        {lease.subnet ? <Badge variant="outline">{lease.subnet}</Badge> : "—"}
                      </TableCell>
                      <TableCell className="whitespace-nowrap">{formatExpiry(lease.expires_at)}</TableCell>
                      <TableCell>
                        <Button
                          aria-label={`Clear lease ${lease.ip_address}`}
                          title={`Clear lease ${lease.ip_address}`}
                          variant="ghost"
                          size="icon"
                          onClick={() => setLeaseToClear(lease)}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </TabsContent>

          <TabsContent value="reservations" className="mt-4">
            {filteredReservations.length === 0 ? (
              <EmptyState
                message={
                  normalizedSearch
                    ? `No reservations match “${searchQuery.trim()}”.`
                    : "No reservations are configured."
                }
              />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>IP address</TableHead>
                    <TableHead>Hostname</TableHead>
                    <TableHead>Identifier type</TableHead>
                    <TableHead>Identifier</TableHead>
                    <TableHead>Subnet</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredReservations.map((reservation, index) => (
                    <TableRow key={`${reservation.ip_address || "reservation"}-${index}`}>
                      <TableCell className="font-mono font-medium">{reservation.ip_address || "—"}</TableCell>
                      <TableCell>{reservation.hostname || "—"}</TableCell>
                      <TableCell>{reservation.identifier_type || "—"}</TableCell>
                      <TableCell className="font-mono text-xs">{reservation.identifier || "—"}</TableCell>
                      <TableCell>{reservation.subnet || "Global"}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </TabsContent>

          <TabsContent value="pools" className="mt-4">
            {filteredPools.length === 0 ? (
              <EmptyState
                message={
                  normalizedSearch
                    ? `No pools match “${searchQuery.trim()}”.`
                    : "No address pools are configured."
                }
              />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Subnet</TableHead>
                    <TableHead>Pool</TableHead>
                    <TableHead>Assigned</TableHead>
                    <TableHead>Capacity</TableHead>
                    <TableHead>Utilization</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filteredPools.map((pool) => (
                    <TableRow key={`${pool.subnet}-${pool.pool}`}>
                      <TableCell className="font-medium">{pool.subnet}</TableCell>
                      <TableCell className="font-mono text-xs">{pool.pool}</TableCell>
                      <TableCell>{pool.assigned.toLocaleString()}</TableCell>
                      <TableCell>{pool.total.toLocaleString()}</TableCell>
                      <TableCell>
                        <div className="flex items-center gap-3">
                          <PoolBar utilization={pool.utilization} />
                          <span className="w-12 text-right text-sm font-medium">{pool.utilization.toFixed(1)}%</span>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </TabsContent>
        </Tabs>
      </CardContent>

      <Dialog
        open={leaseToClear !== null}
        onOpenChange={(open) => {
          if (!open && !isClearing) setLeaseToClear(null);
        }}
      >
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Clear DHCP lease?</DialogTitle>
            <DialogDescription>
              Delete the lease for <span className="font-mono font-medium text-foreground">{leaseToClear?.ip_address}</span>. The address can be assigned again immediately.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setLeaseToClear(null)} disabled={isClearing}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={clearLease} disabled={isClearing}>
              {isClearing && <RefreshCw className="mr-2 h-4 w-4 animate-spin" />}
              Clear lease
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
