// SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
// SPDX-License-Identifier: Apache-2.0

const assert = require("node:assert/strict");
const { test } = require("node:test");

const reportKindIntegrationResult = require("./kind-integration-result.js");

const SHA = "a".repeat(40);
const RUN_URL = "https://github.com/NVIDIA/nv-config-manager/actions/runs/123";
const TEMPLATE_BODY = `## Description

Example PR.

## Validation

Passing Kind Integration run, if not automatically reported:
<!-- kind-integration-result:start -->
<!-- Paste the workflow run URL here only if the Kind result was not automatically updated. -->
<!-- kind-integration-result:end -->

## Checklist

- [ ] Standard CI passes.
`;

function createFixture(options = {}) {
  const updates = [];
  const context = {
    repo: { owner: "NVIDIA", repo: "nv-config-manager" },
    payload: {},
  };
  if (!options.omitWorkflowRun) {
    context.payload.workflow_run = {
      conclusion: Object.hasOwn(options, "conclusion") ? options.conclusion : "success",
      event: options.event ?? "workflow_dispatch",
      head_branch: options.headBranch ?? "pull-request/72",
      head_sha: SHA,
      html_url: RUN_URL,
      status: options.status ?? "completed",
    };
  }
  const github = {
    rest: {
      pulls: {
        get: async () => ({
          data: {
            body: Object.hasOwn(options, "pullBody") ? options.pullBody : TEMPLATE_BODY,
            head: { sha: options.pullHeadSha ?? SHA },
          },
        }),
        update: async (args) => updates.push(args),
      },
    },
  };

  return { context, github, updates };
}

async function runFixture(options) {
  const fixture = createFixture(options);
  await reportKindIntegrationResult({
    ...fixture,
    run: options?.run,
  });
  return fixture;
}

test("updates the PR body with the completed Kind run", async () => {
  const result = await runFixture();

  assert.equal(result.updates.length, 1);
  assert.deepEqual(result.updates[0], {
    owner: "NVIDIA",
    repo: "nv-config-manager",
    pull_number: 72,
    body: `## Description

Example PR.

## Validation

Passing Kind Integration run, if not automatically reported:
<!-- kind-integration-result:start -->
Kind integration completed with **success** for [\`aaaaaaaaaaaa\`](${RUN_URL}).
<!-- kind-integration-result:end -->

## Checklist

- [ ] Standard CI passes.
`,
  });
});

test("replaces an existing automatic Kind result", async () => {
  const result = await runFixture({
    conclusion: "failure",
    pullBody: `## Validation

Passing Kind Integration run, if not automatically reported:
<!-- kind-integration-result:start -->
Kind integration completed with **success** for [\`bbbbbbbbbbbb\`](https://old.example/run).
<!-- kind-integration-result:end -->
`,
  });

  assert.deepEqual(result.updates, [
    {
      owner: "NVIDIA",
      repo: "nv-config-manager",
      pull_number: 72,
      body: `## Validation

Passing Kind Integration run, if not automatically reported:
<!-- kind-integration-result:start -->
Kind integration completed with **failure** for [\`aaaaaaaaaaaa\`](${RUN_URL}).
<!-- kind-integration-result:end -->
`,
    },
  ]);
});

test("reports an unsuccessful Kind conclusion", async () => {
  const result = await runFixture({ conclusion: "failure" });

  assert.match(result.updates[0].body, /\*\*failure\*\*/);
  assert.ok(result.updates[0].body.includes(RUN_URL));
});

test("updates from explicit run details when workflow_run did not fire", async () => {
  const result = await runFixture({
    omitWorkflowRun: true,
    run: {
      conclusion: "success",
      event: "workflow_dispatch",
      head_branch: "pull-request/72",
      head_sha: SHA,
      html_url: RUN_URL,
      status: "completed",
    },
  });

  assert.equal(result.updates.length, 1);
  assert.match(result.updates[0].body, /\*\*success\*\*/);
  assert.ok(result.updates[0].body.includes(RUN_URL));
});

test("does nothing without workflow_run or explicit run details", async () => {
  const result = await runFixture({ omitWorkflowRun: true });

  assert.deepEqual(result.updates, []);
});

test("uses unknown when a completed Kind run has no conclusion", async () => {
  const result = await runFixture({ conclusion: null });

  assert.match(result.updates[0].body, /\*\*unknown\*\*/);
  assert.ok(result.updates[0].body.includes(RUN_URL));
});

test("falls back to appending when the PR body lacks the Kind result slot", async () => {
  const result = await runFixture({ pullBody: "## Description\n\nNo validation section.\n" });

  assert.equal(
    result.updates[0].body,
    `## Description

No validation section.

## Kind Integration

Kind integration completed with **success** for [\`aaaaaaaaaaaa\`](${RUN_URL}).
`,
  );
});

test("ignores Kind runs that are not for a trusted PR branch", async () => {
  const result = await runFixture({ headBranch: "main" });

  assert.deepEqual(result.updates, []);
});

test("ignores Kind runs that have not completed", async () => {
  const result = await runFixture({ status: "in_progress" });

  assert.deepEqual(result.updates, []);
});

test("ignores Kind runs that were not manually dispatched", async () => {
  const result = await runFixture({ event: "push" });

  assert.deepEqual(result.updates, []);
});

test("ignores canceled Kind runs for stale PR commits", async () => {
  const result = await runFixture({
    conclusion: "cancelled",
    pullHeadSha: "b".repeat(40),
  });

  assert.deepEqual(result.updates, []);
});
