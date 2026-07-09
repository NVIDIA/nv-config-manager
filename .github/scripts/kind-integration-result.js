// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

const RESULT_START = "<!-- kind-integration-result:start -->";
const RESULT_END = "<!-- kind-integration-result:end -->";

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function updatePullRequestBody(body, resultLine) {
  const currentBody = body ?? "";
  const resultBlock = `${RESULT_START}\n${resultLine}\n${RESULT_END}`;
  const markerPattern = new RegExp(
    `${escapeRegExp(RESULT_START)}[\\s\\S]*?${escapeRegExp(RESULT_END)}`,
  );

  if (markerPattern.test(currentBody)) {
    return currentBody.replace(markerPattern, resultBlock);
  }

  const legacyPattern =
    /(Passing Kind Integration run, if not automatically reported:\n)([\s\S]*?)(\n## )/;
  if (legacyPattern.test(currentBody)) {
    return currentBody.replace(legacyPattern, `$1${resultBlock}$3`);
  }

  return `${currentBody.trimEnd()}\n\n## Kind Integration\n\n${resultBlock}\n`;
}

function warn(core, message) {
  if (typeof core?.warning === "function") {
    core.warning(message);
    return;
  }

  console.warn(message);
}

function getErrorMessage(error) {
  return error?.message || String(error);
}

module.exports = async ({ github, context, core, run: explicitRun }) => {
  const run = explicitRun ?? context.payload.workflow_run;
  if (!run) {
    return;
  }

  const branchMatch = /^pull-request\/(\d+)$/.exec(run.head_branch ?? "");

  if (run.event !== "workflow_dispatch" || run.status !== "completed" || !branchMatch) {
    return;
  }

  const { owner, repo } = context.repo;
  const pullNumber = Number(branchMatch[1]);
  try {
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
    const resultLine = `Kind integration completed with **${conclusion}** for [\`${shortSha}\`](${run.html_url}).`;

    await github.rest.pulls.update({
      owner,
      repo,
      pull_number: pullNumber,
      body: updatePullRequestBody(pull.body, resultLine),
    });
  } catch (error) {
    warn(
      core,
      `Failed to update PR #${pullNumber} with Kind integration result: ${getErrorMessage(error)}`,
    );
  }
};
