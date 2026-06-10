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
import Link from "next/link";
import useSWRImmutable from "swr/immutable";

import { siteConfig } from "@/config/site";
import { MainNav } from "@/components/nav";
import { ThemeToggle } from "@/components/theme";
import { useState } from "react";
import { LogOut, PlusIcon, UserCircle } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { useRuntimeConfig } from "@/config/runtime";
import { fetcher } from "@/lib/fetcher";
import { cn, sanitizeUrl } from "@/lib/utils";
import {
  WorkflowMetadata,
  WorkflowMetadataResponse,
} from "@/types/data-table.types";

type WhoamiResponse = {
  user: string;
  roles: string[];
};

const workflowMetadataBySlug = (
  workflows: WorkflowMetadata[] | undefined
): Map<string, WorkflowMetadata> => {
  return new Map(
    workflows?.map((workflow) => [workflow.name.toLowerCase(), workflow]) ?? []
  );
};

const canExecuteWorkflow = (
  metadata: WorkflowMetadata | undefined,
  userRoles: Set<string>
): boolean => {
  if (!metadata) {
    return false;
  }

  if (metadata.execute_roles.includes("all")) {
    return true;
  }

  return metadata.execute_roles.some((role) => userRoles.has(role));
};

const getDisabledWorkflowReason = (
  metadata: WorkflowMetadata | undefined,
  isFormEnabled: boolean
): string => {
  if (!isFormEnabled) {
    return "Form Coming Soon!";
  }

  if (!metadata) {
    return "Workflow metadata is unavailable.";
  }

  const executeRoles = metadata.execute_roles;
  if (executeRoles.length === 0) {
    return "Required execute roles are not configured.";
  }

  return `Required execute roles: ${executeRoles.join(", ")}`;
};

const NewWorkflowChooser = () => {
  const [isOpen, setIsOpen] = useState(false);
  const { config } = useRuntimeConfig();
  const apiURL = config?.workflowApiUrl;
  const { data: workflowMetadata } = useSWRImmutable<WorkflowMetadataResponse>(
    apiURL ? sanitizeUrl(`${apiURL}/v1/workflow/metadata`) : null,
    fetcher
  );
  const { data: userInfo } = useSWRImmutable<WhoamiResponse>(
    apiURL ? sanitizeUrl(`${apiURL}/whoami`) : null,
    fetcher
  );

  const metadataBySlug = workflowMetadataBySlug(workflowMetadata?.workflows);
  const userRoles = new Set(userInfo?.roles ?? []);

  return (
    <div className="relative inline-block text-left">
      <Popover open={isOpen} onOpenChange={setIsOpen}>
        <PopoverTrigger asChild>
          <Button
            aria-label="New workflow"
            size="icon"
            title="New workflow"
            variant="ghost"
          >
            <PlusIcon size={24} />
          </Button>
        </PopoverTrigger>

        <PopoverContent align="end" className="max-h-[70vh] overflow-y-auto">
          {siteConfig.workflows.map((item) => {
            const metadata = metadataBySlug.get(item.slug);
            const hasPermission = canExecuteWorkflow(metadata, userRoles);
            const isEnabled = item.enabled && hasPermission;
            const disabledReason = getDisabledWorkflowReason(
              metadata,
              item.enabled
            );

            return isEnabled ? (
              <Link
                key={item.slug}
                href={`/workflows/${item.slug}/form`}
                className="flex rounded-sm border-none px-3 py-2 hover:border-none hover:bg-accent hover:text-accent-foreground"
                onClick={() => setIsOpen(false)}
              >
                {item.title}
              </Link>
            ) : (
              <TooltipProvider delayDuration={0} key={item.slug}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <button
                      aria-disabled="true"
                      className={cn(
                        "flex w-full cursor-not-allowed rounded-sm border-none bg-transparent px-3 py-2 text-left opacity-50",
                        "hover:border-none hover:bg-accent hover:text-accent-foreground"
                      )}
                      type="button"
                    >
                      {item.title}
                    </button>
                  </TooltipTrigger>
                  <TooltipContent side="left">
                    <p>{disabledReason}</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            );
          })}
        </PopoverContent>
      </Popover>
    </div>
  );
};

const UserRolesMenu = () => {
  const { config } = useRuntimeConfig();
  const apiURL = config?.workflowApiUrl;
  const { data: userInfo, error } = useSWRImmutable<WhoamiResponse>(
    apiURL ? sanitizeUrl(`${apiURL}/whoami`) : null,
    fetcher
  );

  const roles = (userInfo?.roles ?? []).filter(
    (role) => role.toLowerCase() !== "all"
  );

  return (
    <Popover>
      <PopoverTrigger asChild>
        <Button
          aria-label="User roles"
          size="icon"
          title="User roles"
          variant="ghost"
        >
          <UserCircle size={24} />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80">
        <div className="space-y-4">
          <div className="space-y-1">
            <div className="text-xs font-medium text-muted-foreground">
              Username
            </div>
            <div className="break-all text-sm font-medium">
              {userInfo?.user ?? "Unknown user"}
            </div>
            {error && (
              <div className="text-xs text-destructive">
                Unable to load roles
              </div>
            )}
          </div>
          <div className="space-y-2">
            <div className="text-xs font-medium text-muted-foreground">
              Roles
            </div>
            <div className="flex flex-wrap gap-2">
              {roles.length > 0 ? (
                roles.map((role) => (
                  <Badge key={role} variant="secondary">
                    {role}
                  </Badge>
                ))
              ) : (
                <span className="text-sm text-muted-foreground">No roles</span>
              )}
            </div>
          </div>
          <Button
            asChild
            className="w-full justify-start gap-2"
            variant="outline"
          >
            <a href="/auth/logout">
              <LogOut size={16} />
              Logout
            </a>
          </Button>
        </div>
      </PopoverContent>
    </Popover>
  );
};

export function SiteHeader() {
  return (
    <header className="bg-background sticky top-0 z-40 w-full border-b">
      <div className="container flex h-16 items-center space-x-4 sm:justify-between sm:space-x-0">
        <MainNav items={siteConfig.mainNav} />
        <div className="flex flex-1 items-center justify-end space-x-4">
          <nav className="flex items-center space-x-1">
            <NewWorkflowChooser />
            <UserRolesMenu />
            <ThemeToggle />
          </nav>
        </div>
      </div>
    </header>
  );
}
