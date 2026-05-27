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

import * as React from "react";
import { useSearchParams } from "next/navigation";
import useSWR from "swr";
import {
  Column,
  ColumnDef,
  ColumnFiltersState,
  FilterFn,
  flexRender,
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  RowData,
  useReactTable,
} from "@tanstack/react-table";
import { RankingInfo, rankItem } from "@tanstack/match-sorter-utils";
import { fetcher } from "@/lib/fetcher";
import { TokenError } from "@/lib/errors";
import { useRuntimeConfig } from "@/config/runtime";
import { sanitizeUrl } from "@/lib/utils";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DataTableProps, Workflow, WORKFLOW_STATUS } from "@/types/data-table.types";
import { DebouncedInput } from "@/components/ui/debounced-input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useHeaderContext } from "@/app/contexts/header";
import { LoadingSpinner } from "@/components/ui/loading-spinner";

declare module "@tanstack/react-table" {
  interface FilterFns {
    fuzzy: FilterFn<unknown>;
  }
  interface FilterMeta {
    itemRank: RankingInfo;
  }
  // eslint-disable-next-line @typescript-eslint/no-unused-vars -- required by module augmentation contract
  interface ColumnMeta<TData extends RowData, TValue> {
    filterVariant?: "select";
  }
}

const fuzzyFilter: FilterFn<Workflow> = (row, columnId, value, addMeta) => {
  const itemRank = rankItem(row.getValue(columnId), value);

  addMeta({
    itemRank,
  });

  return itemRank.passed;
};

const removeSearchAttributesPrefix = (str: string): string => {
  const prefix = "search_attributes_";

  if (str.startsWith(prefix)) {
    return str.slice(prefix.length);
  }

  return str;
};

function Filter({ column }: { column: Column<Workflow, unknown> }) {
  const columnFilterValue = (column.getFilterValue() ?? "") as string;
  const { filterVariant } = column.columnDef.meta ?? {};
  const statusOptions = [
    "not-started",
    "pending",
    "completed",
    "running",
    "failed",
  ];

  const handleSelect = (value: string) => {
    if (value == "all") {
      column.setFilterValue("");
    } else if (statusOptions.includes(value)) {
      column.setFilterValue(value);
    }
  };

  return filterVariant == "select" ? (
    <Select
      onValueChange={handleSelect}
      value={statusOptions.includes(columnFilterValue) ? columnFilterValue : ""}
    >
      <SelectTrigger className="w-full">
        <SelectValue placeholder="Select Status" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="all">All</SelectItem>
        <SelectItem value="not-started">Not Started</SelectItem>
        <SelectItem value="pending">Pending Approval</SelectItem>
        <SelectItem value="completed">Completed</SelectItem>
        <SelectItem value="running">Running</SelectItem>
        <SelectItem value="failed">Failed</SelectItem>
      </SelectContent>
    </Select>
  ) : (
    <DebouncedInput
      type="text"
      value={columnFilterValue}
      onChange={(value) => column.setFilterValue(value)}
      placeholder={`Search...`}
      className="w-36 border shadow rounded"
    />
  );
}

