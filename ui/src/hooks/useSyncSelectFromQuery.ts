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
import { useEffect, useRef } from "react";
import {
  FieldPath,
  FieldPathValue,
  FieldValues,
  UseFormReturn,
} from "react-hook-form";
import { Option } from "@/types/workflow-form.types";

interface UseSyncSelectFromQueryOptions<
  TFieldValues extends FieldValues,
  TFieldName extends FieldPath<TFieldValues>,
> {
  fieldName: TFieldName;
  form: UseFormReturn<TFieldValues>;
  hasLoaded: boolean;
  isLoading: boolean;
  options: Option[];
  queryValue: string;
}

const useSyncSelectFromQuery = <
  TFieldValues extends FieldValues,
  TFieldName extends FieldPath<TFieldValues>,
>({
  fieldName,
  form,
  hasLoaded,
  isLoading,
  options,
  queryValue,
}: UseSyncSelectFromQueryOptions<TFieldValues, TFieldName>): void => {
  const lastSyncedQuery = useRef<string | null>(null);

  useEffect(() => {
    if (!queryValue) {
      lastSyncedQuery.current = null;
      return;
    }
    if (!hasLoaded || isLoading || lastSyncedQuery.current === queryValue) return;

    const queryValueExists = options.some((option) => option.value === queryValue);
    const nextValue = queryValueExists ? queryValue : "";
    if (form.getValues(fieldName) !== nextValue) {
      form.setValue(
        fieldName,
        nextValue as FieldPathValue<TFieldValues, TFieldName>
      );
    }
    lastSyncedQuery.current = queryValue;
  }, [fieldName, form, hasLoaded, isLoading, options, queryValue]);
};

export default useSyncSelectFromQuery;
