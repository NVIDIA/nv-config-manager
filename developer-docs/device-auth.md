# Device Authentication

NVIDIA Config Manager communicates with network devices using a dedicated service account (default username
`nv-config-manager`). This document explains how that account is created, how its credentials flow through
the system, and what must be in place for device workflows to succeed.

## Overview

The credential loop has three stages:

1. **Install** — the installer generates (or accepts) the service-account password and stores
   it in `config-secrets.ini` inside a Kubernetes secret.
2. **Render → ZTP** — when a device config is rendered, the password is hashed and written into
   the device's AAA configuration. ZTP serves that config during first boot, which creates the
   OS-level user account.
3. **Temporal** — when a workflow needs to connect to a device, the worker reads the plaintext
   password from the same `config-secrets.ini` and authenticates as the `nv-config-manager` user.

The same plaintext secret value is used in all three stages; render converts it to a hash on the
way to the device, and Temporal sends it as plaintext over SSH/API.

---

## Stage 1 — Install: seeding credentials

### The service account username

Configured at install time via `secrets.config_manager_service_username` (default: `nv-config-manager`).
The deployer writes it to the `device-creds` Kubernetes secret:

```text
deployer.py _create_core_secrets()  →  K8s secret "device-creds"  {username: "nv-config-manager"}
```

This secret is later mounted into the secret-assembler init-container, which injects it into
`nv-config-manager.ini` under `[device] username`.  There is no `[device] password` in `nv-config-manager.ini`; the
password is always loaded at runtime from `config-secrets.ini`.

### The service account password

The installer collects per-site network secrets via the TUI (`network_secrets.py`).  The entry
labelled "NVIDIA Config Manager Password" has `secret_key = "api_user_key"`.  Combined with its `rotation`
suffix (`r1` by default), the key stored in `config-secrets.ini` is `api_user_key_r1`.

`accounts.py build_config_secrets_ini()` serialises all site secrets into:

```ini
[site.dc01]
api_user_key_r1 = <plaintext-password>
root_password_r1 = <plaintext-password>
bgp_password_r1 = <plaintext-password>
hash_salt = <8-char-random>

[site.dc02]
...
```

This INI content is stored as the `config-secrets.ini` key inside the
`{release}-network-secrets` Kubernetes secret and later mounted into both the render and
Temporal worker pods via `NV_CONFIG_MANAGER_CONFIG_SECRET_PATH`.

When using the vault-agent or ESO secrets methods the same per-site KV paths in Vault are
consumed instead, but the resulting `config-secrets.ini` file on disk has the same format.

> **Requirement:** `vault.configSecrets.enabled` must be `true` (or the equivalent
> `{release}-network-secrets` secret must be present and mounted).  Without it,
> `NV_CONFIG_MANAGER_CONFIG_SECRET_PATH` is unset and both render and Temporal worker cannot access
> per-site passwords, making device interaction unsupported.

---

## Stage 2 — Render and ZTP: provisioning the account on the device

### Nautobot config context: `password_mappings`

Each platform's Nautobot config context carries a `password_mappings` block that declares
which OS users should exist and which config-secrets key holds the password.
`components/nautobot/nv_config_manager_jobs/data/config_contexts.yaml`:

```yaml
password_mappings:
  nvConfigManager:
    password: api_user_key   # base key name in config-secrets.ini
    rotation: r1             # suffix  →  final key: "api_user_key_r1"
    role: system-admin
  cumulus:                   # platform root account
    password: root_password
    rotation: r1
    role: system-admin
```

The map key (`nv-config-manager`) is the literal username that will be created on the device.

### Rendering the AAA stanza

During rendering the `nv_config_manager_templates` library processes `password_mappings` in two
template filter steps:

1. **`users` filter** (`filters/device.py`) — converts the mapping to a list of user objects:
   ```python
   {"username": "nv-config-manager", "role": "system-admin", "password_key": "api_user_key_r1"}
   ```

2. **`load_secret` filter** (`filters/vault.py`) — reads the plaintext password from
   `config-secrets.ini` for the device's site:
   ```text
   NV_CONFIG_MANAGER_CONFIG_SECRET_PATH → [site.dc01] → api_user_key_r1 → <plaintext>
   ```

3. **`encrypt` filter** (`filters/vault.py`) — hashes the plaintext with sha512_crypt using
   the `hash_salt` value from the same site section:
   ```python
   sha512_crypt.using(rounds=5000, salt=<hash_salt>).hash(plaintext)  →  "$6$<salt>$<hash>"
   ```

The final Jinja2 expression in each platform's `system.j2` (or `management.j2` for EOS) looks
like:

```jinja2
{{ user.password_key | load_secret(site=device_data|site_name) | encrypt("sha512", site=...) }}
```

The rendered `startup.yaml` contains an entry such as:

```yaml
# Cumulus Linux (NVUE)
system:
  aaa:
    user:
      nvConfigManager:
        hashed-password: "$6$<salt>$<hash>"
        role: system-admin

# Arista EOS
username nv-config-manager privilege 15 role system-admin secret sha512 $6$<salt>$<hash>
```

Rendered output is committed to the Config Store by the render service.

### ZTP delivery

When the device boots for the first time:

