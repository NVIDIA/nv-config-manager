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
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

const WorkflowsListSkeleton = () => {
  const workflowTypes = ["Type 1", "Type 2", "Type 3"];

  return (
    <Accordion type="multiple" defaultValue={workflowTypes}>
      {workflowTypes.map((type) => (
        <AccordionItem value={type} key={type}>
          <AccordionTrigger>
            <div className="p-3 font-bold text-lg">
              <Skeleton className="h-6 w-24" />
            </div>
          </AccordionTrigger>
          <AccordionContent>
            <SkeletonWorkflowTable />
          </AccordionContent>
        </AccordionItem>
      ))}
    </Accordion>
  );
};

const SkeletonWorkflowTable = () => {
  return (
    <Card className="mt-4 w-full">
      <CardHeader className="flex flex-row items-center justify-between">
        <div className="space-y-4">
          <CardTitle className="mr-4">
            <Skeleton className="h-6 w-24" />
          </CardTitle>
          <div className="flex items-center space-x-2">
            <Skeleton className="h-5 w-20" />
          </div>
        </div>
        <Skeleton className="h-10 w-24" />
      </CardHeader>
      <CardContent>
        <SkeletonDataTable />
      </CardContent>
    </Card>
  );
};

const SkeletonDataTable = () => {
  const columns = ["Column 1", "Column 2", "Column 3"];

  return (
    <Table>
      <TableHeader>
        <TableRow>
          {columns.map((_, index) => (
            <TableHead key={index}>
              <Skeleton className="h-5 w-24" />
            </TableHead>
          ))}
        </TableRow>
      </TableHeader>
      <TableBody>
        {[1, 2, 3, 4, 5].map((_, rowIndex) => (
          <TableRow key={rowIndex}>
            {columns.map((_, colIndex) => (
              <TableCell key={colIndex}>
                <Skeleton className="h-5 w-24" />
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};

export default WorkflowsListSkeleton;
