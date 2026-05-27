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
"""Secret generation and ESO config building.

Generates installer-managed secrets and passwords for deployments.
For network secrets with source=generate, creates random passwords.
For source=manual, the user must provide values at deploy time (placeholder used).
For source=vault, the value comes from ESO at runtime and is not stored here.
"""

from __future__ import annotations

import secrets
import string
from typing import Any

from nv_config_manager_installer.schema import (
    NVConfigManagerInstallConfig,
    PasswordSource,
    SecretsMethod,
    VaultAuthMethod,
    VaultPathConfig,
    VaultPathsConfig,
)


def _k8s_val(config: NVConfigManagerInstallConfig, group: str, vault_key: str) -> str:
    """Return a manually supplied k8s secret value, or empty string if not set."""
    grp = getattr(config.secrets.k8s, group, None)
    if grp is None or not grp.enabled:
        return ""
    return grp.values.get(vault_key, "")


_CRYPT_SAFE_CHARS = string.ascii_letters + string.digits + "./"
_URL_SAFE_CHARS = string.ascii_letters + string.digits + "-_~"


def _generate_password(length: int = 32) -> str:
    """Generate a random password using only sha512_crypt-safe characters [a-zA-Z0-9./]."""
    return "".join(secrets.choice(_CRYPT_SAFE_CHARS) for _ in range(length))


def _generate_url_safe_password(length: int = 32) -> str:
    """Generate a random password safe for use in database/service connection string URLs."""
    return "".join(secrets.choice(_URL_SAFE_CHARS) for _ in range(length))


