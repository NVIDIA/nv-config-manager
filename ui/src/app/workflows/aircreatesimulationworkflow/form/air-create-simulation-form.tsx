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
import { useSearchParams } from "next/navigation";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Form } from "@/components/ui/form";
import { WorkflowFormField } from "@/components/forms/formfield";
import { startWorkflow } from "@/lib/utils";
import { toast } from "@/components/ui/use-toast";
import { AIRCreateSimulationWorkflowInput } from "@/types/data-table.types";

const AIRCreateSimulationWorkflowFormSchema = z.object({
  name: z.string().trim().min(1, { message: "Name is required" }),
  topology: z
    .string()
    .trim()
    .min(1, { message: "Topology JSON is required" })
    .refine(
      (val) => {
        try {
          JSON.parse(val);
          return true;
        } catch {
          return false;
        }
      },
      { message: "Must be valid JSON" }
    ),
});

export type AIRCreateSimulationWorkflowFormSchema = z.infer<
  typeof AIRCreateSimulationWorkflowFormSchema
>;

export const AIRCreateSimulationWorkflowForm = () => {
  const [isSubmitting, setIsSubmitting] = React.useState<boolean>(false);

  const searchParams = useSearchParams();
  const queryName = searchParams && searchParams.get("name");
  const queryTopology = searchParams && searchParams.get("topology");

  const form = useForm<AIRCreateSimulationWorkflowFormSchema>({
    resolver: zodResolver(AIRCreateSimulationWorkflowFormSchema),
    defaultValues: {
      name: queryName || "",
      topology: queryTopology || "",
    },
  });

  const onSubmit = async (
    data: z.infer<typeof AIRCreateSimulationWorkflowFormSchema>
  ) => {
    setIsSubmitting(true);

    const topologyObject = JSON.parse(data.topology);
    const submissionData: AIRCreateSimulationWorkflowInput = {
      name: data.name,
      topology: topologyObject,
    };

    await startWorkflow(
      "/v1/workflow/ngc/air_create_simulation",
      submissionData
    ).catch((error) => {
      toast({
        variant: "destructive",
        title: "Workflow Failed",
        description: error,
      });
    });
    setIsSubmitting(false);
  };

  const formatJSON = () => {
    const currentValue = form.getValues("topology");
    if (currentValue.trim()) {
      try {
        const parsed = JSON.parse(currentValue);
        const formatted = JSON.stringify(parsed, null, 2);
        form.setValue("topology", formatted);
        toast({
          title: "JSON Formatted",
          description: "Your JSON has been prettified!",
        });
      } catch (error) {
        console.error(error);
        toast({
          variant: "destructive",
          title: "Invalid JSON",
          description: "Cannot format invalid JSON. Please check your syntax.",
        });
      }
    }
  };

  return (
    <div className="flex items-center justify-center p-6">
      <Card className="w-full max-w-2xl border-2 shadow-md">
        <CardHeader className="pb-6">
          <CardTitle className="text-center">AIR Create Simulation</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <WorkflowFormField
                type="input"
                control={form.control}
                name="name"
                label="Simulation Name"
                placeholder="Enter simulation name"
                disabled={isSubmitting}
              />
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium">Topology JSON</label>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={formatJSON}
                    disabled={isSubmitting}
                  >
                    Format JSON
                  </Button>
                </div>
                <WorkflowFormField
                  type="textarea"
                  control={form.control}
                  name="topology"
                  label=""
                  placeholder="Enter topology configuration as JSON"
                  disabled={isSubmitting}
                />
              </div>
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
