#!/usr/bin/env python3
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
"""Add SPDX license headers to source files in the NVIDIA Config Manager repository."""

import sys
from pathlib import Path

PYTHON_HEADER = """\
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
"""

JS_TS_HEADER = """\
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
"""

GO_HEADER = """\
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
"""

PYTHON_DIRS = [
    "src/nv_config_manager",
    "src/tests",
    "db/migrations",
    "scripts",
    "components/nautobot",
    "components/network-templates",
    "development/mock_topology",
    "installer/src",
    "installer/tests",
    "installer/scripts",
]

JS_TS_DIRS = [
    "ui/src",
    "ui/tests",
]

GO_DIRS = [
    "components/nats-ready",
]

SKIP_PATTERNS = {
    "__pycache__",
    ".pyc",
    "node_modules",
    ".git",
    ".venv",
    "uv.lock",
}

SHORT_SPDX_PYTHON = (
    "# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES."
    " All rights reserved.\n"
    "# SPDX-License-Identifier: Apache-2.0\n"
)

SHORT_SPDX_PYTHON_ALT = (
    "# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.\n"
    "# SPDX-License-Identifier: Apache-2.0\n"
)

SHORT_SPDX_JS = (
    "// SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES."
    " All rights reserved.\n"
    "// SPDX-License-Identifier: Apache-2.0\n"
)


def should_skip(path: Path) -> bool:
    path_str = str(path)
    return any(skip in path_str for skip in SKIP_PATTERNS)


def has_full_header(content: str) -> bool:
    return "SPDX-License-Identifier" in content and "Licensed under the Apache License" in content


def has_short_header(content: str) -> bool:
    return (
        "SPDX-License-Identifier" in content and "Licensed under the Apache License" not in content
    )


def replace_short_header_python(content: str) -> str:
    """Replace a short 2-line SPDX header with the full license block."""
    if SHORT_SPDX_PYTHON in content:
        return content.replace(SHORT_SPDX_PYTHON, PYTHON_HEADER, 1)
    if SHORT_SPDX_PYTHON_ALT in content:
        return content.replace(SHORT_SPDX_PYTHON_ALT, PYTHON_HEADER, 1)
    return content


def replace_short_header_js(content: str) -> str:
    return content.replace(SHORT_SPDX_JS, JS_TS_HEADER, 1)


def add_header_to_python(file_path: Path) -> bool:
    try:
        content = file_path.read_text(encoding="utf-8")

        if has_full_header(content):
            return False

        if has_short_header(content):
            file_path.write_text(replace_short_header_python(content), encoding="utf-8")
            return True

        if content.startswith("#!"):
            lines = content.split("\n", 1)
            new_content = lines[0] + "\n" + PYTHON_HEADER + (lines[1] if len(lines) > 1 else "")
        else:
            new_content = PYTHON_HEADER + content

        file_path.write_text(new_content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def add_header_to_js_ts(file_path: Path) -> bool:
    try:
        content = file_path.read_text(encoding="utf-8")

        if has_full_header(content):
            return False

        if has_short_header(content):
            file_path.write_text(replace_short_header_js(content), encoding="utf-8")
            return True

        stripped = content.strip()
        if stripped.startswith(('"use client"', "'use client'", '"use server"', "'use server'")):
            lines = content.split("\n", 1)
            new_content = lines[0] + "\n" + JS_TS_HEADER + (lines[1] if len(lines) > 1 else "")
        else:
            new_content = JS_TS_HEADER + content

        file_path.write_text(new_content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def add_header_to_go(file_path: Path) -> bool:
    try:
        content = file_path.read_text(encoding="utf-8")

        if has_full_header(content):
            return False

        if has_short_header(content):
            file_path.write_text(replace_short_header_js(content), encoding="utf-8")
            return True

        if content.startswith("//go:build") or content.startswith("// +build"):
            lines = content.split("\n")
            build_tag_end = 0
            for i, line in enumerate(lines):
                if line.startswith("//go:build") or line.startswith("// +build") or line == "":
                    build_tag_end = i + 1
                else:
                    break
            new_content = (
                "\n".join(lines[:build_tag_end])
                + "\n"
                + GO_HEADER
                + "\n".join(lines[build_tag_end:])
            )
        else:
            new_content = GO_HEADER + content

        file_path.write_text(new_content, encoding="utf-8")
        return True
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False


def process_directory(
    base_path: Path, dir_path: str, extension: str, add_header_func: object
) -> tuple[int, int]:
    full_path = base_path / dir_path
    if not full_path.exists():
        print(f"  Directory not found: {full_path}")
        return 0, 0

    modified = 0
    skipped = 0

    for file_path in sorted(full_path.rglob(f"*{extension}")):
        if should_skip(file_path):
            continue
        if add_header_func(file_path):
            print(f"  Added header: {file_path.relative_to(base_path)}")
            modified += 1
        else:
            skipped += 1

    return modified, skipped


def main() -> None:
    script_path = Path(__file__).resolve()
    repo_root = script_path.parent.parent

    if not (repo_root / "pyproject.toml").exists():
        print("Error: Could not find repository root")
        sys.exit(1)

    print(f"Repository root: {repo_root}")
    print()

    total_modified = 0
    total_skipped = 0

    print("Processing Python files...")
    for dir_path in PYTHON_DIRS:
        modified, skipped = process_directory(repo_root, dir_path, ".py", add_header_to_python)
        total_modified += modified
        total_skipped += skipped

    print("\nProcessing TypeScript/JavaScript files...")
    for dir_path in JS_TS_DIRS:
        for ext in (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"):
            modified, skipped = process_directory(repo_root, dir_path, ext, add_header_to_js_ts)
            total_modified += modified
            total_skipped += skipped

    print("\nProcessing Go files...")
    for dir_path in GO_DIRS:
        modified, skipped = process_directory(repo_root, dir_path, ".go", add_header_to_go)
        total_modified += modified
        total_skipped += skipped

    print()
    print(f"Total files modified: {total_modified}")
    print(f"Total files skipped (already had header): {total_skipped}")


if __name__ == "__main__":
    main()
