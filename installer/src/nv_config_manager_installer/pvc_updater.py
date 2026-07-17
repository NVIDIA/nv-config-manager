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
controller cannot put into a volume and restarts workloads when changed content
must be reloaded.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
import tempfile
import threading
import time
import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from nv_config_manager_installer.k8s import K8sClient
from nv_config_manager_installer.nautobot_jobs import NautobotJobRunner

CONTENT_HASH_ANNOTATION = "nv-config-manager.nvidia.com/content-sha256"
CUSTOM_JOBS_PACKAGE_MARKER = "# Custom Nautobot jobs package maintained by nvcm-installer.\n"
JOBS_PVC_NAME = "nautobot-custom-jobs"
TEMPLATES_PVC_NAME = "render-service-template-plugins"
ZTP_PVC_NAME = "ztp-os-images"
PVC_UPDATE_LEASE_DURATION_SECONDS = 3_600

_COMMON_IGNORES = (".venv", "__pycache__", ".git", "*.pyc", "tests")
_TEMPLATE_IGNORES = (*_COMMON_IGNORES, "tests")


@dataclass(frozen=True)
class ZTPImageSource:
    """An OS image and the metadata required by the ZTP file backend."""

    platform: str
    version: str
    path: Path


def validate_ztp_path_component(label: str, component: str) -> None:
    """Reject ZTP metadata that cannot safely become one directory name."""
    if (
        not component
        or component in {".", ".."}
        or "/" in component
        or "\\" in component
        or Path(component).name != component
        or not component.replace("-", "").replace("_", "").replace(".", "").isalnum()
    ):
        raise ValueError(f"Invalid ZTP {label}: {component!r}")


def normalize_ztp_platform(platform: str) -> str:
    """Normalize a display platform name to the storage path identifier."""
    return platform.strip().replace(" ", "-").lower()


def _pvc_update_lease_name(pvc_name: str) -> str:
    """Return a stable, DNS-safe Lease name for one PVC."""
    digest = hashlib.sha256(pvc_name.encode()).hexdigest()[:16]
    return f"nvcm-pvc-update-{digest}"


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


def _replace_pvc_content_command(mount_path: str, post_extract: str) -> str:
    """Build a transactional same-volume PVC content replacement command.

    A PVC is mounted at ``mount_path``, so its root cannot be renamed. The
    command validates content in a hidden staging directory, moves old entries
    into a hidden backup directory, then moves the staged entries into place.
    If the switch fails, it restores the backup before reporting the error.
    """
    staging_name = ".nvcm-pvc-updater-staging"
    backup_name = ".nvcm-pvc-updater-backup"
    post_extract_command = f'\n(cd "$staging" && {post_extract})' if post_extract else ""
    return f'''set -eu
live="{mount_path}"
staging="$live/{staging_name}"
backup="$live/{backup_name}"
if [ -e "$staging" ] || [ -e "$backup" ]; then
    echo "Incomplete previous PVC update found; inspect $staging and $backup before retrying" >&2
    exit 1
fi
cleanup_staging() {{
    rm -rf "$staging"
}}
trap cleanup_staging EXIT
mkdir "$staging"
tar xzf /tmp/content.tar.gz -C "$staging"{post_extract_command}
mkdir "$backup"
move_old_content() {{
    for entry in "$live"/.[!.]* "$live"/..?* "$live"/*; do
        if [ ! -e "$entry" ] && [ ! -L "$entry" ]; then
            continue
        fi
        if [ "$entry" = "$staging" ] || [ "$entry" = "$backup" ]; then
            continue
        fi
        mv "$entry" "$backup"/ || return 1
    done
}}
move_new_content() {{
    for entry in "$staging"/.[!.]* "$staging"/..?* "$staging"/*; do
        if [ ! -e "$entry" ] && [ ! -L "$entry" ]; then
            continue
        fi
        mv "$entry" "$live"/ || return 1
    done
}}
restore_old_content() {{
    for entry in "$backup"/.[!.]* "$backup"/..?* "$backup"/*; do
        if [ ! -e "$entry" ] && [ ! -L "$entry" ]; then
            continue
        fi
        mv "$entry" "$live"/ || return 1
    done
    rmdir "$backup"
}}
rollback_new_content() {{
    for entry in "$live"/.[!.]* "$live"/..?* "$live"/*; do
        if [ ! -e "$entry" ] && [ ! -L "$entry" ]; then
            continue
        fi
        if [ "$entry" = "$staging" ] || [ "$entry" = "$backup" ]; then
            continue
        fi
        rm -rf "$entry" || return 1
    done
    restore_old_content
}}
if ! move_old_content; then
    restore_old_content || true
    exit 1
fi
if ! move_new_content; then
    rollback_new_content || true
    exit 1
fi
rm -rf "$backup"
rmdir "$staging"
trap - EXIT'''


