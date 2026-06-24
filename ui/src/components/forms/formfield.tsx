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
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { SelectBox } from "@/components/ui/selectbox";
import { Textarea } from "@/components/ui/textarea";
import { Input } from "@/components/ui/input";
import { LoadingSpinner } from "@/components/ui/loading-spinner";
import { Control } from "react-hook-form";

interface CommonFieldProps {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any -- Control<any> is the accepted pattern for generic form field wrappers (contravariance prevents Control<FieldValues>)
  control: Control<any>;
  name: string;
  label: string;
  disabled?: boolean;
  isSubmitting?: boolean;
  handleChange?: (name: string, value: string) => void;
}

interface SelectFieldProps extends CommonFieldProps {
  type: "select";
  options: { key: string; value: string }[];
  isLoading?: boolean;
  multiple?: boolean;
  searchable?: boolean;
}

interface InputFieldProps extends CommonFieldProps {
  type: "input" | "number";
  placeholder?: string;
}

interface TextareaFieldProps extends CommonFieldProps {
  type: "textarea";
  placeholder?: string;
}

type FormFieldProps = SelectFieldProps | InputFieldProps | TextareaFieldProps;

export const WorkflowFormField = ({
  control,
  name,
  label,
  disabled = false,
  isSubmitting = false,
  handleChange,
  ...props
}: FormFieldProps) => {
  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => (
        <FormItem className="flex flex-col">
          <FormLabel>{label}</FormLabel>
          <FormMessage />
          <FormControl>
            {props.type === "select" ? (
              <div className="flex items-center space-x-2">
                <SelectBox
                  options={props.options}
                  value={field.value}
                  onChange={(value: string | string[]) => {
                    handleChange?.(name, value as string);
                    field.onChange(value);
                  }}
                  placeholder={`Select a ${label}...`}
                  //placeholder={props.multiple ? `Select ${label}...` : `Select a ${label}...`}
                  inputPlaceholder={`Search ${label}`}
                  emptyPlaceholder={`No ${label} found.`}
                  multiple={props.multiple}
                  searchable={props.searchable}
                  disabled={disabled || props.isLoading || isSubmitting}
                />
                {props.isLoading ? <LoadingSpinner /> : null}
              </div>
            ) : props.type === "input" || props.type === "number" ? (
              <Input
                type={props.type}
                placeholder={props.placeholder || label}
                {...field}
                disabled={disabled || isSubmitting}
                onChange={(e) => {
                  const value =
                    props.type === "number"
                      ? e.target.valueAsNumber
                      : e.target.value;
                  handleChange?.(name, value as string);
                  field.onChange(value);
                }}
              />
            ) : props.type === "textarea" ? (
              <Textarea
                placeholder={props.placeholder || label}
                {...field}
                disabled={disabled || isSubmitting}
                onChange={(e) => {
                  const value = e.target.value;
                  handleChange?.(name, value);
                  field.onChange(value);
                }}
              />
            ) : null}
          </FormControl>
        </FormItem>
      )}
    />
  );
};
