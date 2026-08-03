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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Skeleton } from "@/components/ui/skeleton";

const WorkflowsListSkeleton = () => {
  return (
    <div className="w-full px-8 py-6">
      <div className="mb-4 flex flex-row items-center justify-between">
        <div className="space-y-4">
          <Skeleton className="h-8 w-36" />
          <Skeleton className="h-5 w-48" />
        </div>
        <Skeleton className="h-10 w-32" />
      </div>
      <div className="mb-4 mt-2 rounded-md border border-border/70 bg-card p-2 shadow-sm">
        <div className="flex flex-wrap items-center justify-end gap-1.5">
          <Skeleton className="h-9 w-36" />
          <Skeleton className="h-9 w-[32rem] max-w-full" />
          <Skeleton className="h-9 w-20" />
          <Skeleton className="h-9 w-28" />
          <Skeleton className="h-9 w-28" />
        </div>
      </div>
      <SkeletonDataTable />
    </div>
  );
};

const SkeletonDataTable = () => {
  const columns = ["Column 1", "Column 2", "Column 3", "Column 4", "Column 5"];
  const rows = ["Row 1", "Row 2", "Row 3", "Row 4", "Row 5"];

  return (
    <div className="rounded-md border">
      <Table>
      <TableHeader>
        <TableRow>
          {columns.map((column) => (
            <TableHead key={column}>
              <Skeleton className="h-5 w-24" />
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row}>
            {columns.map((column) => (
              <TableCell key={`${row}-${column}`}>
                <Skeleton className="h-5 w-24" />
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
    </div>
  );
};

export default WorkflowsListSkeleton;
