# NVIDIA Config Manager docs

This directory contains the Fern documentation site for NVIDIA Config Manager.

## Local preview

Run these commands from the repository root:

```sh
make docs-live
```

For one-off checks:

```sh
make openapi-check
make docs-lint
make docs-lint-fern
make docs-preview
```

## Editing

- Content pages live under `docs/**/*.mdx`.
- Navigation is defined in `docs/fern/docs.yml`.
- OpenAPI specs are generated into `docs/api-specs/` with `make openapi`.
- Installer TUI screenshots are generated into `docs/assets/images/installer/` with `make docs-screenshots`.

Fern publishing in GitHub Actions uses a repository secret named `FERN_TOKEN`.
