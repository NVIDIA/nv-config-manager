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

interface InterfaceRefPayload {
  device: string;
  interface: string;
  membership?: string;
}

interface MembershipRequest {
  host?: string;
  pkey?: string;
  interfaces?: InterfaceRefPayload[];
  guids?: string[];
  guid_memberships?: string[];
}

const PKEY_PATTERN = /^0[xX][0-9a-fA-F]{1,4}$/;
const GUID_PATTERN = /^0[xX][0-9a-fA-F]{16}$/;

function isValidInterfaceRef(entry: unknown): entry is InterfaceRefPayload {
  if (!entry || typeof entry !== "object") {
    return false;
  }
  const ref = entry as Partial<InterfaceRefPayload>;
  return (
    typeof ref.device === "string" &&
    ref.device.trim().length > 0 &&
    typeof ref.interface === "string" &&
    ref.interface.trim().length > 0
  );
}

function validateMembershipBody(
  body: MembershipRequest,
): { error: string; status: number } | null {
  if (!body.host) {
    return { error: "Missing required field: host", status: 400 };
  }
  if (!body.pkey) {
    return { error: "Missing required field: pkey", status: 400 };
  }
  if (!PKEY_PATTERN.test(body.pkey)) {
    return {
      error: "pkey must match /^0[xX][0-9a-fA-F]{1,4}$/",
      status: 400,
    };
  }
  const hasInterfaces =
    Array.isArray(body.interfaces) && body.interfaces.length > 0;
  const hasGuids = Array.isArray(body.guids) && body.guids.length > 0;
  if (hasInterfaces === hasGuids) {
    return {
      error: "Provide exactly one of 'interfaces' or 'guids'",
      status: 400,
    };
  }
  if (
    hasInterfaces &&
    body.interfaces!.some((entry) => !isValidInterfaceRef(entry))
  ) {
    return {
      error: "Each interfaces entry must include non-empty 'device' and 'interface'",
      status: 400,
    };
  }
  if (hasGuids && body.guids!.some((g) => !GUID_PATTERN.test(g))) {
    return {
      error: "Each guid must match 0x + 16 hex digits",
      status: 400,
    };
  }
  return null;
}

function successResponse(workflowKind: string, body: MembershipRequest) {
  const workflowId = `${workflowKind}-${Date.now()}`;
  return HttpResponse.json(
    {
      id: workflowId,
      href: `https://url-to-temporal.com/namespaces/default/workflows/${workflowId}`,
      submitted_data: body,
    },
    { status: 201 },
  );
}

function makeMembershipHandler(path: string, workflowKind: string) {
  return http.post(
    sanitizeUrl(`${apiURL}${path}`),
    async ({ request }) => {
      const body = (await request.json()) as MembershipRequest;
      const err = validateMembershipBody(body);
      if (err) {
        return HttpResponse.json({ error: err.error }, { status: err.status });
      }
      await delay(1500);
      return successResponse(workflowKind, body);
    },
  );
}

export const ibPkeyMemberHandlers = [
  makeMembershipHandler(
    "/v1/workflow/ngc/ib_pkey_member_add",
    "ib-pkey-member-add",
  ),
  makeMembershipHandler(
    "/v1/workflow/ngc/ib_pkey_member_delete",
    "ib-pkey-member-delete",
  ),
  makeMembershipHandler(
    "/v1/workflow/ngc/ib_pkey_member_update",
    "ib-pkey-member-update",
  ),
];
