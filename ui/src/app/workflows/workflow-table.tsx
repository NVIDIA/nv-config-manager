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
import Link from "next/link";
import { DataTable } from "@/components/data-table/data-table";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import { workflowColumns } from "./columns";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { WorkflowTableProps } from "@/types/data-table.types";
import { siteConfig } from "@/config/site";

const WorkflowTable: React.FC<WorkflowTableProps> = ({
  title,
  workflowType,
}) => {
  const enableWorkflowFormCreation = siteConfig.workflows.find(
    (workflow) =>
      workflow.slug.includes(title.toLowerCase()) && workflow.enabled,
  );

  return (
    <Card className="mt-4 w-full" key={title}>
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="space-y-4">
          <CardTitle className="mr-4">{title}</CardTitle>
        </div>
        {enableWorkflowFormCreation ? (
          <Link
            className="btn-primary"
            href={`workflows/${title.toLowerCase()}/form`}
          >
            New Workflow
          </Link>
        ) : (
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <div className="cursor-not-allowed">
                  <Button
                    className="btn-primary pointer-events-none"
                    disabled
                    variant="default"
                  >
                    New Workflow
                  </Button>
                </div>
              </TooltipTrigger>
              <TooltipContent side="left">
                <p>Form Coming Soon!</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        )}
      </CardHeader>
      <CardContent>
        <DataTable columns={workflowColumns} workflowType={workflowType} />
      </CardContent>
    </Card>
  );
};

export default WorkflowTable;