1. DHCP hands the device a boot-file URL pointing to the ZTP service.
2. The device fetches its boot-script (`GET /v1/device/<uuid>/boot-script`).  The ZTP service
   serves this from the Config Store after verifying the requesting IP against Nautobot.
3. The boot-script downloads `startup.yaml` from the ZTP service and applies it:
   ```bash
   retry_curl http://<ztp-server>/v1/device/<uuid>/config/startup.yaml -o /tmp/startup.yaml
   nv config replace /tmp/startup.yaml
   nv config apply -y
   ```
4. The OS-level `nv-config-manager` user is created with the sha512-hashed password from `startup.yaml`.
5. The boot-script POSTs to `/v1/device/<uuid>/provisioned`.  The ZTP service updates the
   device status in Nautobot and triggers a Temporal backup workflow.

At this point the device is reachable by NVIDIA Config Manager using the plaintext `api_user_key_r1` secret,
because the hash on the device was derived from it.

---

## Stage 3 — Temporal: runtime device connections

The Temporal worker resolves credentials in `NetworkConnection.__init__()` (`temporal/client/device.py`):

1. **Username** — read from `nv-config-manager.ini [device] username` (value: `"nv-config-manager"`, sourced from the
   `device-creds` Kubernetes secret at pod start).

2. **Site** — passed in from the workflow's device data (from Nautobot).

3. **Passwords** — `resolve_config_section()` (`temporal/common/secrets.py`) looks up the
   `[site.<slug>]` section in `config-secrets.ini`; `get_rotation_passwords()` scans for all
   keys matching `api_user_key_r*`, sorts by revision number descending, and returns up to two
   passwords to try.

4. **Connection** — `_try_passwords_with_callback()` tries each password in order and caches
   the first that succeeds.

This means during a password rotation the worker automatically handles the transition window:
if `r2` is the newest revision it is tried first; if the device has not yet received the
re-rendered config and still accepts `r1`, the fallback succeeds transparently.

---

## Password rotation

To rotate the device service-account password:

1. Add `api_user_key_r2` to each site's secrets (new plaintext value); keep `api_user_key_r1`.
2. The render service re-renders all affected devices; the new hash appears in `startup.yaml`.
3. Deploy the new config to devices (via Temporal deploy workflow or ZTP re-provisioning).
4. Temporal workers now try `r2` first.  Any device still on the old password accepts `r1` as
   fallback during the rollout window.
5. Once all devices are updated, remove `api_user_key_r1` from `config-secrets.ini` and
   re-render.

---

## Component map

| What | Where | Key detail |
|:-----|:------|:-----------|
| Username default | `installer/src/nv_config_manager_installer/schema.py:231` | `config_manager_service_username = "nv-config-manager"` |
| `device-creds` secret creation | `installer/src/nv_config_manager_installer/deployer.py:794–800` | only `username` stored |
| `config-secrets.ini` builder | `installer/src/nv_config_manager_installer/accounts.py:45–87` | per-site INI sections |
| TUI "NVIDIA Config Manager Password" entry | `installer/src/nv_config_manager_installer/tui/screens/network_secrets.py:39` | `secret_key: "api_user_key"` |
| `password_mappings` config context | `components/nautobot/nv_config_manager_jobs/data/config_contexts.yaml:12–21` | defines OS users per platform |
| `users` filter (maps to password_key) | `nv_config_manager_templates/filters/device.py:966–992` | builds `"api_user_key_r1"` |
| `load_secret` filter | `nv_config_manager_templates/filters/vault.py:23–62` | reads `NV_CONFIG_MANAGER_CONFIG_SECRET_PATH` |
| `encrypt` filter | `nv_config_manager_templates/filters/vault.py:65–97` | sha512_crypt with `hash_salt` |
| Cumulus AAA template | `nv_config_manager_templates/templates/cumulus-linux/**/system.j2` | renders `hashed-password` |
| Arista EOS AAA template | `nv_config_manager_templates/templates/arista-eos/**/management.j2:125–134` | renders `secret sha512` |
| NV-OS AAA template | `nv_config_manager_templates/templates/nv-os/**/system.j2:4–8` | renders `password` |
| ZTP boot-script (applies startup.yaml) | `nv_config_manager_templates/templates/cumulus-linux/**/boot-script.j2:100–122` | `nv config replace + apply` |
| ZTP API (serves configs, marks provisioned) | `src/nv_config_manager/ztp/api/device_v1.py:77–167` | IP-authorised, triggers backup |
| `[device] username` in nv-config-manager.ini | `deploy/helm/templates/kubernetes-secrets.yaml:228–231` | injected from `device-creds` |
| Temporal credential resolution | `src/nv_config_manager/temporal/client/device.py:363–419` | `NetworkConnection.__init__` |
| Rotation key reader | `src/nv_config_manager/temporal/common/secrets.py:127–169` | `get_rotation_passwords()` |
| `NV_CONFIG_MANAGER_CONFIG_SECRET_PATH` on render pods | `deploy/helm/templates/render-service.yaml:68–71` | must be set for render to work |
| `NV_CONFIG_MANAGER_CONFIG_SECRET_PATH` on temporal pods | `deploy/helm/templates/temporal.yaml:379–382` | must be set for device access |
