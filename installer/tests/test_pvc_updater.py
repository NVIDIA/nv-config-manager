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
"""Tests for the GitOps PVC content updater."""

from __future__ import annotations

import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nv_config_manager_installer.pvc_updater import (
    JOBS_PVC_NAME,
    PVCUpdater,
    ZTPImageSource,
    _safe_extract,
)


def _updater(k8s: MagicMock) -> PVCUpdater:
    return PVCUpdater(k8s, "nv-config-manager", "nv-config-manager")


def test_jobs_updates_existing_pvc_and_restarts_consumers(tmp_path: Path) -> None:
    source = tmp_path / "jobs"
    source.mkdir()
    (source / "example.py").write_text("print('job')\n")
    k8s = MagicMock()
    k8s.pvc_exists.return_value = True
    k8s.get_pvc_annotation.return_value = "old-content"
    k8s.list_deployment_names.side_effect = [
        ["nv-config-manager-nautobot"],
        ["nv-config-manager-nautobot-celery"],
        ["nv-config-manager-nautobot-celery-beat"],
    ]
    k8s.restart_deployment.side_effect = [3, 4, 5]

    changed = _updater(k8s).update_jobs([source])

    assert changed is True
    k8s.create_loader_pod.assert_called_once_with(
        "nvcm-pvc-updater-jobs", "nv-config-manager", JOBS_PVC_NAME, "/jobs"
    )
    k8s.annotate_pvc.assert_called_once()
    assert k8s.restart_deployment.call_count == 3
    assert k8s.wait_for_rollout.call_count == 3


def test_unchanged_templates_do_not_create_loader_or_restart(tmp_path: Path) -> None:
    source = tmp_path / "templates"
    source.mkdir()
    (source / "plugin.py").write_text("PLUGIN = True\n")
    k8s = MagicMock()
    k8s.pvc_exists.return_value = True
    k8s.get_pvc_annotation.return_value = "same-content"

    with patch(
        "nv_config_manager_installer.pvc_updater._hash_staged_content",
        return_value="same-content",
    ):
        changed = _updater(k8s).update_templates([source])

    assert changed is False
    k8s.create_loader_pod.assert_not_called()
    k8s.restart_deployment.assert_not_called()


def test_missing_pvc_fails_without_attempting_to_create_it(tmp_path: Path) -> None:
    source = tmp_path / "jobs"
    source.mkdir()
    k8s = MagicMock()
    k8s.pvc_exists.return_value = False

    with pytest.raises(RuntimeError, match="does not exist"):
        _updater(k8s).update_jobs([source])

    k8s.create_loader_pod.assert_not_called()


def test_ztp_rebuilds_content_and_restarts_ztp(tmp_path: Path) -> None:
    image = tmp_path / "image.bin"
    image.write_bytes(b"firmware")
    k8s = MagicMock()
    k8s.pvc_exists.return_value = True
    k8s.get_pvc_annotation.return_value = "old-content"
    k8s.list_deployment_names.return_value = ["nv-config-manager-ztp"]
    k8s.restart_deployment.return_value = 9

    changed = _updater(k8s).update_ztp(
        [ZTPImageSource(platform="Cumulus Linux", version="5.13.0", path=image)]
    )

    assert changed is True
    k8s.create_loader_pod.assert_called_once_with(
        "nvcm-pvc-updater-ztp", "nv-config-manager", "ztp-os-images", "/mnt/images"
    )
    k8s.restart_deployment.assert_called_once_with("nv-config-manager-ztp", "nv-config-manager")


def test_restarts_only_requested_release(tmp_path: Path) -> None:
    source = tmp_path / "templates"
    source.mkdir()
    (source / "plugin.py").write_text("PLUGIN = True\n")
    k8s = MagicMock()
    k8s.pvc_exists.return_value = True
    k8s.get_pvc_annotation.return_value = "old-content"
    k8s.list_deployment_names.return_value = [
        "nv-config-manager-render",
        "another-release-render",
    ]
    k8s.restart_deployment.return_value = 9

    _updater(k8s).update_templates([source])

    k8s.restart_deployment.assert_called_once_with("nv-config-manager-render", "nv-config-manager")


def test_rejects_tar_archive_with_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.tar"
    with tarfile.open(archive, "w") as contents:
        info = tarfile.TarInfo("../outside")
        info.size = 0
        contents.addfile(info)

    with pytest.raises(ValueError, match="unsafe path"):
        _safe_extract(archive, tmp_path / "staging")
