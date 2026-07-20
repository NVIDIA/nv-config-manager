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

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIGURE_SCRIPT="$(cd "$SCRIPT_DIR/.." && pwd)/configure-gpg-signing.sh"
PRE_COMMIT_HOOK="$(cd "$SCRIPT_DIR/.." && pwd)/hooks/pre-commit"
FINGERPRINT="0123456789ABCDEF0123456789ABCDEF01234567"

fail() {
    echo "FAIL: $*" >&2
    exit 1
}

assert_equal() {
    local expected="$1"
    local actual="$2"
    local description="$3"

    if [[ "$expected" != "$actual" ]]; then
        fail "$description: expected '$expected', got '$actual'"
    fi
}

run_suite() {
    local bash_path="$1"
    local test_root
    local repo
    local output
    local missing_repo
    local missing_output

    test_root="$(mktemp -d "${TMPDIR:-/tmp}/nvcm-gpg-signing.XXXXXX")"
    repo="$test_root/repo"
    trap 'rm -rf "$test_root"' EXIT INT TERM

    mkdir -p "$test_root/bin" "$test_root/home" "$repo"
    cat >"$test_root/bin/gpg" <<EOF
#!/bin/sh
case "\$*" in
    *--list-secret-keys*)
        if [ "\${GPG_STUB_HAS_KEY:-1}" = "0" ]; then
            exit 2
        fi
        cat <<'KEY_OUTPUT'
sec:u:4096:1:89ABCDEF01234567:1700000000::::::scESC:::+:::23::0:
fpr:::::::::$FINGERPRINT:
uid:u::::1700000000::HASH::Test User <test@example.com>::::::::::0:
KEY_OUTPUT
        ;;
    *--detach-sign*)
        cat >/dev/null
        if [ "\${GPG_STUB_CAN_SIGN:-1}" = "0" ]; then
            exit 2
        fi
        ;;
    *)
        exit 2
        ;;
esac
EOF
    chmod +x "$test_root/bin/gpg"

    git init -q "$repo"
    git -C "$repo" config user.name "Test User"
    git -C "$repo" config user.email "test@example.com"

    output="$(
        cd "$repo"
        PATH="$test_root/bin:$PATH" HOME="$test_root/home" \
            "$bash_path" "$CONFIGURE_SCRIPT" 89ABCDEF01234567
    )"

    assert_equal "openpgp" "$(git -C "$repo" config --local --get gpg.format)" "GPG format"
    assert_equal "$test_root/bin/gpg" "$(git -C "$repo" config --local --get gpg.program)" "GPG program"
    assert_equal "$FINGERPRINT" "$(git -C "$repo" config --local --get user.signingkey)" "signing fingerprint"
    assert_equal "true" "$(git -C "$repo" config --local --bool --get commit.gpgsign)" "automatic signing"

    if ! printf '%s\n' "$output" | grep -F "Configured repository-local commit signing" >/dev/null; then
        fail "success output did not explain the configured scope"
    fi

    if ! (
        cd "$repo"
        PATH="$test_root/bin:$PATH" HOME="$test_root/home" \
            "$bash_path" "$PRE_COMMIT_HOOK" >/dev/null
    ); then
        fail "pre-commit hook rejected a configured secret key"
    fi

    missing_repo="$test_root/missing-repo"
    mkdir -p "$missing_repo"
    git init -q "$missing_repo"
    missing_output="$test_root/missing-output"
    if (
        cd "$missing_repo"
        PATH="$test_root/bin:$PATH" HOME="$test_root/home" \
            "$bash_path" "$PRE_COMMIT_HOOK" >"$missing_output" 2>&1
    ); then
        fail "pre-commit hook accepted missing signing configuration"
    fi
    if ! grep -F "./scripts/configure-gpg-signing.sh" "$missing_output" >/dev/null; then
        fail "pre-commit failure did not provide the setup command"
    fi

    if (
        cd "$repo"
        PATH="$test_root/bin:$PATH" HOME="$test_root/home" GPG_STUB_HAS_KEY=0 \
            "$bash_path" "$CONFIGURE_SCRIPT" missing-key >/dev/null 2>&1
    ); then
        fail "missing secret key unexpectedly succeeded"
    fi

    echo "PASS: $($bash_path --version | head -n 1)"
    rm -rf "$test_root"
    trap - EXIT INT TERM
}

if [[ "${1:-}" == "--run-suite" ]]; then
    run_suite "$2"
    exit 0
fi

tested_paths=" "
tested_count=0
for bash_path in /bin/bash /opt/homebrew/bin/bash /usr/local/bin/bash; do
    if [[ ! -x "$bash_path" ]]; then
        continue
    fi
    case "$tested_paths" in
        *" $bash_path "*) continue ;;
    esac
    tested_paths="$tested_paths$bash_path "
    "$bash_path" "$0" --run-suite "$bash_path"
    tested_count=$((tested_count + 1))
done

if [[ "$tested_count" -eq 0 ]]; then
    fail "no supported Bash executable was found"
fi
