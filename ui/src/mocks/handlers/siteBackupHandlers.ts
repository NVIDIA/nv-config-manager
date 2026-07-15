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
import { delay, http, HttpResponse } from "msw";
import { sanitizeUrl } from "@/lib/utils";
import { mockApiURL as apiURL } from "@/config/mockApiUrl";
import { SiteBackupWorkflowInput } from "@/types/data-table.types";
import { FORBIDDEN_SITE_ID } from "@/mocks/data/formData";

export const siteBackupHandlers = [
  http.post(
    sanitizeUrl(`${apiURL}/v1/workflow/ngc/site_backup`),
    async ({ request }) => {
      const body = (await request.json()) as SiteBackupWorkflowInput;

      if (body.site === FORBIDDEN_SITE_ID) {
        return HttpResponse.json(
          {
            error: "Forbidden: You do not have permission to run this workflow",
          },
          { status: 403 }
        );
      }

      await delay(2500);

      return HttpResponse.json(
        {
          id: body.site || "site-used-for-id",
          href: `https://url-to-temporal.com/namespaces/default/workflows/${
            body.site || "site-used-for-id"
          }`,
        },
        { status: 201 }
      );
    }
  ),
];
