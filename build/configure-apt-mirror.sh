#!/bin/sh
# Usage: configure-apt-mirror.sh <mirror_url> <gpg_key_url> <distro>
# Reconfigures apt to use a custom mirror. No-op if mirror_url is empty.
# distro: ubuntu → main restricted universe multiverse
#         debian → main contrib non-free non-free-firmware
set -eu

MIRROR="${1:-}"
GPG_KEY_URL="${2:-}"
DISTRO="${3:-ubuntu}"

if [ -z "$MIRROR" ]; then exit 0; fi

# Bootstrap curl/gpg from default sources if not already present
if [ -n "$GPG_KEY_URL" ] && { ! command -v curl >/dev/null 2>&1 || ! command -v gpg >/dev/null 2>&1; }; then
    apt-get update -qq
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates gnupg curl
    rm -rf /var/lib/apt/lists/*
fi

codename="$(. /etc/os-release && echo "$VERSION_CODENAME")"
KEYOPTS=""

if [ -n "$GPG_KEY_URL" ]; then
    mkdir -p /etc/apt/trusted.gpg.d
    curl -fsSL "$GPG_KEY_URL" \
        | gpg --dearmor -o /etc/apt/trusted.gpg.d/custom-mirror.gpg
    KEYOPTS="[signed-by=/etc/apt/trusted.gpg.d/custom-mirror.gpg]"
fi

rm -f /etc/apt/sources.list \
      /etc/apt/sources.list.d/*.list \
      /etc/apt/sources.list.d/*.sources 2>/dev/null || true

if [ "$DISTRO" = "debian" ]; then
    COMPONENTS="main contrib non-free non-free-firmware"
else
    COMPONENTS="main restricted universe multiverse"
fi

# Append a trailing space to KEYOPTS only when non-empty, so the deb line has
# no stray leading space when no signed-by option is in use.
KEYOPTS_PREFIX="${KEYOPTS:+$KEYOPTS }"

{
    printf 'deb %s%s %s %s\n'    "$KEYOPTS_PREFIX" "$MIRROR" "$codename"             "$COMPONENTS"
    printf 'deb %s%s %s-%s %s\n' "$KEYOPTS_PREFIX" "$MIRROR" "$codename" "updates"   "$COMPONENTS"
    printf 'deb %s%s %s-%s %s\n' "$KEYOPTS_PREFIX" "$MIRROR" "$codename" "security"  "$COMPONENTS"
    printf 'deb %s%s %s-%s %s\n' "$KEYOPTS_PREFIX" "$MIRROR" "$codename" "backports" "$COMPONENTS"
} > /etc/apt/sources.list.d/mirror.list
