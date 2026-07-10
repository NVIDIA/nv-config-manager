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
"""Group-mapping driven RBAC for JWT-authenticated Nautobot users.

This is the richer counterpart to ``NV_CONFIG_MANAGER_SUPERUSER_GROUPS`` (defined in
:mod:`nv_config_manager_auth.jwt_authentication`).  Where the env var only flips
``is_superuser`` based on a single privileged group list, this module reads a
YAML mapping file that lets you express:

* which IdP group names map to which Django ``Group``;
* what Nautobot :class:`~nautobot.users.models.ObjectPermission` records each
  Django Group should own (per-action ``content_types`` + optional
  ``constraints``);
* whether membership in a given group additionally grants superuser status.

Django ``Group`` lifecycle is **operator-managed by default**: this module
will neither create nor delete groups, and entries whose ``Group`` does not
yet exist in Nautobot are logged at WARNING and skipped at login.  Operators
are expected to create matching ``Group`` rows up front (admin UI / fixture
/ one-shot Job) so that the group catalog is auditable and stable.

Set ``NV_CONFIG_MANAGER_AUTO_CREATE_GROUPS=true`` (Helm: ``nautobot.rbac.autoCreateGroups``)
to flip into a self-service mode where missing Django Groups are created on
the fly the first time a logging-in user matches their entry.  This is handy
for greenfield deployments where the YAML *is* the source of truth for the
catalog; we never delete groups even when set, so removing an entry from the
mapping leaves the (now-empty) Group in place for an operator to clean up.

Django Groups defined outside the mapping (e.g. manually-created admin groups
the operator wants to keep static) are never touched -- we only read/write
group memberships and ObjectPermissions for the names listed in the mapping.

Mapping file format -- entries live under a top-level ``groups:`` key::

    groups:
      - name: "ipam-rw"               # name from the JWT roles claim
        nautobot_permissions:
          view:
            content_types: ["all"]    # "all" → every model in any installed app
          add:
            content_types: ["ipam.*"] # "<app>.*" → every model in that app
          change:
            content_types: ["ipam.ipaddress", "ipam.prefix"]
          delete:
            content_types: ["ipam.ipaddress"]
            constraints:               # per-action constraints (optional)
              status__name: "Active"
          run:
            content_types: ["extras.job"]
      - name: "admin-rw"
        is_superuser: true             # superuser shortcut; permissions optional
        nautobot_permissions:          # ignored when is_superuser is true
          ...

Configuration::

    NV_CONFIG_MANAGER_GROUP_MAPPING_PATH = /opt/nautobot/rbac/group-mapping.yaml
    NV_CONFIG_MANAGER_AUTO_CREATE_GROUPS = false  # set to "true" to auto-create Django Groups

If the mapping file is missing the feature is silently disabled (no-op).
The mapping is reloaded on every login so a ConfigMap edit takes effect
without a Nautobot restart.

Removing entries from the mapping -- revocation semantics
---------------------------------------------------------
Removing an action from a kept entry's ``nautobot_permissions`` is cleaned
up automatically: ``_apply_group_permission_config`` detaches and deletes
the stale ``<group>_<action>`` :class:`ObjectPermission` on the next login
that touches the group.

Removing a **whole entry** is also cleaned up automatically on each
affected user's next login, via :func:`_revoke_removed_mapping_groups`:
the user is removed from the Django Group and the group's managed
``<group>_<action>`` permissions are detached and (when no other group
references them) deleted outright.  The Django Group row itself stays put
so operators retain final say over the group catalog.

Manual Django Groups (no ``<group>_<action>`` perms attached) are not
touched -- operators can layer manual groups on top without worrying
about a YAML edit silently revoking them.

Known limitation for the ``is_superuser: true`` revocation pass:
``is_superuser: true`` entries strip their group's managed perms (see
:func:`_prune_group_object_permissions`), so removing an entry leaves
no ``<group>_<action>`` marker on the Django Group for
:func:`_revoke_removed_mapping_groups` to find.  ``is_superuser``
revocation goes through :func:`_sync_superuser_status` instead, gated
on :func:`mapping_is_configured`: as long as the operator has opted
into mapping-based RBAC, ``_sync_superuser_status`` runs on every JWT
login and demotes users who no longer match either source.  Membership
in the Django Group itself still lingers until the operator removes it
via the admin UI -- the permissions side, which is what governs
access, is fully revoked.
"""

