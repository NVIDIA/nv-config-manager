// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

const APPROVAL_LABEL = "trust-boundary-reviewed";
const APPROVER_PERMISSIONS = new Set(["admin", "write"]);

const TRUST_BOUNDARY_PATHS = [
  ".gitlab-ci.yml",
  ".github/CODEOWNERS",
  ".github/copy-pr-bot.yaml",
];
const TRUST_BOUNDARY_PREFIXES = [
  ".gitlab/ci/",
  ".github/actions/",
  ".github/scripts/",
  ".github/workflows/",
];

function isTrustBoundaryPath(path) {
  return (
    TRUST_BOUNDARY_PATHS.includes(path) ||
    TRUST_BOUNDARY_PREFIXES.some((prefix) => path.startsWith(prefix))
  );
}

async function ensureApprovalLabel({ github, owner, repo }) {
  try {
    await github.rest.issues.getLabel({ owner, repo, name: APPROVAL_LABEL });
  } catch (error) {
    if (error.status !== 404) {
      throw error;
    }
    try {
      await github.rest.issues.createLabel({
        owner,
        repo,
        name: APPROVAL_LABEL,
        color: "b60205",
        description: "Current PR head has received deliberate trust-boundary review",
      });
    } catch (createError) {
      // Another PR run may have created this repository-wide label concurrently.
      if (createError.status !== 422) {
        throw createError;
      }
    }
  }
}

async function removeApprovalLabel({ github, owner, repo, pullNumber }) {
  try {
    await github.rest.issues.removeLabel({
      owner,
      repo,
      issue_number: pullNumber,
      name: APPROVAL_LABEL,
    });
  } catch (error) {
    if (error.status !== 404) {
      throw error;
    }
  }
}

async function writeSummary(core, changedPaths, message) {
  core.summary.addHeading("Trust Boundary Review");
  core.summary.addRaw(message);
  if (changedPaths.length > 0) {
    core.summary.addHeading("Trust-boundary files", 3);
    core.summary.addList(changedPaths);
  }
  await core.summary.write();
}

module.exports = async ({ github, context, core }) => {
  const { owner, repo } = context.repo;
  const pullNumber = context.payload.pull_request.number;
  const action = context.payload.action;
  const eventLabel = context.payload.label?.name;
  const actor = context.payload.sender.login;

  await ensureApprovalLabel({ github, owner, repo });

  const changedFiles = await github.paginate(github.rest.pulls.listFiles, {
    owner,
    repo,
    pull_number: pullNumber,
    per_page: 100,
  });
  const changedPaths = changedFiles
    .filter(
      ({ filename, previous_filename: previousFilename }) =>
        isTrustBoundaryPath(filename) ||
        (previousFilename && isTrustBoundaryPath(previousFilename)),
    )
    .map(({ filename }) => filename)
    .sort();

  let approved = context.payload.pull_request.labels.some(
    ({ name }) => name === APPROVAL_LABEL,
  );
  let failure;

  if (action === "synchronize" && approved) {
    await removeApprovalLabel({ github, owner, repo, pullNumber });
    approved = false;
    failure =
      "The trust-boundary approval was cleared because the PR head changed. " +
      "Review the current changes and apply the label again.";
  }

  if (action === "labeled" && eventLabel === APPROVAL_LABEL) {
    let permission = "none";
    try {
      const response = await github.rest.repos.getCollaboratorPermissionLevel({
        owner,
        repo,
        username: actor,
      });
      permission = response.data.permission;
    } catch (error) {
      if (error.status !== 404) {
        throw error;
      }
    }
    if (!APPROVER_PERMISSIONS.has(permission)) {
      await removeApprovalLabel({ github, owner, repo, pullNumber });
      approved = false;
      failure = `@${actor} needs write access to approve trust-boundary changes.`;
    }
  }

  if (changedPaths.length === 0) {
    await writeSummary(core, [], "No trust-boundary files changed.");
    return;
  }

  if (!approved) {
    failure ??=
      `A maintainer must review the current PR head and apply the ${APPROVAL_LABEL} label ` +
      "before approving CI execution.";
    await writeSummary(core, changedPaths, failure);
    core.setFailed(failure);
    return;
  }

  await writeSummary(
    core,
    changedPaths,
    `The ${APPROVAL_LABEL} label confirms deliberate review of the current PR head.`,
  );
};

module.exports.APPROVAL_LABEL = APPROVAL_LABEL;
module.exports.isTrustBoundaryPath = isTrustBoundaryPath;
