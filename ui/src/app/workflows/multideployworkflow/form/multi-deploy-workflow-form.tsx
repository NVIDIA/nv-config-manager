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
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
} from "@/components/ui/form";
import { useToast } from "@/components/ui/use-toast";
import { Checkbox } from "@/components/ui/checkbox";
import { WorkflowFormField } from "@/components/forms/formfield";
import { useEnvData } from "@/hooks";
import { startWorkflow } from "@/lib/utils";
import { MultiDeployWorkflowInput } from "@/types/data-table.types";

const multiDeployFormSchema = z.object({
  role: z.string().trim().min(1, { message: "Role is required" }),
  max_batch_size: z.coerce
    .number()
    .min(1, { message: "Batch size must be at least 1" })
    .max(100, { message: "Batch size cannot exceed 100" })
    .default(10),
  location: z.string().trim().optional(),
  status: z
    .union([z.string(), z.array(z.string())])
    .transform((val) => (Array.isArray(val) ? val : []))
    .pipe(z.array(z.string()))
    .optional(),
  tenant: z.string().trim().optional(),
  commit_confirm: z.boolean().optional().default(true),
});

type MultiDeployFormData = z.infer<typeof multiDeployFormSchema>;

export const MultiDeployWorkflowForm = () => {
  const [isSubmitting, setIsSubmitting] = React.useState<boolean>(false);
  const [isManualChange, setIsManualChange] = React.useState<boolean>(false);
  const { data: envData } = useEnvData();
  const { toast } = useToast();
  const searchParams = useSearchParams();

  const queryRole = searchParams && searchParams.get("role");
  const queryBatchSize = searchParams && searchParams.get("max_batch_size");
  const queryLocation = searchParams && searchParams.get("location");
  const queryStatuses = React.useMemo(() => searchParams ? searchParams.getAll("status") : [], [searchParams]);
  const queryTenant = searchParams && searchParams.get("tenant");

  const form = useForm<MultiDeployFormData>({
    resolver: zodResolver(multiDeployFormSchema),
    defaultValues: {
      role: "",
      max_batch_size: 10,
      location: "",
      status: [],
      tenant: "",
      commit_confirm: true,
    },
  });

  React.useEffect(() => {
    if (!isManualChange) {
      const validateAndSetValue = (
        queryValue: string | string[] | null,
        data: { key: string; value: string }[],
        fieldName: "role" | "location" | "status" | "tenant"
      ) => {
        if (
          !queryValue ||
          (Array.isArray(queryValue) && queryValue.length === 0)
        ) {
          if (fieldName === "status") {
            form.setValue(fieldName, []);
          } else {
            form.setValue(fieldName, "");
          }
          return;
        }

        if (Array.isArray(queryValue)) {
          // For multi-select fields like status
          const validValues = queryValue.filter((value) =>
            data.some((option) => option.key === value)
          );
          form.setValue(
            fieldName as "status",
            validValues.length > 0 ? validValues : []
          );
        } else {
          // For single-value fields - store the key, not the display value
          const isValid = data.some((option) => option.key === queryValue);
          form.setValue(fieldName as "role" | "location" | "tenant", isValid ? queryValue : "");
        }
      };

      validateAndSetValue(queryRole, envData.rolesData, "role");
      validateAndSetValue(queryLocation, envData.siteData, "location");
      validateAndSetValue(queryStatuses, envData.statusData, "status");
      validateAndSetValue(queryTenant, envData.tenantsData, "tenant");

      if (queryBatchSize) {
        const batchSize = parseInt(queryBatchSize);
        if (!isNaN(batchSize) && batchSize >= 1 && batchSize <= 100) {
          form.setValue("max_batch_size", batchSize);
        } else {
          form.setValue("max_batch_size", 10);
        }
      }
    }
  }, [
    queryRole,
    queryBatchSize,
    queryLocation,
    queryStatuses,
    queryTenant,
    envData,
    form,
    isManualChange,
  ]);

  const handleChange = () => {
    setIsManualChange(true);
  };

  const onSubmit = async (data: MultiDeployFormData) => {
    setIsSubmitting(true);
    const endpoint = "/v1/workflow/ngc/multi_deploy";
    const params: MultiDeployWorkflowInput = {
      role: data.role,
      max_batch_size: data.max_batch_size || 10,
      location: data.location?.trim() || null,
      status: data.status && data.status.length > 0 ? data.status : null,
      tenant: data.tenant?.trim() || null,
      commit_confirm: data.commit_confirm ?? true,
    } as MultiDeployWorkflowInput;

    try {
      await startWorkflow(endpoint, params);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Workflow Failed",
        description: `Failed to create workflow: ${error}`,
      });
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex items-center justify-center p-6">
      <Card className="h-full border-2 shadow-md justify-center">
        <CardHeader>
          <CardTitle>Multi-Deploy Workflow Form</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <WorkflowFormField
                type="select"
                control={form.control}
                name="role"
                label="Role"
                options={envData.rolesData}
                isSubmitting={isSubmitting}
                handleChange={handleChange}
                multiple={false}
              />
              <WorkflowFormField
                type="number"
                control={form.control}
                name="max_batch_size"
                label="Max Batch Size"
                placeholder="10"
                isSubmitting={isSubmitting}
                handleChange={handleChange}
              />
              <WorkflowFormField
                type="select"
                control={form.control}
                name="location"
                label="Location"
                options={envData.siteData}
                isSubmitting={isSubmitting}
                handleChange={handleChange}
              />
              <WorkflowFormField
                type="select"
                control={form.control}
                name="status"
                label="Device Status"
                options={envData.statusData}
                isSubmitting={isSubmitting}
                handleChange={handleChange}
                multiple={true}
              />
              <WorkflowFormField
                type="select"
                control={form.control}
                name="tenant"
                label="Tenant"
                options={envData.tenantsData}
                isSubmitting={isSubmitting}
                handleChange={handleChange}
              />
              <FormField
                control={form.control}
                name="commit_confirm"
                render={({ field }) => (
                  <FormItem className="flex flex-row items-start space-x-3 space-y-0">
                    <FormControl>
                      <Checkbox
                        checked={field.value}
                        onCheckedChange={field.onChange}
                        disabled={isSubmitting}
                      />
                    </FormControl>
                    <div className="space-y-1 leading-none">
                      <FormLabel>Use commit-confirm</FormLabel>
                      <FormDescription>
                        Rollback if device becomes unreachable after apply.
                        Disable for changes that are expected to interrupt connectivity.
                      </FormDescription>
                    </div>
                  </FormItem>
                )}
              />
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Submitting..." : "Submit"}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
};
