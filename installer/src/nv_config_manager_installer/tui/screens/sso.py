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
"""SSO / OIDC configuration screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Input, Label, RadioButton, RadioSet

from nv_config_manager_installer.schema import (
    JWTProvider,
    NVConfigManagerInstallConfig,
    SSOProvider,
)
from nv_config_manager_installer.tui.widgets import LabeledSwitch

_W_ENABLED = "#sso-enabled"


class _JWTProviderCard(Vertical):
    """Editable card for one additional JWT provider."""

    def __init__(self, provider: JWTProvider, index: int, **kwargs: object) -> None:
        super().__init__(**kwargs, classes="account-card")
        self._provider = provider
        self._index = index

    def compose(self) -> ComposeResult:
        p = self._provider
        pfx = f"jwt-{self._index}"
        with Horizontal(classes="account-title-row"):
            yield Label(f"Provider {self._index + 1}", classes="account-header")
            yield Button(
                "Remove", variant="error", id=f"{pfx}-remove", classes="remove-button-inline"
            )
        with Horizontal(classes="compact-field-row"):
            with Vertical(classes="compact-field"):
                yield Label("Name", classes="field-label-compact")
                yield Input(value=p.name, placeholder="e.g. spire", id=f"{pfx}-name")
            with Vertical(classes="compact-field"):
                yield Label("Issuer URL", classes="field-label-compact")
                yield Input(value=p.issuer, placeholder="https://...", id=f"{pfx}-issuer")
        with Horizontal(classes="compact-field-row"):
            with Vertical(classes="compact-field"):
                yield Label("Audiences (comma-separated, optional)", classes="field-label-compact")
                yield Input(value=p.audiences, placeholder="", id=f"{pfx}-audiences")
            with Vertical(classes="compact-field"):
                yield Label("JWKS URI (optional, auto-derived)", classes="field-label-compact")
                yield Input(value=p.jwks_uri, placeholder="", id=f"{pfx}-jwks-uri")

    def collect(self) -> JWTProvider:
        pfx = f"jwt-{self._index}"
        return JWTProvider(
            name=self.query_one(f"#{pfx}-name", Input).value,
            issuer=self.query_one(f"#{pfx}-issuer", Input).value,
            audiences=self.query_one(f"#{pfx}-audiences", Input).value,
            jwks_uri=self.query_one(f"#{pfx}-jwks-uri", Input).value,
        )


class SSOScreen(Container):
    """SSO settings: provider, issuer URL, client ID."""

    def __init__(self, config: NVConfigManagerInstallConfig, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._config = config

    def compose(self) -> ComposeResult:
        sso = self._config.sso
        yield Label("SSO Configuration", classes="section-title")
        yield Label("─" * 40, classes="section-divider")

        yield LabeledSwitch("Enable SSO", value=sso.enabled, id="sso-enabled")

        with Container(id="sso-fields"):
            yield Label("Provider", classes="field-label")
            with RadioSet(id="sso-provider"):
                yield RadioButton(
                    "keycloak",
                    value=sso.provider == SSOProvider.KEYCLOAK,
                    id="sso-keycloak",
                )
                yield RadioButton("azure", value=sso.provider == SSOProvider.AZURE, id="sso-azure")
                yield RadioButton(
                    "generic", value=sso.provider == SSOProvider.GENERIC, id="sso-generic"
                )

            yield Label("Issuer URL", classes="field-label")
            yield Input(
                value=sso.issuer_url,
                placeholder="https://keycloak.example.com/realms/nv-config-manager",
                id="sso-issuer-url",
            )

            yield Label("Client ID", classes="field-label")
            yield Input(value=sso.client_id, placeholder="OIDC client ID", id="sso-client-id")

            yield Label("CLI Client ID (optional)", classes="field-label")
            yield Input(
                value=sso.cli_client_id,
                placeholder="Defaults to client ID",
                id="sso-cli-client-id",
            )

            yield Label("Client Secret", classes="field-label")
            yield Input(
                value=sso.client_secret,
                placeholder="OIDC client secret",
                id="sso-client-secret",
                password=True,
            )

            yield Label("JWKS URI (optional, auto-derived)", classes="field-label")
            yield Input(value=sso.jwks_uri, placeholder="", id="sso-jwks-uri")

            yield Label("Audiences (comma-separated, optional)", classes="field-label")
            yield Input(value=sso.audiences, placeholder="", id="sso-audiences")

            yield Label("Scopes (comma-separated, optional)", classes="field-label")
            yield Input(value=sso.scopes, placeholder="", id="sso-scopes")

            yield Label("─" * 40, classes="section-divider")
            yield Label("Additional JWT Providers", classes="section-title")
            yield Label(
                "Add extra JWT issuers the gateway should accept beyond the primary OIDC "
                "provider (e.g. SPIRE workload identity, external service accounts).",
            )
            yield Button("+ Add Provider", id="add-jwt-provider", classes="add-button")
            yield Vertical(id="jwt-provider-list")

    def on_mount(self) -> None:
        self._toggle_sso_fields()
        self._rebuild_jwt_cards()

    def _rebuild_jwt_cards(self) -> None:
        container = self.query_one("#jwt-provider-list", Vertical)
        container.remove_children()
        for i, p in enumerate(self._config.sso.jwt_providers):
            container.mount(_JWTProviderCard(p, i))

    def _collect_jwt_providers(self) -> None:
        self._config.sso.jwt_providers = [c.collect() for c in self.query(_JWTProviderCard)]

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "add-jwt-provider":
            self._collect_jwt_providers()
            self._config.sso.jwt_providers.append(JWTProvider())
            self._rebuild_jwt_cards()
        elif event.button.id and event.button.id.endswith("-remove"):
            self._collect_jwt_providers()
            parts = event.button.id.split("-")
            try:
                idx = int(parts[1])
                if 0 <= idx < len(self._config.sso.jwt_providers):
                    self._config.sso.jwt_providers.pop(idx)
            except (ValueError, IndexError):
                pass
            self._rebuild_jwt_cards()

    def on_labeled_switch_changed(self, event: LabeledSwitch.Changed) -> None:
        if event.labeled_switch.id == "sso-enabled":
            self._toggle_sso_fields()

    def _toggle_sso_fields(self) -> None:
        enabled = self.query_one(_W_ENABLED, LabeledSwitch).value
        self.query_one("#sso-fields").display = enabled

    def write_to_config(self, config: NVConfigManagerInstallConfig) -> None:
        config.sso.enabled = self.query_one(_W_ENABLED, LabeledSwitch).value

        if self.query_one("#sso-azure", RadioButton).value:
            config.sso.provider = SSOProvider.AZURE
        elif self.query_one("#sso-generic", RadioButton).value:
            config.sso.provider = SSOProvider.GENERIC
        else:
            config.sso.provider = SSOProvider.KEYCLOAK

        config.sso.issuer_url = self.query_one("#sso-issuer-url", Input).value
        config.sso.client_id = self.query_one("#sso-client-id", Input).value
        config.sso.cli_client_id = self.query_one("#sso-cli-client-id", Input).value
        config.sso.client_secret = self.query_one("#sso-client-secret", Input).value
        config.sso.jwks_uri = self.query_one("#sso-jwks-uri", Input).value
        config.sso.audiences = self.query_one("#sso-audiences", Input).value
        config.sso.scopes = self.query_one("#sso-scopes", Input).value
        self._collect_jwt_providers()
        config.sso.jwt_providers = list(self._config.sso.jwt_providers)

    def sync_from_config(self, config: NVConfigManagerInstallConfig) -> None:
        sso = config.sso
        self._config = config
        self.query_one(_W_ENABLED, LabeledSwitch).value = sso.enabled

        self.query_one("#sso-keycloak", RadioButton).value = sso.provider == SSOProvider.KEYCLOAK
        self.query_one("#sso-azure", RadioButton).value = sso.provider == SSOProvider.AZURE
        self.query_one("#sso-generic", RadioButton).value = sso.provider == SSOProvider.GENERIC

        self.query_one("#sso-issuer-url", Input).value = sso.issuer_url
        self.query_one("#sso-client-id", Input).value = sso.client_id
        self.query_one("#sso-cli-client-id", Input).value = sso.cli_client_id
        self.query_one("#sso-client-secret", Input).value = sso.client_secret
        self.query_one("#sso-jwks-uri", Input).value = sso.jwks_uri
        self.query_one("#sso-audiences", Input).value = sso.audiences
        self.query_one("#sso-scopes", Input).value = sso.scopes
        self._toggle_sso_fields()
        self._rebuild_jwt_cards()

    def get_status(self, config: NVConfigManagerInstallConfig) -> str:
        if not config.sso.enabled:
            return "[*]"
        if config.sso.issuer_url and config.sso.client_id and config.sso.client_secret:
            return "[*]"
        return "[!]"
