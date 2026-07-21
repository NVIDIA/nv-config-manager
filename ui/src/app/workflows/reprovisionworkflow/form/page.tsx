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
import { ReprovisionWorkflowInput } from "@/types/data-table.types";
import {
  DeviceWorkflowForm,
  DeviceWorkflowFormSchema,
} from "@/components/forms/workflow";
import { startWorkflow } from "@/lib/utils";

const ReprovisionWorkflowForm = () => {
  const { toast } = useToast();
  const onSubmit = (data: DeviceWorkflowFormSchema) => {
    const endpoint = "/v1/workflow/ngc/reprovision";
    const params: ReprovisionWorkflowInput = {
      device_id: data.device,
    };
    startWorkflow(endpoint, params).catch((error) => {
      toast({
        variant: "destructive",
        title: "Workflow Failed",
        description: `${error}`,
      });
    });
  };

  return (
    <DeviceWorkflowForm
      title="New Reprovision Workflow"
      onSubmit={onSubmit}
      deviceFilterParams={[["platform", "Cumulus Linux"], ["platform", "NV-OS"]]}
      destructiveWarning="This workflow is destructive. It will replace all existing configuration on the device with the intended configuration."
    />
  );
};

export default ReprovisionWorkflowForm;
