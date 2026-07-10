# NVIDIA Config Manager UI - Next.js Application
#
# Uses NVIDIA distroless Node.js image for minimal attack surface.
# Multi-stage build: deps/builder stages use Ubuntu, runtime uses distroless.

# =============================================================================
# Dependencies stage - install npm packages
# =============================================================================
FROM nvcr.io/nvidia/base/ubuntu:noble-20260217 AS deps

ARG APT_MIRROR=""
ARG APT_MIRROR_GPG_KEY_URL=""

ENV DEBIAN_FRONTEND=noninteractive

# Install Node.js 24.x
COPY --from=scripts configure-apt-mirror.sh /tmp/configure-apt-mirror.sh
RUN set -eux; \
    /tmp/configure-apt-mirror.sh "$APT_MIRROR" "$APT_MIRROR_GPG_KEY_URL" ubuntu && \
    apt-get update && apt-get upgrade -y && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        gnupg && \
    mkdir -p /etc/apt/keyrings && \
    curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg && \
    echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_24.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list && \
    apt-get update && \
    apt-get install -y --no-install-recommends nodejs && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies based on the preferred package manager
# Note: Build context is ui/
COPY package.json package-lock.json* ./
RUN npm ci

# =============================================================================
# Builder stage - build the Next.js application
# =============================================================================
FROM deps AS builder
WORKDIR /app
COPY next-env.d.ts next.config.mjs postcss.config.mjs tailwind.config.ts tsconfig.json ./
COPY public/ ./public/
COPY src/ ./src/

# Next.js telemetry disabled
ENV NEXT_TELEMETRY_DISABLED=1

RUN npm run build

# =============================================================================
# Runtime stage - NVIDIA distroless Node.js
# =============================================================================
FROM artifactory.pdx.nvidia.com/sw-distroless-docker-local/distroless/node:24-v4.0.10 AS runner

WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

# Copy public assets
COPY --from=builder --chown=1000:1000 /app/public ./public

# Copy the standalone build output
COPY --from=builder --chown=1000:1000 /app/.next/standalone ./
COPY --from=builder --chown=1000:1000 /app/.next/static ./.next/static

USER nvs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["server.js"]
