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

import json
import os
import shutil
import subprocess
import tarfile
from pathlib import Path
from unittest.mock import ANY, MagicMock, call, patch

import pytest

from nv_config_manager_installer.pvc_updater import (
    JOBS_PVC_NAME,
    PVCUpdater,
    ZTPImageSource,
    _make_tarball,
    _replace_pvc_content_command,
    _safe_extract,
    normalize_ztp_platform,
)


def _updater(k8s: MagicMock) -> PVCUpdater:
    k8s.get_pvc_mounted_node.return_value = None
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
    staged_package_marker = ""

    def capture_package_marker(staging: Path, _tarball: Path) -> None:
        nonlocal staged_package_marker
        staged_package_marker = (staging / "__init__.py").read_text()

    with patch(
        "nv_config_manager_installer.pvc_updater._make_tarball",
        side_effect=capture_package_marker,
    ):
        changed = _updater(k8s).update_jobs([source])

    assert changed is True
    assert "Custom Nautobot jobs package" in staged_package_marker
    loader_call = k8s.create_loader_pod.call_args.args
    assert loader_call[0].startswith("nvcm-pvc-updater-jobs-")
    assert loader_call[1:] == ("nv-config-manager", JOBS_PVC_NAME, "/jobs")
    k8s.annotate_pvc.assert_called_once()
    assert k8s.restart_deployment.call_count == 3
    assert k8s.wait_for_rollout.call_count == 3
    command = k8s.exec_command.call_args.args[2][2]
    assert 'tar xzf /tmp/content.tar.gz -C "$staging"' in command
    assert command.index("tar xzf") < command.index("move_old_content")
    assert "rollback_new_content" in command

    annotation_index = next(
        index
        for index, recorded_call in enumerate(k8s.mock_calls)
        if recorded_call
        == call.annotate_pvc(
            JOBS_PVC_NAME,
            "nv-config-manager",
            "nv-config-manager.nvidia.com/content-sha256",
            ANY,
        )
    )
    rollout_index = max(
        index
        for index, recorded_call in enumerate(k8s.mock_calls)
        if recorded_call[0] == "wait_for_rollout"
    )
    assert rollout_index < annotation_index
    assert k8s.wait_for_pod_gone.call_count == 2

    loader_pod_name = loader_call[0]
    cleanup_wait_index = max(
        index
        for index, recorded_call in enumerate(k8s.mock_calls)
        if recorded_call == call.wait_for_pod_gone(loader_pod_name, "nv-config-manager")
    )
    first_restart_index = next(
        index
        for index, recorded_call in enumerate(k8s.mock_calls)
        if recorded_call[0] == "restart_deployment"
    )
    assert cleanup_wait_index < first_restart_index
    k8s.release_lease.assert_called_once()


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


def test_loader_targets_the_node_currently_mounting_the_pvc(tmp_path: Path) -> None:
    source = tmp_path / "templates"
    source.mkdir()
    (source / "plugin.py").write_text("PLUGIN = True\n")
    k8s = MagicMock()
    k8s.pvc_exists.return_value = True
    k8s.get_pvc_annotation.return_value = "old-content"
    k8s.list_deployment_names.return_value = ["nv-config-manager-render"]
    k8s.restart_deployment.return_value = 1
    updater = _updater(k8s)
    k8s.get_pvc_mounted_node.return_value = "worker-a"

    updater.update_templates([source])

    loader_call = k8s.create_loader_pod.call_args
    assert loader_call.args[1:] == (
        "nv-config-manager",
        "render-service-template-plugins",
        "/plugins",
    )
    assert loader_call.kwargs == {"node_name": "worker-a"}


@patch("nv_config_manager_installer.pvc_updater.NautobotJobRunner")
def test_jobs_can_run_a_nautobot_job_after_the_pvc_update(
    mock_runner_class: MagicMock,
) -> None:
    k8s = MagicMock()
    runner = mock_runner_class.return_value
    runner.run.return_value = True

    completed = _updater(k8s).run_nautobot_job(
        "custom_jobs.bootstrap.SiteBootstrap",
        {"site": "site-1"},
        timeout=123,
    )

    assert completed is True
    mock_runner_class.assert_called_once_with(
        k8s,
        "nv-config-manager",
        "nv-config-manager",
        on_log=ANY,
    )
    runner.run.assert_called_once_with(
        "custom_jobs.bootstrap.SiteBootstrap",
        {"site": "site-1"},
        timeout=123,
    )


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
    manifest: dict[str, object] = {}

    def capture_manifest(staging: Path, _tarball: Path) -> None:
        manifest.update(json.loads((staging / "manifest.json").read_text()))

    with patch(
        "nv_config_manager_installer.pvc_updater._make_tarball", side_effect=capture_manifest
    ):
        changed = _updater(k8s).update_ztp(
            [ZTPImageSource(platform="Cumulus Linux", version="5.13.0", path=image)]
        )

    assert changed is True
    loader_call = k8s.create_loader_pod.call_args.args
    assert loader_call[0].startswith("nvcm-pvc-updater-ztp-")
    assert loader_call[1:] == ("nv-config-manager", "ztp-os-images", "/mnt/images")
    k8s.restart_deployment.assert_called_once_with("nv-config-manager-ztp", "nv-config-manager")
    assert manifest["images"] == [
        {
            "platform": "cumulus-linux",
            "version": "5.13.0",
            "filename": "image.bin",
            "path": "cumulus-linux/5.13.0/image.bin",
            "sha256": ANY,
            "tags": {"firmware-image": ""},
        }
    ]


