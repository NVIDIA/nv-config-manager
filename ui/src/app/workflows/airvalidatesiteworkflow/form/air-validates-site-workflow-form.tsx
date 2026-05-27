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
import { useEnvData } from "@/hooks";
import { WorkflowFormField } from "@/components/forms/formfield";
import { startWorkflow } from "@/lib/utils";
import { toast } from "@/components/ui/use-toast";
import { AIRValidateSiteWorkflowInput } from "@/types/data-table.types";

const AIRValidateSiteWorkflowFormSchema = z.object({
  site: z.string().trim().min(1, { message: "Site is required" }),
});

export type AIRValidateSiteWorkflowFormSchema = z.infer<
  typeof AIRValidateSiteWorkflowFormSchema
>;

export const AIRValidateSiteWorkflowForm = () => {
  const [isSubmitting, setIsSubmitting] = React.useState<boolean>(false);
  const [isManualSiteChange, setIsManualSiteChange] = React.useState(false);
  const {
    data: { siteData: sites },
    errors: { siteError },
    isLoading: { siteIsLoading },
  } = useEnvData();

  const searchParams = useSearchParams();
  const querySite = searchParams && searchParams.get("site");

  const form = useForm<AIRValidateSiteWorkflowFormSchema>({
    resolver: zodResolver(AIRValidateSiteWorkflowFormSchema),
    defaultValues: {
      site: querySite || "",
    },
  });

  if (siteError) console.error(`Failed to query devices: ${siteError}`);

  const onSubmit = async (
    data: z.infer<typeof AIRValidateSiteWorkflowFormSchema>
  ) => {
    setIsSubmitting(true);

    const submissionData: AIRValidateSiteWorkflowInput = {
      site_name: data.site,
    };

    await startWorkflow(
      "/v1/workflow/ngc/air_validate_site",
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

  React.useEffect(() => {
    if (querySite && !isManualSiteChange) {
      const isSiteValid = sites.some((option) => option.key === querySite);
      const siteId = sites.find((option) => option.key === querySite)?.value;

      if (!isSiteValid) {
        if (form.getValues("site") !== "") {
          form.setValue("site", ""); // Clear site if invalid
        }
      } else {
        if (siteId && form.getValues("site") !== siteId) {
          form.setValue("site", siteId); // Set valid site from URL
        }
      }
    }
  }, [querySite, sites, form, isManualSiteChange]);

  const handleSiteChange = (newSite: string | string[]) => {
    setIsManualSiteChange(true);

    if (Array.isArray(newSite)) {
      form.setValue("site", newSite[0]);
    } else {
      form.setValue("site", newSite);
    }
  };

  const SiteField = () => {
    return (
      <WorkflowFormField
        type="select"
        control={form.control}
        name="site"
        label="Site"
        options={sites}
        isLoading={siteIsLoading}
        disabled={isSubmitting}
        handleChange={(_, value) => handleSiteChange(value)}
      />
    );
  };

  return (
    <div className="flex items-center justify-center p-6">
      <Card className="w-full max-w-lg border-2 shadow-md">
        <CardHeader className="pb-6">
          <CardTitle className="text-center">AIR Validate Site</CardTitle>
        </CardHeader>
        <CardContent>
          <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
              <SiteField />
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
