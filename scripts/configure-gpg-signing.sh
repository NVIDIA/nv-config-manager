#!/bin/bash
# SPDX-FileCopyrightText: Copyright (c) 2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# Configure repository-local OpenPGP commit signing for nv-config-manager.

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: ./scripts/configure-gpg-signing.sh <GPG_KEY_ID_OR_FINGERPRINT>

Configure this repository to sign every commit with an existing OpenPGP
secret key. This does not create, export, or upload key material.

Find available secret keys with:

  gpg --list-secret-keys --keyid-format=long
EOF
}

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
    usage
    exit 0
fi

if [[ "$#" -ne 1 ]]; then
    usage >&2
    exit 2
fi

for required_command in git awk grep; do
    if ! command -v "$required_command" >/dev/null 2>&1; then
        fail "Required command '$required_command' was not found in PATH."
    fi
done

if [[ -n "${GPG_PROGRAM:-}" ]]; then
    if ! command -v "$GPG_PROGRAM" >/dev/null 2>&1; then
        fail "Configured GPG_PROGRAM '$GPG_PROGRAM' was not found in PATH."
    fi
elif command -v gpg >/dev/null 2>&1; then
    GPG_PROGRAM="gpg"
elif command -v gpg2 >/dev/null 2>&1; then
    GPG_PROGRAM="gpg2"
else
    fail "Neither 'gpg' nor 'gpg2' was found in PATH."
fi

GPG_PROGRAM_PATH="$(command -v "$GPG_PROGRAM")"

if ! REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)"; then
    fail "Run this command from inside a Git repository."
fi

KEY_SELECTOR="$1"

# --with-colons is the stable, machine-readable GnuPG interface. The first
# fingerprint following the primary secret-key record is used so abbreviated
# key IDs cannot remain ambiguous in Git configuration.
SECRET_KEY_OUTPUT="$(
    "$GPG_PROGRAM_PATH" --batch --with-colons --fingerprint --list-secret-keys "$KEY_SELECTOR" 2>/dev/null || true
)"

if ! printf '%s\n' "$SECRET_KEY_OUTPUT" | grep '^sec:' >/dev/null; then
    fail "No OpenPGP secret key matched '$KEY_SELECTOR'."
fi

FINGERPRINT="$(
    printf '%s\n' "$SECRET_KEY_OUTPUT" |
        awk -F: '$1 == "sec" { found_secret = 1; next } found_secret && $1 == "fpr" { print $10; exit }'
)"

if [[ -z "$FINGERPRINT" ]]; then
    fail "GnuPG did not return a primary fingerprint for '$KEY_SELECTOR'."
fi

if [[ -t 0 && -z "${GPG_TTY:-}" ]]; then
    GPG_TTY="$(tty)"
    export GPG_TTY
fi

echo "Testing OpenPGP signing with $FINGERPRINT..."
if ! printf '%s\n' "nv-config-manager commit-signing check" |
    "$GPG_PROGRAM_PATH" --local-user "$FINGERPRINT" --armor --detach-sign --output - >/dev/null; then
    fail "GnuPG could not sign with $FINGERPRINT. Check the key, agent, and pinentry configuration."
fi

git -C "$REPO_ROOT" config --local gpg.format openpgp
git -C "$REPO_ROOT" config --local gpg.program "$GPG_PROGRAM_PATH"
git -C "$REPO_ROOT" config --local user.signingkey "$FINGERPRINT"
git -C "$REPO_ROOT" config --local commit.gpgsign true

GIT_USER_EMAIL="$(git -C "$REPO_ROOT" config --get user.email || true)"
if [[ -z "$GIT_USER_EMAIL" ]]; then
    echo "WARNING: Git user.email is not configured; GitHub cannot associate signatures without it." >&2
elif ! printf '%s\n' "$SECRET_KEY_OUTPUT" | grep -F "$GIT_USER_EMAIL" >/dev/null; then
    echo "WARNING: Git user.email '$GIT_USER_EMAIL' was not found in this key's identities." >&2
    echo "GitHub requires the commit email to match a verified email associated with the GPG key." >&2
fi

cat <<EOF

Configured repository-local commit signing:
  Repository:  $REPO_ROOT
  Format:      openpgp
  Program:     $GPG_PROGRAM_PATH
  Fingerprint: $FINGERPRINT
  Auto-sign:   true

Add the public key to GitHub if it is not already registered:

  gpg --armor --export $FINGERPRINT

Then open https://github.com/settings/keys and add it as a GPG key.

Commit signing and DCO sign-off are separate. Continue using git commit -s;
commit.gpgsign=true adds the cryptographic signature automatically.
EOF
