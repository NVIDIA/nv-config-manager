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

import { ColumnDef } from "@tanstack/react-table";
import { SortableHeaderButton } from "@/components/data-table";
import { WorkflowColumns } from "@/types/data-table.types";
import { renderDeviceNameField } from "@/lib/utils";
import { useRuntimeConfig } from "@/config/runtime";
import Link from "next/link";

// Component wrapper to use runtime config in cell renderer
function DeviceNameCell({ workflow }: { workflow: WorkflowColumns }) {
  const { config } = useRuntimeConfig();
  return <>{renderDeviceNameField(workflow, config?.nautobotUrl)}</>;
}

export const workflowColumns: ColumnDef<WorkflowColumns>[] = [
  {
    accessorKey: "status",
    meta: {
      filterVariant: "select",
    },
    header: ({ column }) => {
      return <SortableHeaderButton column={column} title="Status" />;
    },
  },
  {
    accessorKey: "search_attributes.User",
    filterFn: "includesString",
    header: ({ column }) => {
      return <SortableHeaderButton column={column} title="User" />;
    },
  },
  {
    accessorKey: "search_attributes.Site",
    filterFn: "includesString",
    header: ({ column }) => {
      return <SortableHeaderButton column={column} title="Site" />;
    },
  },
  {
    accessorKey: "search_attributes.DeviceName",
    filterFn: "includesString",
    header: ({ column }) => {
      return <SortableHeaderButton column={column} title="Device Name" />;
    },
    cell: ({ row }) => {
      return <DeviceNameCell workflow={row.original} />;
    }
  },
  {
    accessorKey: "id",
    filterFn: "includesString",
    header: ({ column }) => {
      return <SortableHeaderButton column={column} title="Workflow Id" />;
    },
    cell: ({ row }) => {
      const id = row.original.id;
      return <Link href={`/workflows/${id}`} title="View workflow details">{id}</Link>
    },
  },
  {
    accessorKey: "start_time",
    header: ({ column }) => {
      return <SortableHeaderButton column={column} title="Start Time" />;
    },
    cell: ({ row }) => {return new Date(row.original.start_time).toLocaleString()}
  },
  {
    accessorKey: "close_time",
    header: ({ column }) => {
      return <SortableHeaderButton column={column} title="End Time" />;
    },
    cell: ({ row }) => {return row.original.close_time ? new Date(row.original.close_time).toLocaleString() : ""}
  },
];
