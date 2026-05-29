#!/bin/bash
# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
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
# Install git hooks for the nv-config-manager repository.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"
SOURCE_HOOKS_DIR="$SCRIPT_DIR/hooks"

echo "Installing git hooks..."

mkdir -p "$HOOKS_DIR"

for hook in pre-commit commit-msg; do
    if [[ -f "$SOURCE_HOOKS_DIR/$hook" ]]; then
        cp "$SOURCE_HOOKS_DIR/$hook" "$HOOKS_DIR/$hook"
        chmod +x "$HOOKS_DIR/$hook"
        echo "  ✓ Installed $hook hook"
    else
        echo "  ✗ $hook hook not found at $SOURCE_HOOKS_DIR/$hook"
        exit 1
    fi
done

echo ""
echo "Git hooks installed successfully!"
echo ""
echo "Hooks installed:"
echo "  - pre-commit: Auto-formats staged Python files with ruff, checks SPDX license headers"
echo "  - commit-msg: Requires a DCO Signed-off-by trailer"
echo ""
echo "To skip local hooks for a specific commit, use:"
echo "  git commit --no-verify"
