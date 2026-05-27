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
"""Render Service configuration screen."""

from __future__ import annotations

from textual import work
from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Button, Input, Label, RadioButton, RadioSet
from textual_fspicker import SelectDirectory

from nv_config_manager_installer.schema import NVConfigManagerInstallConfig, TemplatePath
from nv_config_manager_installer.tui.screens.node_picker import NodeSelectorPanel


class RenderScreen(Container):
    """Render Service: toggle, template plugins, PVC storage, and node scheduling."""

    def __init__(self, config: NVConfigManagerInstallConfig, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._config = config

    def compose(self) -> ComposeResult:
        tpc = self._config.content.template_plugins_config
        yield Label("Template Plugins", classes="section-title")
        yield Label("─" * 40, classes="section-divider")

        yield Label("Template plugin paths", classes="field-label")
        yield Label(
            "Paths to template plugin directories or .tar.gz files",
            classes="section-divider",
        )
        yield Button("+ Add Template Plugin", id="render-add-tpl", classes="add-button")
        yield Vertical(id="render-tpl-list")

        yield Label("Plugin PVC Storage Class (optional)", classes="field-label")
        yield Input(
            value=tpc.storage_class,
            placeholder="e.g. nfs-client  (leave empty for cluster default)",
            id="render-storage-class",
        )

        yield Label("Plugin PVC Access Mode", classes="field-label")
        with RadioSet(id="render-access-mode"):
            yield RadioButton(
                "ReadWriteOnce  (single-node, no NFS required)",
                value=tpc.access_mode != "ReadWriteMany",
                id="render-access-rwo",
            )
            yield RadioButton(
                "ReadWriteMany  (multi-node, requires NFS or RWX storage class)",
                value=tpc.access_mode == "ReadWriteMany",
                id="render-access-rwx",
            )

        yield NodeSelectorPanel("render", tpc.node_selector, id="render-node-selector")

    def on_mount(self) -> None:
        self._rebuild_tpl_list()

    def _rebuild_tpl_list(self) -> None:
        container = self.query_one("#render-tpl-list", Vertical)
        container.remove_children()
        for i, tp in enumerate(self._config.content.template_plugins):
            row = Container(classes="account-card")
            row.compose_add_child(
                Input(value=tp.path, placeholder="/path/to/plugin", id=f"render-tpl-{i}-path")
            )
            row.compose_add_child(
                Button(
                    "Remove",
                    variant="error",
                    id=f"render-tpl-{i}-remove",
                    classes="remove-button",
                )
            )
            container.mount(row)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        self._collect_all()
        if bid == "render-add-tpl":
            self._pick_tpl_path()
        elif bid.startswith("render-tpl-") and bid.endswith("-remove"):
            try:
                idx = int(bid.split("-")[2])
                if 0 <= idx < len(self._config.content.template_plugins):
                    self._config.content.template_plugins.pop(idx)
            except (ValueError, IndexError):
                pass
            self._rebuild_tpl_list()

    @work
    async def _pick_tpl_path(self) -> None:
        dialog = SelectDirectory(title="Select template plugin directory")
        picked = await self.app.push_screen_wait(dialog)
        if picked is None:
            return
        self._collect_all()
        self._config.content.template_plugins.append(TemplatePath(path=str(picked)))
        self._rebuild_tpl_list()

    def _collect_all(self) -> None:
        tpls: list[TemplatePath] = []
        for i in range(len(self._config.content.template_plugins)):
            try:
                path = self.query_one(f"#render-tpl-{i}-path", Input).value
                tpls.append(TemplatePath(path=path))
            except Exception:
                break
        self._config.content.template_plugins = tpls

        tpc = self._config.content.template_plugins_config
        try:
            tpc.storage_class = self.query_one("#render-storage-class", Input).value.strip()
            tpc.access_mode = (
                "ReadWriteMany"
                if self.query_one("#render-access-rwx", RadioButton).value
                else "ReadWriteOnce"
            )
            tpc.node_selector = self.query_one("#render-node-selector", NodeSelectorPanel).collect()
        except Exception:
            pass

    def write_to_config(self, config: NVConfigManagerInstallConfig) -> None:
        self._collect_all()
        config.content.template_plugins = list(self._config.content.template_plugins)
        config.content.template_plugins_config = (
            self._config.content.template_plugins_config.model_copy()
        )

    def sync_from_config(self, config: NVConfigManagerInstallConfig) -> None:
        self._config = config
        self._rebuild_tpl_list()
        tpc = config.content.template_plugins_config
        try:
            self.query_one("#render-storage-class", Input).value = tpc.storage_class
            self.query_one("#render-access-rwo", RadioButton).value = (
                tpc.access_mode != "ReadWriteMany"
            )
            self.query_one("#render-access-rwx", RadioButton).value = (
                tpc.access_mode == "ReadWriteMany"
            )
            self.query_one("#render-node-selector", NodeSelectorPanel).set_selector(
                tpc.node_selector
            )
        except Exception:
            pass

    def get_status(self, config: NVConfigManagerInstallConfig) -> str:
        return "[*]" if config.services.render else "[ ]"
