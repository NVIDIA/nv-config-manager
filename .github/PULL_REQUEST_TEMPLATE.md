## Description

<!-- Provide a standalone description of the change. Reference issues with "closes #1234" when applicable. -->

## Validation

<!-- List the commands, manual checks, or screenshots used to validate the change. -->

- [ ] Standard CI passes.
- [ ] Kind integration passes, or this PR explains why it was not run.

The kind integration test is manual due to taking ~30 min to complete. When the PR is ready for
review, approve the current commit and start the suite with these PR comments. If this PR changes
CI trust-boundary files, first review the `Trust Boundary Review` check and apply the
`trust-boundary-reviewed` label only after reviewing the current head. The label is cleared when
the PR head changes.

```text
/ok to test <sha>
/kind test
```

As a fallback, run Actions -> Kind Integration -> Run workflow against the copy-pr-bot generated
`pull-request/<PR_NUMBER>` branch. Use the default `test_path` for the full suite, or narrow it
only while debugging.

The completed workflow updates this PR description with its conclusion and exact run URL.

Passing Kind Integration run, if not automatically reported:
<!-- kind-integration-result:start -->
<!-- Paste the workflow run URL here only if the Kind result was not automatically updated. -->
<!-- kind-integration-result:end -->

## Checklist

- [ ] I am familiar with the contributing guidelines in `CONTRIBUTING.md`.
- [ ] Commits are signed off for DCO compliance.
- [ ] New or existing tests cover these changes, or the PR explains why tests are not needed.
- [ ] Documentation is updated for user-facing behavior changes.
- [ ] Generated artifacts are updated when applicable, such as OpenAPI specs,
      docs screenshots, or Helm/rendered outputs.
