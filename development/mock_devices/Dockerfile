# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Mock Network Device
# Follows the same multi-stage pattern as build/nv-config-manager.Dockerfile.

# =============================================================================
# Builder stage
# =============================================================================
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

# libpcap-dev: required by scapy for packet capture (dhcp command)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpcap-dev openssl && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /pcap-lib && \
    cp /usr/lib/*/libpcap.so* /pcap-lib/ 2>/dev/null || true && \
    cd /pcap-lib && ln -sf libpcap.so.* libpcap.so 2>/dev/null || true

WORKDIR /app

# Self-signed TLS cert for mock HTTPS APIs (Temporal clients require TLS)
RUN openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
    -keyout /app/tls.key -out /app/tls.crt \
    -subj '/CN=mock-device' 2>/dev/null && \
    chmod 644 /app/tls.key /app/tls.crt

COPY pyproject.toml .
COPY mock_device/ /app/mock_device/
COPY fixtures/ /app/fixtures/
RUN uv venv /app/.venv && \
    uv pip install --python /app/.venv/bin/python .

# =============================================================================
# Runtime stage - NVIDIA distroless Python
# =============================================================================
FROM nvcr.io/nvidia/distroless/python:3.13-v4.0.3

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/mock_device /app/mock_device
COPY --from=builder /app/fixtures /app/fixtures
COPY --from=builder /app/tls.crt /app/tls.crt
COPY --from=builder /app/tls.key /app/tls.key

# libpcap for scapy packet capture
COPY --from=builder /pcap-lib/ /usr/lib/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

ENTRYPOINT ["python", "-m", "mock_device.cli"]
CMD ["serve"]
