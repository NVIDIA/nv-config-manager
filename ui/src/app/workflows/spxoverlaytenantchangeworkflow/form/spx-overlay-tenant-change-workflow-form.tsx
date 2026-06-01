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

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Form } from "@/components/ui/form";
import { useToast } from "@/components/ui/use-toast";
import { useEnvData, useDevices } from "@/hooks";
import { WorkflowFormField } from "@/components/forms/formfield";
import { startWorkflow } from "@/lib/utils";
import { SpXOverlayTenantChangeWorkflowInput } from "@/types/data-table.types";

const SpXOverlayTenantChangeFormSchema = z.object({
  site: z.string().trim().min(1, { message: "Site is required" }),
  vpc: z.string().trim().min(1, { message: "VPC is required" }),
  device: z.string().trim().min(1, { message: "Device is required" }),
  port_names: z.string().trim().min(1, { message: "Port names are required" }),
  namespace: z.string().trim().optional(),
});

type SpXOverlayTenantChangeFormData = z.infer<typeof SpXOverlayTenantChangeFormSchema>;

export const SpXOverlayTenantChangeWorkflowForm = () => {
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const { toast } = useToast();
  const searchParams = useSearchParams();
  const querySite = searchParams?.get("site") ?? "";
  const queryVPC = searchParams?.get("vpc") ?? "";
  const queryDevice = searchParams?.get("device-id") ?? "";
  const queryPortNames = searchParams?.get("port_names") ?? "";
  const queryNamespace = searchParams?.get("namespace") ?? "spectrumx";
  const {
    data: { siteData: sites },
    isLoading: { siteIsLoading },
  } = useEnvData();

  const form = useForm<SpXOverlayTenantChangeFormData>({
    resolver: zodResolver(SpXOverlayTenantChangeFormSchema),
    defaultValues: {
      site: querySite,
      vpc: queryVPC,
      device: queryDevice,
      port_names: queryPortNames,
      namespace: queryNamespace,
    },
  });

  const site = form.watch("site");
  const filterParams: [string, string][] = site ? [["site", site]] : [];
  const {
    devices: deviceData,
    error: deviceError,
    isLoading: deviceIsLoading,
  } = useDevices({ site, filterParams });

  if (deviceError) console.error(`Failed to query devices: ${deviceError}`);

  useEffect(() => {
    if (!siteIsLoading && querySite) {
      const siteExists = sites?.some((site) => site.key === querySite);
      if (siteExists) {
        if (!form.getValues("site")) {
          form.setValue("site", querySite);
        }
      } else {
        form.setValue("site", "");
      }
    }
  }, [sites, querySite, siteIsLoading, form]);

  useEffect(() => {
    if (queryDevice) {
      const isDeviceValid = deviceData?.some(
        (device) => device.value === queryDevice
      );
      if (isDeviceValid) {
        if (form.getValues("device") !== queryDevice) {
          form.setValue("device", queryDevice);
        }
      } else if (form.getValues("device") !== "") {
        form.setValue("device", "");
      }
    }
  }, [queryDevice, deviceData, form]);

  useEffect(() => {
    if (site) {
      form.setValue("device", ""); // Clear device when site changes
    }
  }, [site, form]);

  const onSubmit = async (data: SpXOverlayTenantChangeFormData): Promise<void> => {
    setIsSubmitting(true);
    // Transform comma-separated port names to array
    const portNamesArray = data.port_names
      .split(",")
      .map((p) => p.trim())
      .filter((p) => p.length > 0);
    const submissionData: SpXOverlayTenantChangeWorkflowInput = {
      site: data.site,
      vpc_id: data.vpc,
      device_id: data.device,
      port_names: portNamesArray,
      namespace_tag: data.namespace,
    };
    await startWorkflow(
      "/v1/workflow/ngc/spx-overlay-tenant-change",
      submissionData
    ).catch((error) => {
      toast({
        variant: "destructive",
        title: "SpX Overlay Tenant Change Workflow Failed",
        description: error,
      });
    });
    setIsSubmitting(false);
  };

  return (
    <div className="flex items-center justify-center p-6">
      <Card className="h-full border-2 shadow-md justify-center">
        <CardHeader>
          <CardTitle>SpX Overlay Tenant Change Workflow Form</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <WorkflowFormField
                type="select"
                control={form.control}
                name="site"
                label="Site"
                options={sites}
                isLoading={siteIsLoading}
                isSubmitting={isSubmitting}
                disabled={isSubmitting || deviceIsLoading}
              />
              <WorkflowFormField
                type="input"
                control={form.control}
                name="vpc"
                label="VPC ID"
                isSubmitting={isSubmitting}
              />
              <WorkflowFormField
                type="select"
                control={form.control}
                name="device"
                label="Device"
                options={deviceData}
                isLoading={deviceIsLoading || siteIsLoading}
                isSubmitting={isSubmitting}
                disabled={!site || isSubmitting || deviceIsLoading}
              />
              <WorkflowFormField
                type="input"
                control={form.control}
                name="port_names"
                label="Port Names (comma-separated)"
                placeholder="swp1, swp2, swp3"
                isSubmitting={isSubmitting}
                disabled={!site || !form.watch("device") || isSubmitting}
              />
              <WorkflowFormField
                type="input"
                control={form.control}
                name="namespace"
                label="Namespace (optional)"
                isSubmitting={isSubmitting}
              />
              <Button
                type="submit"
                disabled={
                  isSubmitting ||
                  !site ||
                  !form.watch("vpc") ||
                  !form.watch("device") ||
                  !form.watch("port_names") ||
                  deviceIsLoading ||
                  siteIsLoading
                }
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
