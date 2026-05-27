# NVIDIA Config Manager Rename Plan

This plan tracks the repository-wide rename to NVIDIA Config Manager and the move to a clean-history OSS repository.

## Scope

- Keep the new working tree in `../nv-config-manager` until it is ready for publication.
- Remove legacy brand references from internal code names, docs, examples, paths, and generated artifacts.
- Do not change current Nautobot plugin GraphQL or REST wire names until the vendored plugin update lands.
- Preserve existing NATS stream and subject names as configurable Helm values so current deployments are not forced to rename streams.
- Confirm OpenAPI paths and methods remain stable after the rename.

## Completed

- Created the clean working tree at `../nv-config-manager`.
- Moved documentation to `developer-docs/`.
- Added configurable NATS stream and subject values that flow into service config.
- Replaced docs-facing legacy hostnames and sample URLs with `config-manager.*` examples.
- Rewrote air-gapped bundle docs around a full bundle plus generic OCI registry image/chart upload.
- Confirmed generated OpenAPI specs are current and contain no legacy brand strings.
- Compared new OpenAPI path/method surface with the original generated specs; all five services match.

## Remaining Checks

- Keep auditing for accidental legacy strings outside approved Nautobot plugin wire names, preserved NATS stream values, and intentionally unchanged vault/config paths.
- Re-run OpenAPI generation after API-adjacent edits.
- Re-run focused installer and service tests before publishing the clean-history repository.

