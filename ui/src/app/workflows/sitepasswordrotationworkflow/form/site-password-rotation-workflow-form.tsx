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
import useSWR from "swr";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Form } from "@/components/ui/form";
import { useToast } from "@/components/ui/use-toast";
import { SitePasswordRotationWorkflowInput } from "@/types/data-table.types";
import { useEnvData, useDevices } from "@/hooks";
import { startWorkflow, sanitizeUrl } from "@/lib/utils";
import { useRuntimeConfig } from "@/config/runtime";
import { WorkflowFormField } from "@/components/forms/formfield";
import { fetcher } from "@/lib/fetcher";

const SitePasswordRotationWorkflowFormSchema = z.object({
  location: z.string().trim().min(1, { message: "Location is required" }),
  selected_secret: z.string().trim().min(1, { message: "Secret is required" }),
  roles: z.union([z.string(), z.array(z.string())])
    .transform((val: string | string[]) => (Array.isArray(val) ? val : []))
    .pipe(z.array(z.string()).min(1, { message: "Roles is required" })),
  status: z.union([z.string(), z.array(z.string())])
    .transform((val: string | string[]) => (Array.isArray(val) ? val : []))
    .pipe(z.array(z.string()).min(1, { message: "Device Status is required" })),
  tenant: z.string().trim().min(1, { message: "Tenant is required" }),
});

