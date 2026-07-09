// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

module.exports = async ({ github, context }) => {
  const run = context.payload.workflow_run;
  const branchMatch = /^pull-request\/(\d+)$/.exec(run.head_branch ?? "");

  if (run.event !== "workflow_dispatch" || run.status !== "completed" || !branchMatch) {
    return;
  }

  const { owner, repo } = context.repo;
  const pullNumber = Number(branchMatch[1]);
  const { data: pull } = await github.rest.pulls.get({
    owner,
    repo,
    pull_number: pullNumber,
  });
  if (pull.head.sha.toLowerCase() !== run.head_sha.toLowerCase()) {
    return;
  }

  const conclusion = run.conclusion ?? "unknown";
  const shortSha = run.head_sha.slice(0, 12);

  await github.rest.issues.createComment({
    owner,
    repo,
    issue_number: pullNumber,
    body: `Kind integration completed with **${conclusion}** for \`${shortSha}\`: ${run.html_url}`,
  });
};