def _generate_token(length: int = 40) -> str:
    """Generate a random hex token."""
    return secrets.token_hex((length + 1) // 2)[:length]


def _generate_redfish_secrets(config: NVConfigManagerInstallConfig, state: dict[str, str]) -> None:
    """Populate Redfish/BMC credential secrets when explicitly enabled."""
    if not config.redfish.enabled or config.secrets.method != SecretsMethod.KUBERNETES:
        return
    for vendor, creds in config.redfish.vendors.items():
        state[f"redfish_{vendor}_default_user"] = creds.default_user or "local-mock-user"
        state[f"redfish_{vendor}_default_password"] = creds.default_password or _generate_password()
        state[f"redfish_{vendor}_config_manager_password"] = (
            creds.config_manager_password or _generate_password()
        )


_DB_GROUPS: list[tuple[str, str, str]] = [
    ("temporal", "temporalUser", "temporalPassword"),
    ("temporal_visibility", "temporalVisibilityUser", "temporalVisibilityPassword"),
    ("config_store", "configStoreUser", "configStorePassword"),
    ("dhcp", "dhcpUser", "dhcpPassword"),
    ("nautobot", "nautobotUser", "nautobotPassword"),
]


def _generate_core_k8s_secrets(state: dict[str, str], _v: Any) -> None:
    """Populate core Kubernetes secrets (Nautobot, Redis, PostgreSQL)."""
    state["nautobot_token"] = _v("nautobot", "token") or _generate_token(40)
    state["nats_password"] = _v("nautobot", "natsPassword") or _generate_url_safe_password()
    state["redis_password"] = _v("redis", "password") or _generate_url_safe_password()
    state["nautobot_admin_password"] = _v("nautobot_app", "adminPassword") or _generate_password()
    state["django_secret_key"] = _v("nautobot_app", "djangoSecretKey") or _generate_password(50)
    if sv := _v("nautobot_app", "superuserApiToken"):
        state["superuser_api_token"] = sv
    for db, user_key, pass_key in _DB_GROUPS:
        state[f"{db}_db_user"] = _v("postgres", user_key) or db
        state[f"{db}_db_password"] = _v("postgres", pass_key) or _generate_url_safe_password()


def _generate_optional_k8s_secrets(
    config: NVConfigManagerInstallConfig, state: dict[str, str], _v: Any
) -> None:
    """Populate optional integration secrets (Slack, AIR, Jira, CNPG backup)."""
    k8s = config.secrets.k8s
    if k8s.slack.enabled:
        state["slack_token"] = _v("slack", "token") or _generate_url_safe_password()
    if k8s.air.enabled:
        state["air_ssa_client_id"] = _v("air", "ssaClientId") or ""
        state["air_ssa_client_secret"] = (
            _v("air", "ssaClientSecret") or _generate_url_safe_password()
        )
    if k8s.jira.enabled:
        state["jira_base_url"] = _v("jira", "baseUrl") or ""
        state["jira_api_token"] = _v("jira", "apiToken") or ""
    if k8s.cnpg_backup.enabled:
        state["cnpg_access_key_id"] = _v("cnpg_backup", "accessKeyId") or ""
        state["cnpg_access_secret_key"] = _v("cnpg_backup", "accessSecretKey") or ""


def generate_secrets(config: NVConfigManagerInstallConfig) -> dict[str, str]:
    """Generate all secrets needed for deployment.

    Returns a dict of key -> value for every secret that needs a concrete value.
    Vault-sourced secrets are omitted (ESO provides them at runtime).

    The dict includes:
    - Network secrets:    {secret_key}_{rotation} -> generated or manually supplied value
                          (manual entries must have a non-empty value; missing values raise ValueError)
    - Infrastructure:     nautobot_token, nautobot_admin_password, redis_password,
                          nats_password, hash_salt, django_secret_key, etc.
    """
    state: dict[str, str] = {}

    # -- Network secrets --
    for entry in config.network_secrets:
        if not entry.secret_key:
            continue
        full_key = (
            entry.secret_key if not entry.rotation else f"{entry.secret_key}_{entry.rotation}"
        )
        if entry.source == PasswordSource.GENERATE:
            state[full_key] = _generate_password()
        elif entry.source == PasswordSource.MANUAL:
            if not entry.value.strip():
                raise ValueError(
                    f"Manual secret '{full_key}' has no value; "
                    "manual entries must be provided before deployment."
                )
            state[full_key] = entry.value

    # -- Hash salt --
    state["hash_salt"] = _generate_password(8)

    if config.secrets.method != SecretsMethod.KUBERNETES:
        return state

    def _v(group: str, vault_key: str) -> str:
        return _k8s_val(config, group, vault_key)

    _generate_core_k8s_secrets(state, _v)
    _generate_optional_k8s_secrets(config, state, _v)
    _generate_redfish_secrets(config, state)

    return state


# ---------------------------------------------------------------------------
# ESO config generation
# ---------------------------------------------------------------------------

# Maps schema field names (snake_case) to the camelCase keys the Helm chart
# expects under ``secrets.vault.paths``.  Also defines the fallback path
# suffix used when the user hasn't specified a custom vault path.
_VAULT_PATH_GROUPS: list[tuple[str, str, str]] = [
    # (schema_field, helm_key, default_path_suffix)
    ("nautobot", "nautobot", "nautobot"),
    ("redis", "redis", "redis"),
    ("postgres", "postgres", "postgres"),
    ("network", "network", "network"),
    ("nautobot_app", "nautobotApp", "nautobot-app"),
    ("oidc", "oidc", "oidc"),
    ("slack", "slack", "slack"),
    ("air", "air", "air"),
    ("jira", "jira", "jira"),
    ("cnpg_backup", "cnpgBackup", "cnpg-backup"),
]


def _build_vault_auth(v: Any, vault_section: dict[str, Any]) -> None:
    """Populate auth-related fields on the vault section."""
    if v.auth.method == VaultAuthMethod.TOKEN:
        vault_section["tokenAuth"] = {"enabled": True, "secretName": v.auth.token_secret_name}
    else:
        if v.mount_path:
            vault_section["mountPath"] = v.mount_path
        if v.role:
            vault_section["role"] = v.role


def _build_vault_paths(v: Any, env: str) -> dict[str, Any]:
    """Build the ``paths`` sub-section from the vault path groups."""
    defaults = VaultPathsConfig()
    paths: dict[str, Any] = {}
    for schema_field, helm_key, default_suffix in _VAULT_PATH_GROUPS:
        pc: VaultPathConfig = getattr(v.paths, schema_field)
        if not pc.enabled:
            continue
        entry: dict[str, Any] = {"path": pc.path or f"{env}/{default_suffix}"}
        keys = pc.keys if pc.keys else getattr(defaults, schema_field).keys
        if keys:
            entry["keys"] = dict(keys)
        paths[helm_key] = entry
    return paths


def build_eso_vault_config(config: NVConfigManagerInstallConfig) -> dict[str, Any]:
    """Build the ``secrets`` section for Helm values when using ESO."""
    if config.secrets.method != SecretsMethod.ESO:
        return {}

    v = config.secrets.vault
    vault_section: dict[str, Any] = {
        "server": v.server,
        "namespace": v.namespace,
        "secretsPath": v.secrets_path,
    }
    if v.config_secrets_path:
        vault_section["configSecretsPath"] = v.config_secrets_path

    _build_vault_auth(v, vault_section)
    vault_section["paths"] = _build_vault_paths(v, config.cluster.environment)

    return {"secrets": {"method": "eso", "vault": vault_section}}
