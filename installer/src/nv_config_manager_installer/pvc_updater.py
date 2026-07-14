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
"""Update installer-owned PVC content in an already deployed NVCM release.

This module deliberately does not create or resize PVCs.  GitOps owns their
specification; this updater only supplies the mutable data that a GitOps
controller cannot put into a volume and restarts the workloads that consume it.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
import tempfile
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

from nv_config_manager_installer.k8s import K8sClient

CONTENT_HASH_ANNOTATION = "nv-config-manager.nvidia.com/content-sha256"
JOBS_PVC_NAME = "nautobot-custom-jobs"
TEMPLATES_PVC_NAME = "render-service-template-plugins"
ZTP_PVC_NAME = "ztp-os-images"

_COMMON_IGNORES = (".venv", "__pycache__", ".git", "*.pyc")
_TEMPLATE_IGNORES = (*_COMMON_IGNORES, "tests")


@dataclass(frozen=True)
class ZTPImageSource:
    """An OS image and the metadata required by the ZTP file backend."""

    platform: str
    version: str
    path: Path


def _safe_extract(tarball: Path, destination: Path) -> None:
    """Extract a regular-file-only archive without allowing path traversal."""
    with tarfile.open(tarball) as archive:
        members = archive.getmembers()
        for member in members:
            member_path = Path(member.name)
            if member_path.is_absolute() or ".." in member_path.parts:
                raise ValueError(f"Archive contains an unsafe path: {member.name}")
            if not (member.isdir() or member.isfile()):
                raise ValueError(f"Archive contains unsupported entry: {member.name}")
        archive.extractall(destination, members=members, filter="data")


def _stage_sources(
    sources: Iterable[Path],
    destination: Path,
    *,
    ignore_patterns: tuple[str, ...],
) -> None:
    """Stage directories and tar archives under a deterministic content root."""
    for source in sources:
        if not source.exists():
            raise FileNotFoundError(f"Content source does not exist: {source}")
        if source.is_dir():
            shutil.copytree(
                source,
                destination / source.name,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns(*ignore_patterns),
            )
        elif source.is_file() and tarfile.is_tarfile(source):
            _safe_extract(source, destination)
        else:
            raise ValueError(f"Content source must be a directory or tar archive: {source}")


def _hash_staged_content(staging: Path) -> str:
    """Hash staged files by relative path and bytes, ignoring filesystem metadata."""
    digest = hashlib.sha256()
    for path in sorted(staging.rglob("*")):
        if not path.is_file():
            continue
        relative_path = path.relative_to(staging).as_posix().encode()
        digest.update(len(relative_path).to_bytes(8, "big"))
        digest.update(relative_path)
        with path.open("rb") as content:
            for chunk in iter(lambda: content.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
    return digest.hexdigest()


def _make_tarball(staging: Path, output: Path) -> None:
    """Create a tarball containing the root of a staged content tree."""
    with tarfile.open(output, "w:gz") as archive:
        for path in sorted(staging.iterdir()):
            archive.add(path, arcname=path.name)


class PVCUpdater:
    """Populate the three NVCM content PVCs and restart their consumers."""

    def __init__(
        self,
        k8s: K8sClient,
        namespace: str,
        release_name: str,
        *,
        rollout_timeout: int = 600,
        on_log: Callable[[str], None] | None = None,
    ) -> None:
        self._k8s = k8s
        self.namespace = namespace
        self.release_name = release_name
        self.rollout_timeout = rollout_timeout
        self._on_log = on_log or (lambda _message: None)

    def update_jobs(self, sources: Iterable[Path], *, pvc_name: str = JOBS_PVC_NAME) -> bool:
        """Update custom-job content and restart Nautobot plus Celery workers."""
        return self._update_content(
            kind="jobs",
            sources=sources,
            pvc_name=pvc_name,
            mount_path="/jobs",
            ignore_patterns=_COMMON_IGNORES,
            post_extract="chown -R 1000:1000 /jobs",
            selectors=(
                "app.kubernetes.io/component=nautobot",
                "app.kubernetes.io/component=celery",
                "app.kubernetes.io/component=celery-beat",
            ),
        )

    def update_templates(
        self,
        sources: Iterable[Path],
        *,
        pvc_name: str = TEMPLATES_PVC_NAME,
    ) -> bool:
        """Update template plugins and restart all Render Service deployments."""
        return self._update_content(
            kind="templates",
            sources=sources,
            pvc_name=pvc_name,
            mount_path="/plugins",
            ignore_patterns=_TEMPLATE_IGNORES,
            post_extract="chmod -R a+rX /plugins",
            selectors=("app.kubernetes.io/component=render-service",),
        )

    def update_ztp(
        self,
        images: Iterable[ZTPImageSource],
        *,
        pvc_name: str = ZTP_PVC_NAME,
    ) -> bool:
        """Update ZTP OS images and their manifest, then restart Network ZTP."""
        image_list = list(images)
        if not image_list:
            raise ValueError("At least one --image is required")
        with tempfile.TemporaryDirectory(prefix="nvcm-pvc-updater-") as tmpdir:
            staging = Path(tmpdir) / "ztp"
            staging.mkdir()
            manifest: dict[str, list[dict[str, object]]] = {"images": []}
            for image in image_list:
                if not image.path.is_file():
                    raise FileNotFoundError(f"OS image does not exist: {image.path}")
                platform = image.platform.replace(" ", "_").lower()
                destination = staging / platform / image.version
                destination.mkdir(parents=True, exist_ok=True)
                target = destination / image.path.name
                shutil.copy2(image.path, target)
                manifest["images"].append(
                    {
                        "platform": image.platform,
                        "version": image.version,
                        "filename": image.path.name,
                        "path": target.relative_to(staging).as_posix(),
                        "sha256": self._file_sha256(target),
                        "tags": {"firmware-image": ""},
                    }
                )
            (staging / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
            return self._upload_staging(
                kind="ztp",
                staging=staging,
                pvc_name=pvc_name,
                mount_path="/mnt/images",
                post_extract="",
                selectors=("app.kubernetes.io/component=network-ztp",),
            )

    def _update_content(
        self,
        *,
        kind: str,
        sources: Iterable[Path],
        pvc_name: str,
        mount_path: str,
        ignore_patterns: tuple[str, ...],
        post_extract: str,
        selectors: tuple[str, ...],
    ) -> bool:
        source_list = list(sources)
        if not source_list:
            raise ValueError("At least one --source is required")
        with tempfile.TemporaryDirectory(prefix="nvcm-pvc-updater-") as tmpdir:
            staging = Path(tmpdir) / kind
            staging.mkdir()
            _stage_sources(source_list, staging, ignore_patterns=ignore_patterns)
            return self._upload_staging(
                kind=kind,
                staging=staging,
                pvc_name=pvc_name,
                mount_path=mount_path,
                post_extract=post_extract,
                selectors=selectors,
            )

    def _upload_staging(
        self,
        *,
        kind: str,
        staging: Path,
        pvc_name: str,
        mount_path: str,
        post_extract: str,
        selectors: tuple[str, ...],
    ) -> bool:
        self._require_pvc(pvc_name)
        content_hash = _hash_staged_content(staging)
        current_hash = self._k8s.get_pvc_annotation(
            pvc_name, self.namespace, CONTENT_HASH_ANNOTATION
        )
        if current_hash == content_hash:
            self._on_log(f"{kind}: content unchanged; PVC and workloads left untouched")
            return False

        with tempfile.TemporaryDirectory(prefix="nvcm-pvc-updater-") as tmpdir:
            tarball = Path(tmpdir) / f"{kind}.tar.gz"
            _make_tarball(staging, tarball)
            pod_name = f"nvcm-pvc-updater-{kind}"
            self._k8s.delete_pod(pod_name, self.namespace)
            self._k8s.wait_for_pod_gone(pod_name, self.namespace)
            try:
                self._k8s.create_loader_pod(pod_name, self.namespace, pvc_name, mount_path)
                self._k8s.wait_for_pod_ready(pod_name, self.namespace)
                self._on_log(f"{kind}: copying content into PVC {pvc_name}")
                self._k8s.copy_to_pod(str(tarball), pod_name, self.namespace, "/tmp/content.tar.gz")
                command = (
                    f"cd {mount_path} && find . -mindepth 1 -maxdepth 1 -exec rm -rf {{}} \\; "
                    "&& tar xzf /tmp/content.tar.gz"
                )
                if post_extract:
                    command = f"{command} && {post_extract}"
                self._k8s.exec_command(pod_name, self.namespace, ["sh", "-c", command])
            finally:
                self._k8s.delete_pod(pod_name, self.namespace)

        self._k8s.annotate_pvc(pvc_name, self.namespace, CONTENT_HASH_ANNOTATION, content_hash)
        self._restart_consumers(kind, selectors)
        return True

    def _require_pvc(self, pvc_name: str) -> None:
        if not self._k8s.pvc_exists(pvc_name, self.namespace):
            raise RuntimeError(
                f"PVC '{pvc_name}' does not exist in namespace '{self.namespace}'. "
                "Create it through the NVCM GitOps application before running pvc-updater."
            )

    def _restart_consumers(self, kind: str, selectors: tuple[str, ...]) -> None:
        deployment_names: set[str] = set()
        for selector in selectors:
            deployment_names.update(
                self._k8s.list_deployment_names(self.namespace, label_selector=selector)
            )
        release_prefix = f"{self.release_name}-"
        deployment_names = {
            name
            for name in deployment_names
            if name == self.release_name or name.startswith(release_prefix)
        }
        if not deployment_names:
            raise RuntimeError(
                f"No workloads for release '{self.release_name}' consume the {kind} PVC "
                f"in namespace '{self.namespace}'"
            )
        generations: dict[str, int] = {}
        for name in sorted(deployment_names):
            self._on_log(f"{kind}: restarting deployment {name}")
            generations[name] = self._k8s.restart_deployment(name, self.namespace)
        for name in sorted(deployment_names):
            self._k8s.wait_for_rollout(
                name,
                self.namespace,
                timeout=self.rollout_timeout,
                on_message=self._on_log,
                min_generation=generations[name],
            )

    @staticmethod
    def _file_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as image:
            for chunk in iter(lambda: image.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
