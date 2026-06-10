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
import { http, HttpResponse, delay } from "msw";
import { sanitizeUrl } from "@/lib/utils";
import { mockApiURL as apiURL } from "@/config/mockApiUrl";

interface IBPKeyCreationRequest {
  host?: string;
  pkey?: string;
}

const PKEY_PATTERN = /^0[xX][0-9a-fA-F]{1,4}$/;

export const ibPkeyCreationHandlers = [
  http.post(
    sanitizeUrl(`${apiURL}/v1/workflow/ngc/ib_pkey_creation`),
    async ({ request }) => {
      const body = (await request.json()) as IBPKeyCreationRequest;
      const normalizedPkey = body.pkey?.trim();

      if (!body.host) {
        return HttpResponse.json(
          { error: "Missing required field: host" },
          { status: 400 },
        );
      }

      if (normalizedPkey && !PKEY_PATTERN.test(normalizedPkey)) {
        return HttpResponse.json(
          { error: "pkey must match /^0[xX][0-9a-fA-F]{1,4}$/" },
          { status: 400 },
        );
      }

      await delay(1500);

      const workflowId = `ib-pkey-creation-${Date.now()}`;
      const submittedData: IBPKeyCreationRequest = { ...body };
      if (normalizedPkey) {
        submittedData.pkey = normalizedPkey;
      } else {
        delete submittedData.pkey;
      }

      return HttpResponse.json(
        {
          id: workflowId,
          href: `https://url-to-temporal.com/namespaces/default/workflows/${workflowId}`,
          submitted_data: submittedData,
        },
        { status: 201 },
      );
    },
  ),
];
