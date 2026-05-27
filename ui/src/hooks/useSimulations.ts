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
import { Option } from "@/types/workflow-form.types";

interface SimulationData {
  id: string;
  name: string;
  state: string;
}

interface UseSimulationsReturn {
  simulations: Option[];
  error: unknown;
  isLoading: boolean;
}

const useSimulations = (): UseSimulationsReturn => {
  const { config } = useRuntimeConfig();
  const apiURL = config?.workflowApiUrl;
  
  const { data, error, isLoading } = useSWR(
    apiURL ? sanitizeUrl(`${apiURL}/v1/parameter/simulations`) : null,
    fetcher
  );

  const transformToOptions = (simulations: SimulationData[]): Option[] => {
    if (!simulations || !Array.isArray(simulations)) {
      return [];
    }

    return simulations.map((simulation) => ({
      key: simulation.name, // This is what users see in the dropdown
      value: simulation.id, // This is what gets submitted as the selection
    }));
  };

  return {
    simulations: transformToOptions(data) || [],
    error,
    isLoading,
  };
};

export default useSimulations;
