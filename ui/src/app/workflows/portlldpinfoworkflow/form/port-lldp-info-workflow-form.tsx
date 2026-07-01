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
import { getErrorMessage, startWorkflow } from "@/lib/utils";
import { WorkflowFormField } from "@/components/forms/formfield";
import { PortLLDPInfoWorkflowInput } from "@/types/data-table.types";
import { DeviceOption } from "@/types/workflow-form.types";

const PortLLDPFormSchema = z
  .object({
    site: z.string().trim(),
    device: z.string().trim(),
    interface: z.string().trim(),
    remote_mac_address: z.string().trim(),
  })
  .superRefine((data, ctx) => {
    const hasAllDeviceInfo = Boolean(
      data.site && data.device && data.interface
    );
    const hasMacAddress = Boolean(data.remote_mac_address);

    // Case 1: Neither complete device info nor MAC address
    if (!hasAllDeviceInfo && !hasMacAddress) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message:
          "Please provide either all device information or a MAC address",
        path: ["remote_mac_address"],
      });
    }

    // Case 2: Partial device info (some fields filled but not all)
    if ((data.site || data.device || data.interface) && !hasAllDeviceInfo) {
      if (!data.site) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Site is required when providing device information",
          path: ["site"],
        });
      }
      if (!data.device) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Device is required when providing device information",
          path: ["device"],
        });
      }
      if (!data.interface) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: "Interface is required when providing device information",
          path: ["interface"],
        });
      }
    }

    // Case 3: Both device info and MAC address provided
    if (hasAllDeviceInfo && hasMacAddress) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message:
          "Please provide either device information OR MAC address, not both",
        path: ["remote_mac_address"],
      });
    }
  });

