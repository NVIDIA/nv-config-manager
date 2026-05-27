# NVIDIA Config Manager - NATS Ready Check
#
# Uses NVIDIA distroless Go image for minimal attack surface.
# Multi-stage build: builder compiles the binary on Ubuntu, runtime uses distroless.

# =============================================================================
# Builder stage - compile the Go binary
# =============================================================================
FROM nvcr.io/nvidia/base/ubuntu:noble-20260217 AS builder

ARG APT_MIRROR=""
ARG APT_MIRROR_GPG_KEY_URL=""

# Official SHA256 checksums from https://go.dev/dl/
ARG GO_VERSION=1.26.3
ARG GO_SHA256_AMD64=2b2cfc7148493da5e73981bffbf3353af381d5f93e789c82c79aff64962eb556
ARG GO_SHA256_ARM64=9d89a3ea57d141c2b22d70083f2c8459ba3890f2d9e818e7e933b75614936565

# Install Go with checksum verification
COPY --from=scripts configure-apt-mirror.sh /tmp/configure-apt-mirror.sh
RUN set -eux; \
    /tmp/configure-apt-mirror.sh "$APT_MIRROR" "$APT_MIRROR_GPG_KEY_URL" ubuntu && \
    apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl && \
    ARCH=$(dpkg --print-architecture) && \
    TARBALL="go${GO_VERSION}.linux-${ARCH}.tar.gz" && \
    if [ "$ARCH" = "amd64" ]; then EXPECTED="$GO_SHA256_AMD64"; \
    elif [ "$ARCH" = "arm64" ]; then EXPECTED="$GO_SHA256_ARM64"; \
    else echo "Unsupported architecture: $ARCH" >&2; exit 1; fi && \
    curl -fsSL -o /tmp/${TARBALL} "https://go.dev/dl/${TARBALL}" && \
    echo "${EXPECTED}  /tmp/${TARBALL}" | sha256sum -c - && \
    tar -C /usr/local -xzf /tmp/${TARBALL} && \
    rm /tmp/${TARBALL} && \
    rm -rf /var/lib/apt/lists/*

ENV PATH="/usr/local/go/bin:$PATH"
ENV CGO_ENABLED=0

# Note: Build context is components/nats-ready/
WORKDIR /build
COPY . .

# Build static binary
RUN go build -ldflags="-s -w" -o bin/nats-ready ./cmd/nats-ready

# =============================================================================
# Runtime stage - NVIDIA distroless Go image (minimal, no shell)
# =============================================================================
FROM nvcr.io/nvidia/distroless/go:v4.0.6

COPY --from=builder /build/bin/nats-ready /nats-ready
ENTRYPOINT ["/nats-ready"]
