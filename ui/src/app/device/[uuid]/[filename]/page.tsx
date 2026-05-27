"use client";
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

import { use } from "react";
import { useSearchParams } from "next/navigation";
import { useConfigFile, useConfigVersions } from "@/lib/config-store-api";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { CodeBlock } from "@/components/ui/code-block";
import { formatDate } from "@/lib/utils";
import { downloadConfigFile } from "@/lib/download-config";
import { ArrowLeft, History, FileText, Download } from "lucide-react";
import Link from "next/link";

export default function ConfigFilePage({ 
  params 
}: Readonly<{ 
  params: Promise<{ uuid: string; filename: string }>
}>) {
  const { uuid, filename } = use(params);
  const searchParams = useSearchParams();
  const fileType = (searchParams?.get("file_type") as "intended" | "backup") || "intended";
  const versionParam = searchParams?.get("version");
  const version = versionParam ? parseInt(versionParam, 10) : undefined;
  const decodedFilename = decodeURIComponent(filename);
  const { data: config, error, isLoading } = useConfigFile(uuid, decodedFilename, fileType, version);
  const { data: versions } = useConfigVersions(uuid, decodedFilename, fileType);
  
  // Check if the current version is the latest
  const isLatestVersion = versions ? config?.version === versions.versions[0]?.version : !version;
  const isViewingHistoricVersion = version && !isLatestVersion;

  if (isLoading) {
    return (
      <div className="container py-6">
        <div className="flex items-center justify-center">
          <p>Loading config file...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="container py-6">
        <Card className="border-destructive">
          <CardHeader>
            <CardTitle className="text-destructive">Error Loading Config</CardTitle>
            <CardDescription>{error.message}</CardDescription>
          </CardHeader>
        </Card>
      </div>
    );
  }

  if (!config) {
    return (
      <div className="container py-6">
        <Card>
          <CardHeader>
            <CardTitle>Config Not Found</CardTitle>
          </CardHeader>
        </Card>
      </div>
    );
  }

  return (
    <div className="container py-6">
      <div className="flex flex-col gap-6">
        <div>
          <div className="flex items-center gap-4 mb-2">
            <Button variant="ghost" size="sm" asChild>
              <Link href={`/device/${uuid}?file_type=${fileType}`} className="no-underline">
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Device
              </Link>
            </Button>
          </div>
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight flex items-center gap-2">
                <FileText className="h-8 w-8" />
                {decodedFilename}
              </h1>
              {config.device && (
                <p className="text-muted-foreground mt-2">
                  {config.device.name} - {config.device.site}
                </p>
              )}
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() =>
                  downloadConfigFile(
                    config.content,
                    `${config.device?.name ?? uuid}_${decodedFilename}`
                  )
                }
              >
                <Download className="mr-2 h-4 w-4" />
                Download
              </Button>
              {isViewingHistoricVersion && (
                <Button variant="outline" asChild>
                  <Link
                    href={`/device/${uuid}/${filename}?file_type=${fileType}`}
                    className="no-underline"
                  >
                    View Latest Version
                  </Link>
                </Button>
              )}
              <Button asChild>
                <Link
                  href={`/device/${uuid}/${filename}/history?file_type=${fileType}`}
                  className="no-underline"
                >
                  <History className="mr-2 h-4 w-4" />
                  View History
                </Link>
              </Button>
            </div>
          </div>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>File Metadata</CardTitle>
            {isViewingHistoricVersion && (
              <CardDescription className="flex items-center gap-2">
                <Badge variant="outline" className="text-amber-600 border-amber-600">
                  Viewing Historic Version
                </Badge>
              </CardDescription>
            )}
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 md:grid-cols-2">
              <div>
                <span className="text-sm text-muted-foreground">Version:</span>{" "}
                <Badge variant={isViewingHistoricVersion ? "outline" : "secondary"}>v{config.version}</Badge>
                {isLatestVersion && <span className="text-xs text-muted-foreground ml-2">(latest)</span>}
              </div>
              <div>
                <span className="text-sm text-muted-foreground">Author:</span>{" "}
                <span className="text-sm">{config.author}</span>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">Modified:</span>{" "}
                <span className="text-sm">{formatDate(config.created_at)}</span>
              </div>
              <div>
                <span className="text-sm text-muted-foreground">Hash:</span>{" "}
                <code className="text-xs bg-muted px-1 py-0.5 rounded">
                  {config.content_hash.substring(0, 12)}...
                </code>
              </div>
            </div>
            {config.commit_message && (
              <div className="mt-4">
                <span className="text-sm text-muted-foreground">Commit Message:</span>
                <p className="text-sm mt-1 bg-muted p-2 rounded">
                  {config.commit_message}
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>File Content</CardTitle>
            <CardDescription>
              {config.content.split('\n').length} lines
            </CardDescription>
          </CardHeader>
          <CardContent>
            <CodeBlock 
              code={config.content} 
              filename={decodedFilename}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

