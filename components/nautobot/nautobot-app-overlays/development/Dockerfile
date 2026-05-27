# Accepts a desired Nautobot version as build argument, default to 2.4.5
ARG NAUTOBOT_VER="2.4.5"

# Accepts a desired Python version as build argument, default to 3.11
ARG PYTHON_VER="3.11"

# Retrieve published development image of Nautobot base which should include most CI dependencies
FROM ghcr.io/nautobot/nautobot-dev:${NAUTOBOT_VER}-py${PYTHON_VER}

# Runtime argument and environment setup
ARG NAUTOBOT_ROOT=/opt/nautobot
ENV NAUTOBOT_ROOT=${NAUTOBOT_ROOT}

RUN --mount=type=cache,target=/root/.cache/pip \
    pip install uv==0.6.10 --root-user-action=ignore

WORKDIR /source

# Copy the pyproject.toml and uv.lock files first for cache optimization
COPY pyproject.toml uv.lock /source/

# Copy the rest of the source code
COPY . /source/

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system --group dev -r pyproject.toml -e .

# Copy the nautobot_config.py file
COPY development/nautobot_config.py ${NAUTOBOT_ROOT}/nautobot_config.py

# Copy the entrypoint script for installing local plugins
COPY development/entrypoint.sh /opt/entrypoint.sh
RUN chmod +x /opt/entrypoint.sh
