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
export const TEST_CSV_WORKFLOWS = {
  workflow_type: "TestCsvWorkflow",
  workflow_input: {
    test: "csv-display-test",
  },
  workflows: [
    {
      id: "test-small-csv-workflow",
      name: "Test Small CSV Workflow",
      status: "COMPLETED",
      workflow_type: "TestCsvWorkflow",
      started_at: "2023-10-19T14:30:00Z",
      completed_at: "2023-10-19T14:35:00Z",
      workflow_input: {
        site: "test-site",
        url: "https://example.com/test-site",
      },
      stages: [
        {
          name: "Small CSV Test Stage",
          state: "COMPLETE",
          description:
            "This stage has a small CSV for testing display functionality",
          requires_approval: false,
          retryable: true,
          state_history: [
            {
              state: "PENDING",
              time: "2023-10-19T14:30:00Z",
            },
            {
              state: "IN_PROGRESS",
              time: "2023-10-19T14:31:00Z",
            },
            {
              state: "COMPLETE",
              time: "2023-10-19T14:32:00Z",
            },
          ],
          output: {
            display:
              "Here is a small CSV containing test data.\n\n[Export to CSV](data:text/csv;base64,SXRlbSxRdWFudGl0eSxQcmljZSxUb3RhbAphcHBsZXMsMTAsMS45OSwxOS45MAp2YW5pbGxhIGljZSBjcmVhbSwyLDMuOTksNy45OApjaG9jb2xhdGUgY2FrZSwxLDkuOTksOS45OQp0b3RhbCwsLDM3Ljg4)",
          },
        },
        {
          name: "Large CSV Test Stage",
          state: "COMPLETE",
          description:
            "This stage has a larger CSV for testing the display vs. download functionality",
          requires_approval: false,
          retryable: true,
          state_history: [
            {
              state: "PENDING",
              time: "2023-10-19T14:33:00Z",
            },
            {
              state: "IN_PROGRESS",
              time: "2023-10-19T14:34:00Z",
            },
            {
              state: "COMPLETE",
              time: "2023-10-19T14:35:00Z",
            },
          ],
          output: {
            display:
              "Here is a larger CSV with more data that should trigger the download-only functionality.\n\n[Export to CSV](data:text/csv;base64,SWQsTGFzdE5hbWUsRmlyc3ROYW1lLEVtYWlsLEdlbmRlcixJcEFkZHJlc3MNCjEsV2F0bGluZyxLaXJzdGVuLGt3YXRsaW5nMEBpbWd1ci5jb20sRmVtYWxlLDIxOC4yMTMuNjIuMTA1DQoyLFJleWtzdW4sQ2VjaWxpYSxjcmV5a3N1bjFAZGlzY3VzLm5ldCxGZW1hbGUsMTgzLjExMC4xMjIuMjQ3DQozLFN1Y2hlLFJvYmVydGEscnN1Y2hlMkBleGJsb2cuanAsRmVtYWxlLDIzOC4xMjMuMTM3LjIyNA0KNCxTaG93ZWxsLEhhcmxleSxoc2hvd2VsbDNAbWFjLmNvbSxGZW1hbGUsMTc3LjE0MC4yMTUuMTM0DQo1LEJydWdnZW4sRm9ycmVzdCxmYnJ1Z2dlbjRAbXlzcGFjZS5jb20sTWFsZSw2LjE5My4xOC4xNTYNCjYsRnVybWFuZ2UsVHJhdmlzLHRmdXJtYW5nZTVAZ2l6bW9kby5jb20sTWFsZSw5MS4xNDUuMTA4LjEwOA0KNyxQb3R0ZXIsQ3Jpc3N5LGNwb3R0ZXI2QHN0YW5mb3JkLmVkdSxGZW1hbGUsMTAwLjEyNi42NS4xNDENCjgsR2FsbGFjaGVyLENvbm9yLGNnYWxsYWNoZXI3QGZlZWRidXJuZXIuY29tLE1hbGUsMTUzLjExOC40NS45OA0KOSxHdWlyYXVkLFZpdGEsdmd1aXJhdWQ4QHNiLmNvbSxGZW1hbGUsMzYuODYuODUuMTU0DQoxMCxSZWluaGFyZHQsQ2FzaWEsY3JlaW5oYXJkdDlAcXVhbnRjYXN0Lm5ldCxGZW1hbGUsODYuMzguMTgyLjE3NA0KMTEsTW9ycmlsbCxCbGlzcy5ibW9ycmlsbGFAYnVzaW5lc3N3aXJlLmNvbSxGZW1hbGUsMTA2LjE2Mi4yMTkuMjE0DQoxMixCcnVubyxLaW5nLGticnVub2JAaHVmZmluZ3RvbnBvc3QuY29tLE1hbGUsMTI2LjM2LjgwLjExNg0KMTMsTWFuZHJ5LFRvYml0Z21hbmRyeWNAaW1ndXIuY29tLE1hbGUsMTAuMTM1LjI2LjE1NA0KMTQsV3JpZ2h0LEdpYmJpLGd3cmlnaHRkQGltZ3VyLmNvbSxNYWxlLDIyMi4yMDQuMTI5Ljk4DQoxNSxLdXNpY2ssQWxseXNvbixha3VzaWNrZUBhb2wuY29tLEZlbWFsZSw5My4xODkuMjUwLjIxMw0KMTYsSGlnaG5hbSxNaWtpZSxtaGlnaG5hbWZAcGhvdG9idWNrZXQuY29tLE1hbGUsMTcyLjIzNC41MS45MA0KMTcsRGVubnlzLE15Y2hhbCxtZGVubnlzZ0B0aGVnbG9iZWFuZG1haWwuY29tLE1hbGUsMTkyLjEyNS4zMS4xMzUNCjE4LEtvbnplbG1hbm4sQWRkaWUgLGFrb256ZWxtYW5uaEBnbWFpbC5jb20sRmVtYWxlLDE5My4xNDIuMjQzLjQ3DQoxOSxLaW5naG9ybixGcmFuY2lzY28sZmtpbmdob3JuaUBwaG90b2J1Y2tldC5jb20sTWFsZSw1Ni4xODkuNDUuMTk3DQoyMCxXaGFsbGV5LENhbCxjd2hhbGxleWpAY25ldC5jb20sTWFsZSw1MS4xNzcuMTI4LjE2MQ0KMjEsRmllbGQsRWRpdGgsZWZpZWxka0BnbWFpbC5jb20sRmVtYWxlLDgzLjE1Mi4xMS41Nw0KMjIsU2luZ2VyLEJldHNleSwic2Jpbmdlclc4QG5ldGxvZy5jb20iLEZlbWFsZSwyMTEuMy4xNzAuMjA5DQoyMyxEYXZpZCxBbHRvbixhZGF2aWRtQHllbHAuY29tLE1hbGUsMTA1LjY1Ljc1LjIxMA0KMjQsUmF5dG9uLEVtbWllLGVyYXl0b25uQHR3aXR0ZXIuY29tLEZlbWFsZSw3OS4yMTAuMTQ1LjY1DQoyNSxEaXRjaGZpZWxkLEFyaWVsbGEsYWRpdGNoZmllbGRvQHJldXRlcnMuY29tLEZlbWFsZSw2OS4zNS44OS43Nw0KMjYsTWFjRGV2aXR0LEhhbnMsaG1hY2Rldml0dHBAd2lraSxNYWxlLDM4LjI0Mi4xNzAuMTY0DQoyNyxNYWtlLExhdXJlbixtbGFrZXFAbWFjLmNvbSxGZW1hbGUsMTgxLjEzOC4yMjguMTY3DQoyOCxXZWJiLUJvd2VuLFJhbmRpLHJ3ZWJiYm93ZW5yQG1haWNoaW1wLmNvbSxGZW1hbGUsMTc3LjIyOC4xNS4xNTcNCjI5LEphbWlzb24sQWthbixhamFtaXNvbnNAd2lraXBlZGlhLmNvbSxNYWxlLDEyMC41Ni4yMzEuMTc0DQozMCxXYWxsa2VyLFJhY2hlbGxlLHJ3YWxsa2VydEBnbWFpbC5jb20sRmVtYWxlLDg3LjIxMy4xMDQuOTMNCjMxLFN1dHRvbixXaWxsaWFtLHdzdXR0b251QGJhaWR1LmNvbSxNYWxlLDE4MC4zOS4yMjMuMTcxDQozMixCZXJyaWZmLEFubmllcnJvc2UsYWJlcnJpZmZ2QGV4YW1wbGUuY29tLEZlbWFsZSwyMTkuOTcuMTQxLjE2NQ0KMzMsQmFyY2xheSxBcmxpZSxhYmFyY2xheXdAZ29vZ2xlLmVzLEZlbWFsZSwxOTcuMTcwLjE1Ny4xNDYNCjM0LEhhcnQtVGhvbXBzb24sSmFuZSxqaGFydHRob21wc29ueEBzYi5jb20sRmVtYWxlLDYyLjE5Mi41Ny4xOTQNCjM1LE9ybWVyb2QsVGVkLE9ybWVyb2Q7dGVkQHNvLmNvLExhdC4sTWFsZSw5OC4xNDAuODkuMjM2DQozNixTdGVwaGVucyxNZWxpc3NhLG1zdGVwaGVuc3pAZW5nYWRnZXQuY29tLEZlbWFsZSwyMDMuMTk3LjE3Ny43DQozNyxLb3V6ZSxLaXJieWUsa2tvdXplMTBAZXhhbXBsZS5jb20sRmVtYWxlLDAuMTcwLjM2LjIwNw0KMzgsQXRraW5zLEpveWFubmEsamF0a2luczExQHdlZWJseS5jb20sRmVtYWxlLDI5LjI1NC4xMjcuMjM3DQozOSxEYXJieXNoaXJlLFNlcmdlaSxzZGFyYnlzaGlyZTEyQGJpZ2Nhcm1lbC5jb20sTWFsZSwyNDUuMTA4LjEwNi45OA0KNDAsR2lsbGlhcmQsQnJpYW5hLGJnaWxsaWFyZDEzQGdvb2dsZS5jb20sRmVtYWxlLDE5MC4xMTQuMTcuMTgzDQo0MSxNYWxhY3JpZGEsRml0eiwibWFsYWNyaWRhO2ZpdHpAYWJjLm5ldCIsTWFsZSwxMzUuMTk4LjIzMi44DQo0MixXZXJsb2NrLEJydWNlLGJ3ZXJsb2NrMTVAY29jb2xvZ28uY29tLE1hbGUsMjQxLjE2OC4xODYuMjM4DQo0MyxDYXN0YWduYXNzZSxDYWx2aW4sY2Nhc3RhZ25hc3NlMTZAZXRobmlvbG9ndWUuY29tLE1hbGUsNTkuMTU1LjE1NS43Nw0KNDQsS2FyemFnLEFsbGlzb24sYWthcnphZzE3QHN0dW1ibGV1cG9uLmNvbSxGZW1hbGUsNDQuNTkuNjIuMzE)",
          },
        },
      ],
    },
  ],
};
