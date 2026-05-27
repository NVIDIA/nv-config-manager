# NVIDIA Config Manager MCP Plan

This document tracks possible MCP integration work for NVIDIA Config Manager developer and operator workflows.

## Goals

- Expose safe read-only views of deployment state, generated values, OpenAPI specs, and service health.
- Provide guarded workflows for common local development actions such as OpenAPI checks, Helm template validation, and focused test runs.
- Keep secrets out of MCP responses by default.

## Candidate Resources

| Resource | Purpose |
| -------- | ------- |
| OpenAPI specs | Let tools inspect API schemas without starting services |
| Helm values schema | Explain chart values and generated installer output |
| Installer config schema | Validate and explain `nv-config-manager-install.yaml` |
| Pod and Helm status | Summarize deployment health for local clusters |
| Test reports | Surface failing tests and logs in a structured way |

## Candidate Tools

| Tool | Guardrails |
| ---- | ---------- |
| Generate OpenAPI | Runs the existing generator and reports diffs |
| Helm template | Always uses `deploy/helm/values-ci.yaml`; optional observability overlay |
| Validate installer config | Runs installer validation without printing secret values |
| Summarize deployment | Reads Kubernetes status from the selected namespace |

## Open Questions

- Whether MCP should live in this repository or a separate operations package.
- Which actions should be read-only by default and which should require explicit approval.
- How to redact generated values while keeping troubleshooting output useful.