def test_ztp_normalizes_cumulus_linux_platform_identifier() -> None:
    assert normalize_ztp_platform("Cumulus Linux") == "cumulus-linux"


def test_restarts_only_requested_release(tmp_path: Path) -> None:
    source = tmp_path / "templates"
    source.mkdir()
    (source / "plugin.py").write_text("PLUGIN = True\n")
    k8s = MagicMock()
    k8s.pvc_exists.return_value = True
    k8s.get_pvc_annotation.return_value = "old-content"
    expected_selector = (
        "app.kubernetes.io/component=render-service,app.kubernetes.io/instance=nv-config-manager"
    )
    k8s.list_deployment_names.side_effect = lambda _namespace, label_selector: (
        ["nv-config-manager-render"] if label_selector == expected_selector else []
    )
    k8s.restart_deployment.return_value = 9

    _updater(k8s).update_templates([source])

    k8s.list_deployment_names.assert_called_once_with(
        "nv-config-manager", label_selector=expected_selector
    )
    k8s.restart_deployment.assert_called_once_with("nv-config-manager-render", "nv-config-manager")


@pytest.mark.parametrize(
    ("platform", "version"),
    [
        ("../cumulus", "5.13.0"),
        ("cumulus", "../5.13.0"),
        ("cumulus/linux", "5.13.0"),
        ("cumulus", "5.13.0/evil"),
        ("cumulus", "."),
        ("cumulus;id", "5.13.0"),
    ],
)
def test_ztp_rejects_unsafe_destination_components(
    tmp_path: Path,
    platform: str,
    version: str,
) -> None:
    image = tmp_path / "image.bin"
    image.write_bytes(b"firmware")
    k8s = MagicMock()

    with pytest.raises(ValueError, match="Invalid ZTP"):
        _updater(k8s).update_ztp([ZTPImageSource(platform=platform, version=version, path=image)])

    k8s.create_loader_pod.assert_not_called()


def test_ztp_rejects_duplicate_normalized_destinations(tmp_path: Path) -> None:
    first = tmp_path / "one" / "image.bin"
    second = tmp_path / "two" / "image.bin"
    first.parent.mkdir()
    second.parent.mkdir()
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    k8s = MagicMock()

    with pytest.raises(ValueError, match="Duplicate ZTP image destination"):
        _updater(k8s).update_ztp(
            [
                ZTPImageSource("Cumulus Linux", "5.13.0", first),
                ZTPImageSource("cumulus-linux", "5.13.0", second),
            ]
        )

    k8s.create_loader_pod.assert_not_called()


def test_jobs_preserve_a_source_provided_package_init(tmp_path: Path) -> None:
    package_init_source = tmp_path / "__init__.py"
    package_init_source.write_text("from .example import Example\n")
    source = tmp_path / "jobs.tar"
    with tarfile.open(source, "w") as archive:
        archive.add(package_init_source, arcname="__init__.py")
    k8s = MagicMock()
    k8s.pvc_exists.return_value = True
    k8s.get_pvc_annotation.return_value = "old-content"
    k8s.list_deployment_names.return_value = ["nv-config-manager-nautobot"]
    k8s.restart_deployment.return_value = 1
    package_init = ""

    def capture_package_init(staging: Path, _tarball: Path) -> None:
        nonlocal package_init
        package_init = (staging / "__init__.py").read_text()

    with patch(
        "nv_config_manager_installer.pvc_updater._make_tarball",
        side_effect=capture_package_init,
    ):
        _updater(k8s).update_jobs([source])

    assert package_init == "from .example import Example\n"


