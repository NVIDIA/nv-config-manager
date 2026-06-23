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
import { NextRequest, NextResponse } from "next/server";

const DEFAULT_AUTH_COOKIE_NAMES = [
  "NVConfigManagerAccessToken",
  "NVConfigManagerIdToken",
];

const COOKIE_NAME_PATTERN = /^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$/;

const expiredCookie = (name: string, domain?: string): string => {
  const domainPart = domain ? ` Domain=${domain};` : "";
  return [
    `${name}=;`,
    domainPart,
    " Path=/;",
    " Expires=Thu, 01 Jan 1970 00:00:00 GMT;",
    " Max-Age=0;",
    " Secure;",
    " HttpOnly;",
    " SameSite=Lax",
  ].join("");
};

const cookieDomains = (hostname: string): string[] => {
  if (!hostname.includes(".") || hostname === "localhost") {
    return [];
  }

  const labels = hostname.split(".").filter(Boolean);
  const domains = new Set<string>();
  domains.add(hostname);
  domains.add(`.${hostname}`);

  if (labels.length > 2) {
    const parentDomain = labels.slice(1).join(".");
    domains.add(parentDomain);
    domains.add(`.${parentDomain}`);
  }

  return Array.from(domains);
};

const cookieNamesToClear = (request: NextRequest): string[] => {
  const names = new Set(DEFAULT_AUTH_COOKIE_NAMES);

  request.cookies.getAll().forEach((cookie) => {
    if (COOKIE_NAME_PATTERN.test(cookie.name)) {
      names.add(cookie.name);
    }
  });

  return Array.from(names);
};

export async function GET(request: NextRequest) {
  const response = new NextResponse(null, {
    status: 302,
    headers: {
      Location: "/oauth2/logout",
    },
  });
  const hostname = request.nextUrl.hostname;
  const domains = cookieDomains(hostname);

  cookieNamesToClear(request).forEach((name) => {
    response.headers.append("Set-Cookie", expiredCookie(name));
    domains.forEach((domain) => {
      response.headers.append("Set-Cookie", expiredCookie(name, domain));
    });
  });

  return response;
}

export const dynamic = "force-dynamic";
