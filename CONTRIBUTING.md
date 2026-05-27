# Contributing to NVIDIA Config Manager

Thank you for your interest in contributing to NVIDIA Config Manager! This document provides guidelines and instructions for contributing.

## Table of Contents

- [Developer Certificate of Origin (DCO)](#developer-certificate-of-origin-dco)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [License](#license)

## Developer Certificate of Origin (DCO)

NVIDIA Config Manager requires the Developer Certificate of Origin (DCO) process for all contributions.

The DCO is a lightweight way for contributors to certify that they wrote or otherwise have the right to submit the code they are contributing to the project. Here is the full text of the [DCO](https://developercertificate.org/):

```
Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.

Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
```

### Signing Off Your Commits

To sign off your commits, add a `Signed-off-by` line to your commit messages:

```
This is my commit message

Signed-off-by: Your Name <your.email@example.com>
```

You can do this automatically by using the `-s` or `--signoff` flag when committing:

```bash
git commit -s -m "Your commit message"
```

If you've already made commits without signing off, you can amend your last commit:

```bash
git commit --amend -s
```

Or rebase to sign off multiple commits:

```bash
git rebase --signoff HEAD~<number_of_commits>
```

**Note:** Your sign-off must use your real name (no pseudonyms or anonymous contributions) and must match the author information in your Git configuration.

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
   This installs a pre-commit hook that auto-formats staged Python files with `ruff format` and verifies SPDX license headers are present in all source files.

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
4. Sign off all commits (see DCO section above)
5. Submit a pull request

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
- Be signed off using the DCO process described above
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
