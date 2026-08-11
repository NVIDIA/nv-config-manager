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
import {
  useBBCircuits,
  useBBDevices,
  useBBInterfaces,
  useBBNextLag,
  useBBNextPrefix,
} from "@/hooks";
import { getErrorMessage, startWorkflow } from "@/lib/utils";

const optionalPositiveInteger = z.preprocess(
  (value) => (value === "" || Number.isNaN(value) ? undefined : value),
  z.number().int().positive().max(16_777_214).optional()
);

const schema = z
  .object({
    circuit_id: z.string().min(1, "Circuit is required"),
    jira: z.string().regex(/^[A-Za-z][A-Za-z0-9]+-\d+$/, "Use a Jira key such as BB-123"),
    local_device: z.string().min(1, "Local device is required"),
    local_ports: z.array(z.string()).min(1, "Select at least one local port"),
    remote_device: z.string().min(1, "Remote device is required"),
    remote_ports: z.array(z.string()).min(1, "Select at least one remote port"),
    lag_name: z
      .string()
      .trim()
      .refine((value) => !value || /^ae\d+$/.test(value), "Use a LAG name such as ae100"),
    ipv4_prefix: z.string().cidr({ version: "v4", message: "Enter an IPv4 /31 prefix" }),
    ipv6_prefix: z.string().cidr({ version: "v6", message: "Enter an IPv6 /127 prefix" }),
    expected_rtt_ms: z.number().positive("Expected RTT must be greater than zero"),
    igp_metric_override: optionalPositiveInteger,
    minimum_links: z.number().int().positive("Minimum links must be at least one"),
  })
  .superRefine((data, context) => {
    if (data.local_device === data.remote_device) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["remote_device"],
        message: "Remote device must differ from local device",
      });
    }
    if (!data.ipv4_prefix.endsWith("/31")) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["ipv4_prefix"],
        message: "IPv4 prefix must be a /31",
      });
    }
    if (!data.ipv6_prefix.endsWith("/127")) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["ipv6_prefix"],
        message: "IPv6 prefix must be a /127",
      });
    }
    if (data.minimum_links > Math.min(data.local_ports.length, data.remote_ports.length)) {
      context.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["minimum_links"],
        message: "Minimum links cannot exceed either side's selected port count",
      });
    }
  });

type BringupFormData = z.infer<typeof schema>;

