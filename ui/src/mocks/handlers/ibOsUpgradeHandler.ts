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
import { IBOSUpgradeWorkflowInput } from "@/types/data-table.types";
import { FORBIDDEN_DEVICE_IDS } from "@/mocks/data/devicesData";

export const ibOsUpgradeHandlers = [
  http.post(
    sanitizeUrl(`${apiURL}/v1/workflow/ngc/infiniband_mlnx_os_upgrade`),
    async ({ request }) => {
      const body = (await request.json()) as IBOSUpgradeWorkflowInput;

      if (!body.device_id) {
        return HttpResponse.json(
          { error: "Missing required fields" },
          { status: 400 }
        );
      }

      if (Object.values(FORBIDDEN_DEVICE_IDS).includes(body.device_id)) {
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
          id: body.device_id,
          href: `https://url-to-temporal.com/namespaces/default/workflows/${body.device_id}`,
          submitted_data: body,
        },
        { status: 201 }
      );
    }
  ),

  http.post(
    sanitizeUrl(`${apiURL}/v1/workflow/ngc/infiniband_mlnx_os_upgrade`),
    async ({ request }) => {
      const body = (await request.json()) as IBOSUpgradeWorkflowInput;

      if (!body.device_id) {
        return HttpResponse.json(
          { error: "Missing required fields" },
          { status: 400 }
        );
      }

      // Check if UFM device is forbidden
      if (Object.values(FORBIDDEN_DEVICE_IDS).includes(body.device_id)) {
        return HttpResponse.json(
          {
            error:
              "Forbidden: You do not have permission to use this MLNX-OS device",
          },
          { status: 403 }
        );
      }

      await delay(2500);

      const workflowId = `infiniband-mlnx-os-upgrade-${Date.now()}`;

      return HttpResponse.json(
        {
          id: workflowId,
          href: `https://url-to-temporal.com/namespaces/default/workflows/${workflowId}`,
          submitted_data: body,
        },
        { status: 201 }
      );
    }
  ),
];