export const PortLLDPInfoWorkflowForm = () => {
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const [isManualChange, setIsManualChange] = useState<boolean>(false);
  const [hasDeviceInfo, setHasDeviceInfo] = useState<boolean>(false);
  const [hasMacAddress, setHasMacAddress] = useState<boolean>(false);
  const { toast } = useToast();
  const searchParams = useSearchParams();
  const querySite = (searchParams && searchParams.get("site")) || "";
  const queryDevice = (searchParams && searchParams.get("device-id")) || "";
  const queryInterface = (searchParams && searchParams.get("interface")) || "";
  const queryMacAddress =
    (searchParams && searchParams.get("remote_mac_address")) || "";
  const {
    data: { siteData: sites },
    isLoading: { siteIsLoading },
  } = useEnvData();
  const form = useForm<z.infer<typeof PortLLDPFormSchema>>({
    resolver: zodResolver(PortLLDPFormSchema),
    defaultValues: {
      site: querySite,
      device: queryDevice,
      interface: queryInterface,
      remote_mac_address: queryMacAddress,
    },
  });

  const watchSite = form.watch("site") as string;
  const watchDevice = form.watch("device") as string;
  const watchInterface = form.watch("interface") as string;
  const watchMacAddress = form.watch("remote_mac_address") as string;

  const filterParams: string[][] = [
    ["site", watchSite],
    ["managed_only", "true"],
  ];
  const { devices: deviceData, isLoading: deviceIsLoading } = useDevices({
    site: watchSite,
    filterParams,
  });

  useEffect(() => {
    if (querySite && !isManualChange) {
      const isSiteValid = sites.some((option) => option.key === querySite);
      const siteId = sites.find((option) => option.key === querySite)?.value;

      if (!isSiteValid) {
        if (form.getValues("site") !== "") {
          form.setValue("site", ""); // Clear site if invalid
        }
        if (form.getValues("device") !== "") {
          form.setValue("device", ""); // Clear device if site is invalid
        }
      } else {
        if (siteId && form.getValues("site") !== siteId && !hasMacAddress) {
          form.setValue("site", siteId); // Set valid site from URL
        }
      }
    }
  }, [querySite, sites, form, isManualChange, hasMacAddress]);

  useEffect(() => {
    if (deviceData && queryDevice && !isManualChange) {
      const isDeviceValid = deviceData.some(
        (item: DeviceOption) => item.value === queryDevice
      );

      if (isDeviceValid) {
        if (form.getValues("device") !== queryDevice && !hasMacAddress) {
          form.setValue("device", queryDevice); // Set valid device from URL
        }
      } else {
        if (form.getValues("device") !== "") {
          form.setValue("device", ""); // Clear device if invalid
        }
      }
    }
  }, [queryDevice, deviceData, form, isManualChange, hasMacAddress]);

  useEffect(() => {
    form.setValue("device", "");
    console.log("changing");
  }, [watchSite, form]);

  useEffect(() => {
    if (queryMacAddress) {
      form.reset({
        site: "",
        device: "",
        interface: "",
        remote_mac_address: queryMacAddress,
      });
      setHasMacAddress(true);
      setHasDeviceInfo(false);
    } else if (querySite || queryDevice || queryInterface) {
      form.reset({
        site: querySite,
        device: queryDevice,
        interface: queryInterface,
        remote_mac_address: "",
      });
      setHasMacAddress(false);
      setHasDeviceInfo(true);
    }
  }, [queryMacAddress, querySite, queryDevice, queryInterface, form]);

  useEffect(() => {
    if (!isManualChange) return;

    const hasDeviceFields = Boolean(watchSite || watchDevice || watchInterface);
    const hasMacField = Boolean(watchMacAddress);

    if (hasMacField) {
      form.setValue("site", "");
      form.setValue("device", "");
      form.setValue("interface", "");
      setHasDeviceInfo(false);
      setHasMacAddress(true);
    }

    if (hasDeviceFields) {
      form.setValue("remote_mac_address", "");
      setHasMacAddress(false);
      setHasDeviceInfo(true);
    }
  }, [
    watchSite,
    watchDevice,
    watchInterface,
    watchMacAddress,
    isManualChange,
    form,
  ]);

  const handleChange = (fieldName: string, value: string) => {
    setIsManualChange(true);

    if (fieldName === "remote_mac_address") {
      if (value) {
        // If MAC address is being entered
        setHasMacAddress(true);
        setHasDeviceInfo(false);
        form.setValue("site", "");
        form.setValue("device", "");
        form.setValue("interface", "");
      } else {
        // If MAC address is being cleared
        setHasMacAddress(false);
        setHasDeviceInfo(false);
      }
    } else {
      // For site, device, or interface fields
      if (value) {
        setHasMacAddress(false);
        setHasDeviceInfo(true);
        form.setValue("remote_mac_address", "");
      } else {
        // Check all device fields after this change
        const currentValues = {
          site: fieldName === "site" ? "" : form.getValues("site"),
          device: fieldName === "device" ? "" : form.getValues("device"),
          interface:
            fieldName === "interface" ? "" : form.getValues("interface"),
        };

        // Only disable MAC if any device fields are filled
        const hasAnyDeviceField = Object.values(currentValues).some(
          (val) => val
        );
        setHasDeviceInfo(hasAnyDeviceField);
      }
    }
  };

  const onSubmit = async (data: z.infer<typeof PortLLDPFormSchema>) => {
    setIsSubmitting(true);

    const submissionData: PortLLDPInfoWorkflowInput = data.remote_mac_address
      ? { remote_mac_address: data.remote_mac_address }
      : {
          device_id: data.device,
          interface: data.interface,
        };

    await startWorkflow(
      "/v1/workflow/ngc/port_lldp_info",
      submissionData
    ).catch((error) => {
      toast({
        variant: "destructive",
        title: "Workflow Failed",
        description: getErrorMessage(error),
      });
    });
    setIsSubmitting(false);
  };

  return (
    <div className="flex items-center justify-center p-6">
      <Card className="h-full border-2 shadow-md justify-center">
        <CardHeader>
          <CardTitle>New Port LLDP Info Workflow</CardTitle>
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
                disabled={hasMacAddress}
                isSubmitting={isSubmitting}
                handleChange={handleChange}
              />
              <WorkflowFormField
                type="select"
                control={form.control}
                name="device"
                label="Device"
                options={deviceData}
                isLoading={deviceIsLoading}
                disabled={hasMacAddress}
                isSubmitting={isSubmitting}
                handleChange={handleChange}
              />
              <WorkflowFormField
                type="input"
                control={form.control}
                name="interface"
                label="Interface"
                disabled={hasMacAddress}
                isSubmitting={isSubmitting}
                handleChange={handleChange}
              />
              <WorkflowFormField
                type="input"
                control={form.control}
                name="remote_mac_address"
                label="MAC Address"
                disabled={hasDeviceInfo}
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
