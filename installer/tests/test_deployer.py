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
"""Tests for nv_config_manager_installer.deployer -- step sequencing, callbacks, and re-run detection."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nv_config_manager_installer.accounts import build_config_secrets_ini
from nv_config_manager_installer.deployer import (
    Deployer,
    DeployOptions,
    DeployStep,
    StepStatus,
    _get_image_digest_tag,
    _hash_content_dir,
    _RerunState,
)
from nv_config_manager_installer.k8s import LOADER_POD_IMAGE
from nv_config_manager_installer.schema import (
    ClusterConfig,
    ContentConfig,
    GitTokenEntry,
    ImagePullSecret,
    ImagesConfig,
    ImageSource,
    JobPath,
    JobsConfig,
    NetworkSecretEntry,
    NVConfigManagerInstallConfig,
    RedfishConfig,
    RedfishVendorCreds,
    SecretsConfig,
    ServicesConfig,
    SiteConfig,
    TemplatePath,
)

_OPERATOR_VERSIONS = """\
GATEWAY_API_VERSION=v1.4.1
ENVOY_GATEWAY_VERSION=v1.6.5
CERT_MANAGER_VERSION=v1.20.2
CNPG_OPERATOR_VERSION=0.28.0
INGRESS_NGINX_VERSION=4.15.1
PROMETHEUS_CRD_VERSION=v0.90.1
PROMETHEUS_OPERATOR_VERSION=84.5.0
"""


def _make_config() -> NVConfigManagerInstallConfig:
    return NVConfigManagerInstallConfig(
        cluster=ClusterConfig(hostname="test.local"),
        secrets=SecretsConfig(config_manager_service_username="nv-config-manager"),
        sites=[SiteConfig(name="dc01")],
    )


_TEST_KUBE_CONTEXT = "test-context"


@pytest.fixture(autouse=True)
def _stub_kube_context_helpers():
    """Stub the module-level kube-context helpers used by Deployer.run().

    Two helpers in ``nv_config_manager_installer.deployer`` reach past the K8sClient mock
    and shell out to real ``kubectl``:

    * ``kubectl_current_context()`` — the prereq step calls this to detect a
      mismatch between the Python kubernetes client's bound context and what
      kubectl reports. On a CI runner that has kubectl installed, its
      current-context would never match the mock's ``_TEST_KUBE_CONTEXT`` and
      the mismatch check would raise.
    * ``pin_kubeconfig_to_current_context()`` — Deployer.run() calls this
      first thing to materialize a single-context kubeconfig under /tmp. We
      don't want tests touching the host filesystem or invoking kubectl.

    Pin both: the context helper returns the same value the mock K8sClient
    advertises; the pinning helper is a no-op (returns None, deployer just
    logs a warning and proceeds).
    """
    with (
        patch(
            "nv_config_manager_installer.deployer.kubectl_current_context",
            return_value=_TEST_KUBE_CONTEXT,
        ),
        patch(
            "nv_config_manager_installer.deployer.pin_kubeconfig_to_current_context",
            return_value=None,
        ),
    ):
        yield


def _mock_k8s():
    """Create a MagicMock that satisfies the K8sClient interface."""
    k8s = MagicMock()
    k8s.check_connectivity.return_value = True
    k8s.ensure_namespace.return_value = False
    k8s.secret_exists.return_value = False
    k8s.read_secret_data.return_value = {}
    k8s.get_pvc_annotation.return_value = ""
    k8s.list_deployment_names.return_value = []
    k8s.restart_deployment.return_value = 0
    # Match what the real K8sClient sets after binding to a context. The
    # deployer's prereq + create-namespace steps now check these explicitly to
    # detect Python-vs-kubectl context drift; a bare MagicMock would surface
    # as `<MagicMock ...>` and fail the equality check.
    k8s.active_context = _TEST_KUBE_CONTEXT
    k8s.api_server = "https://test.local:6443"
    k8s.namespace_phase.return_value = "Active"
    return k8s


class RecordingCallback:
    """Test callback that records all events."""

    def __init__(self):
        self.step_updates: list[tuple[str, str]] = []
        self.logs: list[str] = []
        self.completed: list[tuple[bool, list[str]]] = []

    def on_step_update(self, step: DeployStep) -> None:
        self.step_updates.append((step.id, step.status))

    def on_log(self, message: str) -> None:
        self.logs.append(message)

    def on_complete(self, success: bool, endpoints: list[str]) -> None:
        self.completed.append((success, endpoints))


class TestDeployerInit:
    def test_steps_initialized(self):
        config = _make_config()
        deployer = Deployer(config, DeployOptions())
        assert len(deployer.steps) == 18
        assert all(s.status == StepStatus.PENDING for s in deployer.steps)

    def test_step_ids_unique(self):
        config = _make_config()
        deployer = Deployer(config, DeployOptions())
        ids = [s.id for s in deployer.steps]
        assert len(ids) == len(set(ids))


class TestStepSequencing:
    @patch("nv_config_manager_installer.deployer.shutil.which", return_value=None)
    def test_prereqs_fail_when_kubectl_missing(self, mock_which):
        config = _make_config()
        callback = RecordingCallback()
        deployer = Deployer(config, DeployOptions(), callback)
        success = deployer.run()
        assert not success
        assert any(s[1] == StepStatus.FAILED for s in callback.step_updates)

    @patch("nv_config_manager_installer.deployer._run_logged")
    @patch("nv_config_manager_installer.deployer._run")
    @patch("nv_config_manager_installer.deployer.K8sClient")
    @patch("nv_config_manager_installer.deployer.shutil.which", return_value="/usr/bin/kubectl")
    def test_skip_steps_when_not_requested(
        self, mock_which, mock_k8s_cls, mock_run, mock_run_logged
    ):
        mock_k8s_cls.return_value = _mock_k8s()
        mock_result = MagicMock(returncode=0, stdout="", stderr="")
        mock_run.return_value = mock_result
        mock_run_logged.return_value = mock_result
        config = _make_config()
        callback = RecordingCallback()
        options = DeployOptions(dry_run=True)
        deployer = Deployer(config, options, callback)
        deployer.run()
        statuses = dict(callback.step_updates)
        assert statuses.get("build-images") == StepStatus.SKIPPED
        assert statuses.get("load-kind") == StepStatus.SKIPPED
        assert statuses.get("install-crds") == StepStatus.SKIPPED
        assert statuses.get("helm-install") == StepStatus.SKIPPED

    def test_callback_protocol(self):
        cb = RecordingCallback()
        step = DeployStep(id="test", label="Test step", status=StepStatus.RUNNING)
        cb.on_step_update(step)
        cb.on_log("test message")
        cb.on_complete(True, ["http://test/"])
        assert len(cb.step_updates) == 1
        assert len(cb.logs) == 1
        assert len(cb.completed) == 1


class TestInstallCrds:
    def test_cert_manager_online_install_uses_matching_pin(self, tmp_path, monkeypatch):
        (tmp_path / "helm").mkdir()
        (tmp_path / "operator-versions.env").write_text(_OPERATOR_VERSIONS)
        run_commands: list[list[str]] = []
        logged_commands: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            run_commands.append(cmd)
            return MagicMock(returncode=0, stdout="", stderr="")

        def fake_run_logged(cmd, step, callback, **kwargs):
            logged_commands.append(cmd)
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr("nv_config_manager_installer.deployer._run", fake_run)
        monkeypatch.setattr("nv_config_manager_installer.deployer._run_logged", fake_run_logged)

        deployer = Deployer(
            _make_config(),
            DeployOptions(chart_dir=str(tmp_path / "helm"), install_cert_manager=True),
            RecordingCallback(),
        )
        deployer._install_crds()

        assert any("charts.jetstack.io" in " ".join(cmd) for cmd in run_commands)
        assert any("v1.20.2/cert-manager.crds.yaml" in " ".join(cmd) for cmd in logged_commands)
        cert_cmd = next(
            cmd
            for cmd in logged_commands
            if cmd[:4] == ["helm", "upgrade", "--install", "cert-manager"]
        )
        assert cert_cmd[cert_cmd.index("--version") + 1] == "v1.20.2"

    def test_airgap_operator_installs_use_local_artifacts(self, tmp_path, monkeypatch):
        root = tmp_path / "bundle"
        chart_dir = root / "helm"
        charts_dir = root / "charts"
        manifests_dir = root / "manifests"
        chart_dir.mkdir(parents=True)
        charts_dir.mkdir()
        manifests_dir.mkdir()
        (root / "operator-versions.env").write_text(_OPERATOR_VERSIONS)
        (charts_dir / "cert-manager-v1.20.2.tgz").touch()
        (charts_dir / "cloudnative-pg-0.28.0.tgz").touch()
        (charts_dir / "gateway-helm-v1.6.5.tgz").touch()
        (charts_dir / "prometheus-operator-crds-28.0.1.tgz").touch()
        (manifests_dir / "gateway-api-v1.4.1.yaml").touch()

        run_commands: list[list[str]] = []
        logged_commands: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            run_commands.append(cmd)
            return MagicMock(returncode=0, stdout="", stderr="")

        def fake_run_logged(cmd, step, callback, **kwargs):
            logged_commands.append(cmd)
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr("nv_config_manager_installer.deployer._run", fake_run)
        monkeypatch.setattr("nv_config_manager_installer.deployer._run_logged", fake_run_logged)

        config = _make_config()
        config.cluster.airgapped = True
        config.infrastructure.monitoring.observability_enabled = True
        config.images = ImagesConfig(
            source=ImageSource.REGISTRY,
            registry="registry.example.com/nv-config-manager",
        )
        deployer = Deployer(
            config,
            DeployOptions(
                chart_dir=str(chart_dir),
                install_envoy_gateway=True,
                install_cert_manager=True,
                install_cnpg_operator=True,
            ),
            RecordingCallback(),
        )
        deployer._install_crds()

        rendered_commands = [" ".join(cmd) for cmd in logged_commands]
        assert not any(
            str(manifests_dir / "gateway-api-v1.4.1.yaml") in cmd for cmd in rendered_commands
        )
        assert any(str(charts_dir / "gateway-helm-v1.6.5.tgz") in cmd for cmd in rendered_commands)
        envoy_cmd = next(
            cmd for cmd in logged_commands if cmd[:4] == ["helm", "upgrade", "--install", "eg"]
        )
        assert "--force-conflicts" not in envoy_cmd
        assert "--take-ownership" not in envoy_cmd
        assert (
            "global.images.envoyGateway.image="
            "registry.example.com/nv-config-manager/envoyproxy/gateway:v1.6.5" in envoy_cmd
        )
        assert (
            "global.images.ratelimit.image="
            "registry.example.com/nv-config-manager/envoyproxy/ratelimit:c8765e89" in envoy_cmd
        )

        cert_cmd = next(
            cmd
            for cmd in logged_commands
            if cmd[:4] == ["helm", "upgrade", "--install", "cert-manager"]
        )
        assert any(str(charts_dir / "cert-manager-v1.20.2.tgz") in cmd for cmd in rendered_commands)
        assert any("crds.enabled=true" in cmd for cmd in rendered_commands)
        assert (
            "image.repository=registry.example.com/nv-config-manager/jetstack/cert-manager-controller"
            in cert_cmd
        )
        assert "image.tag=v1.20.2" in cert_cmd
        assert (
            "webhook.image.repository=registry.example.com/nv-config-manager/"
            "jetstack/cert-manager-webhook" in cert_cmd
        )
        assert (
            "cainjector.image.repository=registry.example.com/nv-config-manager/"
            "jetstack/cert-manager-cainjector" in cert_cmd
        )
        assert (
            "startupapicheck.image.repository=registry.example.com/nv-config-manager/"
            "jetstack/cert-manager-startupapicheck" in cert_cmd
        )
        assert (
            "acmesolver.image.repository=registry.example.com/nv-config-manager/"
            "jetstack/cert-manager-acmesolver" in cert_cmd
        )

        cnpg_cmd = next(
            cmd for cmd in logged_commands if cmd[:4] == ["helm", "upgrade", "--install", "cnpg"]
        )
        assert any(
            str(charts_dir / "cloudnative-pg-0.28.0.tgz") in cmd for cmd in rendered_commands
        )
        assert (
            "image.repository=registry.example.com/nv-config-manager/cloudnative-pg/cloudnative-pg"
            in cnpg_cmd
        )
        assert "image.tag=1.29.0" in cnpg_cmd

        prom_crds_cmd = next(
            cmd
            for cmd in logged_commands
            if cmd[:4] == ["helm", "upgrade", "--install", "nv-config-manager-prom-crds"]
        )
        assert str(charts_dir / "prometheus-operator-crds-28.0.1.tgz") in prom_crds_cmd
        assert run_commands == []
        assert not any("github.com/cert-manager" in cmd for cmd in rendered_commands)


class TestDeployOptions:
    def test_defaults(self):
        opts = DeployOptions()
        assert opts.chart_dir == "deploy/helm"
        assert opts.build_images is False
        assert opts.load_kind is False
        assert opts.helm_timeout == "15m"
        assert opts.dry_run is False

    def test_custom_options(self):
        opts = DeployOptions(
            build_images=True,
            load_kind=True,
            kind_cluster="test-cluster",
            dry_run=True,
        )
        assert opts.build_images is True
        assert opts.kind_cluster == "test-cluster"


class TestKindImageLoading:
    def test_load_kind_tags_arch_specific_loader_image_as_canonical(self, monkeypatch):
        run_commands: list[list[str]] = []
        logged_commands: list[list[str]] = []

        def fake_run(cmd, **kwargs):
            run_commands.append(cmd)
            if cmd[:3] == ["docker", "version", "--format"]:
                return MagicMock(returncode=0, stdout="linux/amd64\n", stderr="")
            return MagicMock(returncode=0, stdout="", stderr="")

        def fake_run_logged(cmd, step, callback, **kwargs):
            logged_commands.append(cmd)
            return MagicMock(returncode=0, stdout="", stderr="")

        monkeypatch.setattr("nv_config_manager_installer.deployer._run", fake_run)
        monkeypatch.setattr("nv_config_manager_installer.deployer._run_logged", fake_run_logged)

        deployer = Deployer(
            _make_config(),
            DeployOptions(load_kind=True, kind_cluster="test-cluster"),
            RecordingCallback(),
        )
        deployer._load_kind()

        assert [
            "docker",
            "version",
            "--format",
            "{{.Server.Os}}/{{.Server.Arch}}",
        ] in run_commands
        assert [
            "docker",
            "pull",
            "--platform",
            "linux/amd64",
            "docker.io/amd64/busybox:1.36",
        ] in logged_commands
        assert [
            "docker",
            "tag",
            "docker.io/amd64/busybox:1.36",
            LOADER_POD_IMAGE,
        ] in logged_commands
        assert [
            "kind",
            "load",
            "docker-image",
            LOADER_POD_IMAGE,
            "--name",
            "test-cluster",
        ] in logged_commands


class TestContentHashing:
    def test_deterministic_hash(self):
        with tempfile.TemporaryDirectory() as d:
            job_dir = Path(d) / "my_job"
            job_dir.mkdir()
            (job_dir / "main.py").write_text("print('hello')")
            (job_dir / "util.py").write_text("x = 1")

            h1 = _hash_content_dir([job_dir])
            h2 = _hash_content_dir([job_dir])
            assert h1 == h2, "Same content should produce the same hash"

    def test_different_content_different_hash(self):
        with tempfile.TemporaryDirectory() as d:
            job_dir = Path(d) / "my_job"
            job_dir.mkdir()
            (job_dir / "main.py").write_text("print('v1')")

            h1 = _hash_content_dir([job_dir])
            (job_dir / "main.py").write_text("print('v2')")
            h2 = _hash_content_dir([job_dir])
            assert h1 != h2, "Changed content should produce a different hash"

    def test_ignores_patterns(self):
        with tempfile.TemporaryDirectory() as d:
            job_dir = Path(d) / "my_job"
            job_dir.mkdir()
            (job_dir / "main.py").write_text("print('hello')")

            h1 = _hash_content_dir([job_dir])
            pycache = job_dir / "__pycache__"
            pycache.mkdir()
            (pycache / "main.cpython-313.pyc").write_bytes(b"\x00\x01\x02")
            h2 = _hash_content_dir([job_dir])
            assert h1 == h2, "Ignored files should not affect the hash"

    def test_empty_paths(self):
        h = _hash_content_dir([])
        assert isinstance(h, str) and len(h) == 64

    def test_missing_path_ignored(self):
        h = _hash_content_dir([Path("/nonexistent/path")])
        assert isinstance(h, str) and len(h) == 64


class TestRerunState:
    def test_defaults(self):
        state = _RerunState()
        assert state.is_rerun is False
        assert state.jobs_changed is True
        assert state.templates_changed is True

    def test_deployer_has_rerun_state(self):
        config = _make_config()
        deployer = Deployer(config, DeployOptions())
        assert deployer._rerun.is_rerun is False
        assert deployer._rerun.jobs_changed is True


class TestConditionalRestart:
    """Verify _restart_nautobot and _restart_render_service skip logic."""

    def _make_deployer(self, *, jobs=True, templates=False) -> tuple:
        content_kwargs: dict = {"include_bootstrap_jobs": False}
        if jobs:
            content_kwargs["jobs"] = [JobPath(path="/fake/jobs")]
        if templates:
            content_kwargs["template_plugins"] = [TemplatePath(path="/fake/tpls")]
        config = _make_config()
        config = NVConfigManagerInstallConfig(
            cluster=config.cluster,
            secrets=config.secrets,
            sites=config.sites,
            content=ContentConfig(**content_kwargs),
        )
        cb = RecordingCallback()
        deployer = Deployer(config, DeployOptions(), cb)
        deployer._k8s = _mock_k8s()
        return deployer, cb

    def test_skip_restart_nautobot_on_fresh_install(self):
        deployer, cb = self._make_deployer(jobs=True)
        deployer._rerun = _RerunState(is_rerun=False, jobs_changed=True)
        deployer._restart_nautobot()
        statuses = dict(cb.step_updates)
        assert statuses.get("restart-nautobot") == StepStatus.SKIPPED

    def test_skip_restart_nautobot_when_jobs_unchanged(self):
        deployer, cb = self._make_deployer(jobs=True)
        deployer._rerun = _RerunState(is_rerun=True, jobs_changed=False)
        deployer._restart_nautobot()
        statuses = dict(cb.step_updates)
        assert statuses.get("restart-nautobot") == StepStatus.SKIPPED

    @patch("nv_config_manager_installer.deployer._run_logged")
    def test_restart_nautobot_on_rerun_with_changed_jobs(self, mock_run_logged):
        mock_run_logged.return_value = MagicMock(returncode=0, stdout="", stderr="")
        deployer, cb = self._make_deployer(jobs=True)
        deployer._rerun = _RerunState(is_rerun=True, jobs_changed=True)
        deployer._restart_nautobot()
        statuses = dict(cb.step_updates)
        assert statuses.get("restart-nautobot") == StepStatus.SUCCESS
        deployer._k8s.restart_deployment.assert_called()

    def test_skip_restart_render_on_fresh_install(self):
        deployer, cb = self._make_deployer(templates=True)
        deployer._rerun = _RerunState(is_rerun=False, templates_changed=True)
        deployer._restart_render_service()
        statuses = dict(cb.step_updates)
        assert statuses.get("restart-render") == StepStatus.SKIPPED

    def test_skip_restart_render_when_templates_unchanged(self):
        deployer, cb = self._make_deployer(templates=True)
        deployer._rerun = _RerunState(is_rerun=True, templates_changed=False)
        deployer._restart_render_service()
        statuses = dict(cb.step_updates)
        assert statuses.get("restart-render") == StepStatus.SKIPPED

    @patch("nv_config_manager_installer.deployer._run_logged")
    def test_restart_render_on_rerun_with_changed_templates(self, mock_run_logged):
        mock_run_logged.return_value = MagicMock(returncode=0, stdout="", stderr="")
        deployer, cb = self._make_deployer(templates=True)
        deployer._rerun = _RerunState(is_rerun=True, templates_changed=True)
        deployer._k8s.list_deployment_names.return_value = [
            "nv-config-manager-render-api",
            "nv-config-manager-render-consumer-nautobot",
        ]
        deployer._restart_render_service()
        statuses = dict(cb.step_updates)
        assert statuses.get("restart-render") == StepStatus.SUCCESS
        assert deployer._k8s.restart_deployment.call_count == 2

    def test_skip_restart_render_when_no_template_plugins(self):
        deployer, cb = self._make_deployer(templates=False)
        deployer._rerun = _RerunState(is_rerun=True, templates_changed=True)
        deployer._restart_render_service()
        statuses = dict(cb.step_updates)
        assert statuses.get("restart-render") == StepStatus.SKIPPED


class TestPvcContentUpload:
    """Verify PVC content uploads replace prior extracted content."""

    def test_jobs_upload_clears_existing_content(self, tmp_path: Path):
        job_dir = tmp_path / "mock_topology"
        job_dir.mkdir()
        (job_dir / "__init__.py").write_text("")

        config = _make_config()
        config.content = ContentConfig(
            include_bootstrap_jobs=False,
            jobs=[JobPath(path=str(job_dir))],
        )
        deployer = Deployer(config, DeployOptions(), RecordingCallback())
        deployer._k8s = _mock_k8s()
        deployer._rerun = _RerunState(is_rerun=True, jobs_changed=True)

        deployer._setup_jobs_pvc()

        exec_command = deployer._k8s.exec_command.call_args.args[2]
        assert "find . -mindepth 1 -maxdepth 1 -exec rm -rf {} \\;" in exec_command[2]
        assert "tar xzf /tmp/jobs.tar.gz" in exec_command[2]

    def test_template_plugin_upload_clears_existing_content(self, tmp_path: Path):
        plugin_dir = tmp_path / "network_templates"
        plugin_dir.mkdir()
        (plugin_dir / "pyproject.toml").write_text('[project]\nname = "network-templates"\n')

        config = _make_config()
        config.content = ContentConfig(
            include_bootstrap_jobs=False,
            template_plugins=[TemplatePath(path=str(plugin_dir))],
        )
        deployer = Deployer(config, DeployOptions(), RecordingCallback())
        deployer._k8s = _mock_k8s()
        deployer._rerun = _RerunState(is_rerun=True, templates_changed=True)

        deployer._setup_templates_pvc()

        exec_command = deployer._k8s.exec_command.call_args.args[2]
        assert "find . -mindepth 1 -maxdepth 1 -exec rm -rf {} \\;" in exec_command[2]
        assert "tar xzf /tmp/plugins.tar.gz" in exec_command[2]


class TestK8sClientIntegration:
    """Verify the deployer interacts with K8sClient correctly."""

    def test_check_prerequisites_initializes_k8s(self):
        config = _make_config()
        deployer = Deployer(config, DeployOptions())
        assert deployer._k8s is None

    @patch("nv_config_manager_installer.deployer._run_logged")
    @patch("nv_config_manager_installer.deployer._run")
    @patch("nv_config_manager_installer.deployer.K8sClient")
    @patch("nv_config_manager_installer.deployer.shutil.which", return_value="/usr/bin/kubectl")
    def test_namespace_creation(self, mock_which, mock_k8s_cls, mock_run, mock_run_logged):
        mock_k8s = _mock_k8s()
        mock_k8s.ensure_namespace.return_value = True
        mock_k8s_cls.return_value = mock_k8s
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_run_logged.return_value = MagicMock(returncode=0, stdout="", stderr="")

        config = _make_config()
        cb = RecordingCallback()
        deployer = Deployer(config, DeployOptions(dry_run=True), cb)
        deployer.run()

        mock_k8s.ensure_namespace.assert_called_with("nv-config-manager")
        statuses = dict(cb.step_updates)
        assert statuses.get("create-namespace") == StepStatus.SUCCESS

    @patch("nv_config_manager_installer.deployer._run_logged")
    @patch("nv_config_manager_installer.deployer._run")
    @patch("nv_config_manager_installer.deployer.K8sClient")
    @patch("nv_config_manager_installer.deployer.shutil.which", return_value="/usr/bin/kubectl")
    def test_secret_creation_uses_k8s_client(
        self, mock_which, mock_k8s_cls, mock_run, mock_run_logged
    ):
        mock_k8s = _mock_k8s()
        mock_k8s_cls.return_value = mock_k8s
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_run_logged.return_value = MagicMock(returncode=0, stdout="", stderr="")

        config = _make_config()
        cb = RecordingCallback()
        deployer = Deployer(config, DeployOptions(dry_run=True), cb)
        deployer.run()

        mock_k8s.apply_secret.assert_called()
        secret_names = [call.args[0] for call in mock_k8s.apply_secret.call_args_list]
        assert "redis-password" in secret_names
        assert "nautobot-token" in secret_names
        assert "nautobot-admin" in secret_names

    def test_api_token_retrieval(self):
        config = _make_config()
        deployer = Deployer(config, DeployOptions())
        deployer._k8s = _mock_k8s()
        deployer._k8s.read_secret_data.return_value = {"api_token": "test-token-123"}

        token = deployer._get_nautobot_api_token()
        assert token == "test-token-123"
        deployer._k8s.read_secret_data.assert_called_with("nautobot-admin", "nv-config-manager")

    def test_api_token_fallback_to_nautobot_token(self):
        config = _make_config()
        deployer = Deployer(config, DeployOptions())
        deployer._k8s = _mock_k8s()
        deployer._k8s.read_secret_data.side_effect = [
            {},
            {"token": "fallback-token"},
        ]

        token = deployer._get_nautobot_api_token()
        assert token == "fallback-token"

    def test_network_secret_updates_stale_existing_content(self):
        config = _make_config()
        config.cluster.release_name = "nv-config-manager"
        config.sites = [SiteConfig(name="test-site")]
        config.network_secrets = [
            NetworkSecretEntry(name="Root Password", secret_key="root_password"),
        ]
        deployer = Deployer(config, DeployOptions())
        deployer._k8s = _mock_k8s()
        deployer._k8s.secret_exists.return_value = True
        deployer._k8s.read_secret_data.return_value = {
            "config-secrets.ini": "[site.dc01]\nroot_password_r1 = old-root\n"
        }
        step = DeployStep("create-secrets", "Create Kubernetes secrets")

        deployer._create_network_secrets(
            step,
            {"root_password_r1": "new-root", "hash_salt": "new-salt"},
        )

        deployer._k8s.apply_file_secret.assert_called_once()
        name, namespace, data = deployer._k8s.apply_file_secret.call_args.args
        assert name == "nv-config-manager-network-secrets"
        assert namespace == "nv-config-manager"
        rendered = data["config-secrets.ini"].decode()
        assert "[site.test-site]" in rendered
        assert "root_password_r1 = new-root" in rendered
        assert "Updated: nv-config-manager-network-secrets" in step.output

    def test_network_secret_skips_when_existing_content_matches(self):
        config = _make_config()
        config.cluster.release_name = "nv-config-manager"
        config.network_secrets = [
            NetworkSecretEntry(name="Root Password", secret_key="root_password"),
        ]
        existing = build_config_secrets_ini(
            config,
            {"root_password_r1": "existing-root", "hash_salt": "existing-salt"},
        )
        deployer = Deployer(config, DeployOptions())
        deployer._k8s = _mock_k8s()
        deployer._k8s.secret_exists.return_value = True
        deployer._k8s.read_secret_data.return_value = {"config-secrets.ini": existing}
        step = DeployStep("create-secrets", "Create Kubernetes secrets")

        deployer._create_network_secrets(
            step,
            {"root_password_r1": "new-root", "hash_salt": "new-salt"},
        )

        deployer._k8s.apply_file_secret.assert_not_called()
        assert "Secret exists, skipping: nv-config-manager-network-secrets" in step.output

    @patch("nv_config_manager_installer.deployer._run_logged")
    @patch("nv_config_manager_installer.deployer._run")
    @patch("nv_config_manager_installer.deployer.K8sClient")
    @patch("nv_config_manager_installer.deployer.shutil.which", return_value="/usr/bin/kubectl")
    def test_pull_secret_from_config_images(
        self, mock_which, mock_k8s_cls, mock_run, mock_run_logged
    ):
        mock_k8s = _mock_k8s()
        mock_k8s_cls.return_value = mock_k8s
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_run_logged.return_value = MagicMock(returncode=0, stdout="", stderr="")

        config = _make_config()
        config.images = ImagesConfig(
            source=ImageSource.REGISTRY,
            pull_secret=ImagePullSecret(
                name="my-reg-cred",
                server="registry.corp.com",
                username="robot$ci",
                password="my-key",
            ),
        )
        cb = RecordingCallback()
        deployer = Deployer(config, DeployOptions(dry_run=True), cb)
        deployer.run()

        mock_k8s.apply_docker_registry_secret.assert_called_once_with(
            "my-reg-cred",
            "nv-config-manager",
            server="registry.corp.com",
            username="robot$ci",
            password="my-key",
        )

    @patch("nv_config_manager_installer.deployer._run_logged")
    @patch("nv_config_manager_installer.deployer._run")
    @patch("nv_config_manager_installer.deployer.K8sClient")
    @patch("nv_config_manager_installer.deployer.shutil.which", return_value="/usr/bin/kubectl")
    def test_no_pull_secret_when_local_source(
        self, mock_which, mock_k8s_cls, mock_run, mock_run_logged
    ):
        mock_k8s = _mock_k8s()
        mock_k8s_cls.return_value = mock_k8s
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_run_logged.return_value = MagicMock(returncode=0, stdout="", stderr="")

        config = _make_config()
        config.images = ImagesConfig(
            source=ImageSource.LOCAL,
            pull_secret=ImagePullSecret(password="my-key"),
        )
        cb = RecordingCallback()
        deployer = Deployer(config, DeployOptions(dry_run=True), cb)
        deployer.run()

        mock_k8s.apply_docker_registry_secret.assert_not_called()

    @patch("nv_config_manager_installer.deployer._run_logged")
    @patch("nv_config_manager_installer.deployer._run")
    @patch("nv_config_manager_installer.deployer.K8sClient")
    @patch("nv_config_manager_installer.deployer.shutil.which", return_value="/usr/bin/kubectl")
    def test_git_token_secrets_created(self, mock_which, mock_k8s_cls, mock_run, mock_run_logged):
        mock_k8s = _mock_k8s()
        mock_k8s_cls.return_value = mock_k8s
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_run_logged.return_value = MagicMock(returncode=0, stdout="", stderr="")

        config = _make_config()
        config.git_tokens = [
            GitTokenEntry(name="prismo", token="ghp_abc123", username="bot-user"),
            GitTokenEntry(name="gitlab", token="glpat-xyz"),
        ]
        cb = RecordingCallback()
        deployer = Deployer(config, DeployOptions(dry_run=True), cb)
        deployer.run()

        secret_names = [call.args[0] for call in mock_k8s.apply_secret.call_args_list]
        assert "git-token-prismo" in secret_names
        assert "git-token-gitlab" in secret_names

        prismo_call = next(
            c for c in mock_k8s.apply_secret.call_args_list if c.args[0] == "git-token-prismo"
        )
        assert prismo_call.args[2] == {"token": "ghp_abc123", "username": "bot-user"}

        gitlab_call = next(
            c for c in mock_k8s.apply_secret.call_args_list if c.args[0] == "git-token-gitlab"
        )
        assert gitlab_call.args[2] == {"token": "glpat-xyz"}

    @patch("nv_config_manager_installer.deployer._run_logged")
    @patch("nv_config_manager_installer.deployer._run")
    @patch("nv_config_manager_installer.deployer.K8sClient")
    @patch("nv_config_manager_installer.deployer.shutil.which", return_value="/usr/bin/kubectl")
    def test_no_git_token_secrets_when_empty(
        self, mock_which, mock_k8s_cls, mock_run, mock_run_logged
    ):
        mock_k8s = _mock_k8s()
        mock_k8s_cls.return_value = mock_k8s
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_run_logged.return_value = MagicMock(returncode=0, stdout="", stderr="")

        config = _make_config()
        cb = RecordingCallback()
        deployer = Deployer(config, DeployOptions(dry_run=True), cb)
        deployer.run()

        secret_names = [call.args[0] for call in mock_k8s.apply_secret.call_args_list]
        assert not any(n.startswith("git-token-") for n in secret_names)

    def test_jobs_pvc_uses_storage_config_and_node_selector(self):
        config = _make_config()
        config.content = ContentConfig(
            jobs=[JobPath(path="/fake/jobs")],
            include_bootstrap_jobs=False,
            jobs_config=JobsConfig(
                storage_class="local-path",
                access_mode="ReadWriteOnce",
                node_selector={"kubernetes.io/hostname": "worker-1"},
            ),
        )
        callback = RecordingCallback()
        deployer = Deployer(config, DeployOptions(), callback)
        deployer._k8s = _mock_k8s()

        deployer._setup_jobs_pvc()

        deployer._k8s.ensure_pvc.assert_called_once_with(
            "nautobot-custom-jobs",
            "nv-config-manager",
            access_mode="ReadWriteOnce",
            storage_class="local-path",
            allow_recreate=False,
        )
        deployer._k8s.create_loader_pod.assert_called_once_with(
            "nv-config-manager-jobs-loader",
            "nv-config-manager",
            "nautobot-custom-jobs",
            mount_path="/jobs",
            node_selector={"kubernetes.io/hostname": "worker-1"},
        )


class TestContentAddressedTags:
    def test_deployer_initializes_empty_tags(self):
        config = _make_config()
        deployer = Deployer(config, DeployOptions())
        assert deployer._local_image_tags == {}

    @patch("nv_config_manager_installer.deployer.subprocess.run")
    def test_get_image_digest_tag(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="sha256:a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6\n"
        )
        tag = _get_image_digest_tag("nv-config-manager:local")
        assert tag == "sha-a1b2c3d4e5f6"
        mock_run.assert_called_once()

    @patch("nv_config_manager_installer.deployer.subprocess.run")
    def test_get_image_digest_tag_failure(self, mock_run):
        mock_run.side_effect = subprocess.CalledProcessError(1, "docker")
        tag = _get_image_digest_tag("nv-config-manager:local")
        assert tag == ""

    @patch("nv_config_manager_installer.deployer.subprocess.run")
    def test_get_image_digest_tag_no_docker(self, mock_run):
        mock_run.side_effect = FileNotFoundError("docker not found")
        tag = _get_image_digest_tag("nv-config-manager:local")
        assert tag == ""

    @patch("nv_config_manager_installer.deployer.subprocess.run")
    def test_get_image_digest_tag_empty_id(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="\n")
        tag = _get_image_digest_tag("nv-config-manager:local")
        assert tag == ""


class TestRedfishSecrets:
    @patch("nv_config_manager_installer.deployer._run_logged")
    @patch("nv_config_manager_installer.deployer._run")
    @patch("nv_config_manager_installer.deployer.K8sClient")
    @patch("nv_config_manager_installer.deployer.shutil.which", return_value="/usr/bin/kubectl")
    def test_redfish_creds_created_when_enabled(
        self, mock_which, mock_k8s_cls, mock_run, mock_run_logged
    ):
        mock_k8s = _mock_k8s()
        mock_k8s_cls.return_value = mock_k8s
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_run_logged.return_value = MagicMock(returncode=0, stdout="", stderr="")

        config = _make_config()
        config.redfish = RedfishConfig(
            enabled=True,
            vendors={
                "lenovo": RedfishVendorCreds(default_user="admin"),
                "bluefield": RedfishVendorCreds(),
            },
        )
        cb = RecordingCallback()
        deployer = Deployer(config, DeployOptions(dry_run=True), cb)
        deployer.run()

        secret_names = [call.args[0] for call in mock_k8s.apply_secret.call_args_list]
        assert "redfish-creds" in secret_names
        redfish_call = next(
            c for c in mock_k8s.apply_secret.call_args_list if c.args[0] == "redfish-creds"
        )
        data = redfish_call.args[2]
        assert "lenovo-default-user" in data
        assert "bluefield-default-user" in data

    @patch("nv_config_manager_installer.deployer._run_logged")
    @patch("nv_config_manager_installer.deployer._run")
    @patch("nv_config_manager_installer.deployer.K8sClient")
    @patch("nv_config_manager_installer.deployer.shutil.which", return_value="/usr/bin/kubectl")
    def test_no_redfish_creds_when_disabled(
        self, mock_which, mock_k8s_cls, mock_run, mock_run_logged
    ):
        mock_k8s = _mock_k8s()
        mock_k8s_cls.return_value = mock_k8s
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_run_logged.return_value = MagicMock(returncode=0, stdout="", stderr="")

        config = _make_config()
        cb = RecordingCallback()
        deployer = Deployer(config, DeployOptions(dry_run=True), cb)
        deployer.run()

        secret_names = [call.args[0] for call in mock_k8s.apply_secret.call_args_list]
        assert "redfish-creds" not in secret_names

    @patch("nv_config_manager_installer.deployer._run_logged")
    @patch("nv_config_manager_installer.deployer._run")
    @patch("nv_config_manager_installer.deployer.K8sClient")
    @patch("nv_config_manager_installer.deployer.shutil.which", return_value="/usr/bin/kubectl")
    def test_device_creds_skipped_when_temporal_disabled(
        self, mock_which, mock_k8s_cls, mock_run, mock_run_logged
    ):
        mock_k8s = _mock_k8s()
        mock_k8s_cls.return_value = mock_k8s
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mock_run_logged.return_value = MagicMock(returncode=0, stdout="", stderr="")

        config = _make_config()
        config.services = ServicesConfig(temporal=False)
        cb = RecordingCallback()
        deployer = Deployer(config, DeployOptions(dry_run=True), cb)
        deployer.run()

        secret_names = [call.args[0] for call in mock_k8s.apply_secret.call_args_list]
        assert not any("device-creds" in n for n in secret_names)
