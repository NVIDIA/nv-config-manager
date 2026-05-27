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
"""SPIFFE configuration screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Input, Label, RadioButton, RadioSet

from nv_config_manager_installer.schema import (
    NVConfigManagerInstallConfig,
    SPIFFEAuthMode,
    SPIFFEProvider,
)
from nv_config_manager_installer.tui.widgets import LabeledSwitch

_W_ENABLED = "#spiffe-enabled"
_W_TRUST_DOMAIN = "#spiffe-trust-domain"
_W_TELEPORT = "#spiffe-teleport"


class _GroupPrefixRow(Horizontal):
    """A single prefix=group mapping row."""

    def __init__(self, prefix: str, group: str, index: int, **kwargs: object) -> None:
        super().__init__(**kwargs, classes="compact-field-row")
        self._prefix = prefix
        self._group = group
        self._index = index

    def compose(self) -> ComposeResult:
        idx = self._index
        with Vertical(classes="compact-field"):
            yield Label("SPIFFE ID Prefix", classes="field-label-compact")
            yield Input(
                value=self._prefix,
                placeholder="spiffe://domain/ns/nv-config-manager",
                id=f"gp-{idx}-prefix",
            )
        with Vertical(classes="compact-field"):
            yield Label("Group", classes="field-label-compact")
            yield Input(value=self._group, placeholder="nv-config-manager", id=f"gp-{idx}-group")
        yield Button(
            "Remove", variant="error", id=f"gp-{idx}-remove", classes="remove-button-inline"
        )

    def collect(self) -> str:
        prefix = self.query_one(f"#gp-{self._index}-prefix", Input).value.strip()
        group = self.query_one(f"#gp-{self._index}-group", Input).value.strip()
        if prefix and group:
            return f"{prefix}={group}"
        return ""


class SPIFFEScreen(Container):
    """SPIFFE settings: provider, auth mode, trust domain, group prefixes."""

    def __init__(self, config: NVConfigManagerInstallConfig, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._config = config

    def compose(self) -> ComposeResult:
        sp = self._config.spiffe
        yield Label("SPIFFE Authentication", classes="section-title")
        yield Label("─" * 40, classes="section-divider")

        yield LabeledSwitch("Enable SPIFFE", value=sp.enabled, id="spiffe-enabled")

        with Container(id="spiffe-fields"):
            yield Label("Provider", classes="field-label")
            with RadioSet(id="spiffe-provider"):
                yield RadioButton(
                    "SPIRE (CSI driver)",
                    value=sp.provider == SPIFFEProvider.SPIRE,
                    id="spiffe-spire",
                )
                yield RadioButton(
                    "Teleport (Machine ID)",
                    value=sp.provider == SPIFFEProvider.TELEPORT,
                    id="spiffe-teleport",
                )

            yield Label("Auth Mode", classes="field-label")
            with RadioSet(id="spiffe-auth-mode"):
                yield RadioButton(
                    "JWT-SVID",
                    value=sp.auth_mode == SPIFFEAuthMode.JWT,
                    id="spiffe-jwt",
                )
                yield RadioButton(
                    "mTLS (X.509-SVID)",
                    value=sp.auth_mode == SPIFFEAuthMode.MTLS,
                    id="spiffe-mtls",
                )

            yield Label("Trust Domain", classes="field-label")
            yield Input(
                value=sp.trust_domain, placeholder="e.g. example.com", id="spiffe-trust-domain"
            )

            yield Label("Socket Mount Path", classes="field-label")
            yield Input(value=sp.socket_mount_path, id="spiffe-socket-mount")

            yield Label("Socket File", classes="field-label")
            yield Input(value=sp.socket_file, id="spiffe-socket-file")

            with Container(id="spiffe-teleport-fields"):
                yield Label("Socket Host Path (Teleport only)", classes="field-label")
                yield Input(value=sp.socket_host_path, id="spiffe-socket-host")

            yield Label("Group Prefix Mappings", classes="field-label")
            yield Label(
                "Map SPIFFE ID prefixes to authorization groups. "
                "Callers whose SPIFFE ID matches a prefix are granted the mapped group.",
            )
            with Horizontal(classes="compact-field-row"):
                yield Button("+ Add Mapping", id="gp-add", classes="add-button")
                yield Button(
                    "Auto-generate Default",
                    id="gp-auto",
                    variant="primary",
                    classes="add-button",
                )
            yield Vertical(id="gp-list")

    def on_mount(self) -> None:
        self._toggle_spiffe_fields()
        self._toggle_teleport_fields()
        self._rebuild_gp_rows()

    def on_labeled_switch_changed(self, event: LabeledSwitch.Changed) -> None:
        if event.labeled_switch.id == "spiffe-enabled":
            self._toggle_spiffe_fields()

    def on_radio_set_changed(self, event: RadioSet.Changed) -> None:
        if event.radio_set.id == "spiffe-provider":
            self._toggle_teleport_fields()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id or ""
        if bid == "gp-add":
            self._collect_group_prefixes()
            self._config.spiffe.group_prefixes.append("=")
            self._rebuild_gp_rows()
        elif bid == "gp-auto":
            self._collect_group_prefixes()
            domain = self.query_one(_W_TRUST_DOMAIN, Input).value.strip()
            ns = self._config.cluster.namespace or "nv-config-manager"
            if domain:
                default = f"spiffe://{domain}/ns/{ns}=nv-config-manager"
                existing = set(self._config.spiffe.group_prefixes)
                if default not in existing:
                    self._config.spiffe.group_prefixes.append(default)
                    self._rebuild_gp_rows()
        elif bid.startswith("gp-") and bid.endswith("-remove"):
            self._collect_group_prefixes()
            parts = bid.split("-")
            try:
                idx = int(parts[1])
                if 0 <= idx < len(self._config.spiffe.group_prefixes):
                    self._config.spiffe.group_prefixes.pop(idx)
            except (ValueError, IndexError):
                pass
            self._rebuild_gp_rows()

    def _toggle_spiffe_fields(self) -> None:
        enabled = self.query_one(_W_ENABLED, LabeledSwitch).value
        self.query_one("#spiffe-fields").display = enabled

    def _toggle_teleport_fields(self) -> None:
        is_teleport = self.query_one(_W_TELEPORT, RadioButton).value
        self.query_one("#spiffe-teleport-fields").display = is_teleport

    def _rebuild_gp_rows(self) -> None:
        container = self.query_one("#gp-list", Vertical)
        container.remove_children()
        for i, entry in enumerate(self._config.spiffe.group_prefixes):
            if "=" in entry:
                prefix, group = entry.split("=", 1)
            else:
                prefix, group = entry, ""
            container.mount(_GroupPrefixRow(prefix, group, i))

    def _collect_group_prefixes(self) -> None:
        rows = self.query(_GroupPrefixRow)
        self._config.spiffe.group_prefixes = [val for row in rows if (val := row.collect())]

    def write_to_config(self, config: NVConfigManagerInstallConfig) -> None:
        config.spiffe.enabled = self.query_one(_W_ENABLED, LabeledSwitch).value

        if self.query_one(_W_TELEPORT, RadioButton).value:
            config.spiffe.provider = SPIFFEProvider.TELEPORT
        else:
            config.spiffe.provider = SPIFFEProvider.SPIRE

        if self.query_one("#spiffe-mtls", RadioButton).value:
            config.spiffe.auth_mode = SPIFFEAuthMode.MTLS
        else:
            config.spiffe.auth_mode = SPIFFEAuthMode.JWT

        config.spiffe.trust_domain = self.query_one(_W_TRUST_DOMAIN, Input).value
        config.spiffe.socket_mount_path = self.query_one("#spiffe-socket-mount", Input).value
        config.spiffe.socket_file = self.query_one("#spiffe-socket-file", Input).value
        config.spiffe.socket_host_path = self.query_one("#spiffe-socket-host", Input).value
        self._collect_group_prefixes()
        config.spiffe.group_prefixes = list(self._config.spiffe.group_prefixes)

    def sync_from_config(self, config: NVConfigManagerInstallConfig) -> None:
        sp = config.spiffe
        self.query_one(_W_ENABLED, LabeledSwitch).value = sp.enabled
        self.query_one(_W_TRUST_DOMAIN, Input).value = sp.trust_domain
        self.query_one("#spiffe-socket-mount", Input).value = sp.socket_mount_path
        self.query_one("#spiffe-socket-file", Input).value = sp.socket_file
        self.query_one("#spiffe-socket-host", Input).value = sp.socket_host_path

        self.query_one("#spiffe-spire", RadioButton).value = sp.provider == SPIFFEProvider.SPIRE
        self.query_one(_W_TELEPORT, RadioButton).value = sp.provider == SPIFFEProvider.TELEPORT
        self.query_one("#spiffe-jwt", RadioButton).value = sp.auth_mode == SPIFFEAuthMode.JWT
        self.query_one("#spiffe-mtls", RadioButton).value = sp.auth_mode == SPIFFEAuthMode.MTLS

        self._config.spiffe.group_prefixes = list(sp.group_prefixes)
        self._rebuild_gp_rows()
        self._toggle_spiffe_fields()
        self._toggle_teleport_fields()

    def get_status(self, config: NVConfigManagerInstallConfig) -> str:
        if not config.spiffe.enabled:
            return "[*]"
        if config.spiffe.trust_domain:
            return "[*]"
        return "[!]"
