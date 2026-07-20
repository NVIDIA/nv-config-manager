// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

const assert = require("node:assert/strict");
const { test } = require("node:test");

const reviewTrustBoundary = require("./trust-boundary-review.js");
const { APPROVAL_LABEL, isTrustBoundaryPath } = reviewTrustBoundary;

function createSummary() {
  const state = { headings: [], lists: [], raw: [], writes: 0 };
  return {
    ...state,
    addHeading(value) {
      state.headings.push(value);
      return this;
    },
    addList(value) {
      state.lists.push(value);
      return this;
    },
    addRaw(value) {
      state.raw.push(value);
      return this;
    },
    async write() {
      state.writes += 1;
    },
    state,
  };
}

function createFixture(options = {}) {
  const createdLabels = [];
  const failures = [];
  const removedLabels = [];
  const summary = createSummary();
  const context = {
    repo: { owner: "NVIDIA", repo: "nv-config-manager" },
    payload: {
      action: options.action ?? "opened",
      label: options.eventLabel ? { name: options.eventLabel } : undefined,
      pull_request: {
        number: 134,
        labels: (options.labels ?? []).map((name) => ({ name })),
      },
      sender: { login: options.actor ?? "reviewer" },
    },
  };
  const github = {
    paginate: async () =>
      (options.files ?? ["README.md"]).map((file) =>
        typeof file === "string" ? { filename: file } : file,
      ),
    rest: {
      issues: {
        getLabel: async () => {
          if (options.missingApprovalLabel) {
            const error = new Error("Not Found");
            error.status = 404;
            throw error;
          }
        },
        createLabel: async (args) => createdLabels.push(args),
        removeLabel: async (args) => removedLabels.push(args),
      },
      pulls: {
        listFiles: async () => {},
      },
      repos: {
        getCollaboratorPermissionLevel: async () => {
          if (options.missingCollaborator) {
            const error = new Error("Not Found");
            error.status = 404;
            throw error;
          }
          return { data: { permission: options.permission ?? "write" } };
        },
      },
    },
  };
  const core = {
    setFailed: (message) => failures.push(message),
    summary,
  };

  return { context, core, createdLabels, failures, github, removedLabels, summary };
}

async function runFixture(options) {
  const fixture = createFixture(options);
  await reviewTrustBoundary(fixture);
  return fixture;
}

test("recognizes files that define the CI trust boundary", () => {
  for (const path of [
    ".gitlab-ci.yml",
    ".gitlab/ci/test.yml",
    ".github/CODEOWNERS",
    ".github/copy-pr-bot.yaml",
    ".github/actions/example/action.yml",
    ".github/scripts/example.js",
    ".github/workflows/public-ci.yml",
  ]) {
    assert.equal(isTrustBoundaryPath(path), true, path);
  }
  assert.equal(isTrustBoundaryPath("README.md"), false);
  assert.equal(isTrustBoundaryPath("github/workflows/example.yml"), false);
});

test("passes when no trust-boundary files changed", async () => {
  const result = await runFixture({ files: ["README.md"] });

  assert.deepEqual(result.failures, []);
  assert.equal(result.summary.state.writes, 1);
  assert.match(result.summary.state.raw[0], /No trust-boundary files changed/);
});

test("requires deliberate approval for trust-boundary changes", async () => {
  const result = await runFixture({ files: [".github/workflows/public-ci.yml"] });

  assert.match(result.failures[0], /must review the current PR head/);
  assert.deepEqual(result.summary.state.lists[0], [".github/workflows/public-ci.yml"]);
});

test("accepts a maintainer approval label", async () => {
  const result = await runFixture({
    action: "labeled",
    eventLabel: APPROVAL_LABEL,
    files: [".gitlab-ci.yml"],
    labels: [APPROVAL_LABEL],
    permission: "write",
  });

  assert.deepEqual(result.failures, []);
  assert.deepEqual(result.removedLabels, []);
  assert.match(result.summary.state.raw[0], /confirms deliberate review/);
});

test("clears approval whenever the PR head changes", async () => {
  const result = await runFixture({
    action: "synchronize",
    files: [".gitlab/ci/test.yml"],
    labels: [APPROVAL_LABEL],
  });

  assert.equal(result.removedLabels.length, 1);
  assert.match(result.failures[0], /approval was cleared/);
});

test("removes approval applied by an actor without write access", async () => {
  const result = await runFixture({
    action: "labeled",
    eventLabel: APPROVAL_LABEL,
    files: [".github/copy-pr-bot.yaml"],
    labels: [APPROVAL_LABEL],
    permission: "triage",
  });

  assert.equal(result.removedLabels.length, 1);
  assert.match(result.failures[0], /needs write access/);
});

test("removes approval when the actor is not a repository collaborator", async () => {
  const result = await runFixture({
    action: "labeled",
    eventLabel: APPROVAL_LABEL,
    files: [".github/CODEOWNERS"],
    labels: [APPROVAL_LABEL],
    missingCollaborator: true,
  });

  assert.equal(result.removedLabels.length, 1);
  assert.match(result.failures[0], /needs write access/);
});

test("detects a trust-boundary file renamed out of a protected path", async () => {
  const result = await runFixture({
    files: [{ filename: "archive/public-ci.yml", previous_filename: ".github/workflows/public-ci.yml" }],
  });

  assert.match(result.failures[0], /must review the current PR head/);
  assert.deepEqual(result.summary.state.lists[0], ["archive/public-ci.yml"]);
});

test("creates the repository approval label when it is missing", async () => {
  const result = await runFixture({ missingApprovalLabel: true });

  assert.equal(result.createdLabels.length, 1);
  assert.equal(result.createdLabels[0].name, APPROVAL_LABEL);
});
