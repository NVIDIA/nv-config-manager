# Contributing to NVIDIA Config Manager

Thank you for your interest in contributing to NVIDIA Config Manager! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Cryptographically Signing Commits](#cryptographically-signing-commits)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [License](#license)

## Cryptographically Signing Commits

Copy-pr-bot only auto-syncs an otherwise trusted pull request when every commit
has GitHub's `Verified` signature status. NVIDIA trustees who expect automatic
CI branch creation must configure GPG signing.

Create or select a personal GPG key whose email matches a verified email on your
GitHub account, then add its public key under
[GitHub SSH and GPG keys](https://github.com/settings/keys). GitHub documents the
complete process for
[generating a GPG key](https://docs.github.com/en/authentication/managing-commit-signature-verification/generating-a-new-gpg-key)
and
[adding it to your account](https://docs.github.com/en/authentication/managing-commit-signature-verification/adding-a-gpg-key-to-your-github-account).

List the secret keys available locally and configure one for this repository:

```bash
gpg --list-secret-keys --keyid-format=long
./scripts/configure-gpg-signing.sh <GPG_KEY_ID_OR_FINGERPRINT>
```

The helper validates that the secret key can sign and writes only repository-local
Git configuration. It does not create, export, upload, or otherwise manage private
key material. Once configured, `commit.gpgsign=true` signs new commits
automatically. The pre-commit hook checks that automatic OpenPGP signing is
enabled and that the configured secret key exists locally. It cannot determine
whether the public key has been added to GitHub, so confirm the `Verified` status
after pushing.

Verify a new commit locally and confirm that GitHub displays `Verified` after it is
pushed:

```bash
git log --show-signature -1
```

To re-sign every commit on an existing pull-request branch, first make sure the
branch is clean, then run:

```bash
git fetch origin
base="$(git merge-base origin/main HEAD)"
git rebase --exec 'git commit --amend --no-edit -S' "$base"
git push --force-with-lease
```

This rewrites commit IDs. Coordinate with anyone else using the branch before
force-pushing it.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/nv-config-manager.git
   cd nv-config-manager
   ```
3. **Set up the development environment**:
   ```bash
   # Install uv (Python package manager)
   curl -LsSf https://astral.sh/uv/install.sh | sh

   # Install dependencies
   uv sync --dev

   # For UI development
   cd ui && npm install
   ```
4. **Install git hooks** (required for contributions):
   ```bash
   ./scripts/install-hooks.sh
   ```
   This installs:

   - `pre-commit`, which verifies local GPG signing configuration, auto-formats
     staged Python files outside ignored/generated directories with `ruff format`,
     and verifies SPDX license headers in supported source files.

   The installer also reports whether cryptographic commit signing is configured.
   NVIDIA trustees should configure an existing GPG key as described above.

5. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## How to Contribute

### Reporting Bugs

- Use the GitHub issue tracker to report bugs
- Describe the bug clearly with steps to reproduce
- Include version information and environment details
- Attach relevant logs or screenshots if applicable

### Suggesting Enhancements

- Use the GitHub issue tracker for feature requests
- Clearly describe the proposed enhancement and its use case
- Discuss potential implementation approaches if you have ideas

### Submitting Code Changes

1. Ensure your code follows the project's coding standards
2. Write or update tests as needed
3. Update documentation if applicable
4. Submit a pull request

## Pull Request Process

1. **Ensure all tests pass** before submitting:
   ```bash
   # Python tests
   uv run pytest

   # Linting
   uv run ruff check .
   uv run mypy src/

   # UI tests
   cd ui && npm run lint && npm run test:e2e:ci
   ```

2. **Update the README.md** or documentation if your changes affect usage

3. **Follow the PR template** and provide a clear description of changes

4. **Address review feedback** promptly and constructively

5. **Ensure your PR**:
   - Has a clear title and description
   - References any related issues
   - Has all commits signed off
   - Passes CI checks

## Coding Standards

### Python

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use type hints for all function signatures
- Write docstrings in Google style format
- Run `ruff check` and `mypy` before committing
- Target Python 3.13+

### TypeScript/JavaScript (UI)

- Follow the ESLint configuration in the project
- Use TypeScript for all new code
- Follow React best practices and hooks patterns
- Run `npm run lint` before committing

### Go

- Follow standard Go formatting (`go fmt`)
- Use meaningful variable and function names
- Write tests for new functionality

### General Guidelines

- Keep commits atomic and focused
- Write clear, descriptive commit messages
- Add tests for new functionality
- Update documentation as needed
- Don't introduce unnecessary dependencies

## License

By contributing to NVIDIA Config Manager, you agree that your contributions will be licensed under the Apache License 2.0. See the [LICENSE](LICENSE) file for details.

All contributions must:
- Include the appropriate SPDX license identifier in new source files
- Not include code from incompatible licenses without prior approval
### SPDX License Headers

All source files must include SPDX license headers. The pre-commit hook will check for these automatically.

**Python files** (`.py`):
```python
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
```

**TypeScript/JavaScript/Go files** (`.ts`, `.tsx`, `.js`, `.go`):
```typescript
/*
 * SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
 * SPDX-License-Identifier: Apache-2.0
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
```

To automatically add headers to all source files, run:
```bash
uv run python scripts/add_spdx_headers.py
```

---

Thank you for contributing to NVIDIA Config Manager!
