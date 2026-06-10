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
import { Form } from "@/components/ui/form";
import { useToast } from "@/components/ui/use-toast";
import { startWorkflow } from "@/lib/utils";
import { WorkflowFormField } from "@/components/forms/formfield";

// Soft hint only - backend canonicalizes "0xNNNN" and accepts blank for auto-assign.
const PKEY_HINT_PATTERN = /^0[xX][0-9a-fA-F]{1,4}$/;

const IBPKeyCreationFormSchema = z.object({
  host: z.string().trim().min(1, { message: "Host is required" }),
  pkey: z.string().trim().optional(),
});

type IBPKeyCreationFormValues = z.infer<typeof IBPKeyCreationFormSchema>;

interface IBPKeyCreationRequest {
  host: string;
  pkey?: string;
}

export const IBPKeyCreationWorkflowForm = () => {
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const { toast } = useToast();
  const searchParams = useSearchParams();

  const form = useForm<IBPKeyCreationFormValues>({
    resolver: zodResolver(IBPKeyCreationFormSchema),
    defaultValues: {
      host: searchParams?.get("host") ?? "",
      pkey: searchParams?.get("pkey") ?? "",
    },
  });

  const pkeyValue = form.watch("pkey");
  const pkeyHint =
    pkeyValue && !PKEY_HINT_PATTERN.test(pkeyValue)
      ? "Expected format: 0x followed by 1-4 hex digits (e.g. 0x8001). Server will reject if invalid."
      : pkeyValue
        ? "Will be canonicalized server-side to 0xNNNN."
        : "Leave blank to auto-assign the next free PKey.";

  const onSubmit = async (data: IBPKeyCreationFormValues) => {
    setIsSubmitting(true);

    const params: IBPKeyCreationRequest = { host: data.host };
    if (data.pkey) params.pkey = data.pkey;

    try {
      await startWorkflow("/v1/workflow/ngc/ib_pkey_creation", params);
    } catch (error) {
      toast({
        variant: "destructive",
        title: "Workflow Failed",
        description: typeof error === "string" ? error : String(error),
      });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="flex items-center justify-center p-6">
      <Card className="w-full max-w-3xl border-2 shadow-md">
        <CardHeader>
          <CardTitle>InfiniBand PKey Creation Workflow</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form
              onSubmit={form.handleSubmit(onSubmit)}
              className="space-y-6"
              noValidate
            >
              <WorkflowFormField
                type="input"
                control={form.control}
                name="host"
                label="UFM Host"
                placeholder="ufm.example.com"
                isSubmitting={isSubmitting}
              />

              <div>
                <WorkflowFormField
                  type="input"
                  control={form.control}
                  name="pkey"
                  label="PKey (optional)"
                  placeholder="0x8001 (leave blank to auto-assign)"
                  isSubmitting={isSubmitting}
                />
                <p className="mt-1 text-sm text-muted-foreground">{pkeyHint}</p>
              </div>

              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Submitting..." : "Create PKey"}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
};
