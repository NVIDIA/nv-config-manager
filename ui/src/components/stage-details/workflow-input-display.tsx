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
import { Workflow } from "@/types/data-table.types";

interface WorkflowInputDisplayProps {
  workflow: Workflow;
}

const WorkflowInputDisplay: React.FC<WorkflowInputDisplayProps> = ({
  workflow,
}) => {
  if (!workflow?.workflow_input || Object.keys(workflow.workflow_input).length === 0) {
    return (
      <div className="text-sm text-muted-foreground p-4 text-center">
        No input parameters available
      </div>
    );
  }

  return (
    <pre className="text-xs bg-muted p-4 rounded overflow-x-auto max-w-full whitespace-pre-wrap">
      {JSON.stringify(workflow.workflow_input, null, 2)}
    </pre>
  );
};

export default WorkflowInputDisplay;