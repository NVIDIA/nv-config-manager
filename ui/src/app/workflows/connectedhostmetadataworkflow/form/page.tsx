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
import { useToast } from "@/components/ui/use-toast";
import { ConnectedDeviceMetadataWorkflowInput } from "@/types/data-table.types";
import { startWorkflow } from "@/lib/utils";
import {
  DeviceWorkflowForm,
  DeviceWorkflowFormSchema,
} from "@/components/forms/workflow";

const ConnectedHostMetadataWorkflowForm = () => {
  const { toast } = useToast();
  const onSubmit = (data: DeviceWorkflowFormSchema) => {
    const endpoint = "/v1/workflow/ngc/connected_host_metadata";
    const params: ConnectedDeviceMetadataWorkflowInput = {
      device_id: data.device,
    };
    startWorkflow(endpoint, params).catch((error) => {
      toast({
        variant: "destructive",
        title: "Workflow Failed",
        description: `Failed to create workflow: ${error}`,
      });
    });
  };

  return (
    <DeviceWorkflowForm
      title="New Connected Host Metadata Workflow"
      onSubmit={onSubmit}
    />
  );
};

export default ConnectedHostMetadataWorkflowForm;
