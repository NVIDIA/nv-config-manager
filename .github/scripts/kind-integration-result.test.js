// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

const assert = require("node:assert/strict");
const { test } = require("node:test");

const reportKindIntegrationResult = require("./kind-integration-result.js");

const SHA = "a".repeat(40);
const RUN_URL = "https://github.com/NVIDIA/nv-config-manager/actions/runs/123";

function createFixture(options = {}) {
  const comments = [];
  const context = {
    repo: { owner: "NVIDIA", repo: "nv-config-manager" },
    payload: {
      workflow_run: {
        conclusion: Object.hasOwn(options, "conclusion") ? options.conclusion : "success",
        event: options.event ?? "workflow_dispatch",
        head_branch: options.headBranch ?? "pull-request/72",
        head_sha: SHA,
        html_url: RUN_URL,
        status: options.status ?? "completed",
      },
    },
  };
  const github = {
    rest: {
      issues: {
        createComment: async (args) => comments.push(args),
      },
      pulls: {
        get: async () => ({ data: { head: { sha: options.pullHeadSha ?? SHA } } }),
      },
    },
  };

  return { comments, context, github };
}

async function runFixture(options) {
  const fixture = createFixture(options);
  await reportKindIntegrationResult(fixture);
  return fixture;
}

test("comments on the PR with the completed Kind run", async () => {
  const result = await runFixture();

  assert.deepEqual(result.comments, [
    {
      owner: "NVIDIA",
      repo: "nv-config-manager",
      issue_number: 72,
      body:
        "Kind integration completed with **success** for `aaaaaaaaaaaa`: " + RUN_URL,
    },
  ]);
});

test("reports an unsuccessful Kind conclusion", async () => {
  const result = await runFixture({ conclusion: "failure" });

  assert.match(result.comments[0].body, /\*\*failure\*\*/);
  assert.ok(result.comments[0].body.includes(RUN_URL));
});

test("uses unknown when a completed Kind run has no conclusion", async () => {
  const result = await runFixture({ conclusion: null });

  assert.match(result.comments[0].body, /\*\*unknown\*\*/);
  assert.ok(result.comments[0].body.includes(RUN_URL));
});

test("ignores Kind runs that are not for a trusted PR branch", async () => {
  const result = await runFixture({ headBranch: "main" });

  assert.deepEqual(result.comments, []);
});

test("ignores Kind runs that have not completed", async () => {
  const result = await runFixture({ status: "in_progress" });

  assert.deepEqual(result.comments, []);
});

test("ignores Kind runs that were not manually dispatched", async () => {
  const result = await runFixture({ event: "push" });

  assert.deepEqual(result.comments, []);
});

test("ignores canceled Kind runs for stale PR commits", async () => {
  const result = await runFixture({
    conclusion: "cancelled",
    pullHeadSha: "b".repeat(40),
  });

  assert.deepEqual(result.comments, []);
});
