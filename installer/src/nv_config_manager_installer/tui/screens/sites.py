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
"""Sites configuration screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Button, Input, Label

from nv_config_manager_installer.schema import (
    NVConfigManagerInstallConfig,
    SecretsMethod,
    SiteConfig,
)


class SiteRow(Container):
    """Editable row for a single site."""

    def __init__(
        self, site: SiteConfig, index: int, *, eso_mode: bool = False, **kwargs: object
    ) -> None:
        super().__init__(**kwargs, classes="account-card")
        self._site = site
        self._index = index
        self._eso_mode = eso_mode

    def compose(self) -> ComposeResult:
        prefix = f"site-{self._index}"
        yield Label(f"Site {self._index + 1}", classes="account-header")

        yield Label("Name", classes="field-label")
        yield Input(value=self._site.name, placeholder="dc01", id=f"{prefix}-name")

        if self._eso_mode:
            with Container(id=f"{prefix}-vault-path-group"):
                yield Label("Vault Path", classes="field-label")
                yield Input(
                    value=self._site.vault_path,
                    placeholder="prod/site/dc01/config_secrets",
                    id=f"{prefix}-vault-path",
                )

        yield Button("Remove", variant="error", id=f"{prefix}-remove", classes="remove-button")

    def collect(self) -> SiteConfig:
        """Read widget values."""
        prefix = f"site-{self._index}"
        vault_path = ""
        if self._eso_mode:
            try:
                vault_path = self.query_one(f"#{prefix}-vault-path", Input).value
            except Exception:
                pass
        return SiteConfig(
            name=self.query_one(f"#{prefix}-name", Input).value,
            vault_path=vault_path,
        )


class SitesScreen(Container):
    """Sites / data centers that NVIDIA Config Manager manages."""

    def __init__(self, config: NVConfigManagerInstallConfig, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._config = config

    @property
    def _eso_mode(self) -> bool:
        return self._config.secrets.method == SecretsMethod.ESO

    def compose(self) -> ComposeResult:
        yield Label("Sites", classes="section-title")
        yield Label("─" * 40, classes="section-divider")
        yield Label("Define the sites (data centers) this deployment manages.")

        yield Button("+ Add Site", id="add-site", classes="add-button")
        yield Vertical(id="sites-list")

    def on_mount(self) -> None:
        """Populate site rows."""
        self._rebuild_rows()

    def _rebuild_rows(self) -> None:
        container = self.query_one("#sites-list", Vertical)
        container.remove_children()
        for i, site in enumerate(self._config.sites):
            container.mount(SiteRow(site, i, eso_mode=self._eso_mode))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle add/remove."""
        if event.button.id == "add-site":
            self._collect_all()
            self._config.sites.append(SiteConfig(name=""))
            self._rebuild_rows()
        elif event.button.id and event.button.id.endswith("-remove"):
            self._collect_all()
            parts = event.button.id.split("-")
            try:
                idx = int(parts[1])
                if 0 <= idx < len(self._config.sites):
                    self._config.sites.pop(idx)
            except (ValueError, IndexError):
                pass
            self._rebuild_rows()

    def _collect_all(self) -> None:
        rows = self.query(SiteRow)
        self._config.sites = [row.collect() for row in rows]

    def write_to_config(self, config: NVConfigManagerInstallConfig) -> None:
        self._collect_all()
        config.sites = list(self._config.sites)

    def sync_from_config(self, config: NVConfigManagerInstallConfig) -> None:
        self._config = config
        self._rebuild_rows()

    def get_status(self, config: NVConfigManagerInstallConfig) -> str:
        if not config.sites:
            return "[ ]"
        if all(s.name for s in config.sites):
            return "[*]"
        return "[!]"