export const BBInternalBackboneBringupForm = () => {
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const { toast } = useToast();
  const { options: circuits, isLoading: circuitsLoading } = useBBCircuits();
  const { options: devices, isLoading: devicesLoading } = useBBDevices();
  const form = useForm<BringupFormData>({
    resolver: zodResolver(schema),
    defaultValues: {
      circuit_id: "",
      jira: "",
      local_device: "",
      local_ports: [],
      remote_device: "",
      remote_ports: [],
      lag_name: "",
      ipv4_prefix: "",
      ipv6_prefix: "",
      expected_rtt_ms: 10,
      igp_metric_override: undefined,
      minimum_links: 1,
    },
  });
  const localDevice = form.watch("local_device");
  const remoteDevice = form.watch("remote_device");
  const { options: localPorts, isLoading: localPortsLoading } = useBBInterfaces(
    localDevice,
    "lag-member"
  );
  const { options: remotePorts, isLoading: remotePortsLoading } = useBBInterfaces(
    remoteDevice,
    "lag-member"
  );
  const lagSuggestion = useBBNextLag(localDevice, remoteDevice);
  const ipv4Suggestion = useBBNextPrefix(31);
  const ipv6Suggestion = useBBNextPrefix(127);

  React.useEffect(() => {
    form.setValue("local_ports", []);
  }, [localDevice, form]);
  React.useEffect(() => {
    form.setValue("remote_ports", []);
  }, [remoteDevice, form]);
  React.useEffect(() => {
    if (lagSuggestion.data) form.setValue("lag_name", lagSuggestion.data.lag_name);
  }, [lagSuggestion.data, form]);
  React.useEffect(() => {
    if (ipv4Suggestion.data) form.setValue("ipv4_prefix", ipv4Suggestion.data.prefix);
  }, [ipv4Suggestion.data, form]);
  React.useEffect(() => {
    if (ipv6Suggestion.data) form.setValue("ipv6_prefix", ipv6Suggestion.data.prefix);
  }, [ipv6Suggestion.data, form]);

  const remoteDevices = devices.filter((device) => device.value !== localDevice);
  const calculatedMetric = Math.max(10, Math.round((form.watch("expected_rtt_ms") || 0) * 10));

  const onSubmit = async (data: BringupFormData) => {
    setIsSubmitting(true);
    try {
      await startWorkflow("/v1/workflow/bb_sandbox/internal_backbone_bringup", {
        ...data,
        lag_name: data.lag_name || null,
        igp_metric_override: data.igp_metric_override ?? null,
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
      <Card className="h-full w-full max-w-4xl border-2 shadow-md">
        <CardHeader>
          <CardTitle>BB Sandbox: Internal Backbone Bringup</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <div className="grid gap-6 md:grid-cols-2">
                <WorkflowFormField type="select" control={form.control} name="circuit_id" label="Circuit" options={circuits} isLoading={circuitsLoading} isSubmitting={isSubmitting} />
                <WorkflowFormField type="input" control={form.control} name="jira" label="Jira" placeholder="BB-123" isSubmitting={isSubmitting} />
                <WorkflowFormField type="select" control={form.control} name="local_device" label="Local Device" options={devices} isLoading={devicesLoading} isSubmitting={isSubmitting} />
                <WorkflowFormField type="select" control={form.control} name="remote_device" label="Remote Device" options={remoteDevices} isLoading={devicesLoading} isSubmitting={isSubmitting} />
                <WorkflowFormField type="select" control={form.control} name="local_ports" label="Local Ports" options={localPorts} multiple isLoading={localPortsLoading} disabled={!localDevice} isSubmitting={isSubmitting} />
                <WorkflowFormField type="select" control={form.control} name="remote_ports" label="Remote Ports" options={remotePorts} multiple isLoading={remotePortsLoading} disabled={!remoteDevice} isSubmitting={isSubmitting} />
                <WorkflowFormField type="input" control={form.control} name="lag_name" label="LAG Name (optional)" placeholder="Auto-select from ae100" isSubmitting={isSubmitting} />
                <WorkflowFormField type="number" control={form.control} name="minimum_links" label="Minimum Links" isSubmitting={isSubmitting} />
                <WorkflowFormField type="input" control={form.control} name="ipv4_prefix" label="IPv4 /31" placeholder="Allocated from BB-P2P" isSubmitting={isSubmitting} />
                <WorkflowFormField type="input" control={form.control} name="ipv6_prefix" label="IPv6 /127" placeholder="Allocated from BB-P2P" isSubmitting={isSubmitting} />
                <WorkflowFormField type="number" control={form.control} name="expected_rtt_ms" label="Expected RTT (ms)" isSubmitting={isSubmitting} />
                <WorkflowFormField type="number" control={form.control} name="igp_metric_override" label="IS-IS Metric Override (optional)" isSubmitting={isSubmitting} />
              </div>
              <p className="text-sm text-muted-foreground">
                BB-P2P suggestions are previews from Nautobot. Without an override, the stored IS-IS metric will be {calculatedMetric}.
              </p>
              {(ipv4Suggestion.error || ipv6Suggestion.error) && (
                <p className="text-sm text-destructive">
                  A BB-P2P allocation pool is unavailable; enter the prefixes manually or assign the BB-P2P role to IPv4 and IPv6 container prefixes in Nautobot.
                </p>
              )}
              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Submitting..." : "Start Staged Bringup"}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
};
