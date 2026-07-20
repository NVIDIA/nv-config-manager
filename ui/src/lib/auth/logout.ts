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

/**
 * Build the oauth2-proxy sign-out redirect for the configured identity provider.
 */
export const providerLogoutRedirect = (
  returnUrl: string,
  endpoint = process.env.OIDC_END_SESSION_ENDPOINT,
  clientId = process.env.OIDC_CLIENT_ID
): string => {
  if (!endpoint) {
    return `/oauth2/sign_out?rd=${encodeURIComponent(returnUrl)}`;
  }

  try {
    const url = new URL(endpoint);
    if (url.protocol !== "https:" && url.protocol !== "http:") {
      return `/oauth2/sign_out?rd=${encodeURIComponent(returnUrl)}`;
    }
    url.searchParams.set("post_logout_redirect_uri", returnUrl);
    if (clientId) {
      url.searchParams.set("client_id", clientId);
    }
    // oauth2-proxy replaces this placeholder from its server-side session before
    // redirecting, allowing providers such as Keycloak to end the right session
    // without an interactive logout confirmation.
    url.searchParams.set("id_token_hint", "{id_token}");
    const providerLogoutUrl = url
      .toString()
      .replace("%7Bid_token%7D", "{id_token}");
    return `/oauth2/sign_out?rd=${encodeURIComponent(providerLogoutUrl)}`;
  } catch {
    return `/oauth2/sign_out?rd=${encodeURIComponent(returnUrl)}`;
  }
};
