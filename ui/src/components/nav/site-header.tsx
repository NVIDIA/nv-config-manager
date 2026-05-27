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

import { siteConfig } from "@/config/site";
import { MainNav } from "@/components/nav";
import { ThemeToggle } from "@/components/theme";
import { useState } from "react";
import { PlusIcon } from "lucide-react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const NewWorkflowChooser = () => {
  const [isOpen, setIsOpen] = useState(false);
  const togglePopover = () => setIsOpen(!isOpen);
  return (
    <div className="relative inline-block text-left">
      <Popover open={isOpen} onOpenChange={togglePopover}>
        <PopoverTrigger asChild>
          <button
            className="inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 hover:bg-accent hover:text-accent-foreground h-10 w-10"
            title="New workflow"
          >
            <PlusIcon size={24} />
          </button>
        </PopoverTrigger>

        <PopoverContent>
          {siteConfig.workflows.map((item, index) =>
            item.enabled ? (
              <Link
                key={index}
                href={`/workflows/${item.slug}/form`}
                className="flex hover:bg-accent hover:text-accent-foreground rounded-sm border-none hover:border-none px-3 py-2"
                onClick={togglePopover}
              >
                {item.title}
              </Link>
            ) : (
              <TooltipProvider key={index}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <div className="cursor-not-allowed">
                      <div className="flex hover:bg-accent hover:text-accent-foreground rounded-sm border-none hover:border-none px-3 py-2 pointer-events-none opacity-50">
                        {item.title}
                      </div>
                    </div>
                  </TooltipTrigger>
                  <TooltipContent side="left">
                    <p>Form Coming Soon!</p>
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            )
          )}
        </PopoverContent>
      </Popover>
    </div>
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
            <ThemeToggle />
          </nav>
        </div>
      </div>
    </header>
  );
}
