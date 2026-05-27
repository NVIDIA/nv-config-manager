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
import { AIRDeleteSimulationWorkflowInput } from "@/types/data-table.types";
import { useSimulations } from "@/hooks";

const AIRDeleteSimulationWorkflowFormSchema = z.object({
  simulation_id: z
    .string()
    .trim()
    .min(1, { message: "Simulation ID is required" }),
});

export type AIRDeleteSimulationWorkflowFormSchema = z.infer<
  typeof AIRDeleteSimulationWorkflowFormSchema
>;

export const AIRDeleteSimulationWorkflowForm = () => {
  const [isSubmitting, setIsSubmitting] = React.useState<boolean>(false);
  const [isManualSimulationChange, setIsManualSimulationChange] =
    React.useState<boolean>(false);

  const searchParams = useSearchParams();
  const querySimulationId = searchParams && searchParams.get("simulation_id");

  const {
    simulations,
    isLoading: simulationsIsLoading,
  } = useSimulations();

  const form = useForm<AIRDeleteSimulationWorkflowFormSchema>({
    resolver: zodResolver(AIRDeleteSimulationWorkflowFormSchema),
    defaultValues: {
      simulation_id: querySimulationId || "",
    },
  });

  // Handle URL param prefill
  React.useEffect(() => {
    if (querySimulationId && !isManualSimulationChange) {
      const isSimulationValid = simulations.some(
        (simulation) => simulation.value === querySimulationId
      );

      if (isSimulationValid) {
        if (form.getValues("simulation_id") !== querySimulationId) {
          form.setValue("simulation_id", querySimulationId);
        }
      } else {
        if (form.getValues("simulation_id") !== "") {
          form.setValue("simulation_id", "");
        }
      }
    }
  }, [querySimulationId, simulations, form, isManualSimulationChange]);

  const handleSimulationChange = (newSimulation: string | string[]) => {
    setIsManualSimulationChange(true);

    if (Array.isArray(newSimulation)) {
      form.setValue("simulation_id", newSimulation[0]);
    } else {
      form.setValue("simulation_id", newSimulation);
    }
  };

  const onSubmit = async (
    data: z.infer<typeof AIRDeleteSimulationWorkflowFormSchema>
  ) => {
    setIsSubmitting(true);

    const submissionData: AIRDeleteSimulationWorkflowInput = {
      simulation_id: data.simulation_id,
    };

    await startWorkflow("/v1/workflow/ngc/air_delete", submissionData).catch(
      (error) => {
        toast({
          variant: "destructive",
          title: "Workflow Failed",
          description: error.message || String(error),
        });
      }
    );
    setIsSubmitting(false);
  };

  return (
    <div className="flex items-center justify-center p-6">
      <Card className="w-full max-w-lg border-2 shadow-md">
        <CardHeader className="pb-6">
          <CardTitle className="text-center">AIR Delete Simulation</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <WorkflowFormField
                type="select"
                control={form.control}
                name="simulation_id"
                label="Simulation"
                options={simulations}
                isLoading={simulationsIsLoading}
                disabled={isSubmitting}
                handleChange={(_, value) => handleSimulationChange(value)}
              />
              <Button
                type="submit"
                disabled={isSubmitting || simulationsIsLoading}
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
