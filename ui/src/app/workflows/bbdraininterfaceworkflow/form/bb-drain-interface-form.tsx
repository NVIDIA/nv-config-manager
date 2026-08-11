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
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { WorkflowFormField } from "@/components/forms/formfield";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Form } from "@/components/ui/form";
import { useToast } from "@/components/ui/use-toast";
import { useBBDevices, useBBInterfaces } from "@/hooks";
import { getErrorMessage, startWorkflow } from "@/lib/utils";

const schema = z.object({
  device: z.string().min(1, "Device is required"),
  port: z.string().min(1, "Interface is required"),
  jira: z
    .string()
    .trim()
    .refine((value) => !value || /^[A-Za-z][A-Za-z0-9]+-\d+$/.test(value), {
      message: "Use a Jira key such as BB-123",
    }),
});

type DrainFormData = z.infer<typeof schema>;

export const BBDrainInterfaceForm = () => {
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const { toast } = useToast();
  const { options: devices, isLoading: devicesLoading } = useBBDevices();
  const form = useForm<DrainFormData>({
    resolver: zodResolver(schema),
    defaultValues: { device: "", port: "", jira: "" },
  });
  const device = form.watch("device");
  const { options: interfaces, isLoading: interfacesLoading } = useBBInterfaces(
    device,
    "drain"
  );

  React.useEffect(() => {
    form.setValue("port", "");
  }, [device, form]);

  const onSubmit = async (data: DrainFormData) => {
    setIsSubmitting(true);
    try {
      await startWorkflow("/v1/workflow/bb_sandbox/drain_interface", {
        device: data.device,
        port: data.port,
        jira: data.jira || null,
      });
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Workflow Failed",
        description: getErrorMessage(error),
      });
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex items-center justify-center p-6">
      <Card className="h-full w-full max-w-2xl border-2 shadow-md">
        <CardHeader>
          <CardTitle>BB Sandbox: Drain Interface</CardTitle>
          <p className="text-sm text-muted-foreground">
            Sets Maintenance intent in Nautobot, triggers a fresh render, then presents
            the rendered-to-device diff for approval and deployment.
          </p>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <WorkflowFormField
                type="select"
                control={form.control}
                name="device"
                label="Device"
                options={devices}
                isLoading={devicesLoading}
                isSubmitting={isSubmitting}
              />
              <WorkflowFormField
                type="select"
                control={form.control}
                name="port"
                label="Interface"
                options={interfaces}
                isLoading={interfacesLoading}
                disabled={!device}
                isSubmitting={isSubmitting}
              />
              <WorkflowFormField
                type="input"
                control={form.control}
                name="jira"
                label="Jira (optional)"
                placeholder="BB-123"
                isSubmitting={isSubmitting}
              />
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Submitting..." : "Review Drain"}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
};
