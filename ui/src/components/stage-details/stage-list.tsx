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
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import {
  formatTimestamp,
  handleBadgeClassName,
  getInitialStage,
} from "@/lib/utils";
import { StateHistory, WorkflowStage } from "@/types/data-table.types";
import { StagesListProps } from "@/types/stage-details.types";

export const StagesList: React.FC<StagesListProps> = ({
  stages,
  selectedStageName,
  handleClick,
}) => {
  const handleSelect = (stage: WorkflowStage) => {
    handleClick(stage);
  };
  const selectedName = selectedStageName ?? getInitialStage(stages)?.name;

  return (
    <Table>
      <TableHeader>
        <TableRow className="sr-only">
          <TableHead>Workflow stage</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody className="cursor-pointer">
        {stages.length > 0 ? (
          stages.map((stage) => (
            <TableRow
              key={stage.name}
              className={`${
                selectedName === stage.name
                  ? "bg-blue-100 dark:bg-blue-700"
                  : ""
              }`}
            >
              <TableCell className="p-0 text-center">
                <div className="relative">
                  <button
                    type="button"
                    className="absolute inset-0 w-full cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                    aria-label={`Select ${stage.description}`}
                    aria-pressed={selectedName === stage.name}
                    onClick={() => handleSelect(stage)}
                  />
                  <div className="pointer-events-none relative py-4">
                    <div className="space-y-3">
                      <div>
                        <h3 className="font-semibold text-base text-foreground">
                          {stage.description}
                        </h3>
                      </div>
                      <div>
                        <p className="text-sm text-muted-foreground">
                          {formatTimestamp(
                            stage.state_history[stage.state_history.length - 1]
                              .time,
                          )}
                        </p>
                      </div>
                      <div className="flex space-x-2 justify-center">
                        <Badge
                          className={handleBadgeClassName(
                            stage.state as StateHistory["state"],
                          )}
                        >
                          {stage.state}
                        </Badge>
                        {stage.requires_approval &&
                          stage.state == "PENDING_APPROVAL" && (
                            <Badge>Requires Approval</Badge>
                          )}
                      </div>
                    </div>
                  </div>
                </div>
              </TableCell>
            </TableRow>
          ))
        ) : (
          <TableRow>
            <TableCell className="h-24 text-center">No Stages</TableCell>
          </TableRow>
        )}
      </TableBody>
    </Table>
  );
};