export function DataTable<TData, TValue>({
  columns,
  workflowType,
}: DataTableProps<TData, TValue>) {
  const { config } = useRuntimeConfig();
  const apiURL = config?.workflowApiUrl;
  
  const [globalFilter, setGlobalFilter] = React.useState("");
  const [columnFilters, setColumnFilters] = React.useState<ColumnFiltersState>(
    []
  );
  const [isHideCompletedChecked, setIsHideCompletedChecked] =
    React.useState<boolean>(false);

  const [workflowData, setWorkflowData] = React.useState<Workflow[]>([]);
  const [nextPageToken, setNextPageToken] = React.useState("");
  const [hasMoreData, setHasMoreData] = React.useState(true);
  const searchParams = useSearchParams();
  const { refreshPaused, setRefreshPaused } = useHeaderContext();
  const [apiLimit, setApiLimit] = React.useState(10);

  const {
    data,
    error: workflowError,
    isLoading,
  } = useSWR(
    !refreshPaused && hasMoreData && apiURL
      ? sanitizeUrl(
          `${apiURL}/v1/workflow/?workflow_type=${workflowType}&limit=${apiLimit}&next_page_token=${nextPageToken}`
        )
      : null,
    fetcher,
    {
      refreshInterval: 60000,
      onSuccess: (data) => {
        const uniqueWorkflows = Array.from(
          new Map(
            [...workflowData, ...data.workflows].map((item) => [item.id, item])
          ).values()
        );
        setWorkflowData(uniqueWorkflows);
        setNextPageToken(data.next_page_token || "");
        setHasMoreData(!!data.next_page_token);
        setApiLimit(100);
      },
    }
  );

  React.useEffect(() => {
    if (workflowError instanceof TokenError) {
      setRefreshPaused(true);
    }
  }, [workflowError, setRefreshPaused]);

  React.useEffect(() => {
    const queryParam = searchParams?.get("hidecompleted")?.toLowerCase();
    if (queryParam == "true") {
      const filteredData = workflowData.filter(
        (workflow) => workflow.status != WORKFLOW_STATUS.completed
      );
      setWorkflowData(filteredData);
      setIsHideCompletedChecked(true);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps -- workflowData is set here; adding it would cause an infinite loop
  }, [data, searchParams]);
  const [pagination, setPagination] = React.useState({
    pageIndex: 0,
    pageSize: 10,
  });

  const table = useReactTable({
    data: workflowData,
    columns: columns as ColumnDef<Workflow, unknown>[],
    filterFns: {
      fuzzy: fuzzyFilter,
    },
    state: {
      columnFilters,
      globalFilter,
      pagination,
    },
    autoResetPageIndex: false,
    onPaginationChange: setPagination,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    globalFilterFn: "fuzzy",
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });

  React.useEffect(() => {
    const headers = table.getHeaderGroups()[0].headers;
    headers.forEach(({ id }) => {
      const queryParam = searchParams?.get(
        removeSearchAttributesPrefix(id).toLowerCase()
      );
      table.getColumn(id)?.setFilterValue(queryParam);
    });
  // eslint-disable-next-line react-hooks/exhaustive-deps -- table is recreated every render; including it would run on every render
  }, [searchParams]);

  const handleToggleHideCompleted = (checked: boolean) => {
    if (checked) {
      setWorkflowData(
        workflowData.filter(
          (workflow) => workflow.status != WORKFLOW_STATUS.completed
        )
      );
      setIsHideCompletedChecked(true);
    } else {
      setWorkflowData(data);
      setIsHideCompletedChecked(false);
    }
  };

  const handleClearFilters = () => {
    const headers = table.getHeaderGroups()[0].headers;
    headers.forEach(({ id }) => {
      table.getColumn(id)?.setFilterValue("");
    });
    setWorkflowData(data);
    setIsHideCompletedChecked(false);
    table.resetGlobalFilter();
  };

  return (
    <>
      <div className="flex items-center py-4 gap-4">
        <DebouncedInput
          value={globalFilter ?? ""}
          onChange={(value) => setGlobalFilter(String(value))}
          className="p-2 font-lg shadow border border-block"
          placeholder="Search all columns..."
        />
        <div className="flex items-center space-x-2">
          <Checkbox
            onCheckedChange={handleToggleHideCompleted}
            checked={isHideCompletedChecked}
          />
          <label className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70">
            Hide Completed Workflows
          </label>
        </div>

        <Button onClick={handleClearFilters}>Clear All Filters</Button>
      </div>
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => {
                  return (
                    <TableHead key={header.id}>
                      {header.isPlaceholder
                        ? null
                        : flexRender(
                            header.column.columnDef.header,
                            header.getContext()
                          )}
                      {header.column.getCanFilter() && (
                        <div>
                          <Filter column={header.column} />
                        </div>
                      )}
                    </TableHead>
                  );
                })}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {isLoading &&
            table.getState().pagination.pageIndex *
              table.getState().pagination.pageSize >=
              workflowData.length ? (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center"
                >
                  <div className="flex items-center justify-center h-full">
                    <LoadingSpinner />
                  </div>
                </TableCell>
              </TableRow>
            ) : table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <TableRow
                  key={row.id}
                  data-state={row.getIsSelected() && "selected"}
                >
                  {row.getVisibleCells().map((cell) => (
                    <TableCell key={cell.id}>
                      {flexRender(
                        cell.column.columnDef.cell,
                        cell.getContext()
                      )}
                    </TableCell>
                  ))}
                </TableRow>
              ))
            ) : (
              <TableRow>
                <TableCell
                  colSpan={columns.length}
                  className="h-24 text-center"
                >
                  No results.
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
        <div className="flex items-center justify-between w-full p-4 border-t">
          <div className="flex items-center space-x-2">
            <Select
              value={String(table.getState().pagination.pageSize)}
              onValueChange={(value) => {
                table.setPageSize(Number(value));
              }}
            >
              <SelectTrigger className="w-full">
                <SelectValue placeholder="Rows per page" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="10">10 Rows</SelectItem>
                <SelectItem value="50">50 Rows</SelectItem>
                <SelectItem value="100">100 Rows</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="text-center flex flex-col items-center flex-grow">
            <div>
              {table.getState().pagination.pageIndex + 1} of{" "}
              {table.getPageCount()}
            </div>
            <div className="flex items-center space-x-2">
              <span>Go to page:</span>
              <Input
                type="number"
                defaultValue={table.getState().pagination.pageIndex + 1}
                onChange={(e) => {
                  const maxPage = table.getPageCount();
                  let page = e.target.value ? Number(e.target.value) - 1 : 0;

                  if (page >= maxPage) {
                    page = maxPage - 1;
                  }

                  table.setPageIndex(page);
                }}
                className="border p-1 rounded w-16"
                min={1}
                max={table.getPageCount()}
              />
            </div>
          </div>

          <div className="flex items-center space-x-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.previousPage()}
              disabled={!table.getCanPreviousPage()}
              className="px-4 py-2 border rounded"
            >
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => table.nextPage()}
              disabled={hasMoreData ? false : !table.getCanNextPage()}
              className="px-4 py-2 border rounded"
            >
              Next
            </Button>
          </div>
        </div>
      </div>
    </>
  );
}
