#!/usr/bin/env bash
#
# Setup script for ISC Stork agent on Debian/Ubuntu
# Source: https://dl.cloudsmith.io/public/isc/stork/
#

set -e

echo "Setting up ISC Stork repository for Debian/Ubuntu..."

# Install required packages for adding repositories
apt-get update
apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg \
    apt-transport-https

# Detect OS version
. /etc/os-release

# Map Ubuntu Noble (24.04) to Jammy (22.04) since Stork may not have Noble packages yet
STORK_CODENAME="${VERSION_CODENAME}"
if [[ "${VERSION_CODENAME}" = "noble" ]]; then
    echo "Ubuntu Noble detected, using Jammy repository (compatible packages)..."
    STORK_CODENAME="jammy"
fi

# Use the official Cloudsmith setup script for Stork
# This handles key management correctly
curl -1sLf "https://dl.cloudsmith.io/public/isc/stork/setup.deb.sh" | \
    distro="${ID}" codename="${STORK_CODENAME}" bash

echo "Stork repository setup complete!"
