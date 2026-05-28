# Changelog

Notable user-facing changes for NVIDIA Config Manager should be recorded here.

This project uses release tags for published versions. Add entries under
`Unreleased` while changes are in flight, then move them under the release
version when a release tag is promoted.

## Unreleased

- No unreleased changes have been recorded yet.

## 1.2.3

### Security

- Fixed a regression in default authentication behavior introduced when consolidating
  service authentication into the shared mono-repo auth library. When SSO is enabled,
  service endpoints now require authentication by default, with health checks and
  metrics as explicit unauthenticated exceptions.
- Added Envoy header removal for spoofable identity headers, including
  `ssl-client-cert` and `X-Auth-*` headers, so legacy mTLS auth paths cannot be
  reached by forging client-supplied headers.

## 1.2.2

- Official OSS release.
