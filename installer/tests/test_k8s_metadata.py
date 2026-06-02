# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0
"""Tests for installer provenance metadata stamped onto direct-API resources.

Every Kubernetes object the installer creates outside of Helm should carry a
consistent set of ``app.kubernetes.io/*`` labels and a
``nv-config-manager.nvidia.com/installer-version`` annotation so users can find
and clean up installer-managed resources with simple label selectors.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from kubernetes.client.rest import ApiException

from nv_config_manager_installer import __version__
from nv_config_manager_installer.k8s import (
    ANNOTATION_INSTALLER_VERSION,
    INSTALLER_VALUE,
    LABEL_INSTALLER,
    LABEL_INSTANCE,
    LABEL_MANAGED_BY,
    LABEL_PART_OF,
    MANAGED_BY_VALUE,
    PART_OF_VALUE,
    K8sClient,
    nv_config_manager_helm_common_labels,
)


def _make_client(release_name: str | None = "nv-config-manager") -> K8sClient:
    """Construct a K8sClient without touching kubeconfig or the API."""
    obj = K8sClient.__new__(K8sClient)
    obj.v1 = MagicMock()
    obj.apps_v1 = MagicMock()
    obj.active_context = "test-context"
    obj.api_server = "https://test.example.com"
    obj._release_name = release_name
    obj._installer_version = __version__
    return obj


def _assert_installer_metadata(
    meta, *, name: str, namespace: str | None, instance: str | None
) -> None:
    assert meta.name == name
    assert meta.namespace == namespace
    assert meta.labels[LABEL_MANAGED_BY] == MANAGED_BY_VALUE
    assert meta.labels[LABEL_PART_OF] == PART_OF_VALUE
    assert meta.labels[LABEL_INSTALLER] == INSTALLER_VALUE
    if instance is None:
        assert LABEL_INSTANCE not in meta.labels
    else:
        assert meta.labels[LABEL_INSTANCE] == instance
    assert meta.annotations[ANNOTATION_INSTALLER_VERSION] == __version__


class TestObjectMeta:
    def test_includes_managed_by_and_part_of_labels(self):
        client = _make_client(release_name=None)
        meta = client._object_meta("foo")

        _assert_installer_metadata(meta, name="foo", namespace=None, instance=None)

    def test_includes_instance_label_when_release_known(self):
        client = _make_client(release_name="my-release")
        meta = client._object_meta("foo", "nvcm")

        _assert_installer_metadata(meta, name="foo", namespace="nvcm", instance="my-release")

    def test_omits_instance_label_when_release_blank(self):
        client = _make_client(release_name="")
        meta = client._object_meta("foo")

        assert LABEL_INSTANCE not in meta.labels


class TestNamespaceMetadata:
    def test_create_namespace_stamps_installer_labels(self):
        client = _make_client()
        client.create_namespace("nvcm")

        body = client.v1.create_namespace.call_args.args[0]
        _assert_installer_metadata(
            body.metadata, name="nvcm", namespace=None, instance="nv-config-manager"
        )


class TestSecretMetadata:
    def test_apply_secret_stamps_installer_labels(self):
        client = _make_client()
        client.apply_secret("creds", "nvcm", {"key": "value"})

        body = client.v1.create_namespaced_secret.call_args.args[1]
        _assert_installer_metadata(
            body.metadata, name="creds", namespace="nvcm", instance="nv-config-manager"
        )

    def test_apply_secret_replace_path_stamps_installer_labels(self):
        # On 409 the client falls back to replace_namespaced_secret and the
        # body it sends must still carry installer provenance.
        client = _make_client()
        client.v1.create_namespaced_secret.side_effect = ApiException(status=409)

        client.apply_secret("creds", "nvcm", {"key": "value"})

        body = client.v1.replace_namespaced_secret.call_args.args[2]
        _assert_installer_metadata(
            body.metadata, name="creds", namespace="nvcm", instance="nv-config-manager"
        )

    def test_apply_docker_registry_secret_stamps_installer_labels(self):
        client = _make_client()
        client.apply_docker_registry_secret(
            "regcred", "nvcm", "registry.example.com", "user", "pass"
        )

        body = client.v1.create_namespaced_secret.call_args.args[1]
        _assert_installer_metadata(
            body.metadata, name="regcred", namespace="nvcm", instance="nv-config-manager"
        )

    def test_apply_file_secret_stamps_installer_labels(self):
        client = _make_client()
        client.apply_file_secret("certs", "nvcm", {"ca.crt": b"---PEM---"})

        body = client.v1.create_namespaced_secret.call_args.args[1]
        _assert_installer_metadata(
            body.metadata, name="certs", namespace="nvcm", instance="nv-config-manager"
        )


class TestPVCMetadata:
    def test_ensure_pvc_stamps_installer_labels_on_create(self):
        client = _make_client()
        client.v1.read_namespaced_persistent_volume_claim.side_effect = ApiException(status=404)

        created = client.ensure_pvc("data", "nvcm", size="1Gi")

        assert created is True
        body = client.v1.create_namespaced_persistent_volume_claim.call_args.args[1]
        _assert_installer_metadata(
            body.metadata, name="data", namespace="nvcm", instance="nv-config-manager"
        )


class TestLoaderPodMetadata:
    def test_create_loader_pod_stamps_installer_labels(self):
        client = _make_client()
        client.create_loader_pod("loader", "nvcm", "data-pvc", "/data")

        body = client.v1.create_namespaced_pod.call_args.args[1]
        _assert_installer_metadata(
            body.metadata, name="loader", namespace="nvcm", instance="nv-config-manager"
        )


class TestVersionAnnotation:
    def test_default_installer_version_matches_package(self):
        client = _make_client()
        meta = client._object_meta("foo")
        assert meta.annotations[ANNOTATION_INSTALLER_VERSION] == __version__

    def test_explicit_installer_version_override(self):
        obj = _make_client()
        obj._installer_version = "9.9.9-test"
        meta = obj._object_meta("foo")
        assert meta.annotations[ANNOTATION_INSTALLER_VERSION] == "9.9.9-test"


class TestHelmCommonLabels:
    def test_returns_installer_marker(self):
        labels = nv_config_manager_helm_common_labels()
        assert labels[LABEL_INSTALLER] == INSTALLER_VALUE
        assert labels[LABEL_PART_OF] == PART_OF_VALUE

    def test_excludes_managed_by_to_avoid_helm_conflict(self):
        # Helm itself owns ``app.kubernetes.io/managed-by`` on chart-rendered
        # resources (sets it to "Helm"). Including it in commonLabels would
        # either be overridden or cause a conflict, so it must be omitted.
        labels = nv_config_manager_helm_common_labels()
        assert LABEL_MANAGED_BY not in labels


@pytest.mark.parametrize(
    "label",
    [LABEL_MANAGED_BY, LABEL_PART_OF, LABEL_INSTALLER],
)
def test_required_labels_present_on_every_create_method(label):
    """Smoke test: every direct-API create method must stamp the core labels.

    Guards against regressions where a new ``V1ObjectMeta(...)`` call site
    forgets to route through ``_object_meta``.
    """
    client = _make_client()
    client.v1.read_namespaced_persistent_volume_claim.side_effect = ApiException(status=404)

    client.create_namespace("ns")
    client.apply_secret("s1", "ns", {"k": "v"})
    client.apply_docker_registry_secret("s2", "ns", "r.io", "u", "p")
    client.apply_file_secret("s3", "ns", {"f": b"x"})
    client.ensure_pvc("pvc1", "ns")
    client.create_loader_pod("pod1", "ns", "pvc1", "/m")

    bodies = [
        client.v1.create_namespace.call_args.args[0],
        client.v1.create_namespaced_secret.call_args_list[0].args[1],
        client.v1.create_namespaced_secret.call_args_list[1].args[1],
        client.v1.create_namespaced_secret.call_args_list[2].args[1],
        client.v1.create_namespaced_persistent_volume_claim.call_args.args[1],
        client.v1.create_namespaced_pod.call_args.args[1],
    ]
    for body in bodies:
        assert label in body.metadata.labels, f"{label} missing on {body}"
