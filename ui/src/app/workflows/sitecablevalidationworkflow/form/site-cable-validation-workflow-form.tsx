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
} from "@/components/ui/form";
import { useToast } from "@/components/ui/use-toast";
import { SiteCableValidationWorkflowInput } from "@/types/data-table.types";
import { useEnvData } from "@/hooks";
import { getErrorMessage, startWorkflow } from "@/lib/utils";
import { WorkflowFormField } from "@/components/forms/formfield";

export const SiteCableValidationWorkflowForm = () => {

  const SiteCableValidationFormSchema = z.object({
    site: z.string().trim().min(1, { message: "Site is required" }),
    roles: z.union([z.string(), z.array(z.string())])
      .transform((val) => (Array.isArray(val) ? val : []))
      .pipe(z.array(z.string()).min(1, { message: "Roles is required" })),
    status: z.union([z.string(), z.array(z.string())])
      .transform((val) => (Array.isArray(val) ? val : []))
      .pipe(z.array(z.string()).min(1, { message: "Device Status is required" })),
    tenant: z.string().trim().min(1, { message: "Tenant is required" }),
  });

  const [isSubmitting, setIsSubmitting] = React.useState<boolean>(false);
  const [isManualChange, setIsManualChange] = React.useState<boolean>(false);
  const { data: siteCableData } = useEnvData();
  const { toast } = useToast();
  const searchParams = useSearchParams();
  const querySite = searchParams?.get("site");
  const queryRoles = React.useMemo(() => searchParams?.getAll("role") ?? [], [searchParams]);
  const queryStatuses = React.useMemo(() => searchParams?.getAll("status") ?? [], [searchParams]);
  const queryTenant = searchParams?.get("tenant");

  const form = useForm<z.infer<typeof SiteCableValidationFormSchema>>({
    resolver: zodResolver(SiteCableValidationFormSchema),
  });

  // NOTE: might need this to change the api route look at Workflow.tsx. Revist when rest of api routes are defined.
  //const filterParams = [["site", site], ...deviceFilterParams];
  //const params = new URLSearchParams(filterParams).toString();
  React.useEffect(() => {
    if (!isManualChange) {
      const validateAndSetValue = (
        queryValue: string | string[] | null,
        data: { key: string; value: string }[],
        fieldName: keyof z.infer<typeof SiteCableValidationFormSchema>
      ) => {
        if (
          !queryValue ||
          (Array.isArray(queryValue) && queryValue.length === 0)
        ) {
          form.setValue(fieldName, ""); // Clear if no query value
          return;
        }

        if (Array.isArray(queryValue)) {
          // For fields like roles, status, and device_type_ids
          const validValues = queryValue.filter((value) =>
            data.some((option) => option.key === value)
          );
          form.setValue(fieldName, validValues.length > 0 ? validValues : "");
        } else {
          // For single-value fields like site and tenant
          const isValid = data.some((option) => option.key === queryValue);
          const validValue =
            data.find((option) => option.key === queryValue)?.value || "";
          form.setValue(fieldName, isValid ? validValue : "");
        }
      };

      validateAndSetValue(querySite, siteCableData.siteData, "site");
      validateAndSetValue(queryRoles, siteCableData.rolesData, "roles");
      validateAndSetValue(queryStatuses, siteCableData.statusData, "status");
      validateAndSetValue(queryTenant, siteCableData.tenantsData, "tenant");
    }
  }, [
    querySite,
    queryRoles,
    queryStatuses,
    queryTenant,
    siteCableData,
    form,
    isManualChange,
  ]);

  const onSubmit = async(data: z.infer<typeof SiteCableValidationFormSchema>) => {
      setIsSubmitting(true);
      const workflowParams: SiteCableValidationWorkflowInput = {
        site: data.site,
        roles: data.roles,
        status: data.status,
        tenant: data.tenant,
        // Hardcode these values, not relevant to end users
        // only for advanced scenarios
        device_type_ids: [],
        raise_for_invalid: false,
      };

      await startWorkflow(
        "/v1/workflow/ngc/site_cable_validation",
        workflowParams
      ).catch((error) => {
        toast({
          variant: "destructive",
          title: "Workflow Failed",
        description: getErrorMessage(error),
      });
    });
    setIsSubmitting(false);
  };

  const handleChange = () => {
    setIsManualChange(true);
  };

  return (
    <div className="flex items-center justify-center p-6">
      <Card className="h-full border-2 shadow-md justify-center">
        <CardHeader>
          <CardTitle>New Site Cable Validation Workflow</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <WorkflowFormField
                type="select"
                control={form.control}
                name="site"
                label="Site"
                options={siteCableData.siteData}
                isSubmitting={isSubmitting}
                handleChange={handleChange}
              />
              <WorkflowFormField
                type="select"
                control={form.control}
                name="roles"
                label="Roles"
                options={siteCableData.rolesData}
                isSubmitting={isSubmitting}
                handleChange={handleChange}
                multiple={true}
              />
              <WorkflowFormField
                type="select"
                control={form.control}
                name="status"
                label="Device Status"
                options={siteCableData.statusData}
                isSubmitting={isSubmitting}
                handleChange={handleChange}
                multiple={true}
              />
              <WorkflowFormField
                type="select"
                control={form.control}
                name="tenant"
                label="Tenant"
                options={siteCableData.tenantsData}
                isSubmitting={isSubmitting}
                handleChange={handleChange}
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