def test_failed_consumer_restart_does_not_record_content_hash(tmp_path: Path) -> None:
    source = tmp_path / "templates"
    source.mkdir()
    (source / "plugin.py").write_text("PLUGIN = True\n")
    k8s = MagicMock()
    k8s.pvc_exists.return_value = True
    k8s.get_pvc_annotation.return_value = "old-content"
    k8s.list_deployment_names.return_value = ["nv-config-manager-render"]
    k8s.restart_deployment.return_value = 9
    k8s.wait_for_rollout.side_effect = RuntimeError("rollout failed")

    with pytest.raises(RuntimeError, match="rollout failed"):
        _updater(k8s).update_templates([source])

    k8s.annotate_pvc.assert_not_called()


def test_update_fails_before_loading_when_another_run_holds_the_pvc_lease(tmp_path: Path) -> None:
    source = tmp_path / "templates"
    source.mkdir()
    (source / "plugin.py").write_text("PLUGIN = True\n")
    k8s = MagicMock()
    k8s.pvc_exists.return_value = True
    k8s.acquire_lease.side_effect = RuntimeError("another update is already in progress")

    with pytest.raises(RuntimeError, match="already in progress"):
        _updater(k8s).update_templates([source])

    k8s.create_loader_pod.assert_not_called()
    k8s.release_lease.assert_not_called()


def test_rejects_tar_archive_with_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.tar"
    with tarfile.open(archive, "w") as contents:
        info = tarfile.TarInfo("../outside")
        info.size = 0
        contents.addfile(info)

    with pytest.raises(ValueError, match="unsafe path"):
        _safe_extract(archive, tmp_path / "staging")


def test_pvc_content_replacement_stages_then_replaces_live_content(tmp_path: Path) -> None:
    live = tmp_path / "jobs"
    live.mkdir()
    (live / "old.py").write_text("old\n")
    staged = tmp_path / "staged"
    staged.mkdir()
    (staged / "new.py").write_text("new\n")
    tarball = tmp_path / "content.tar.gz"
    _make_tarball(staged, tarball)
    command = _replace_pvc_content_command(str(live), "").replace(
        "/tmp/content.tar.gz", str(tarball)
    )

    subprocess.run(["sh", "-c", command], check=True)

    assert not (live / "old.py").exists()
    assert (live / "new.py").read_text() == "new\n"
    assert not (live / ".nvcm-pvc-updater-staging").exists()
    assert not (live / ".nvcm-pvc-updater-backup").exists()


def test_pvc_content_replacement_preserves_live_content_when_validation_fails(
    tmp_path: Path,
) -> None:
    live = tmp_path / "jobs"
    live.mkdir()
    (live / "old.py").write_text("old\n")
    staged = tmp_path / "staged"
    staged.mkdir()
    (staged / "new.py").write_text("new\n")
    tarball = tmp_path / "content.tar.gz"
    _make_tarball(staged, tarball)
    command = _replace_pvc_content_command(str(live), "false").replace(
        "/tmp/content.tar.gz", str(tarball)
    )

    with pytest.raises(subprocess.CalledProcessError):
        subprocess.run(["sh", "-c", command], check=True)

    assert (live / "old.py").read_text() == "old\n"
    assert not (live / "new.py").exists()


def test_pvc_content_replacement_rolls_back_when_a_move_fails(tmp_path: Path) -> None:
    live = tmp_path / "jobs"
    live.mkdir()
    (live / "old-a.py").write_text("old a\n")
    (live / "old-b.py").write_text("old b\n")
    staged = tmp_path / "staged"
    staged.mkdir()
    (staged / "new.py").write_text("new\n")
    tarball = tmp_path / "content.tar.gz"
    _make_tarball(staged, tarball)
    command = _replace_pvc_content_command(str(live), "").replace(
        "/tmp/content.tar.gz", str(tarball)
    )

    real_mv = shutil.which("mv")
    assert real_mv is not None
    fake_bin = tmp_path / "fake-bin"
    fake_bin.mkdir()
    fake_mv = fake_bin / "mv"
    fake_mv.write_text(
        f'#!/bin/sh\ncase "$1" in\n  *old-b.py) exit 1 ;;\nesac\nexec "{real_mv}" "$@"\n'
    )
    fake_mv.chmod(0o755)
    env = {**os.environ, "PATH": f"{fake_bin}{os.pathsep}{os.environ['PATH']}"}

    result = subprocess.run(["sh", "-c", command], env=env, check=False)

    assert result.returncode != 0
    assert (live / "old-a.py").read_text() == "old a\n"
    assert (live / "old-b.py").read_text() == "old b\n"
    assert not (live / "new.py").exists()
    assert not (live / ".nvcm-pvc-updater-staging").exists()
    assert not (live / ".nvcm-pvc-updater-backup").exists()
