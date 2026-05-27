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
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2",
  {
    variants: {
      variant: {
        default:
          "border-transparent bg-primary text-primary-foreground hover:bg-primary/80",
        secondary:
          "border-transparent bg-secondary text-secondary-foreground hover:bg-secondary/80",
        destructive:
          "border-transparent bg-destructive text-destructive-foreground hover:bg-destructive/80",
        outline: "text-foreground",
        NOT_STARTED:
          "border-gray-400 bg-gray-500 text-gray-100 hover:bg-gray-600",
        IN_PROGRESS:
          "border-blue-500 bg-blue-600 text-blue-100 hover:bg-blue-700",
        PENDING_APPROVAL:
          "border-yellow-300 bg-yellow-400 text-yellow-100 hover:bg-yellow-700",
        COMPLETE:
          "border-green-500 bg-green-600 text-green-100 hover:bg-green-700",
        UNREACHABLE:
          "border-gray-800 bg-gray-900 text-gray-100 hover:bg-gray-800",
        FAILED: "border-red-500 bg-red-600 text-red-100 hover:bg-red-700",
        REJECTED: "border-red-700 bg-red-800 text-red-100 hover:bg-red-900",
        APPROVED:
          "border-green-700 bg-green-800 text-green-100 hover:bg-green-900",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

export interface BadgeProps
  extends
  React.HTMLAttributes<HTMLDivElement>,
  VariantProps<typeof badgeVariants> { }

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