from __future__ import annotations

import logging
import os
from typing import Any

import yaml
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from nautobot.users.models import ObjectPermission

log = logging.getLogger(__name__)


DEFAULT_MAPPING_PATH = "/app/config/group-mapping.yaml"
ALL_CONTENT_TYPES = "all"
_TRUTHY = frozenset({"1", "true", "yes", "on"})

# Django/Nautobot internal models that should NOT be touched by an "all"
# expansion.  Granting view/change on session storage, social-auth scratch
# tables, celery beat schedules etc. is always wrong.  Keep this conservative;
# opt-in by explicit name if needed.
_EXCLUDED_FROM_ALL: frozenset[str] = frozenset(
    {
        "sessions.session",
        "social_django.association",
        "social_django.code",
        "social_django.nonce",
        "social_django.usersocialauth",
        "social_django.partial",
        "taggit.tag",
        "taggit.taggeditem",
        "constance.constance",
        "admin.logentry",
        "django_celery_beat.crontabschedule",
        "django_celery_beat.intervalschedule",
        "django_celery_beat.periodictask",
        "django_celery_beat.periodictasks",
        "django_celery_beat.solarschedule",
        "django_celery_beat.clockedschedule",
        "django_celery_results.taskresult",
        "django_celery_results.chordcounter",
        "django_celery_results.groupresult",
        "silk.profile",
        "silk.request",
        "silk.response",
        "silk.sqlquery",
    }
)


class GroupMappingError(Exception):
    """Base class for group-mapping load/parse errors."""


class GroupMappingReadError(GroupMappingError):
    """The mapping file could not be opened or decoded.

    Covers every filesystem failure mode short of "file doesn't exist"
    (which is a legitimate unconfigured state, not an error):
    permission denied, file disappeared between configuration check and
    open (TOCTOU), file is a directory or other non-regular inode, or the
    bytes on disk are not valid UTF-8.  Callers must catch this (via the
    ``GroupMappingError`` base) and take the same fail-closed path as a
    parse error -- treat the mapping as empty so revocation/demotion still
    runs, rather than letting a raw ``OSError`` crash the login pipeline.
    """


class GroupMappingParseError(GroupMappingError):
    """The mapping YAML could not be parsed or has an invalid shape."""


# ── Mapping loader ─────────────────────────────────────────────────────────


def _mapping_path() -> str:
    """Return the configured group-mapping YAML path (env override or default)."""
    return os.getenv("NV_CONFIG_MANAGER_GROUP_MAPPING_PATH", DEFAULT_MAPPING_PATH)


def mapping_is_configured(path: str | None = None) -> bool:
    """Return True iff group-mapping RBAC has been opted into by the operator.

    Signal precedence (highest wins):

    * ``NV_CONFIG_MANAGER_GROUP_MAPPING_PATH`` env var set -- explicit opt-in.  We
      return True even when the file is currently missing so a transient
      mount gap during a chart upgrade can't silently re-enable stale
      grants; the caller sees an empty load and exercises the
      revocation/demotion path.
    * Otherwise, file existence at ``DEFAULT_MAPPING_PATH`` (or *path*
      when supplied for tests).  The Helm chart renders and mounts the
      group-mapping ConfigMap at ``/app/config/group-mapping.yaml`` only
      when the ``nautobot.rbac.groupMapping`` key is *present* (``hasKey``)
      -- including an explicit ``groupMapping: []`` (the revoke-everyone
      idiom).  Omitting the key entirely leaves the file unmounted, so
      file existence is a reliable proxy for "operator wrote a value".
      This is why the default in ``values.yaml`` leaves the key commented
      out: an absent key means unconfigured, and previously-granted
      privileges are left untouched.

    This is intentionally a *configuration* signal, not a *content*
    signal.  Callers must distinguish three states the truthiness of
    ``load_group_mapping()``'s return value cannot:

    * unconfigured -- skip sync entirely so manual ``is_superuser`` flags
      and Django Group memberships set outside the SSO flow are preserved;
    * configured + loaded OK -- run sync, even when the loaded mapping is
      empty (``groups: []`` is the explicit revoke-everyone idiom);
    * configured + load failed -- the caller should log loudly and behave
      as if the mapping is empty (fail closed: revoke previously-granted
      access rather than silently preserve stale grants behind a parser
      error).
    """
    if path is None and os.environ.get("NV_CONFIG_MANAGER_GROUP_MAPPING_PATH"):
        return True
    return os.path.isfile(path or DEFAULT_MAPPING_PATH)


