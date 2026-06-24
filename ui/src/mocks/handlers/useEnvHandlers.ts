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
import { http, HttpResponse } from "msw";
import { sanitizeUrl } from "@/lib/utils";
import { mockApiURL as apiURL } from "@/config/mockApiUrl";
import {
  DEVICE_TYPES_LIST_API_RESPONSE,
  NAMESPACE_TAGS_LIST_API_RESPONSE,
  ROLES_LIST_API_RESPONSE,
  SITES_LIST_API_RESPONSE,
  STATUS_LIST_API_RESPONSE,
  TENANT_LIST_API_RESPONSE,
} from "@/mocks/data/formData";

export const useEnvDataHandlers = [
  // http.get(
  //     sanitizeUrl(
  //       `${apiURL}/v1/parameter/location?location_type=Site&location_type=Module`
  //     ),
  //     async () => {
  //       return HttpResponse.json({ status: 201 });
  //     }
  //   ),
  http.get(
    sanitizeUrl(`${apiURL}/v1/parameter/location`),
    async () => {
      return HttpResponse.json(SITES_LIST_API_RESPONSE, { status: 200 });
    }
  ),
  http.get(sanitizeUrl(`${apiURL}/v1/parameter/role`), async () => {
    return HttpResponse.json(ROLES_LIST_API_RESPONSE, { status: 200 });
  }),
  http.get(sanitizeUrl(`${apiURL}/v1/parameter/status`), async () => {
    return HttpResponse.json(STATUS_LIST_API_RESPONSE, { status: 200 });
  }),
  http.get(sanitizeUrl(`${apiURL}/v1/parameter/tenant`), async () => {
    return HttpResponse.json(TENANT_LIST_API_RESPONSE, { status: 200 });
  }),
  http.get(sanitizeUrl(`${apiURL}/v1/parameter/namespace-tag`), async () => {
    return HttpResponse.json(NAMESPACE_TAGS_LIST_API_RESPONSE, { status: 200 });
  }),
  http.get(sanitizeUrl(`${apiURL}/v1/parameter/devicetypeid`), async () => {
    return HttpResponse.json(DEVICE_TYPES_LIST_API_RESPONSE, { status: 200 });
  }),
];
