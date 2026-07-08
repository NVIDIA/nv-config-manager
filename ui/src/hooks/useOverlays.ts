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
import { useMemo } from "react";
import useSWR from "swr";
import { fetcher } from "@/lib/fetcher";
import { useRuntimeConfig } from "@/config/runtime";
import { mapRoles, sanitizeUrl } from "@/lib/utils";
import { Option } from "@/types/workflow-form.types";

interface UseOverlaysOptions {
  enabled?: boolean;
  isolationType?: string;
  location?: string;
}

interface UseOverlaysReturn {
  overlays: Option[];
  error: Error | null;
  hasLoaded: boolean;
  isLoading: boolean;
}

export const SPX_OVERLAY_ISOLATION_TYPE = "spectrum_x_vrf";

const useOverlays = ({
  enabled = true,
  isolationType,
  location,
}: UseOverlaysOptions = {}): UseOverlaysReturn => {
  const { config } = useRuntimeConfig();
  const apiURL = config?.workflowApiUrl;
  const params = new URLSearchParams();

  if (location) {
    params.set("location", location);
  }
  if (isolationType) {
    params.set("isolation_type", isolationType);
  }

  const queryString = params.toString();
  const url =
    apiURL && enabled
      ? sanitizeUrl(
          `${apiURL}/v1/parameter/overlay${queryString ? `?${queryString}` : ""}`
        )
      : null;
  const { data, error, isLoading } = useSWR(url, fetcher);
  const overlays = useMemo(
    () => (data && !error ? mapRoles(data, "name", "name") : []),
    [data, error]
  );

  return {
    overlays,
    error,
    hasLoaded: data !== undefined || Boolean(error),
    isLoading,
  };
};

export default useOverlays;
