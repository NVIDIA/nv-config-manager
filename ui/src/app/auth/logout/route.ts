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
import { providerLogoutRedirect } from "@/lib/auth/logout";

const DEFAULT_AUTH_COOKIE_NAMES = [
  "NVConfigManagerAccessToken",
  "NVConfigManagerIdToken",
];
const DEFAULT_PROXY_COOKIE_NAME = "_nvcm_oidc_proxy";

const COOKIE_NAME_PATTERN = /^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$/;

const gatewayUrl = (request: NextRequest): URL => {
  const configuredUrl = process.env.OIDC_GATEWAY_URL;
  if (configuredUrl) {
    try {
      const url = new URL(configuredUrl);
      if (url.protocol === "https:" || url.protocol === "http:") {
        return url;
      }
    } catch {
      // Fall back to the request URL when the deployment setting is malformed.
    }
  }
  return request.nextUrl;
};

const logoutReturnUrl = (request: NextRequest): string => {
  const returnUrl = request.nextUrl.searchParams.get("rd");
  const publicGatewayUrl = gatewayUrl(request);
  const fallback = new URL("/", publicGatewayUrl.origin).toString();

  if (!returnUrl) {
    return fallback;
  }

  try {
    const url = new URL(returnUrl);
    const baseHostname = publicGatewayUrl.hostname;
    const isBaseHostOrSubdomain =
      url.hostname === baseHostname ||
      url.hostname.endsWith(`.${baseHostname}`);

    if (url.protocol !== publicGatewayUrl.protocol || !isBaseHostOrSubdomain) {
      return fallback;
    }
    return url.toString();
  } catch {
    return fallback;
  }
};

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
  const proxyCookieName =
    process.env.OIDC_PROXY_COOKIE_NAME || DEFAULT_PROXY_COOKIE_NAME;
  const names = new Set(
    DEFAULT_AUTH_COOKIE_NAMES.filter((name) => name !== proxyCookieName)
  );

  request.cookies.getAll().forEach((cookie) => {
    if (
      cookie.name !== proxyCookieName &&
      COOKIE_NAME_PATTERN.test(cookie.name)
    ) {
      names.add(cookie.name);
    }
  });

  return Array.from(names);
};

export async function GET(request: NextRequest) {
  const returnUrl = logoutReturnUrl(request);
  const response = new NextResponse(null, {
    status: 302,
    headers: {
      Location: providerLogoutRedirect(returnUrl),
    },
  });
  const hostname = gatewayUrl(request).hostname;
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
