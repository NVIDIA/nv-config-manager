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
"""NVIDIA Config Manager Installer CLI -- Click entry point.

Commands:
    init              Launch the TUI wizard (or load an existing config to edit)
    validate          Validate a nv-config-manager-install.yaml config file
    generate-values   Generate Helm values and config-secrets.ini
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import click

from nv_config_manager_installer import __version__

if TYPE_CHECKING:
    from nv_config_manager_installer.schema import NVConfigManagerInstallConfig


@click.group()
@click.version_option(version=__version__, prog_name="nv-config-manager-installer")
def main() -> None:
    """NVIDIA Config Manager Install Wizard."""


@main.command()
@click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=Path("nv-config-manager-install.yaml"),
    help="Path to nv-config-manager-install.yaml (created if it doesn't exist, pre-populated if it does).",
)
def init(config_path: Path) -> None:
    """Launch the interactive TUI wizard."""
    from nv_config_manager_installer.schema import NVConfigManagerInstallConfig
    from nv_config_manager_installer.tui.app import NVConfigManagerInstallerApp

    config = NVConfigManagerInstallConfig()
    if config_path.exists():
        click.echo(f"Loading existing config: {config_path}")
        config = NVConfigManagerInstallConfig.from_yaml(config_path)

    app = NVConfigManagerInstallerApp(config=config, config_path=config_path)
    app.run()


@main.command()
@click.argument(
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
def validate(config_path: Path) -> None:
    """Validate a nv-config-manager-install.yaml config file."""
    from nv_config_manager_installer.schema import NVConfigManagerInstallConfig

    try:
        config = NVConfigManagerInstallConfig.from_yaml(config_path)
    except Exception as exc:
        click.echo(f"ERROR: Failed to parse config: {exc}", err=True)
        sys.exit(1)

    errors = _collect_validation_errors(config)
    if errors:
        click.echo("Validation errors:", err=True)
        for e in errors:
            click.echo(f"  - {e}", err=True)
        sys.exit(1)

    click.echo(f"Config is valid: {config_path}")


def _collect_validation_errors(config: NVConfigManagerInstallConfig) -> list[str]:
    """Return a list of validation error messages for a NVConfigManagerInstallConfig."""
    errors: list[str] = []
    if not config.cluster.hostname:
        errors.append("cluster.hostname is required")
    if not config.sites:
        errors.append("At least one site is required")
    if config.sso.enabled and not config.sso.issuer_url:
        errors.append("sso.issuer_url is required when SSO is enabled")
    if not config.services.nautobot and (
        config.content.jobs or config.content.include_bootstrap_jobs
    ):
        errors.append(
            "Custom jobs require a local Nautobot deployment "
            "(services.nautobot must be true, or remove content.jobs)"
        )
    return errors


@main.command("generate-values")
@click.argument(
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(file_okay=False, path_type=Path),
    default=Path("."),
    help="Directory to write generated files to.",
)
@click.option(
    "--local-images",
    is_flag=True,
    default=False,
    help="Generate values for locally-built images (repository:tag=local, pullPolicy=IfNotPresent).",
)
@click.option(
    "--chart-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Path to the Helm chart directory used for size profile overrides.",
)
def generate_values(
    config_path: Path,
    output_dir: Path,
    local_images: bool,
    chart_dir: Path | None,
) -> None:
    """Generate Helm values from config."""
    from nv_config_manager_installer.helm_values import generate_helm_values
    from nv_config_manager_installer.schema import NVConfigManagerInstallConfig
    from nv_config_manager_installer.secrets import generate_secrets

    config = NVConfigManagerInstallConfig.from_yaml(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    secrets_state = generate_secrets(config)

    values_path = output_dir / "values-generated.yaml"
    generate_helm_values(
        config,
        secrets_state,
        values_path,
        local_images=local_images,
        chart_dir=chart_dir,
    )
    click.echo(f"  Helm values: {values_path}")

    click.echo("Done.")


@main.command()
@click.argument(
    "config_path",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option("--chart-dir", default="deploy/helm", help="Path to the Helm chart directory.")
@click.option(
    "--image-source",
    type=click.Choice(["local", "registry"]),
    default="local",
    help="Image source: 'local' to build locally, 'registry' to pull from the configured registry.",
)
@click.option("--ngc-api-key", default="", help="NGC API key for NVCR registry authentication.")
@click.option("--build-images", is_flag=True, help="Build local Docker images before deploying.")
@click.option("--load-kind", is_flag=True, help="Load images into a Kind cluster.")
@click.option("--kind-cluster", default="nv-config-manager", help="Kind cluster name.")
@click.option("--install-envoy-gateway", is_flag=True, help="Install Envoy Gateway CRDs/operator.")
@click.option("--install-cert-manager", is_flag=True, help="Install cert-manager.")
@click.option("--install-cnpg-operator", is_flag=True, help="Install CNPG operator.")
@click.option("--helm-timeout", default="15m", help="Helm install/upgrade timeout.")
@click.option("--recreate-secrets", is_flag=True, help="Recreate existing K8s secrets.")
@click.option("--dry-run", is_flag=True, help="Generate values only, skip helm install.")
def deploy(
    config_path: Path,
    chart_dir: str,
    image_source: str,
    ngc_api_key: str,
    build_images: bool,
    load_kind: bool,
    kind_cluster: str,
    install_envoy_gateway: bool,
    install_cert_manager: bool,
    install_cnpg_operator: bool,
    helm_timeout: str,
    recreate_secrets: bool,
    dry_run: bool,
) -> None:
    """Deploy NVIDIA Config Manager from a config file (headless, for CI/CD)."""
    from nv_config_manager_installer.deployer import (
        DeployCallback,
        Deployer,
        DeployOptions,
        DeployStep,
    )
    from nv_config_manager_installer.schema import ImageSource, NVConfigManagerInstallConfig

    config = NVConfigManagerInstallConfig.from_yaml(config_path)

    if image_source:
        config.images.source = ImageSource(image_source)
    if ngc_api_key:
        config.images.pull_secret.password = ngc_api_key

    options = DeployOptions(
        chart_dir=chart_dir,
        build_images=build_images,
        load_kind=load_kind,
        kind_cluster=kind_cluster,
        install_envoy_gateway=install_envoy_gateway,
        install_cert_manager=install_cert_manager,
        install_cnpg_operator=install_cnpg_operator,
        helm_timeout=helm_timeout,
        recreate_secrets=recreate_secrets,
        dry_run=dry_run,
    )

    class _CliCallback(DeployCallback):
        def on_step_update(self, step: DeployStep) -> None:
            icon = {
                "pending": "[ ]",
                "running": "[>]",
                "success": "[*]",
                "failed": "[!]",
                "skipped": "[-]",
            }
            click.echo(f"{icon.get(step.status, '[ ]')}  {step.label}")

        def on_log(self, message: str) -> None:
            click.echo(f"  {message}")

        def on_complete(self, success: bool, endpoints: list[str]) -> None:
            if success:
                click.echo("\nDeployment completed successfully!")
                for ep in endpoints:
                    click.echo(f"  {ep}")
            else:
                click.echo("\nDeployment failed.", err=True)

    deployer = Deployer(config, options, _CliCallback())
    success = deployer.run()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
