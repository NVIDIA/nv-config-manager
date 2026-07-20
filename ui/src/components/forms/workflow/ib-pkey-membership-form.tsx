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
import {
  type Control,
  type FieldPath,
  useFieldArray,
  useForm,
} from "react-hook-form";
import { z } from "zod";
import { Plus, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/components/ui/use-toast";
import { WorkflowFormField } from "@/components/forms/formfield";
import { startWorkflow } from "@/lib/utils";

const PKEY_PATTERN = /^0[xX][0-9a-fA-F]{1,4}$/;
const GUID_PATTERN = /^0[xX][0-9a-fA-F]{16}$/;

const MEMBERSHIP_OPTIONS = [
  { key: "full", value: "full" },
  { key: "limited", value: "limited" },
];

const MEMBERSHIP_REQUIRED_MESSAGE = "Select a membership type";

const makeMembershipFormSchema = (requireMembership: boolean) =>
  z
    .object({
      host: z.string().trim().min(1, { message: "Host is required" }),
      pkey: z
        .string()
        .trim()
        .min(1, { message: "PKey is required" })
        .regex(PKEY_PATTERN, {
          message: "PKey must match 0x + 1-4 hex digits (e.g. 0x8001)",
        }),
      input_mode: z.enum(["interfaces", "guids"]),
      interfaces: z
        .array(
          z.object({
            device: z.string().trim(),
            interface: z.string().trim(),
            membership: z.string().default(""),
          }),
        )
        .default([]),
      guids: z
        .array(
          z.object({
            guid: z.string().trim(),
            membership: z.string().default(""),
          }),
        )
        .default([]),
    })
    .superRefine((data, ctx) => {
      if (data.input_mode === "interfaces") {
        const nonEmpty = data.interfaces.filter(
          (row) => row.device && row.interface,
        );
        if (nonEmpty.length === 0) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ["interfaces"],
            message: "Add at least one device/interface row",
          });
        }
        data.interfaces.forEach((row, idx) => {
          if (row.device && !row.interface) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              path: ["interfaces", idx, "interface"],
              message: "Interface name is required",
            });
          }
          if (!row.device && row.interface) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              path: ["interfaces", idx, "device"],
              message: "Device name is required",
            });
          }
          if (requireMembership && row.device && row.interface && !row.membership) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              path: ["interfaces", idx, "membership"],
              message: MEMBERSHIP_REQUIRED_MESSAGE,
            });
          }
        });
      } else {
        const nonEmpty = data.guids.filter((row) => row.guid);
        if (nonEmpty.length === 0) {
          ctx.addIssue({
            code: z.ZodIssueCode.custom,
            path: ["guids"],
            message: "Provide at least one GUID",
          });
        }
        data.guids.forEach((row, idx) => {
          if (row.guid && !GUID_PATTERN.test(row.guid)) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              path: ["guids", idx, "guid"],
              message: "Invalid GUID. Expected 0x + 16 hex digits.",
            });
          }
          if (requireMembership && row.guid && !row.membership) {
            ctx.addIssue({
              code: z.ZodIssueCode.custom,
              path: ["guids", idx, "membership"],
              message: MEMBERSHIP_REQUIRED_MESSAGE,
            });
          }
        });
      }
    });

type MembershipFormValues = z.infer<ReturnType<typeof makeMembershipFormSchema>>;

interface InterfaceRefPayload {
  device: string;
  interface: string;
  membership?: string;
}

interface MembershipRequest {
  host: string;
  pkey: string;
  interfaces?: InterfaceRefPayload[];
  guids?: string[];
  guid_memberships?: string[];
}

