"use client"
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

import { useState } from "react"
import { Copy } from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

interface ErrorTracebackViewerProps {
  error: {
    traceback: string
  }
  className?: string
}

interface ParsedError {
  message: string
  type: string
  frames: {
    file: string
    line?: string
    function?: string
    code?: string
    pointer?: string
  }[]
  cause?: ParsedError
}

const getFrameKey = (frame: ParsedError["frames"][number]) =>
  [frame.file, frame.line, frame.function, frame.code].filter(Boolean).join(":")

const getKeyedFrames = (frames: ParsedError["frames"]) => {
  const seenFrameCounts = new Map<string, number>()

  return frames.map((frame) => {
    const frameKey = getFrameKey(frame)
    const occurrence = seenFrameCounts.get(frameKey) ?? 0
    seenFrameCounts.set(frameKey, occurrence + 1)

    return {
      frame,
      key: `${frameKey}|occurrence:${occurrence}`,
    }
  })
}

const getErrorKey = (error: ParsedError) =>
  [error.type, error.message].filter(Boolean).join(":")

export function ErrorTracebackViewer({ error, className }: ErrorTracebackViewerProps) {
  const [copied, setCopied] = useState(false)

  // Parse Python-style traceback
  const parseTraceback = (traceback: string): ParsedError[] => {
    const errors: ParsedError[] = []
    let currentError: ParsedError | null = null

    // Split by lines and process
    const lines = traceback.split("\n")
    let i = 0

    while (i < lines.length) {
      const line = lines[i]

      // Check for error type and message
      if (line.includes("Error:") || line.includes("Exception:")) {
        const parts = line.split(": ", 2)
        currentError = {
          type: parts[0].trim(),
          message: parts[1] ? parts[1].trim() : "",
          frames: [],
        }
        errors.push(currentError)
      }
      // Check for "caused by" relationship
      else if (line.includes("The above exception was the direct cause of the following exception:")) {
        // Skip this line and continue
      }
      // Check for "Traceback (most recent call last):"
      else if (line.includes("Traceback (most recent call last):")) {
        // Start of a new traceback section
        if (!currentError) {
          currentError = {
            type: "Unknown Error",
            message: "",
            frames: [],
          }
          errors.push(currentError)
        }
      }
      // Check for stack frame
      else if (line.trim().startsWith("File ")) {
        // This is a stack frame line
        const fileMatch = line.match(/File "([^"]+)", line (\d+), in (.+)/)

        if (fileMatch && currentError) {
          const frame = {
            file: fileMatch[1],
            line: fileMatch[2],
            function: fileMatch[3],
            code: "",
            pointer: "",
          }

          // Check if next line is code
          if (i + 1 < lines.length && !lines[i + 1].trim().startsWith("File ") && lines[i + 1].trim()) {
            i++
            frame.code = lines[i].trim()

            // Check if next line is pointer (^^^^^)
            if (i + 1 < lines.length && lines[i + 1].includes("^")) {
              i++
              frame.pointer = lines[i].trim()
            }
          }

          currentError.frames.push(frame)
        }
      }
      // If we have a current error but this line doesn't match any pattern,
      // it might be part of the error message
      else if (currentError && line.trim() && !line.includes("Traceback")) {
        if (currentError.message) {
          currentError.message += "\n" + line.trim()
        } else {
          currentError.message = line.trim()
        }
      }

      i++
    }

    // Link errors as causes
    for (let i = 0; i < errors.length - 1; i++) {
      errors[i].cause = errors[i + 1]
    }

    return errors.length > 0 ? [errors[0]] : []
  }

  const parsedErrors = parseTraceback(error.traceback)

  const copyToClipboard = () => {
    navigator.clipboard.writeText(error.traceback)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  // Recursive component to render error and its causes
  const ErrorWithCauses = ({ error }: { error: ParsedError }) => (
    <div className="mb-4">
      <div className="bg-red-50/50 dark:bg-red-950/10 p-4 border-l-4 border-red-500">
        <div className="font-semibold text-red-700 dark:text-red-400 font-mono">{error.type}</div>
        <div className="font-mono text-sm whitespace-pre-wrap mt-1">{error.message}</div>
      </div>

      {error.frames.length > 0 && (
        <div className="mt-2 pl-4 border-l border-l-slate-200 dark:border-l-slate-700">
          {getKeyedFrames(error.frames).map(({ frame, key }) => (
            <div key={key} className="mb-3">
              <div className="text-xs text-slate-500 dark:text-slate-400 font-mono">
                File <span className="text-slate-700 dark:text-slate-300">{frame.file}</span>, line{" "}
                <span className="text-slate-700 dark:text-slate-300">{frame.line}</span>, in{" "}
                <span className="text-blue-600 dark:text-blue-400">{frame.function}</span>
              </div>

              {frame.code && (
                <div className="mt-1 pl-4 font-mono text-xs">
                  <div className="text-slate-800 dark:text-slate-200">{frame.code}</div>
                  {frame.pointer && <div className="text-red-500">{frame.pointer}</div>}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {error.cause && (
        <div className="mt-4">
          <div className="text-xs text-slate-500 italic mb-2">Caused by:</div>
          <ErrorWithCauses error={error.cause} />
        </div>
      )}
    </div>
  )

  return (
    <Card className={cn("w-full overflow-hidden", className)}>
      <CardHeader className="bg-red-50 dark:bg-red-950/20 border-b">
        <div className="flex items-center justify-between">
          <CardTitle className="text-red-700 dark:text-red-400">
            <span>Traceback</span>
          </CardTitle>
          <Button variant="outline" size="sm" onClick={copyToClipboard} className="h-8 gap-1">
            <Copy className="h-3.5 w-3.5" />
            <span>{copied ? "Copied!" : "Copy"}</span>
          </Button>
        </div>
      </CardHeader>
      <CardContent className="p-4">
        {parsedErrors.length > 0 ? (
          parsedErrors.map((error) => <ErrorWithCauses key={getErrorKey(error)} error={error} />)
        ) : (
          <div className="text-slate-500 italic">No traceback information available</div>
        )}
      </CardContent>
    </Card>
  )
}
