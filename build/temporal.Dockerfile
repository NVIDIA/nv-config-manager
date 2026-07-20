# syntax=docker/dockerfile:1.7
#
# Project-owned Temporal images.  The upstream images contain a shell and
# debugging utilities; runtime stages below retain only the static binaries and
# data needed by each workload, then run as a non-root distroless user.

# Keep this source line aligned with the currently approved production server
# version.  Changing it requires the Temporal database-upgrade procedure.
ARG TEMPORAL_SERVER_VERSION=1.29.7
# The bootstrap-only admin-tools image supplies Temporal's schema files and
# command-line tools. Temporal does not publish an admin-tools:1.29.7 tag.
ARG TEMPORAL_ADMIN_TOOLS_VERSION=1.29.6
# The UI is independently deployable and does not change Temporal persistence.
ARG TEMPORAL_UI_VERSION=2.52.1

FROM temporalio/server:${TEMPORAL_SERVER_VERSION} AS server-upstream
FROM temporalio/admin-tools:${TEMPORAL_ADMIN_TOOLS_VERSION} AS admin-tools-upstream
FROM temporalio/ui:${TEMPORAL_UI_VERSION} AS ui-upstream

FROM golang:1.26.5-alpine AS bootstrap-builder
WORKDIR /src
COPY components/temporal/go.mod ./
COPY components/temporal/cmd/ ./cmd/
RUN CGO_ENABLED=0 go build -trimpath -ldflags='-s -w' -o /out/temporal-bootstrap ./cmd/temporal-bootstrap

# =============================================================================
# Temporal Server
# =============================================================================
FROM nvcr.io/nvidia/distroless/go:v4.0.8 AS server
COPY --from=server-upstream /usr/local/bin/temporal-server /usr/local/bin/temporal-server
COPY --from=server-upstream /usr/local/bin/dockerize /usr/local/bin/dockerize
USER nvs
ENTRYPOINT ["/usr/local/bin/temporal-server"]

# =============================================================================
# Temporal Bootstrap
# =============================================================================
# This image carries Temporal's v1.29 schema files plus NVIDIA Config Manager's
# bootstrap binary. It runs only as a chart-managed init container.
FROM nvcr.io/nvidia/distroless/go:v4.0.8 AS bootstrap
COPY --from=admin-tools-upstream /usr/local/bin/temporal /usr/local/bin/temporal
COPY --from=admin-tools-upstream /usr/local/bin/temporal-sql-tool /usr/local/bin/temporal-sql-tool
COPY --from=admin-tools-upstream /etc/temporal/schema /etc/temporal/schema
COPY --from=bootstrap-builder /out/temporal-bootstrap /usr/local/bin/temporal-bootstrap
USER nvs
ENTRYPOINT ["/usr/local/bin/temporal-bootstrap"]

# =============================================================================
# Temporal Web UI
# =============================================================================
FROM nvcr.io/nvidia/distroless/go:v4.0.8 AS ui
WORKDIR /home/ui-server
COPY --from=ui-upstream /home/ui-server /home/ui-server
USER nvs
ENTRYPOINT ["/home/ui-server/ui-server", "--env", "docker", "start"]