const MembershipSelect = ({
  control,
  name,
  ariaLabel,
  disabled,
}: {
  control: Control<MembershipFormValues>;
  name: FieldPath<MembershipFormValues>;
  ariaLabel: string;
  disabled?: boolean;
}) => (
  <FormField
    control={control}
    name={name}
    render={({ field }) => (
      <FormItem className="w-40">
        <Select
          value={(field.value as string) || undefined}
          onValueChange={field.onChange}
          disabled={disabled}
        >
          <FormControl>
            <SelectTrigger aria-label={ariaLabel}>
              <SelectValue placeholder="Membership Type" />
            </SelectTrigger>
          </FormControl>
          <SelectContent>
            {MEMBERSHIP_OPTIONS.map((opt) => (
              <SelectItem key={opt.key} value={opt.value}>
                {opt.value}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <FormMessage />
      </FormItem>
    )}
  />
);

export interface IBPKeyMembershipFormProps {
  title: string;
  endpoint: string;
  submitLabel: string;
  destructiveWarning?: string;
  includeMembershipType?: boolean;
}

export const IBPKeyMembershipForm = ({
  title,
  endpoint,
  submitLabel,
  destructiveWarning,
  includeMembershipType = false,
}: IBPKeyMembershipFormProps) => {
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const { toast } = useToast();
  const searchParams = useSearchParams();

  const schema = React.useMemo(
    () => makeMembershipFormSchema(includeMembershipType),
    [includeMembershipType],
  );

  const form = useForm<MembershipFormValues>({
    resolver: zodResolver(schema),
    defaultValues: {
      host: searchParams?.get("host") ?? "",
      pkey: searchParams?.get("pkey") ?? "",
      input_mode: "interfaces",
      interfaces: [{ device: "", interface: "", membership: "" }],
      guids: [{ guid: "", membership: "" }],
    },
  });

  const inputMode = form.watch("input_mode");

  const { fields, append, remove } = useFieldArray({
    control: form.control,
    name: "interfaces",
  });

  const {
    fields: guidFields,
    append: guidAppend,
    remove: guidRemove,
  } = useFieldArray({
    control: form.control,
    name: "guids",
  });

  const interfacesErr = form.formState.errors.interfaces as
    | { message?: string; root?: { message?: string } }
    | undefined;
  const interfacesErrorMessage =
    interfacesErr?.message ?? interfacesErr?.root?.message;

  const guidsErr = form.formState.errors.guids as
    | { message?: string; root?: { message?: string } }
    | undefined;
  const guidsErrorMessage = guidsErr?.message ?? guidsErr?.root?.message;

  const onSubmit = async (data: MembershipFormValues) => {
    setIsSubmitting(true);

    const params: MembershipRequest = {
      host: data.host,
      pkey: data.pkey,
    };
    if (data.input_mode === "interfaces") {
      const rows = data.interfaces.filter((row) => row.device && row.interface);
      params.interfaces = rows.map((row) => {
        const ref: InterfaceRefPayload = {
          device: row.device,
          interface: row.interface,
        };
        if (includeMembershipType) {
          ref.membership = row.membership;
        }
        return ref;
      });
    } else {
      const rows = data.guids.filter((row) => row.guid);
      params.guids = rows.map((row) => row.guid);
      if (includeMembershipType) {
        params.guid_memberships = rows.map((row) => row.membership);
      }
    }

    await startWorkflow(endpoint, params).catch((error) => {
      toast({
        variant: "destructive",
        title: "Workflow Failed",
        description: typeof error === "string" ? error : String(error),
      });
      setIsSubmitting(false);
    });
  };

  return (
    <div className="flex items-center justify-center p-6">
      <Card className="w-full max-w-3xl border-2 shadow-md">
        <CardHeader>
          <CardTitle>{title}</CardTitle>
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

              <WorkflowFormField
                type="input"
                control={form.control}
                name="pkey"
                label="PKey"
                placeholder="0x8001"
                isSubmitting={isSubmitting}
              />

              <FormField
                control={form.control}
                name="input_mode"
                render={({ field }) => (
                  <FormItem className="space-y-3">
                    <FormLabel>Member Source</FormLabel>
                    <FormControl>
                      <RadioGroup
                        onValueChange={field.onChange}
                        value={field.value}
                        className="flex flex-row gap-6"
                        disabled={isSubmitting}
                      >
                        <label className="flex cursor-pointer items-center gap-2">
                          <RadioGroupItem value="interfaces" />
                          <span>By Interfaces</span>
                        </label>
                        <label className="flex cursor-pointer items-center gap-2">
                          <RadioGroupItem value="guids" />
                          <span>By GUIDs</span>
                        </label>
                      </RadioGroup>
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />

              {inputMode === "interfaces" ? (
                <FormField
                  key="interfaces"
                  control={form.control}
                  name="interfaces"
                  render={() => (
                    <FormItem>
                      <FormLabel>Interfaces</FormLabel>
                      <div className="space-y-2">
                        {fields.map((arrayField, idx) => (
                          <div
                            key={arrayField.id}
                            className="flex items-start gap-2"
                          >
                            <FormField
                              control={form.control}
                              name={`interfaces.${idx}.device`}
                              render={({ field }) => (
                                <FormItem className="flex-1">
                                  <FormControl>
                                    <Input
                                      placeholder="device (e.g. hca01)"
                                      disabled={isSubmitting}
                                      {...field}
                                    />
                                  </FormControl>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                            <FormField
                              control={form.control}
                              name={`interfaces.${idx}.interface`}
                              render={({ field }) => (
                                <FormItem className="flex-1">
                                  <FormControl>
                                    <Input
                                      placeholder="interface (e.g. mlx5_0)"
                                      disabled={isSubmitting}
                                      {...field}
                                    />
                                  </FormControl>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                            {includeMembershipType ? (
                              <MembershipSelect
                                control={form.control}
                                name={`interfaces.${idx}.membership`}
                                ariaLabel={`Membership for interface row ${idx + 1}`}
                                disabled={isSubmitting}
                              />
                            ) : null}
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              aria-label={`Remove interface row ${idx + 1}`}
                              onClick={() => remove(idx)}
                              disabled={isSubmitting || fields.length === 1}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        ))}
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() =>
                            append({
                              device: "",
                              interface: "",
                              membership: "",
                            })
                          }
                          disabled={isSubmitting}
                        >
                          <Plus className="mr-1 h-4 w-4" />
                          Add Row
                        </Button>
                      </div>
                      {interfacesErrorMessage ? (
                        <p className="text-sm font-medium text-destructive">
                          {interfacesErrorMessage}
                        </p>
                      ) : null}
                    </FormItem>
                  )}
                />
              ) : (
                <FormField
                  key="guids"
                  control={form.control}
                  name="guids"
                  render={() => (
                    <FormItem>
                      <FormLabel>GUIDs</FormLabel>
                      <div className="space-y-2">
                        {guidFields.map((arrayField, idx) => (
                          <div
                            key={arrayField.id}
                            className="flex items-start gap-2"
                          >
                            <FormField
                              control={form.control}
                              name={`guids.${idx}.guid`}
                              render={({ field }) => (
                                <FormItem className="flex-1">
                                  <FormControl>
                                    <Input
                                      placeholder="0x0011223344556677"
                                      aria-label={`GUID ${idx + 1}`}
                                      disabled={isSubmitting}
                                      {...field}
                                    />
                                  </FormControl>
                                  <FormMessage />
                                </FormItem>
                              )}
                            />
                            {includeMembershipType ? (
                              <MembershipSelect
                                control={form.control}
                                name={`guids.${idx}.membership`}
                                ariaLabel={`Membership for GUID row ${idx + 1}`}
                                disabled={isSubmitting}
                              />
                            ) : null}
                            <Button
                              type="button"
                              variant="ghost"
                              size="icon"
                              aria-label={`Remove GUID row ${idx + 1}`}
                              onClick={() => guidRemove(idx)}
                              disabled={isSubmitting || guidFields.length === 1}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        ))}
                        <Button
                          type="button"
                          variant="outline"
                          size="sm"
                          onClick={() =>
                            guidAppend({
                              guid: "",
                              membership: "",
                            })
                          }
                          disabled={isSubmitting}
                        >
                          <Plus className="mr-1 h-4 w-4" />
                          Add Row
                        </Button>
                      </div>
                      <p className="mt-1 text-sm text-muted-foreground">
                        One GUID per row. Each must match 0x + 16 hex digits.
                      </p>
                      {guidsErrorMessage ? (
                        <p className="text-sm font-medium text-destructive">
                          {guidsErrorMessage}
                        </p>
                      ) : null}
                    </FormItem>
                  )}
                />
              )}

              {destructiveWarning ? (
                <div
                  role="alert"
                  className="rounded-md border border-destructive/50 bg-destructive/10 px-3 py-2 text-sm text-destructive"
                >
                  {destructiveWarning}
                </div>
              ) : null}

              <Button type="submit" disabled={isSubmitting}>
                {isSubmitting ? "Submitting..." : submitLabel}
              </Button>
            </form>
          </Form>
        </CardContent>
      </Card>
    </div>
  );
};
