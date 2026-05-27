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
import type { CommandEntry } from "./useCommandCatalog";

const PLATFORM_LABELS: Record<string, string> = {
  "arista-eos": "Arista EOS",
  "cumulus-linux": "Cumulus Linux",
  "nv-os": "NV-OS",
  "mlnx-os": "MLNX-OS",
};

export interface CommandGroup {
  /** Empty string for the single-platform case (no header rendered). */
  label: string;
  commands: CommandEntry[];
}

interface UseCommandCatalogGroupedReturn {
  /** Grouped commands: shared first, then per-platform exclusive groups. */
  groups: CommandGroup[];
  /** Flat list of all commands across all groups — used for select-all logic. */
  allCommands: CommandEntry[];
  isLoading: boolean;
}

const useCommandCatalogGrouped = (platforms: string[]): UseCommandCatalogGroupedReturn => {
  const { config } = useRuntimeConfig();
  const apiURL = config?.workflowApiUrl;

  const uniquePlatforms = [...new Set(platforms)].filter(Boolean);

  const { data, isLoading } = useSWR(
    uniquePlatforms.length > 0 && apiURL
      ? ["commandCatalogGrouped", [...uniquePlatforms].toSorted((a, b) => a.localeCompare(b)).join(","), apiURL]
      : null,
    async () => {
      const results = await Promise.allSettled(
        uniquePlatforms.map(async (p) => {
          const url = sanitizeUrl(
            `${apiURL}/v1/parameter/diagnostics/commands?platform=${encodeURIComponent(p)}`
          );
          const result = await fetcher(url);
          return {
            platform: p,
            commands: Array.isArray(result) ? (result as CommandEntry[]) : [],
          };
        })
      );
      return results
        .filter((r): r is PromiseFulfilledResult<{ platform: string; commands: CommandEntry[] }> => r.status === "fulfilled")
        .map((r) => r.value);
    }
  );

  if (!data || data.length === 0) {
    return { groups: [], allCommands: [], isLoading };
  }

  // Single platform — return flat list with no group header.
  if (data.length === 1) {
    const commands = [...data[0].commands].sort((a, b) => a.name.localeCompare(b.name));
    return { groups: [{ label: "", commands }], allCommands: commands, isLoading };
  }

  // Multiple platforms: split into shared (intersection) + per-platform exclusive.
  const nameSets = data.map((d) => new Set(d.commands.map((c) => c.name)));

  // Deduplicated command map (first occurrence wins for description).
  const commandMap = new Map<string, CommandEntry>();
  for (const { commands } of data) {
    for (const cmd of commands) {
      if (!commandMap.has(cmd.name)) commandMap.set(cmd.name, cmd);
    }
  }

  const sharedNames = new Set(
    [...commandMap.keys()].filter((name) => nameSets.every((s) => s.has(name)))
  );

  const groups: CommandGroup[] = [];

  if (sharedNames.size > 0) {
    groups.push({
      label: "Runs on all selected devices",
      commands: [...sharedNames]
        .toSorted((a, b) => a.localeCompare(b))
        .map((name) => commandMap.get(name)!),
    });
  }

  for (const { platform, commands } of data) {
    const exclusive = commands
      .filter((cmd) => !sharedNames.has(cmd.name))
      .sort((a, b) => a.name.localeCompare(b.name));
    if (exclusive.length > 0) {
      groups.push({
        label: `${PLATFORM_LABELS[platform] ?? platform} only`,
        commands: exclusive,
      });
    }
  }

  const allCommands = groups.flatMap((g) => g.commands);
  return { groups, allCommands, isLoading };
};

export default useCommandCatalogGrouped;
