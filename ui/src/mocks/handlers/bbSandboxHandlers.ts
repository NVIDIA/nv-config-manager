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

import { mockApiURL as apiURL } from "@/config/mockApiUrl";
import { sanitizeUrl } from "@/lib/utils";

const devices = [
  { id: "bb-device-1", name: "SJC0C-BBR-01" },
  { id: "bb-device-2", name: "SJC0C-BBR-02" },
];

export const bbSandboxHandlers = [
  http.get(sanitizeUrl(`${apiURL}/v1/parameter/bb-sandbox/devices`), () =>
    HttpResponse.json(devices)
  ),
  http.get(sanitizeUrl(`${apiURL}/v1/parameter/bb-sandbox/circuits`), () =>
    HttpResponse.json([
      { id: "circuit-1", cid: "BB-CIRCUIT-001", status: "Planned" },
    ])
  ),
  http.get(
    sanitizeUrl(`${apiURL}/v1/parameter/bb-sandbox/devices/:deviceId/interfaces`),
    () =>
      HttpResponse.json([
        { id: "port-1", name: "et-0/0/0", type: "100gbase-x-qsfp28" },
        { id: "port-2", name: "et-0/0/1", type: "100gbase-x-qsfp28" },
      ])
  ),
  http.get(sanitizeUrl(`${apiURL}/v1/parameter/bb-sandbox/next-lag`), () =>
    HttpResponse.json({ lag_name: "ae103" })
  ),
  http.get(
    sanitizeUrl(`${apiURL}/v1/parameter/bb-sandbox/next-prefix`),
    ({ request }) => {
      const ipv6 = new URL(request.url).searchParams.get("prefix_length") === "127";
      return HttpResponse.json({
        role: "BB-P2P",
        prefix: ipv6 ? "2001:db8::2/127" : "192.0.2.2/31",
        prefix_length: ipv6 ? 127 : 31,
        parent_prefix: ipv6 ? "2001:db8::/120" : "192.0.2.0/24",
      });
    }
  ),
  http.post(
    sanitizeUrl(`${apiURL}/v1/workflow/bb_sandbox/:workflow`),
    async ({ request }) => {
      await delay(100);
      return HttpResponse.json(
        { id: `bb-sandbox-${Date.now()}`, submitted_data: await request.json() },
        { status: 201 }
      );
    }
  ),
];
