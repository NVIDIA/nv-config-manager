/*
 * SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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

import type {
  FieldValues,
  Path,
  PathValue,
  UseFormReturn,
} from "react-hook-form";

export interface QueryOption {
  key: string;
  value: string;
}

/** Maps a single query parameter key to its form option value or clears it. */
export const setSingleQueryValue = <
  TFieldValues extends FieldValues,
  TFieldName extends Path<TFieldValues>,
>(
  form: UseFormReturn<TFieldValues>,
  queryValue: string | null,
  options: readonly QueryOption[],
  fieldName: TFieldName
) => {
  const fieldValue =
    options.find((option) => option.key === queryValue)?.value ?? "";
  form.setValue(
    fieldName,
    fieldValue as PathValue<TFieldValues, TFieldName>
  );
};

/** Keeps valid multi-value query keys and clears values without an option. */
export const setMultiQueryValue = <
  TFieldValues extends FieldValues,
  TFieldName extends Path<TFieldValues>,
>(
  form: UseFormReturn<TFieldValues>,
  queryValues: readonly string[],
  options: readonly QueryOption[],
  fieldName: TFieldName
) => {
  const fieldValue = queryValues.filter((queryValue) =>
    options.some((option) => option.key === queryValue)
  );
  form.setValue(
    fieldName,
    fieldValue as PathValue<TFieldValues, TFieldName>
  );
};
