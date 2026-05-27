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
import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";
import { useRuntimeConfig } from "@/config/runtime";
import { sanitizeUrl } from "@/lib/utils";

export interface CommandEntry {
  name: string;
  description: string;
}

interface UseCommandCatalogReturn {
  commands: CommandEntry[];
  isLoading: boolean;
}

const useCommandCatalog = (platforms: string[]): UseCommandCatalogReturn => {
  const { config } = useRuntimeConfig();
  const apiURL = config?.workflowApiUrl;

  const uniquePlatforms = [...new Set(platforms)].filter(Boolean);
  const params =
    uniquePlatforms.length > 0
      ? new URLSearchParams(uniquePlatforms.map((p) => ["platform", p])).toString()
      : null;

  const url =
    params && apiURL
      ? sanitizeUrl(`${apiURL}/v1/parameter/diagnostics/commands?${params}`)
      : null;

  const { data, isLoading } = useSWR(url, fetcher);

  return {
    commands: Array.isArray(data) ? data : [],
    isLoading,
  };
};

export default useCommandCatalog;
