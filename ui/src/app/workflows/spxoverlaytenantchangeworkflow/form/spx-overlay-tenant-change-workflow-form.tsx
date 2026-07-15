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
import {
  SPX_OVERLAY_ISOLATION_TYPE,
  useDeviceInterfaces,
  useEnvData,
  useDevices,
  useOverlays,
  useSyncSelectFromQuery,
} from "@/hooks";
import { WorkflowFormField } from "@/components/forms/formfield";
import { getErrorMessage, startWorkflow } from "@/lib/utils";
import { SpXOverlayTenantChangeWorkflowInput } from "@/types/data-table.types";

const SpXOverlayTenantChangeFormSchema = z.object({
  site: z.string().trim().min(1, { message: "Site is required" }),
  overlay_id: z.string().trim(),
  device: z.string().trim().min(1, { message: "Device is required" }),
  port_names: z
    .array(z.string())
    .min(1, { message: "At least one port is required" }),
});

type SpXOverlayTenantChangeFormData = z.infer<typeof SpXOverlayTenantChangeFormSchema>;

export const SpXOverlayTenantChangeWorkflowForm = () => {
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const { toast } = useToast();
  const searchParams = useSearchParams();
  const querySite = searchParams?.get("site") ?? "";
  const queryOverlayId = searchParams?.get("overlay_id") ?? "";
  const queryDevice = searchParams?.get("device-id") ?? "";
  const queryPortNames = (searchParams?.get("port_names") ?? "")
    .split(",")
    .map((portName) => portName.trim())
    .filter(Boolean);
  const {
    data: { siteData: sites },
    isLoading: { siteIsLoading },
  } = useEnvData();

  const form = useForm<SpXOverlayTenantChangeFormData>({
    resolver: zodResolver(SpXOverlayTenantChangeFormSchema),
    defaultValues: {
      site: querySite,
      overlay_id: queryOverlayId,
      device: queryDevice,
      port_names: queryPortNames,
    },
  });

  const site = form.watch("site");
  const device = form.watch("device");
  const filterParams: [string, string][] = site
    ? [
        ["site", site],
        ["managed_only", "true"],
      ]
    : [];
  const {
    devices: deviceData,
    error: deviceError,
    isLoading: deviceIsLoading,
  } = useDevices({ site, filterParams });
  const {
    interfaces: deviceInterfaces,
    error: deviceInterfacesError,
    isLoading: deviceInterfacesAreLoading,
  } = useDeviceInterfaces(device);
  const {
    overlays: spxOverlays,
    hasLoaded: spxOverlaysHaveLoaded,
    isLoading: spxOverlaysAreLoading,
  } = useOverlays({
    enabled: Boolean(site),
    isolationType: SPX_OVERLAY_ISOLATION_TYPE,
    location: site,
  });

  if (deviceError) console.error(`Failed to query devices: ${deviceError}`);
  if (deviceInterfacesError) {
    console.error(`Failed to query device interfaces: ${deviceInterfacesError}`);
  }

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

  useSyncSelectFromQuery({
    fieldName: "overlay_id",
    form,
    hasLoaded: spxOverlaysHaveLoaded,
    isLoading: spxOverlaysAreLoading,
    options: spxOverlays,
    queryValue: queryOverlayId,
  });

  const onSubmit = async (data: SpXOverlayTenantChangeFormData): Promise<void> => {
    setIsSubmitting(true);
    const submissionData: SpXOverlayTenantChangeWorkflowInput = {
      site: data.site,
      overlay_id: data.overlay_id || null,
      device_id: data.device,
      port_names: data.port_names,
    };
    await startWorkflow(
      "/v1/workflow/ngc/spx_overlay_tenant_change",
      submissionData
    ).catch((error) => {
      toast({
        variant: "destructive",
        title: "SpX Overlay Tenant Change Workflow Failed",
        description: getErrorMessage(error),
      });
    });
    setIsSubmitting(false);
  };

  return (
    <div className="flex items-center justify-center p-6">
      <Card className="h-full border-2 shadow-md justify-center">
        <CardHeader>
          <CardTitle>New SpX Overlay Tenant Change Workflow</CardTitle>
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
                handleChange={() => {
                  form.setValue("device", "");
                  form.setValue("overlay_id", "");
                  form.setValue("port_names", []);
                }}
              />
              <WorkflowFormField
                type="select"
                control={form.control}
                name="overlay_id"
                label="Overlay ID (optional — leave blank to remove)"
                options={spxOverlays}
                isLoading={spxOverlaysAreLoading}
                isSubmitting={isSubmitting}
                disabled={!site}
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
                handleChange={() => form.setValue("port_names", [])}
              />
              <WorkflowFormField
                type="select"
                control={form.control}
                name="port_names"
                label="Ports"
                options={deviceInterfaces}
                multiple={true}
                searchable={true}
                isLoading={deviceInterfacesAreLoading}
                isSubmitting={isSubmitting}
                disabled={!site || !device || isSubmitting}
              />
              <Button
                type="submit"
                disabled={
                  isSubmitting ||
                  !site ||
                  !device ||
                  form.watch("port_names").length === 0 ||
                  deviceIsLoading ||
                  deviceInterfacesAreLoading ||
                  spxOverlaysAreLoading ||
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
