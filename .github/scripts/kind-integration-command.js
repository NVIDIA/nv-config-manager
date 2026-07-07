// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

module.exports = async ({ github, context, core }) => {
  const { owner, repo } = context.repo;
  const pullNumber = context.payload.issue.number;
  const username = context.payload.comment.user.login;

  const reply = (body) =>
    github.rest.issues.createComment({
      owner,
      repo,
      issue_number: pullNumber,
      body,
    });
  const reject = async (message) => {
    await reply("ERROR: " + message);
    core.setFailed(message);
  };

  let permission = "none";
  try {
    const response = await github.rest.repos.getCollaboratorPermissionLevel({
      owner,
      repo,
      username,
    });
    permission = response.data.permission;
  } catch (error) {
    if (error.status !== 404) {
      throw error;
    }
  }
  if (!["admin", "write"].includes(permission)) {
    await reject("@" + username + " needs write access to start Kind integration tests.");
    return;
  }

  const { data: pull } = await github.rest.pulls.get({
    owner,
    repo,
    pull_number: pullNumber,
  });
  if (pull.state !== "open") {
    await reject("Kind integration tests can only be started for an open PR.");
    return;
  }

  const currentSha = pull.head.sha.toLowerCase();
  const trustedBranch = "pull-request/" + pullNumber;
  let trustedRef;
  try {
    const response = await github.rest.git.getRef({
      owner,
      repo,
      ref: "heads/" + trustedBranch,
    });
    trustedRef = response.data;
  } catch (error) {
    if (error.status !== 404) {
      throw error;
    }
    await reject(
      "Trusted branch " +
        trustedBranch +
        " does not exist. Run /ok to test " +
        currentSha +
        " first.",
    );
    return;
  }

  if (trustedRef.object.sha.toLowerCase() !== currentSha) {
    await reject(
      "Trusted branch " +
        trustedBranch +
        " is stale. Run /ok to test " +
        currentSha +
        " first.",
    );
    return;
  }

  const { data: runs } = await github.rest.actions.listWorkflowRuns({
    owner,
    repo,
    workflow_id: "kind-integration.yml",
    branch: trustedBranch,
    event: "workflow_dispatch",
    per_page: 20,
  });
  const activeRun = runs.workflow_runs.find(
    (run) => run.head_sha.toLowerCase() === currentSha && run.status !== "completed",
  );
  if (activeRun) {
    await reply("INFO: Kind integration is already running: " + activeRun.html_url);
    return;
  }

  await github.rest.actions.createWorkflowDispatch({
    owner,
    repo,
    workflow_id: "kind-integration.yml",
    ref: trustedBranch,
    inputs: {
      test_path: "src/tests/integration/",
      observability: "false",
      approved_sha: currentSha,
    },
  });

  await reply(
    "Queued Kind integration for " +
      currentSha +
      ": https://github.com/" +
      owner +
      "/" +
      repo +
      "/actions/workflows/kind-integration.yml",
  );
};
