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
import {
  AIRValidateSiteWorkflowInput,
  AIRDeleteSimulationWorkflowInput,
  AIRCreateSimulationWorkflowInput,
} from "@/types/data-table.types";
import { FORBIDDEN_SITE_ID, AIR_SIMULATIONS_MOCK_DATA } from "@/mocks/data";

export const airHandlers = [
  http.get(sanitizeUrl(`${apiURL}/v1/parameter/simulations`), async () => {
    return HttpResponse.json(AIR_SIMULATIONS_MOCK_DATA, { status: 200 });
  }),

  http.post(
    sanitizeUrl(`${apiURL}/v1/workflow/ngc/air_validate_site`),
    async ({ request }) => {
      const body = (await request.json()) as AIRValidateSiteWorkflowInput;

      if (!body.site_name) {
        return HttpResponse.json(
          { error: "Missing required fields" },
          { status: 400 }
        );
      }

      if (body.site_name === FORBIDDEN_SITE_ID) {
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
          id: body.site_name,
          href: `https://url-to-temporal.com/namespaces/default/workflows/${body.site_name}`,
          submitted_data: body,
        },
        { status: 201 }
      );
    }
  ),

  http.post(
    sanitizeUrl(`${apiURL}/v1/workflow/ngc/air_create_simulation`),
    async ({ request }) => {
      const body = (await request.json()) as AIRCreateSimulationWorkflowInput;

      if (!body.name || !body.topology) {
        return HttpResponse.json(
          { error: "Missing required fields" },
          { status: 400 }
        );
      }

      // Check for forbidden simulation names (using site ID as example)
      if (body.name === FORBIDDEN_SITE_ID) {
        console.log("FORBIDDEN_SITE_ID", body.name);
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
          id: body.name,
          href: `https://url-to-temporal.com/namespaces/default/workflows/${body.name}`,
          submitted_data: body,
        },
        { status: 201 }
      );
    }
  ),

  http.post("/v1/workflow/ngc/air_delete", async ({ request }) => {
    const body = (await request.json()) as AIRDeleteSimulationWorkflowInput;

    if (body.simulation_id === FORBIDDEN_SITE_ID) {
      return new HttpResponse(
        JSON.stringify({
          error: "Forbidden: You do not have permission to run this workflow",
        }),
        {
          status: 403,
          headers: {
            "Content-Type": "application/json",
          },
        }
      );
    }

    if (!body.simulation_id) {
      return new HttpResponse(
        JSON.stringify({ error: "Missing required fields" }),
        {
          status: 400,
          headers: {
            "Content-Type": "application/json",
          },
        }
      );
    }

    return new HttpResponse(
      JSON.stringify({
        id: body.simulation_id,
        href: `https://url-to-temporal.com/namespaces/default/workflows/${body.simulation_id}`,
        submitted_data: body,
      }),
      {
        status: 201,
        headers: {
          "Content-Type": "application/json",
        },
      }
    );
  }),
];
