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

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pytest

_SCRIPT_PATH = Path(__file__).parents[2] / "scripts" / "add_spdx_headers.py"
_SCRIPT_SPEC = spec_from_file_location("add_spdx_headers", _SCRIPT_PATH)
if _SCRIPT_SPEC is None or _SCRIPT_SPEC.loader is None:
    raise ImportError(f"Could not load {_SCRIPT_PATH}")
_SCRIPT_MODULE = module_from_spec(_SCRIPT_SPEC)
_SCRIPT_SPEC.loader.exec_module(_SCRIPT_MODULE)

GO_HEADER = _SCRIPT_MODULE.GO_HEADER
JS_TS_HEADER = _SCRIPT_MODULE.JS_TS_HEADER
PYTHON_HEADER = _SCRIPT_MODULE.PYTHON_HEADER
HeaderResult = _SCRIPT_MODULE.HeaderResult
add_header_to_go = _SCRIPT_MODULE.add_header_to_go
add_header_to_js_ts = _SCRIPT_MODULE.add_header_to_js_ts
add_header_to_python = _SCRIPT_MODULE.add_header_to_python


@pytest.mark.parametrize(
    ("add_header", "suffix", "expected_header"),
    [
        (add_header_to_python, ".py", PYTHON_HEADER),
        (add_header_to_js_ts, ".ts", JS_TS_HEADER),
        (add_header_to_go, ".go", GO_HEADER),
    ],
)
def test_add_header_only_writes_within_allowed_root(tmp_path, add_header, suffix, expected_header):
    allowed_root = tmp_path / "repository"
    allowed_root.mkdir()
    source_file = allowed_root / f"source{suffix}"
    source_file.write_text("source content\n", encoding="utf-8")

    result = add_header(source_file, allowed_root)

    assert result is HeaderResult.ADDED
    assert source_file.read_text(encoding="utf-8").startswith(expected_header)


@pytest.mark.parametrize(
    ("add_header", "suffix"),
    [
        (add_header_to_python, ".py"),
        (add_header_to_js_ts, ".ts"),
        (add_header_to_go, ".go"),
    ],
)
def test_add_header_rejects_symlink_outside_allowed_root(tmp_path, add_header, suffix):
    allowed_root = tmp_path / "repository"
    allowed_root.mkdir()
    external_file = tmp_path / f"external{suffix}"
    external_file.write_text("external content\n", encoding="utf-8")
    source_file = allowed_root / f"source{suffix}"
    source_file.symlink_to(external_file)

    result = add_header(source_file, allowed_root)

    assert result is HeaderResult.FAILED
    assert external_file.read_text(encoding="utf-8") == "external content\n"


def test_add_header_rejects_file_outside_allowed_root(tmp_path):
    allowed_root = tmp_path / "repository"
    allowed_root.mkdir()
    external_file = tmp_path / "external.py"
    external_file.write_text("external content\n", encoding="utf-8")

    result = add_header_to_python(external_file, allowed_root)

    assert result is HeaderResult.FAILED
    assert external_file.read_text(encoding="utf-8") == "external content\n"
