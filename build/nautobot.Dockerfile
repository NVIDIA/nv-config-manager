# NVIDIA Config Manager Nautobot Dockerfile - Pared down version for external customers
#
# Uses NVIDIA distroless Python image for minimal attack surface.
#
# TROUBLESHOOTING:
# Distroless images have no shell. To debug, use ephemeral debug containers:
#   kubectl debug -it <pod-name> --image=busybox --target=nautobot

# =============================================================================
# Builder stage - use official uv image with Python
# =============================================================================
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

ARG APT_MIRROR_DEBIAN=""
ARG APT_MIRROR_GPG_KEY_URL=""

# Install build dependencies for native extensions + git (required by Nautobot's GitPython)
COPY --from=scripts configure-apt-mirror.sh /tmp/configure-apt-mirror.sh
RUN set -eux; \
    /tmp/configure-apt-mirror.sh "$APT_MIRROR_DEBIAN" "$APT_MIRROR_GPG_KEY_URL" debian && \
    apt-get update && apt-get install -y --no-install-recommends \
    g++ \
    gcc \
    git=1:2.39.5-0+deb12u3 \
    libffi-dev \
    libjpeg-dev \
    libldap2-dev \
    libpq-dev \
    libsasl2-dev \
    libssl-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /opt/nautobot
ARG NAUTOBOT_APP_OVERLAYS_VERSION=""
ARG NAUTOBOT_NV_CONFIG_MANAGER_VERSION=""

# Copy configuration and dependencies
# Note: Build context is components/nautobot/
COPY pyproject.toml uv.lock /opt/nautobot/
COPY nautobot-app-overlays /opt/nautobot/nautobot-app-overlays
COPY nautobot-nv-config-manager /opt/nautobot/nautobot-nv-config-manager
COPY nautobot_config.py /opt/nautobot/nautobot_config.py
COPY nv_config_manager_jobs /opt/nautobot/jobs/nv_config_manager_jobs
COPY nv_config_manager_auth /opt/nautobot/nv_config_manager_auth

# Create venv and install dependencies (--no-editable ensures packages are in site-packages)
RUN uv venv /opt/nautobot/.venv
RUN set -eux; \
    if [ -n "$NAUTOBOT_APP_OVERLAYS_VERSION" ]; then \
        export SETUPTOOLS_SCM_PRETEND_VERSION="$NAUTOBOT_APP_OVERLAYS_VERSION"; \
        export SETUPTOOLS_SCM_PRETEND_VERSION_FOR_NAUTOBOT_APP_OVERLAYS="$NAUTOBOT_APP_OVERLAYS_VERSION"; \
    fi; \
    if [ -n "$NAUTOBOT_NV_CONFIG_MANAGER_VERSION" ]; then \
        export SETUPTOOLS_SCM_PRETEND_VERSION="$NAUTOBOT_NV_CONFIG_MANAGER_VERSION"; \
        export SETUPTOOLS_SCM_PRETEND_VERSION_FOR_NAUTOBOT_NV_CONFIG_MANAGER="$NAUTOBOT_NV_CONFIG_MANAGER_VERSION"; \
    fi; \
    uv sync --frozen --no-dev --no-editable

RUN mkdir -p /opt/nautobot/static \
    /opt/nautobot/media \
    /opt/nautobot/media/devicetype-images \
    /opt/nautobot/media/image-attachments \
    /opt/nautobot/git \
    /opt/nautobot/.cache && \
    chmod -R a+rX /opt/nautobot/.venv /opt/nautobot/nautobot_config.py /opt/nautobot/nv_config_manager_auth

# =============================================================================
# Runtime stage - NVIDIA distroless Python
# =============================================================================
FROM nvcr.io/nvidia/distroless/python:3.11-v4.0.6

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NAUTOBOT_ROOT=/opt/nautobot
ENV NAUTOBOT_CONFIG=/opt/nautobot/nautobot_config.py

WORKDIR /opt/nautobot

# Copy virtual environment and application
COPY --from=builder /opt/nautobot/.venv /opt/nautobot/.venv
COPY --from=builder /opt/nautobot/nautobot_config.py /opt/nautobot/nautobot_config.py
COPY --from=builder /opt/nautobot/nv_config_manager_auth /opt/nautobot/nv_config_manager_auth
COPY --from=builder --chown=1000:1000 /opt/nautobot/static /opt/nautobot/static
COPY --from=builder --chown=1000:1000 /opt/nautobot/media /opt/nautobot/media
COPY --from=builder --chown=1000:1000 /opt/nautobot/git /opt/nautobot/git
COPY --from=builder --chown=1000:1000 /opt/nautobot/jobs /opt/nautobot/jobs
COPY --from=builder --chown=1000:1000 /opt/nautobot/.cache /opt/nautobot/.cache

# Copy required shared libraries for native extensions (psycopg2, ldap, xml, etc.)
COPY --from=builder /usr/lib/*-linux-gnu/libpq.so* /usr/lib/
COPY --from=builder /usr/lib/*-linux-gnu/libxml2.so* /usr/lib/
COPY --from=builder /usr/lib/*-linux-gnu/libxslt.so* /usr/lib/
COPY --from=builder /usr/lib/*-linux-gnu/libexslt.so* /usr/lib/
COPY --from=builder /usr/lib/*-linux-gnu/libldap*.so* /usr/lib/
COPY --from=builder /usr/lib/*-linux-gnu/liblber*.so* /usr/lib/
COPY --from=builder /usr/lib/*-linux-gnu/libsasl2.so* /usr/lib/
COPY --from=builder /usr/lib/*-linux-gnu/libjpeg.so* /usr/lib/

# Copy git + git-core + templates.
COPY --from=builder /usr/bin/git /usr/bin/git
COPY --from=builder /usr/lib/git-core /usr/lib/git-core
COPY --from=builder /usr/share/git-core /usr/share/git-core

# Copy git HTTPS runtime dependency chain 
COPY --from=builder /lib/*-linux-gnu/libbrotlicommon.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libbrotlidec.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libcom_err.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libcrypto.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libcurl-gnutls.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libffi.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libgmp.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libgnutls.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libgssapi_krb5.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libhogweed.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libidn2.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libk5crypto.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libkeyutils.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libkrb5.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libkrb5support.so* /usr/lib/

COPY --from=builder /lib/*-linux-gnu/libnettle.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libnghttp2.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libp11-kit.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libpcre2-8.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libpsl.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/librtmp.so* /usr/lib/

COPY --from=builder /lib/*-linux-gnu/libssh2.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libtasn1.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libunistring.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libz.so* /usr/lib/
COPY --from=builder /lib/*-linux-gnu/libzstd.so* /usr/lib/

## The following dependencies are required by git HTTPS but are already covered by an earlier COPY statement
# COPY --from=builder /lib/*-linux-gnu/libsasl2.so* /usr/lib/
# COPY --from=builder /lib/*-linux-gnu/liblber-2.5.so* /usr/lib/
# COPY --from=builder /lib/*-linux-gnu/libldap-2.5.so* /usr/lib/

# Set PATH to include the venv executables
ENV PATH="/opt/nautobot/.venv/bin:$PATH"

# Expose Nautobot port
EXPOSE 8080

# Default command - can be overridden
CMD ["nautobot-server", "runserver", "0.0.0.0:8080"]
