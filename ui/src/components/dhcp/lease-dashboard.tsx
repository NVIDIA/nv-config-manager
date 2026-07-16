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

import { useEffect, useRef, useState } from "react";
import {
  Activity,
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
  useDhcpConfigSyncTimestamp,
  useDhcpLeases,
  useDhcpPools,
  useDhcpReservations,
  useDhcpSummary,
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
  readonly tooltip?: string;
}

interface InfiniteScrollStatusProps {
  readonly completeLabel?: string;
  readonly hasMore: boolean;
  readonly isValidating: boolean;
  readonly itemCount: number;
  readonly onLoadMore: () => void;
  readonly resourceLabel: string;
  readonly totalCount?: number;
}

/** Render one summary metric in the DHCP dashboard header. */
function Metric({ icon, label, value, detail, tooltip }: MetricProps) {
  return (
    <div
      role="group"
      aria-label={label}
      title={tooltip}
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

/** Render a compact loading state for a lazily fetched dashboard tab. */
function CollectionLoading() {
  return (
    <div className="space-y-3 rounded-md border p-4">
      {[0, 1, 2].map((item) => (
        <Skeleton key={item} className="h-10 w-full" />
      ))}
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

/** Format a Prometheus configuration sync timestamp as a compact age. */
function formatConfigSyncAge(timestamp?: number | null): string {
  if (timestamp == null) return "Unknown";
  const ageSeconds = Math.max(0, Math.floor(Date.now() / 1000 - timestamp));
  if (ageSeconds < 60) return `${ageSeconds}s`;
  if (ageSeconds < 3600) return `${Math.floor(ageSeconds / 60)}m`;
  if (ageSeconds < 86400) return `${Math.floor(ageSeconds / 3600)}h`;
  return `${Math.floor(ageSeconds / 86400)}d`;
}

/** Load the next cursor page when the shared collection footer enters view. */
function InfiniteScrollStatus({
  completeLabel,
  hasMore,
  isValidating,
  itemCount,
  onLoadMore,
  resourceLabel,
  totalCount,
}: InfiniteScrollStatusProps) {
  const sentinelRef = useRef<HTMLDivElement | null>(null);
  const loadRequestedRef = useRef(false);

  useEffect(() => {
    if (!isValidating) loadRequestedRef.current = false;
  }, [isValidating, itemCount]);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (
      !sentinel ||
      !hasMore ||
      isValidating ||
      typeof IntersectionObserver === "undefined"
    ) {
      return;
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (!entry.isIntersecting || loadRequestedRef.current) return;
        loadRequestedRef.current = true;
        onLoadMore();
      },
      { rootMargin: "200px" },
    );
    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasMore, isValidating, onLoadMore]);

  if (itemCount === 0) return null;

  const summary =
    totalCount === undefined
      ? `Loaded ${itemCount.toLocaleString()} ${resourceLabel}${hasMore ? "" : ` · ${completeLabel ?? `All ${resourceLabel} loaded`}`}`
      : `Loaded ${itemCount.toLocaleString()} of ${totalCount.toLocaleString()} ${resourceLabel}`;

  return (
    <div
      ref={sentinelRef}
      role="status"
      aria-live="polite"
      className="mt-4 border-t pt-4 text-center text-sm"
    >
      <p className="text-xs text-muted-foreground">{summary}</p>
      {hasMore && (
        <Button
          className="mt-2"
          variant="ghost"
          size="sm"
          aria-label={`Load more ${resourceLabel}`}
          onClick={() => {
            if (loadRequestedRef.current) return;
            loadRequestedRef.current = true;
            onLoadMore();
          }}
          disabled={isValidating}
        >
          {isValidating && <RefreshCw className="mr-2 h-4 w-4 animate-spin" />}
          {isValidating ? "Loading more" : "Load more"}
        </Button>
      )}
    </div>
  );
}

/** Render live DHCP leases, reservations, and configured pools. */
export function LeaseDashboard({ dhcpUrl }: LeaseDashboardProps) {
  const { data, error, isLoading, isValidating, mutate } = useDhcpSummary(dhcpUrl);
  const {
    data: configSyncTimestamp,
    isValidating: isConfigSyncAgeValidating,
    mutate: mutateConfigSyncTimestamp,
  } = useDhcpConfigSyncTimestamp(dhcpUrl);
  const { toast } = useToast();
  const [leaseToClear, setLeaseToClear] = useState<DhcpLease | null>(null);
  const [isClearing, setIsClearing] = useState(false);
  const [activeTab, setActiveTab] = useState("leases");
  const [searchQuery, setSearchQuery] = useState("");
  const [debouncedSearchQuery, setDebouncedSearchQuery] = useState("");
  const activeLeaseSearchQuery = activeTab === "leases" ? debouncedSearchQuery : "";
  const activeReservationSearchQuery =
    activeTab === "reservations" ? debouncedSearchQuery : "";
  const activePoolSearchQuery = activeTab === "pools" ? debouncedSearchQuery : "";
  const {
    error: leaseError,
    isLoading: areLeasesLoading,
    isValidating: areLeasesValidating,
    hasMore: hasMoreLeases,
    leases,
    loadMore: loadMoreLeases,
    mutate: mutateLeases,
  } = useDhcpLeases(dhcpUrl, activeLeaseSearchQuery);
  const {
    error: reservationError,
    hasMore: hasMoreReservations,
    isLoading: areReservationsLoading,
    isValidating: areReservationsValidating,
    loadMore: loadMoreReservations,
    mutate: mutateReservations,
    reservations,
    totalCount: reservationTotalCount,
  } = useDhcpReservations(
    dhcpUrl,
    activeReservationSearchQuery,
    activeTab === "reservations",
  );
  const {
    error: poolError,
    hasMore: hasMorePools,
    isLoading: arePoolsLoading,
    isValidating: arePoolsValidating,
    loadMore: loadMorePools,
    mutate: mutatePools,
    pools,
    totalCount: poolTotalCount,
  } = useDhcpPools(
    dhcpUrl,
    activePoolSearchQuery,
    activeTab === "pools",
  );
  const areCollectionsValidating =
    areLeasesValidating || areReservationsValidating || arePoolsValidating;

  useEffect(() => {
    const timeout = window.setTimeout(
      () => setDebouncedSearchQuery(searchQuery.trim()),
      300,
    );
    return () => window.clearTimeout(timeout);
  }, [searchQuery]);

  const reloadData = () => {
    void Promise.allSettled([
      mutate(),
      mutateConfigSyncTimestamp(),
      mutateLeases(),
      mutateReservations(),
      mutatePools(),
    ]);
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
      await Promise.allSettled([mutate(), mutateLeases()]);
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

  if (isLoading || areLeasesLoading) {
    return (
      <Card data-testid="dhcp-dashboard-loading">
        <CardHeader>
          <Skeleton className="h-7 w-48" />
          <Skeleton className="h-4 w-72" />
        </CardHeader>
        <CardContent className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {[0, 1, 2, 3].map((item) => (
            <Skeleton key={item} className="h-28" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error || leaseError || !data) {
    const dashboardError = error || leaseError;
    return (
      <Card className="border-dashed" data-testid="dhcp-dashboard-error">
        <CardHeader className="flex-row items-start justify-between space-y-0">
          <div className="space-y-1.5">
            <CardTitle className="flex items-center gap-2 text-xl">
              <Network className="h-5 w-5" /> DHCP leases
            </CardTitle>
            <CardDescription>
              {dashboardError instanceof Error
                ? dashboardError.message
                : "Lease data is unavailable."}
            </CardDescription>
          </div>
          <Button variant="outline" size="sm" onClick={reloadData}>
            <RefreshCw className="mr-2 h-4 w-4" /> Retry
          </Button>
        </CardHeader>
      </Card>
    );
  }

  const leaseResourceLabel = activeLeaseSearchQuery
    ? "matching active leases"
    : "active leases";
  const leaseCompleteLabel = activeLeaseSearchQuery
    ? "All matches loaded"
    : "All active leases loaded";
  return (
    <Card className="overflow-hidden" data-testid="dhcp-dashboard">
      <CardHeader className="border-b bg-card/70">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <CardTitle className="flex items-center gap-2 text-2xl">
              <Network className="h-6 w-6 text-primary" /> DHCP lease activity
            </CardTitle>
            <CardDescription className="mt-2">
              Live address allocations, configured reservations, and address pools.
            </CardDescription>
          </div>
          <Button
            aria-label="Reload DHCP data"
            title="Re-fetch the latest data shown here. This does not run the background DHCP config sync."
            variant="outline"
            size="sm"
            onClick={reloadData}
            disabled={isValidating || isConfigSyncAgeValidating || areCollectionsValidating}
          >
            <RefreshCw
              className={`mr-2 h-4 w-4 ${isValidating || isConfigSyncAgeValidating || areCollectionsValidating ? "animate-spin" : ""}`}
            />
            Reload data
          </Button>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Metric
            icon={<Activity className="h-4 w-4" />}
            label="Active leases"
            value={data.active_lease_count.toLocaleString()}
            detail="Current active allocations"
          />
          <Metric
            icon={<ShieldCheck className="h-4 w-4" />}
            label="Reservations"
            value={data.reservation_count.toLocaleString()}
            detail="Configured static addresses"
          />
          <Metric
            icon={<Database className="h-4 w-4" />}
            label="Pools"
            value={data.pool_count.toLocaleString()}
            detail="Configured address pools"
          />
          <Metric
            icon={<Clock3 className="h-4 w-4" />}
            label="Config sync age"
            value={formatConfigSyncAge(configSyncTimestamp)}
            detail={
              configSyncTimestamp == null
                ? "Config sync metric unavailable"
                : "Since last successful config sync"
            }
            tooltip="Time since the background DHCP config sync last updated Kea from Nautobot."
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
            placeholder="Filter by IP, hostname, MAC address, client ID, or subnet"
            value={searchQuery}
            onChange={(event) => setSearchQuery(event.target.value)}
            className="pl-9"
          />
        </div>
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-3 sm:w-auto">
            <TabsTrigger value="leases">Active leases</TabsTrigger>
            <TabsTrigger value="reservations">Reservations</TabsTrigger>
            <TabsTrigger value="pools">Pools</TabsTrigger>
          </TabsList>

          <TabsContent value="leases" className="mt-4">
            {leases.length === 0 ? (
              <EmptyState
                message={
                  activeLeaseSearchQuery
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
                    <TableHead>MAC / client ID</TableHead>
                    <TableHead>Subnet</TableHead>
                    <TableHead>Expires</TableHead>
                    <TableHead className="w-14"><span className="sr-only">Actions</span></TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {leases.map((lease) => (
                    <TableRow key={lease.ip_address}>
                      <TableCell className="font-mono font-medium">{lease.ip_address}</TableCell>
                      <TableCell>{lease.hostname || "Unknown device"}</TableCell>
                      <TableCell className="font-mono text-xs">
                        {lease.hw_address || lease.client_id || lease.duid || "—"}
                      </TableCell>
                      <TableCell>
                        {lease.subnet ? (
                          <Badge variant="outline">{lease.subnet}</Badge>
                        ) : (
                          <span
                            className="text-sm text-muted-foreground"
                            title="This lease's subnet ID is not present in the current DHCP configuration."
                          >
                            Removed
                          </span>
                        )}
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
            <InfiniteScrollStatus
              completeLabel={leaseCompleteLabel}
              hasMore={hasMoreLeases}
              isValidating={areLeasesValidating}
              itemCount={leases.length}
              onLoadMore={() => void loadMoreLeases()}
              resourceLabel={leaseResourceLabel}
            />
          </TabsContent>

          <TabsContent value="reservations" className="mt-4">
            {areReservationsLoading ? (
              <CollectionLoading />
            ) : reservationError ? (
              <EmptyState message="Reservation data is unavailable." />
            ) : reservations.length === 0 ? (
              <EmptyState
                message={
                  activeReservationSearchQuery
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
                  {reservations.map((reservation, index) => (
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
            <InfiniteScrollStatus
              hasMore={hasMoreReservations}
              isValidating={areReservationsValidating}
              itemCount={reservations.length}
              onLoadMore={() => void loadMoreReservations()}
              resourceLabel={
                activeReservationSearchQuery
                  ? "matching reservations"
                  : "reservations"
              }
              totalCount={reservationTotalCount}
            />
          </TabsContent>

          <TabsContent value="pools" className="mt-4">
            {arePoolsLoading ? (
              <CollectionLoading />
            ) : poolError ? (
              <EmptyState message="Pool data is unavailable." />
            ) : pools.length === 0 ? (
              <EmptyState
                message={
                  activePoolSearchQuery
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
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pools.map((pool) => (
                    <TableRow key={`${pool.subnet}-${pool.pool}`}>
                      <TableCell className="font-medium">{pool.subnet}</TableCell>
                      <TableCell className="font-mono text-xs">{pool.pool}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
            <InfiniteScrollStatus
              hasMore={hasMorePools}
              isValidating={arePoolsValidating}
              itemCount={pools.length}
              onLoadMore={() => void loadMorePools()}
              resourceLabel={
                activePoolSearchQuery ? "matching pools" : "pools"
              }
              totalCount={poolTotalCount}
            />
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
