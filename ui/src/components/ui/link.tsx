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
import NextLink, { LinkProps as NextLinkProps } from "next/link";
import * as React from "react";

interface LinkProps extends NextLinkProps {
  children: React.ReactNode;
  title?: string;
}

/**
 * Custom Link component.
 *
 * Extends NextJS Link component to style external links with an icon, and open
 * them in a new tab.
 */
export const Link: React.FC<LinkProps> = ({
  href,
  title,
  children,
  ...props
}) => {
  const isExternal = String(href).startsWith("http");
  return (
    <NextLink
      href={href}
      title={title}
      target={isExternal ? "_blank" : undefined}
      rel={isExternal ? "noopener noreferrer" : undefined}
      {...props}
    >
      {children}
    </NextLink>
  );
};

