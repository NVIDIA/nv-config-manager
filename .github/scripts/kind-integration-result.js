// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

module.exports = async ({ github, context }) => {
  const run = context.payload.workflow_run;
  const branchMatch = /^pull-request\/(\d+)$/.exec(run.head_branch ?? "");

  if (run.event !== "workflow_dispatch" || run.status !== "completed" || !branchMatch) {
    return;
  }

  const { owner, repo } = context.repo;
  const conclusion = run.conclusion ?? "unknown";
  const shortSha = run.head_sha.slice(0, 12);

  await github.rest.issues.createComment({
    owner,
    repo,
    issue_number: Number(branchMatch[1]),
    body: `Kind integration completed with **${conclusion}** for \`${shortSha}\`: ${run.html_url}`,
  });
};