def _replace_ztp_pvc_content_command(mount_path: str) -> str:
    """Build a live-safe ZTP update command that publishes the manifest last.

    Image files are moved into place with same-volume renames while the old
    manifest remains available.  The new manifest is then atomically renamed
    over it before files that are no longer referenced are removed.
    """
    staging_name = ".nvcm-pvc-updater-staging"
    desired_name = ".nvcm-pvc-updater-desired"
    return f'''set -eu
live="{mount_path}"
staging="$live/{staging_name}"
desired="$live/{desired_name}"
if [ -e "$staging" ] || [ -e "$desired" ]; then
    echo "Incomplete previous ZTP PVC update found; inspect $staging and $desired before retrying" >&2
    exit 1
fi
cleanup_workdirs() {{
    rm -rf "$staging" "$desired"
}}
trap cleanup_workdirs EXIT
mkdir "$staging" "$desired"
tar xzf /tmp/content.tar.gz -C "$staging"
if [ ! -f "$staging/manifest.json" ]; then
    echo "ZTP content archive does not contain manifest.json" >&2
    exit 1
fi
find "$staging" -type f ! -path "$staging/manifest.json" -exec sh -c '
staging=$1
desired=$2
shift 2
for source do
    relative=${{source#"$staging"/}}
    marker="$desired/$relative"
    mkdir -p "$(dirname "$marker")"
    : > "$marker"
done
' sh "$staging" "$desired" {{}} +
find "$staging" -type f ! -path "$staging/manifest.json" -exec sh -c '
staging=$1
live=$2
shift 2
for source do
    relative=${{source#"$staging"/}}
    destination="$live/$relative"
    mkdir -p "$(dirname "$destination")"
    mv -f "$source" "$destination"
done
' sh "$staging" "$live" {{}} +
mv -f "$staging/manifest.json" "$live/manifest.json"
find "$live" \\( -path "$staging" -o -path "$desired" \\) -prune -o \
    -type f ! -path "$live/manifest.json" -exec sh -c '
live=$1
desired=$2
shift 2
for current do
    relative=${{current#"$live"/}}
    if [ ! -f "$desired/$relative" ]; then
        rm -f "$current"
    fi
done
' sh "$live" "$desired" {{}} +
find "$live" -depth -type d ! -path "$live" ! -path "$staging" ! -path "$desired" \
    -exec rmdir {{}} \\; 2>/dev/null || true
cleanup_workdirs
trap - EXIT'''


