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
"""Tests for Temporal SDK connection configuration."""

from __future__ import annotations

from pathlib import Path

import pytest

from nv_config_manager.temporal.client.connection import client_connect_options, temporal_address


def test_defaults_use_local_endpoint_and_default_namespace(custom_ini) -> None:
    custom_ini("")

    assert temporal_address() == "localhost:7233"
    assert client_connect_options() == {"namespace": "default"}


def test_mtls_connection_uses_mounted_secret_files(custom_ini, tmp_path: Path) -> None:
    ca = tmp_path / "ca.crt"
    cert = tmp_path / "tls.crt"
    key = tmp_path / "tls.key"
    ca.write_bytes(b"ca")
    cert.write_bytes(b"certificate")
    key.write_bytes(b"private-key")
    custom_ini(
        "[temporal]\n"
        "grpc_service = temporal.example.com:7233\n"
        "namespace = remote\n"
        "tls_enabled = true\n"
        "tls_server_name = temporal.example.com\n"
        f"tls_ca_cert_path = {ca}\n"
        f"tls_client_cert_path = {cert}\n"
        f"tls_client_key_path = {key}\n"
    )

    options = client_connect_options()

    assert temporal_address() == "temporal.example.com:7233"
    assert options["namespace"] == "remote"
    assert options["tls"].server_root_ca_cert == b"ca"
    assert options["tls"].client_cert == b"certificate"
    assert options["tls"].client_private_key == b"private-key"
    assert options["tls"].domain == "temporal.example.com"


def test_mtls_requires_client_certificate_and_key(
    tmp_path: Path,
    custom_ini,
) -> None:
    custom_ini("[temporal]\ntls_enabled = true\n")

    with pytest.raises(ValueError, match="tls_client_cert_path"):
        client_connect_options()

    certificate = tmp_path / "tls.crt"
    certificate.write_bytes(b"certificate")
    custom_ini(f"[temporal]\ntls_enabled = true\ntls_client_cert_path = {certificate}\n")

    with pytest.raises(ValueError, match="tls_client_key_path"):
        client_connect_options()
