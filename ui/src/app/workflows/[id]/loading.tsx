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
  TableRow,
} from "@/components/ui/table";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "@/components/ui/resizable";
import { Skeleton } from "@/components/ui/skeleton";

const SkeletonDataTable = () => {
  const rows = ["row-1", "row-2", "row-3", "row-4", "row-5"];

  return (
    <Table>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={row}>
            <TableCell>
              <Skeleton className="h-5 w-40 mx-auto" />
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
};

const WorkflowLoadingPage = () => {
  return (
    <div className="h-screen">
      <ResizablePanelGroup className="h-full" direction="horizontal">
        <ResizablePanel defaultSize={25}>
          <div className="flex flex-col h-full items-center overflow-auto">
            <span className="font-bold text-lg mb-2">Stages</span>
            <SkeletonDataTable />
          </div>
        </ResizablePanel>
        <ResizableHandle />
        <ResizablePanel>
          <div className="flex w-full h-full items-center justify-center p-6">
            <Card className="w-full h-full justify-center overflow-auto">
              <CardHeader>
                <CardTitle>
                  <Skeleton className="h-6 w-40" />
                </CardTitle>
                <div className="flex space-x-2">
                  <Skeleton className="h-6 w-20" />{" "}
                  <Skeleton className="h-6 w-32" />
                </div>
              </CardHeader>
              <CardContent>
                <>
                  <Skeleton className="h-5 w-24" />{" "}
                  <Skeleton className="h-5 w-full mt-2" />
                </>
                <Accordion type="multiple">
                  <AccordionItem value="item-1">
                    <AccordionTrigger>
                      <Skeleton className="h-6 w-40" />
                    </AccordionTrigger>
                    <AccordionContent>
                      <Table>
                        <TableBody>
                          {["metadata", "inputs", "outputs"].map((row) => (
                            <TableRow key={row}>
                              <TableCell>
                                <Skeleton className="h-5 w-20" />
                              </TableCell>
                              <TableCell>
                                <Skeleton className="h-5 w-32" />
                              </TableCell>
                            </TableRow>
                          ))}
                        </TableBody>
                      </Table>
                    </AccordionContent>
                  </AccordionItem>
                  <AccordionItem value="item-2">
                    <AccordionTrigger>
                      <Skeleton className="h-6 w-20" />
                    </AccordionTrigger>
                    <AccordionContent>
                      <Skeleton className="h-5 w-full" />
                    </AccordionContent>
                  </AccordionItem>
                </Accordion>
              </CardContent>
              <CardFooter>
                <Skeleton className="h-10 w-32" />
                {" "}
              </CardFooter>
            </Card>
          </div>
        </ResizablePanel>
      </ResizablePanelGroup>
    </div>
  );
};

export default WorkflowLoadingPage;