class _LeaseRenewer:
    """Keep one PVC-update Lease valid while a long update is running."""

    def __init__(
        self,
        k8s: K8sClient,
        lease_name: str,
        namespace: str,
        holder_identity: str,
        duration_seconds: int,
    ) -> None:
        self._k8s = k8s
        self._lease_name = lease_name
        self._namespace = namespace
        self._holder_identity = holder_identity
        self._duration_seconds = duration_seconds
        self._stop_event = threading.Event()
        self._failure: Exception | None = None
        self._failure_lock = threading.Lock()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def __enter__(self) -> _LeaseRenewer:
        self._thread.start()
        return self

    def __exit__(self, exc_type: object, exc_value: object, traceback: object) -> None:
        self._stop_event.set()
        self._thread.join()
        if exc_type is None:
            self.ensure_healthy()

    def ensure_healthy(self) -> None:
        """Raise immediately once lease ownership can no longer be guaranteed."""
        with self._failure_lock:
            failure = self._failure
        if failure is not None:
            raise RuntimeError(
                f"Lost PVC update lease '{self._lease_name}': {failure}"
            ) from failure

    def _record_failure(self, failure: Exception) -> None:
        with self._failure_lock:
            self._failure = failure
        self._stop_event.set()

    def _run(self) -> None:
        renewal_interval = max(1, self._duration_seconds // 4)
        retry_interval = max(1, min(30, self._duration_seconds // 12))
        safe_retry_window = max(1, self._duration_seconds // 2)
        last_success = time.monotonic()
        delay = renewal_interval
        while not self._stop_event.wait(delay):
            try:
                self._k8s.renew_lease(
                    self._lease_name,
                    self._namespace,
                    self._holder_identity,
                    duration_seconds=self._duration_seconds,
                )
            except RuntimeError as exc:  # ownership loss is not retryable
                self._record_failure(exc)
                return
            except Exception as exc:  # pragma: no cover - timing-dependent
                status = getattr(exc, "status", None)
                if status and status < 500 and status not in {408, 429}:
                    self._record_failure(exc)
                    return
                remaining = safe_retry_window - (time.monotonic() - last_success)
                if remaining <= 0:
                    self._record_failure(exc)
                    return
                delay = min(retry_interval, remaining)
            else:
                last_success = time.monotonic()
                delay = renewal_interval


class PVCUpdater:
    """Populate the three NVCM content PVCs and reload consumers when needed."""

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
            post_extract="chown -R 1000:1000 .",
            selectors=(
                "app.kubernetes.io/component=nautobot",
                "app.kubernetes.io/component=celery",
                "app.kubernetes.io/component=celery-beat",
            ),
            package_marker=True,
        )

    def run_nautobot_job(
        self,
        job_class: str,
        job_input: dict[str, Any],
        *,
        timeout: int = 1_800,
    ) -> bool:
        """Run a custom Nautobot job after its PVC content is available."""
        self._on_log(f"jobs: running Nautobot job {job_class}")
        runner = NautobotJobRunner(
            self._k8s,
            self.namespace,
            self.release_name,
            on_log=lambda message: self._on_log(f"jobs: {message}"),
        )
        return runner.run(job_class, job_input, timeout=timeout)

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
            post_extract="chmod -R a+rX .",
            selectors=("app.kubernetes.io/component=render-service",),
        )

    def update_ztp(
        self,
        images: Iterable[ZTPImageSource],
        *,
        pvc_name: str = ZTP_PVC_NAME,
    ) -> bool:
        """Update ZTP OS images and publish their manifest without stopping ZTP."""
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
                platform = normalize_ztp_platform(image.platform)
                version = image.version
                validate_ztp_path_component("platform", platform)
                validate_ztp_path_component("version", version)
                destination = staging / platform / version
                destination.mkdir(parents=True, exist_ok=True)
                target = destination / image.path.name
                if target.exists():
                    raise ValueError(
                        f"Duplicate ZTP image destination: {target.relative_to(staging).as_posix()}"
                    )
                shutil.copy2(image.path, target)
                manifest["images"].append(
                    {
                        "platform": platform,
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
                selectors=(),
                publish_manifest_last=True,
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
        package_marker: bool = False,
    ) -> bool:
        source_list = list(sources)
        if not source_list:
            raise ValueError("At least one --source is required")
        with tempfile.TemporaryDirectory(prefix="nvcm-pvc-updater-") as tmpdir:
            staging = Path(tmpdir) / kind
            staging.mkdir()
            _stage_sources(source_list, staging, ignore_patterns=ignore_patterns)
            package_init = staging / "__init__.py"
            if package_marker and not package_init.exists():
                package_init.write_text(CUSTOM_JOBS_PACKAGE_MARKER)
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
        publish_manifest_last: bool = False,
    ) -> bool:
        self._require_pvc(pvc_name)
        lease_name = _pvc_update_lease_name(pvc_name)
        holder_identity = f"nvcm-installer-{uuid.uuid4().hex}"
        self._k8s.acquire_lease(
            lease_name,
            self.namespace,
            holder_identity,
            duration_seconds=PVC_UPDATE_LEASE_DURATION_SECONDS,
        )
        try:
            with _LeaseRenewer(
                self._k8s,
                lease_name,
                self.namespace,
                holder_identity,
                PVC_UPDATE_LEASE_DURATION_SECONDS,
            ) as lease_renewer:
                content_hash = _hash_staged_content(staging)
                current_hash = self._k8s.get_pvc_annotation(
                    pvc_name, self.namespace, CONTENT_HASH_ANNOTATION
                )
                if current_hash == content_hash:
                    self._on_log(f"{kind}: content unchanged; PVC and workloads left untouched")
                    return False

                deployment_names = (
                    self._consumer_deployment_names(kind, selectors) if selectors else []
                )

                with tempfile.TemporaryDirectory(prefix="nvcm-pvc-updater-") as tmpdir:
                    tarball = Path(tmpdir) / f"{kind}.tar.gz"
                    _make_tarball(staging, tarball)
                    pvc_suffix = hashlib.sha256(pvc_name.encode()).hexdigest()[:12]
                    pod_name = f"nvcm-pvc-updater-{kind}-{pvc_suffix}"
                    self._k8s.delete_pod(pod_name, self.namespace)
                    self._k8s.wait_for_pod_gone(pod_name, self.namespace)
                    original_replicas: dict[str, int] | None = None
                    try:
                        mounted_node = self._k8s.get_pvc_mounted_node(pvc_name, self.namespace)
                        if mounted_node:
                            self._on_log(
                                f"{kind}: placing loader on PVC consumer node {mounted_node}"
                            )
                        self._k8s.create_loader_pod(
                            pod_name,
                            self.namespace,
                            pvc_name,
                            mount_path,
                            node_name=mounted_node,
                        )
                        self._k8s.wait_for_pod_ready(pod_name, self.namespace)
                        self._on_log(f"{kind}: copying content into PVC {pvc_name}")
                        self._k8s.copy_to_pod(
                            str(tarball), pod_name, self.namespace, "/tmp/content.tar.gz"
                        )
                        lease_renewer.ensure_healthy()
                        if deployment_names:
                            original_replicas = self._quiesce_consumers(
                                kind,
                                deployment_names,
                                lease_renewer,
                            )
                        lease_renewer.ensure_healthy()
                        command = (
                            _replace_ztp_pvc_content_command(mount_path)
                            if publish_manifest_last
                            else _replace_pvc_content_command(mount_path, post_extract)
                        )
                        self._k8s.exec_command(pod_name, self.namespace, ["sh", "-c", command])
                        lease_renewer.ensure_healthy()
                    finally:
                        try:
                            self._k8s.delete_pod(pod_name, self.namespace)
                            self._k8s.wait_for_pod_gone(pod_name, self.namespace)
                        finally:
                            if original_replicas is not None:
                                self._restore_consumers(kind, original_replicas)

                lease_renewer.ensure_healthy()
                self._k8s.annotate_pvc(
                    pvc_name, self.namespace, CONTENT_HASH_ANNOTATION, content_hash
                )
                return True
        finally:
            self._k8s.release_lease(lease_name, self.namespace, holder_identity)

    def _require_pvc(self, pvc_name: str) -> None:
        if not self._k8s.pvc_exists(pvc_name, self.namespace):
            raise RuntimeError(
                f"PVC '{pvc_name}' does not exist in namespace '{self.namespace}'. "
                "Create it through the NVCM GitOps application before running pvc-updater."
            )

    def _consumer_deployment_names(
        self,
        kind: str,
        selectors: tuple[str, ...],
    ) -> list[str]:
        deployment_names: set[str] = set()
        for selector in selectors:
            release_selector = f"{selector},app.kubernetes.io/instance={self.release_name}"
            deployment_names.update(
                self._k8s.list_deployment_names(
                    self.namespace,
                    label_selector=release_selector,
                )
            )
        if not deployment_names:
            raise RuntimeError(
                f"No workloads for release '{self.release_name}' consume the {kind} PVC "
                f"in namespace '{self.namespace}'"
            )
        return sorted(deployment_names)

    def _quiesce_consumers(
        self,
        kind: str,
        deployment_names: list[str],
        lease_renewer: _LeaseRenewer,
    ) -> dict[str, int]:
        original_replicas = {
            name: self._k8s.get_deployment_replicas(name, self.namespace)
            for name in deployment_names
        }
        generations: dict[str, int] = {}
        try:
            for name in deployment_names:
                lease_renewer.ensure_healthy()
                if original_replicas[name] == 0:
                    continue
                self._on_log(f"{kind}: quiescing deployment {name}")
                generations[name] = self._k8s.scale_deployment(name, self.namespace, 0)
            for name, generation in generations.items():
                self._k8s.wait_for_rollout(
                    name,
                    self.namespace,
                    timeout=self.rollout_timeout,
                    on_message=self._on_log,
                    min_generation=generation,
                )
                lease_renewer.ensure_healthy()
        except Exception:
            self._restore_consumers(
                kind,
                {name: original_replicas[name] for name in generations},
            )
            raise
        return original_replicas

    def _restore_consumers(self, kind: str, original_replicas: dict[str, int]) -> None:
        generations: dict[str, int] = {}
        for name, replicas in original_replicas.items():
            if replicas == 0:
                continue
            self._on_log(f"{kind}: restoring deployment {name} to {replicas} replica(s)")
            generations[name] = self._k8s.scale_deployment(name, self.namespace, replicas)
        for name, generation in generations.items():
            self._k8s.wait_for_rollout(
                name,
                self.namespace,
                timeout=self.rollout_timeout,
                on_message=self._on_log,
                min_generation=generation,
            )

    @staticmethod
    def _file_sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as image:
            for chunk in iter(lambda: image.read(8 * 1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
