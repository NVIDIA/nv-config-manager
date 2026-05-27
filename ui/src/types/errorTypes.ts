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
export interface ErrorType {
  status: number;
  title: string;
  message: string;
  actionText?: string;
  actionHref?: string;
}

export const ERROR_CONFIGS = {
  FORBIDDEN: {
    status: 403,
    title: "Access Denied",
    message: "You do not have permission to access this resource.",
    actionText: "Go to Workflows",
    actionHref: "/workflows",
  },
  UNAUTHORIZED: {
    status: 401,
    title: "Unauthorized",
    message: "Please log in to access this resource.",
    actionText: "Login",
    actionHref: "/login",
  },
  NOT_FOUND: {
    status: 404,
    title: "Not Found",
    message: "The requested resource could not be found.",
    actionText: "Go to Workflows",
    actionHref: "/workflows",
  },
  SERVER_ERROR: {
    status: 500,
    title: "Server Error",
    message: "An unexpected error occurred. Please try again later.",
  },
} as const;
