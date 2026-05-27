# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0
"""Tests for nv_config_manager_installer.cli -- Click command validation."""

from __future__ import annotations

import tempfile
from pathlib import Path

from click.testing import CliRunner

from nv_config_manager_installer.cli import main
from nv_config_manager_installer.schema import (
    ClusterConfig,
    NVConfigManagerInstallConfig,
    SiteConfig,
)


class TestValidateCommand:
    def test_validate_valid_config(self):
        config = NVConfigManagerInstallConfig(
            cluster=ClusterConfig(hostname="test.example.com"),
            sites=[SiteConfig(name="dc01")],
        )

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            path = Path(f.name)
            config.to_yaml(path)

        try:
            runner = CliRunner()
            result = runner.invoke(main, ["validate", str(path)])
            assert result.exit_code == 0
            assert "valid" in result.output.lower()
        finally:
            path.unlink(missing_ok=True)

    def test_validate_missing_hostname(self):
        config = NVConfigManagerInstallConfig(
            sites=[SiteConfig(name="dc01")],
        )

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            path = Path(f.name)
            config.to_yaml(path)

        try:
            runner = CliRunner()
            result = runner.invoke(main, ["validate", str(path)])
            assert result.exit_code != 0
            assert "hostname" in result.output.lower()
        finally:
            path.unlink(missing_ok=True)

    def test_validate_missing_sites(self):
        config = NVConfigManagerInstallConfig(
            cluster=ClusterConfig(hostname="test.example.com"),
        )

        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False, mode="w") as f:
            path = Path(f.name)
            config.to_yaml(path)

        try:
            runner = CliRunner()
            result = runner.invoke(main, ["validate", str(path)])
            assert result.exit_code != 0
            assert "site" in result.output.lower()
        finally:
            path.unlink(missing_ok=True)

    def test_version(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "nv-config-manager-installer" in result.output

    def test_generate_values_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["generate-values", "--help"])
        assert result.exit_code == 0
        assert "--chart-dir" in result.output


class TestDeployCommand:
    def test_deploy_missing_config(self):
        runner = CliRunner()
        result = runner.invoke(main, ["deploy", "/nonexistent/config.yaml"])
        assert result.exit_code != 0

    def test_deploy_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["deploy", "--help"])
        assert result.exit_code == 0
        assert "--chart-dir" in result.output
        assert "--build-images" in result.output
        assert "--load-kind" in result.output
        assert "--dry-run" in result.output
        assert "--helm-timeout" in result.output