export const SitePasswordRotationWorkflowForm = () => {
  const [isSubmitting, setIsSubmitting] = React.useState<boolean>(false);
  const [isManualChange, setIsManualChange] = React.useState<boolean>(false);
  const { config: runtimeConfig } = useRuntimeConfig();
  const { data: envData } = useEnvData();
  const { toast } = useToast();
  const searchParams = useSearchParams();
  
  // Get query parameters
  const queryLocation = searchParams && searchParams.get("location");
  const querySecret = searchParams && searchParams.get("selected_secret");
  const queryRoles = React.useMemo(() => searchParams ? searchParams.getAll("role") : [], [searchParams]);
  const queryStatuses = React.useMemo(() => searchParams ? searchParams.getAll("status") : [], [searchParams]);
  const queryTenant = searchParams && searchParams.get("tenant");

  const form = useForm<z.infer<typeof SitePasswordRotationWorkflowFormSchema>>({
    resolver: zodResolver(SitePasswordRotationWorkflowFormSchema),
    defaultValues: {
      location: queryLocation || "",
      selected_secret: querySecret || "",
      roles: queryRoles,
      status: queryStatuses,
      tenant: queryTenant || "",
    },
  });

  // Get form values for filtering
  const location = form.watch("location");
  const roles = form.watch("roles");
  const status = form.watch("status");
  const tenant = form.watch("tenant");

  // Build filter parameters for device API
  const filterParams = React.useMemo(() => {
    const params: string[][] = [];
    if (location) params.push(["site", location]);
    if (roles?.length) {
      roles.forEach(role => params.push(["role", role]));
    }
    if (status?.length) {
      status.forEach(stat => params.push(["status", stat]));
    }
    if (tenant) params.push(["tenant", tenant]);
    return params;
  }, [location, roles, status, tenant]);

  const { devices, isLoading: devicesLoading } = useDevices({
    site: location,
    filterParams: filterParams
  });

  const firstDeviceId = devices && devices.length > 0 && !devicesLoading ? devices[0].value : null;

  const { data: passwordUsers } = useSWR(
    firstDeviceId && !devicesLoading && runtimeConfig ? sanitizeUrl(`${runtimeConfig.workflowApiUrl}/v1/parameter/device/${firstDeviceId}/password_users`) : null,
    fetcher
  );

  const secretOptions = React.useMemo(() => {
    if (!passwordUsers) return [];
    return passwordUsers.map((user: { name: string; description: string }) => ({
      value: user.name,
      key: user.name
    }));
  }, [passwordUsers]);

  React.useEffect(() => {
    form.setValue("selected_secret", "");
  }, [location, roles, status, tenant, form]);

  React.useEffect(() => {
    if (!isManualChange) {
      const validateAndSetValue = (
        queryValue: string | string[] | null,
        data: { key: string; value: string }[],
        fieldName: keyof z.infer<typeof SitePasswordRotationWorkflowFormSchema>
      ) => {
        if (
          !queryValue ||
          (Array.isArray(queryValue) && queryValue.length === 0)
        ) {
          return;
        }

        if (Array.isArray(queryValue)) {
          const validValues = queryValue.filter((value) =>
            data.some((option) => option.key === value)
          );
          if (validValues.length > 0) {
            form.setValue(fieldName, validValues);
          }
        } else {
          const isValid = data.some((option) => option.key === queryValue);
          if (isValid) {
            const validValue = data.find((option) => option.key === queryValue)?.value || queryValue;
            form.setValue(fieldName, validValue);
          }
        }
      };

      validateAndSetValue(queryLocation, envData.siteData, "location");
      validateAndSetValue(queryRoles, envData.rolesData, "roles");
      validateAndSetValue(queryStatuses, envData.statusData, "status");
      validateAndSetValue(queryTenant, envData.tenantsData, "tenant");
    }
  }, [
    queryLocation,
    queryRoles,
    queryStatuses,
    queryTenant,
    envData,
    form,
    isManualChange,
  ]);

  const onSubmit = async (data: z.infer<typeof SitePasswordRotationWorkflowFormSchema>) => {
    setIsSubmitting(true);
    
    const workflowParams: SitePasswordRotationWorkflowInput = {
      location: data.location,
      selected_secret: data.selected_secret,
      roles: data.roles,
      status: data.status,
      tenant: data.tenant,
    };

    try {
      await startWorkflow(
        "/v1/workflow/ngc/site_password_rotation",
        workflowParams
      );
      toast({
        title: "Workflow Started",
        description: "Site password rotation workflow has been initiated.",
      });
      form.reset();
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Workflow Failed",
        description: `Failed to create workflow: ${error}`,
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleChange = () => {
    setIsManualChange(true);
  };

  return (
    <div className="flex items-center justify-center p-6">
      <Card className="w-full max-w-4xl border-2 shadow-md">
        <CardHeader>
          <CardTitle>Site Password Rotation Workflow</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
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
                name="roles"
                label="Roles"
                options={envData.rolesData}
                isSubmitting={isSubmitting}
                handleChange={handleChange}
                multiple={true}
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

              {/* Device count and status info */}
              {location && (
                <div className="text-sm text-muted-foreground mb-4">
                  {devicesLoading ? (
                    <div className="flex items-center gap-2">
                      <div className="animate-spin h-4 w-4 border-2 border-primary border-t-transparent rounded-full"></div>
                      Loading devices...
                    </div>
                  ) : devices && devices.length > 0 ? (
                    <div className="text-green-600">
                      ✓ Found {devices.length} matching device{devices.length !== 1 ? 's' : ''}
                    </div>
                  ) : (
                    <div className="text-amber-600">
                      ⚠ No devices found matching the selected criteria
                    </div>
                  )}
                </div>
              )}

              <WorkflowFormField
                type="select"
                control={form.control}
                name="selected_secret"
                label={
                  !location 
                    ? "Secret to Rotate (select location first)"
                    : devicesLoading 
                    ? "Secret to Rotate (loading devices...)"
                    : !firstDeviceId 
                    ? "Secret to Rotate (no matching devices)"
                    : secretOptions.length === 0
                    ? "Secret to Rotate (loading secrets...)"
                    : "Secret to Rotate"
                }
                options={secretOptions}
                disabled={!firstDeviceId || isSubmitting}
                isSubmitting={isSubmitting}
                handleChange={handleChange}
              />
              
              <Button 
                type="submit" 
                disabled={isSubmitting}
              >
                {isSubmitting ? "Submitting..." : "Submit"}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
};