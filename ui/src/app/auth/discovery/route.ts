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
import { NextResponse } from "next/server";

type AuthDiscovery = {
  version: 1;
  authRequired: boolean;
  issuerUrl?: string;
  clientId?: string;
  scopes?: string[];
  services: Record<string, string>;
};

const normalizeUrl = (value?: string): string => {
  const url = value || "";
  let end = url.length;

  while (end > 0 && url[end - 1] === "/") {
    end -= 1;
  }

  return url.slice(0, end);
};

const appendPath = (baseUrl: string, path: string): string => {
  const normalizedBase = normalizeUrl(baseUrl);
  if (!normalizedBase) {
    return "";
  }
  return `${normalizedBase}${path}`;
};

const parseScopes = (value?: string): string[] => {
  if (!value?.trim()) {
    return [];
  }

  try {
    const parsed = JSON.parse(value);
    if (Array.isArray(parsed)) {
      return parsed
        .map((item) => String(item).trim())
        .filter((item) => item.length > 0);
    }
  } catch {
    // Fall through to delimiter parsing.
  }

  return value
    .replace(/,/g, " ")
    .split(/\s+/)
    .map((item) => item.trim())
    .filter((item) => item.length > 0);
};

const serviceUrls = (authRequired: boolean): Record<string, string> => {
  const workflowUrl = authRequired
    ? normalizeUrl(process.env.SVC_WORKFLOW_API_URL) ||
      appendPath(process.env.WORKFLOW_API_URL || "", "/v1/workflow")
    : appendPath(process.env.WORKFLOW_API_URL || "", "/v1/workflow");

  const mcpUrl = authRequired
    ? normalizeUrl(process.env.SVC_MCP_URL) || normalizeUrl(process.env.MCP_URL)
    : normalizeUrl(process.env.MCP_URL);

  return Object.fromEntries(
    Object.entries({
      workflow: workflowUrl,
      mcp: mcpUrl,
    }).filter(([, value]) => value.length > 0),
  );
};

export async function GET() {
  const authRequired = process.env.OIDC_ENABLED === "true";
  const response: AuthDiscovery = {
    version: 1,
    authRequired,
    services: serviceUrls(authRequired),
  };

  if (authRequired) {
    const issuerUrl = normalizeUrl(process.env.OIDC_ISSUER_URL);
    const clientId =
      process.env.OIDC_CLI_CLIENT_ID || process.env.OIDC_CLIENT_ID || "";
    if (!issuerUrl || !clientId) {
      return NextResponse.json(
        {
          error:
            "OIDC discovery misconfigured: missing OIDC_ISSUER_URL or OIDC_CLI_CLIENT_ID/OIDC_CLIENT_ID",
        },
        {
          status: 500,
          headers: {
            "Cache-Control": "no-store",
          },
        },
      );
    }
    response.issuerUrl = issuerUrl;
    response.clientId = clientId;
    response.scopes = parseScopes(process.env.OIDC_SCOPES);
  }

  return NextResponse.json(response, {
    headers: {
      "Cache-Control": "no-store",
    },
  });
}

export const dynamic = "force-dynamic";
