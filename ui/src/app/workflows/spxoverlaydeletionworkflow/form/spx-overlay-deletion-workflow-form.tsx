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
import { useEnvData } from "@/hooks";
import { WorkflowFormField } from "@/components/forms/formfield";
import { startWorkflow } from "@/lib/utils";
import { SpXOverlayDeletionWorkflowInput } from "@/types/data-table.types";

const SpXOverlayDeletionFormSchema = z.object({
  site: z.string().trim().min(1, { message: "Site is required" }),
  overlay_id: z.string().trim().min(1, { message: "Overlay ID is required" }),
  namespace: z.string().trim().min(1, { message: "Namespace is required" }),
});

export const SpXOverlayDeletionWorkflowForm = () => {
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const { toast } = useToast();
  const searchParams = useSearchParams();
  const querySite = (searchParams && searchParams.get("site")) || "";
  const queryOverlayId = (searchParams && searchParams.get("overlay_id")) || "";
  const queryNamespace =
    (searchParams && searchParams.get("namespace")) || "spectrumx";
  const {
    data: { siteData: sites },
    isLoading: { siteIsLoading },
  } = useEnvData();

  const form = useForm<z.infer<typeof SpXOverlayDeletionFormSchema>>({
    resolver: zodResolver(SpXOverlayDeletionFormSchema),
    defaultValues: {
      site: querySite,
      overlay_id: queryOverlayId,
      namespace: queryNamespace,
    },
  });

  useEffect(() => {
    if (!siteIsLoading && sites && querySite) {
      const siteExists = sites.some((site) => site.key === querySite);
      if (siteExists) {
        // Set the site value if it exists and the form value is empty
        if (!form.getValues("site")) {
          form.setValue("site", querySite);
        }
      } else {
        form.setValue("site", "");
      }
    }
  }, [sites, querySite, siteIsLoading, form]);

  const onSubmit = async (data: z.infer<typeof SpXOverlayDeletionFormSchema>) => {
    setIsSubmitting(true);
    const submissionData: SpXOverlayDeletionWorkflowInput = {
      site: data.site,
      overlay_id: data.overlay_id,
      namespace_tag: data.namespace,
    };
    await startWorkflow(
      "/v1/workflow/ngc/spx_overlay_deletion",
      submissionData
    ).catch((error) => {
      toast({
        variant: "destructive",
        title: "SpX Overlay Deletion Workflow Failed",
        description: error,
      });
    });
    setIsSubmitting(false);
  };

  return (
    <div className="flex items-center justify-center p-6">
      <Card className="h-full border-2 shadow-md justify-center">
        <CardHeader>
          <CardTitle>SpX Overlay Deletion Workflow Form</CardTitle>
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
              />
              <WorkflowFormField
                type="input"
                control={form.control}
                name="overlay_id"
                label="Overlay ID"
                isSubmitting={isSubmitting}
              />
              <WorkflowFormField
                type="input"
                control={form.control}
                name="namespace"
                label="Namespace"
                isSubmitting={isSubmitting}
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