def _auto_create_groups() -> bool:
    """Whether to auto-create Django Groups referenced in the mapping.

    Default ``False`` -- group creation is an operator action.  Set
    ``NV_CONFIG_MANAGER_AUTO_CREATE_GROUPS=true`` (or ``1`` / ``yes`` / ``on``) to opt in.
    """
    return os.getenv("NV_CONFIG_MANAGER_AUTO_CREATE_GROUPS", "").strip().lower() in _TRUTHY


def load_group_mapping(path: str | None = None) -> dict[str, dict[str, Any]]:
    """Load and normalise the group-mapping YAML.

    Returns a ``{group_name: group_config}`` dict.  An empty dict is returned
    when the file does not exist, is empty, or contains no mappings -- the
    feature is opt-in and should never crash a login when unconfigured.
    """
    path = path or _mapping_path()

    # Funnel every filesystem failure mode into ``GroupMappingError`` so the
    # caller's documented fail-closed path always runs.  An ``isfile()`` check
    # plus a bare ``open()`` would leave a TOCTOU window (file deleted between
    # check and open) and would not catch ``PermissionError`` /
    # ``IsADirectoryError`` / ``UnicodeDecodeError``; any of those would surface
    # as a raw ``OSError`` past ``except GroupMappingError`` in the caller and
    # crash the login.  Catch and translate them here instead.
    try:
        with open(path, encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except FileNotFoundError:
        # The "no mapping configured" / "ConfigMap not yet mounted" case.
        # ``mapping_is_configured()`` already gates whether we run RBAC at
        # all, and explicitly documents that an env-var-set + file-missing
        # state must surface as an empty load so the caller exercises the
        # revoke/demote path -- so we return ``{}`` here too.
        return {}
    except (OSError, UnicodeDecodeError) as exc:
        raise GroupMappingReadError(f"Failed to read {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise GroupMappingParseError(f"Failed to parse {path}: {exc}") from exc

    # Distinguish "empty file" (``None`` -- legit, treat as no mappings) from
    # "non-mapping top-level" (``false`` / ``0`` / ``[]`` / ``""`` -- operator
    # error, must surface).  Coercing every falsy value into ``{}`` would bypass
    # the validator below and silently disable RBAC, so handle them explicitly.
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise GroupMappingParseError(f"{path}: top-level must be a mapping, got {type(data).__name__}")

    # Entries live under ``groups:``.  Distinguish "key absent" (feature
    # unconfigured -- legitimate no-op) from "key present with wrong shape"
    # (operator error -- raise).  A ``data.get("groups") or []`` idiom would
    # collapse ``groups: {}``, ``groups: ""``, ``groups: false`` into the empty
    # list and silently disable RBAC instead of surfacing the misconfiguration.
    if "groups" in data:
        source_key, entries = "groups", data["groups"]
    else:
        source_key, entries = None, []

    # Explicit ``groups: null`` is the YAML idiom for "key present, no value" --
    # treat it identically to an empty list / absent key.  Empty list
    # (``groups: []``) is also fine.
    if entries is None:
        entries = []

    if not isinstance(entries, list):
        raise GroupMappingParseError(
            f"{path}: {source_key!r} must be a list of group entries, got {type(entries).__name__}"
        )

    out: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise GroupMappingParseError(f"{path}: each group entry must be a mapping, got {type(entry).__name__}")
        name = entry.get("name")
        if not name or not isinstance(name, str):
            raise GroupMappingParseError(f"{path}: each group entry must have a non-empty string 'name'")
        # ``is_superuser`` controls a privilege boundary; reject quoted/truthy
        # surrogates (``"true"``, ``1``) up-front so a YAML typo can't
        # silently promote everyone in a role.
        if "is_superuser" in entry and not isinstance(entry["is_superuser"], bool):
            raise GroupMappingParseError(
                f"{path}: group {name!r}: 'is_superuser' must be a YAML bool (true/false), got "
                f"{type(entry['is_superuser']).__name__} (did you quote it?)"
            )
        # ``nautobot_permissions`` is iterated as a dict of action → mapping;
        # a non-mapping here would explode later with an opaque TypeError.
        perms = entry.get("nautobot_permissions")
        if perms is not None and not isinstance(perms, dict):
            raise GroupMappingParseError(
                f"{path}: group {name!r}: 'nautobot_permissions' must be a mapping of "
                f"action → config, got {type(perms).__name__}"
            )
        out[name] = entry
    return out


# ── Content-type resolution ────────────────────────────────────────────────


def _all_allowed_content_types() -> list[ContentType]:
    """Every ContentType except the ones in :data:`_EXCLUDED_FROM_ALL`."""
    return [ct for ct in ContentType.objects.all() if f"{ct.app_label}.{ct.model}" not in _EXCLUDED_FROM_ALL]


def _resolve_content_types(spec: list[str]) -> list[ContentType]:
    """Resolve a ``content_types`` list to concrete :class:`ContentType` rows.

    Accepted entries (exactly one dot, both halves non-empty):
        * ``"all"``                  -- every model (minus :data:`_EXCLUDED_FROM_ALL`)
        * ``"<app_label>.*"``        -- every model in that app
        * ``"<app_label>.<model>"``  -- a single model

    Anything else is malformed and logged + skipped, including:
        * ``"ipam.prefix.*"``  -- multi-dot; would otherwise be parsed as
          ``app_label="ipam"`` + ``model="prefix.*"`` and silently widened
          to *all* of ipam.
        * ``"ipam.foo.bar"`` / ``".prefix"`` / ``"ipam."``
        * non-strings.

    Unknown / not-installed models (valid shape, no such row) are also
    skipped with a warning rather than raising, so a single typo doesn't
    block a login.
    """
    if not spec:
        return []
    if ALL_CONTENT_TYPES in spec:
        return _all_allowed_content_types()

    out: list[ContentType] = []
    for entry in spec:
        if not isinstance(entry, str) or "." not in entry:
            log.warning("rbac: ignoring malformed content_type %r (expected 'app.model' or 'app.*')", entry)
            continue
        app_label, model = entry.split(".", 1)
        if not app_label or not model or "." in model:
            # Multi-dot entries ("ipam.prefix.*", "ipam.foo.bar") are rejected
            # rather than widened: silently treating "ipam.prefix.*" as
            # "ipam.*" would broaden access on a typo.  Empty halves are
            # malformed too (".prefix", "ipam.").
            log.warning("rbac: ignoring malformed content_type %r (expected 'app.model' or 'app.*')", entry)
            continue
        if model == "*":
            out.extend(ContentType.objects.filter(app_label=app_label))
            continue
        try:
            out.append(ContentType.objects.get(app_label=app_label, model=model))
        except ContentType.DoesNotExist:
            log.warning("rbac: ignoring unknown content_type %r (app or model not installed)", entry)
    return out


# ── Sync entry points ──────────────────────────────────────────────────────


def is_superuser_per_mapping(user_groups: set[str], mapping: dict[str, dict[str, Any]]) -> bool:
    """Return True if any of *user_groups* maps to a ``is_superuser: true`` entry."""
    return any(bool(mapping[name].get("is_superuser")) for name in user_groups if name in mapping)


@transaction.atomic
def sync_groups_and_permissions(
    user: Any,
    user_groups: set[str],
    mapping: dict[str, dict[str, Any]] | None = None,
) -> None:
    """Reconcile *user*'s Django Groups and ObjectPermissions against *mapping*.

    The caller is responsible for the "is the feature configured?" gate
    via :func:`mapping_is_configured` -- this function deliberately does
    NOT short-circuit on an empty mapping.  When the operator opts into
    the feature and then writes ``groupMapping: []`` (or the YAML fails
    to parse), pass 1 + pass 2 become no-ops and pass 3 prunes everything
    this module manages.  Conflating "empty mapping" with "feature
    disabled" would let managed memberships / ObjectPermissions linger
    after the operator removed them -- the fail-open behavior this avoids.

    Three passes run in order:

    1. :func:`_sync_group_permissions` reconciles ``ObjectPermission`` rows
       attached to each of the user's currently-mapped groups (creating /
       updating / pruning per-action perms in place).
    2. :func:`_sync_group_memberships` adds the user to mapped groups they
       hold in the token and removes them from mapped groups they no longer
       hold.
    3. :func:`_revoke_removed_mapping_groups` revokes the user from groups
       that were *previously* managed (have ``<group>_<action>`` perms left
       behind by an earlier sync) but are no longer in the mapping at all.
       With an empty mapping this is the catch-all that revokes every
       previously-managed group the user is still in.

    Manual Django Groups (no managed ``<group>_<action>`` perms attached)
    are never touched by pass 3, so operator-curated groups can coexist
    with mapping-managed ones.  Idempotent: safe to call on every login.
    """
    mapping = mapping if mapping is not None else load_group_mapping()

    managed_names = set(mapping.keys())
    relevant_user_groups = user_groups & managed_names

    _sync_group_permissions(relevant_user_groups, mapping)
    _sync_group_memberships(user, relevant_user_groups, mapping)
    _revoke_removed_mapping_groups(user, managed_names)


def _revoke_removed_mapping_groups(user: Any, current_managed_names: set[str]) -> None:
    """Revoke memberships + prune managed perms for groups removed from the mapping.

    For every Django Group the user belongs to that is **not** in the current
    mapping, we inspect its attached ``ObjectPermission`` rows: if at least
    one follows our ``<group_name>_<action>`` naming pattern, the group was
    previously managed by this module.  We then:

    * remove the user's membership;
    * detach every ``<group_name>_<action>`` permission from the group, and
      delete the permission row outright when no other group still holds it.

    The Django Group row itself is left in place -- the operator may have
    other intentions for it (manually-managed users, scheduled deletion,
    audit trail).  The next sync will continue to skip it as long as it has
    no managed perms attached.

    Heuristic limitation: an ``is_superuser: true`` mapping entry strips its
    Group's managed perms (see :func:`_prune_group_object_permissions`), so
    removing such an entry leaves no marker for this pass to detect.  In
    that case rely on :func:`mapping_is_configured` driving
    ``_sync_superuser_status`` (see the module docstring).
    """
    for group in list(user.groups.exclude(name__in=current_managed_names)):
        managed_prefix = f"{group.name}_"
        managed_perms = [
            p
            for p in group.object_permissions.all()
            if p.name.startswith(managed_prefix) and len(p.name) > len(managed_prefix)
        ]
        if not managed_perms:
            continue  # purely-manual group, leave alone

        user.groups.remove(group)
        log.info(
            "rbac: revoked %s from previously-managed Django Group %r (removed from mapping)",
            user.username,
            group.name,
        )
        for perm in managed_perms:
            perm.groups.remove(group)
            if not perm.groups.exists():
                perm.delete()
                log.info(
                    "rbac: removed stale ObjectPermission %r (group removed from mapping)",
                    perm.name,
                )


def _sync_group_permissions(user_groups: set[str], mapping: dict[str, dict[str, Any]]) -> None:
    """Reconcile :class:`ObjectPermission` rows attached to each of the user's
    matched Django Groups.

    Group lifecycle is operator-managed by default: missing groups are logged
    at WARNING and skipped, so the operator can audit the group catalog
    explicitly.  When :func:`_auto_create_groups` is opted in, missing groups
    are created on the fly and the sync proceeds normally.

    Only iterates the groups *this* user holds; nothing else is touched.
    Existing groups have their attached ObjectPermission rows reconciled in
    place against ``mapping[name]['nautobot_permissions']``.
    """
    auto_create = _auto_create_groups()
    for name in user_groups:
        config = mapping[name]
        if auto_create:
            group, created = Group.objects.get_or_create(name=name)
            if created:
                log.info("rbac: auto-created Django Group %r (NV_CONFIG_MANAGER_AUTO_CREATE_GROUPS=true)", name)
        else:
            try:
                group = Group.objects.get(name=name)
            except Group.DoesNotExist:
                log.warning(
                    "rbac: Django Group %r is in the mapping but does not exist in Nautobot; "
                    "create it (admin UI / fixture / Job) or set NV_CONFIG_MANAGER_AUTO_CREATE_GROUPS=true",
                    name,
                )
                continue

        # ``is_superuser`` groups don't get per-action ObjectPermissions --
        # the user's global superuser flag obviates them.
        if config.get("is_superuser"):
            _prune_group_object_permissions(group)
            continue

        _apply_group_permission_config(group, config.get("nautobot_permissions") or {})


def _sync_group_memberships(
    user: Any,
    user_groups: set[str],
    mapping: dict[str, dict[str, Any]],
) -> None:
    """Reconcile *user*'s Django Group memberships -- but only for groups that
    appear in *mapping* **and** already exist in Nautobot.

    Group lifecycle is operator-managed by default (see
    :func:`_sync_group_permissions`).  Permission sync runs first, so when
    ``NV_CONFIG_MANAGER_AUTO_CREATE_GROUPS=true`` the relevant groups will already exist
    by the time we get here; in operator-managed mode, missing groups are
    skipped with a single WARNING listing the missing names.  Manual /
    unrelated group memberships are preserved.
    """
    managed_names = set(mapping.keys())
    current_managed = set(user.groups.filter(name__in=managed_names).values_list("name", flat=True))

    to_add = user_groups - current_managed
    to_remove = current_managed - user_groups

    if to_add:
        addable = Group.objects.filter(name__in=to_add)
        addable_names = set(addable.values_list("name", flat=True))
        missing = to_add - addable_names
        if addable_names:
            user.groups.add(*addable)
            log.info("rbac: added %s to Django groups %s", user.username, sorted(addable_names))
        if missing:
            log.warning(
                "rbac: skipped adding %s to non-existent Django groups %s "
                "(operator must create them in Nautobot first)",
                user.username,
                sorted(missing),
            )
    if to_remove:
        user.groups.remove(*Group.objects.filter(name__in=to_remove))
        log.info("rbac: removed %s from Django groups %s", user.username, sorted(to_remove))


def _apply_group_permission_config(group: Group, perms_config: dict[str, dict[str, Any]]) -> None:
    """Reconcile ObjectPermissions attached to *group* against *perms_config*.

    Permissions are named ``"<group>_<action>"`` so they round-trip
    predictably and we can prune any that no longer appear in the config.

    The snapshot below is used **only** to drive the prune pass at the
    bottom (it tells us which managed ``<group>_<action>`` rows were
    attached to this group and need a delete decision).  The per-action
    upsert deliberately ignores the snapshot and goes straight through
    ``ObjectPermission.objects.update_or_create`` keyed by ``name`` so the
    create + update branches are atomic in a single Django savepoint --
    two concurrent logins for users in the same group cannot both decide
    "no perm exists" and both INSERT, and the snapshot cannot hand us a
    stale row that another transaction has already deleted out from
    under us.
    """
    existing_perms = {perm.name: perm for perm in group.object_permissions.all()}

    kept_perm_names: set[str] = set()
    for action, action_config in perms_config.items():
        if not isinstance(action_config, dict):
            log.warning(
                "rbac: group %r action %r config must be a mapping, got %s; skipping",
                group.name,
                action,
                type(action_config).__name__,
            )
            continue
        perm_name = f"{group.name}_{action}"
        kept_perm_names.add(perm_name)

        content_types = _resolve_content_types(action_config.get("content_types") or [])
        constraints = action_config.get("constraints") or {}
        if not isinstance(constraints, dict):
            log.warning(
                "rbac: group %r action %r constraints must be a mapping; coercing to {}",
                group.name,
                action,
            )
            constraints = {}

        perm, _created = ObjectPermission.objects.update_or_create(
            name=perm_name,
            defaults={"actions": [action], "constraints": constraints},
        )

        current_cts = set(perm.object_types.all())
        desired_cts = set(content_types)
        if current_cts != desired_cts:
            perm.object_types.set(content_types)

        if group not in perm.groups.all():
            perm.groups.add(group)

    # Prune any per-action permissions that used to exist but are no longer in
    # config.  We only manage ObjectPermissions we created (matching our
    # "<group>_<action>" naming); anything else attached to the group is left
    # alone so operators can layer additional manual permissions if desired.
    managed_prefix = f"{group.name}_"
    stale = {
        name: perm
        for name, perm in existing_perms.items()
        if name.startswith(managed_prefix) and name not in kept_perm_names and name.replace(managed_prefix, "", 1)
    }
    for name, perm in stale.items():
        perm.groups.remove(group)
        # If no other group references the permission, delete it outright.
        if not perm.groups.exists():
            perm.delete()
            log.info("rbac: removed stale ObjectPermission %r", name)
        else:
            log.info("rbac: detached ObjectPermission %r from group %s", name, group.name)


def _prune_group_object_permissions(group: Group) -> None:
    """Remove all nv-config-manager-managed ObjectPermissions attached to *group*."""
    managed_prefix = f"{group.name}_"
    for perm in list(group.object_permissions.all()):
        if not perm.name.startswith(managed_prefix):
            continue
        perm.groups.remove(group)
        if not perm.groups.exists():
            perm.delete()
            log.info("rbac: removed stale ObjectPermission %r (superuser group)", perm.name)
