# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
"""Tests for :mod:`nv_config_manager_auth.rbac`."""

from __future__ import annotations

import os
import textwrap
from collections import namedtuple
from unittest.mock import MagicMock

import pytest

# Real ``django.contrib.contenttypes.models.ContentType`` rows are hashable
# (Django Model.__hash__ uses ``pk``).  Mirror that with a namedtuple so the
# set-difference logic in :mod:`nv_config_manager_auth.rbac` works in unit tests too.
_FakeCT = namedtuple("_FakeCT", ["app_label", "model"])


@pytest.fixture()
def rbac():
    """Import the module *after* the autouse conftest stubs are installed."""
    from nv_config_manager_auth import rbac as mod  # noqa: PLC0415 -- deferred for stub fixture

    return mod


# ── load_group_mapping ─────────────────────────────────────────────────────


def test_load_group_mapping_missing_file_returns_empty(rbac, tmp_path):
    """A missing file is the unconfigured state -- never raise."""
    assert rbac.load_group_mapping(str(tmp_path / "nope.yaml")) == {}


def test_load_group_mapping_empty_file_returns_empty(rbac, tmp_path):
    path = tmp_path / "empty.yaml"
    path.write_text("")
    assert rbac.load_group_mapping(str(path)) == {}


def test_load_group_mapping_groups_key(rbac, tmp_path):
    path = tmp_path / "m.yaml"
    path.write_text(
        textwrap.dedent(
            """\
            groups:
              - name: "ipam-rw"
                nautobot_permissions:
                  view:
                    content_types: ["all"]
              - name: "admins"
                is_superuser: true
            """
        )
    )
    out = rbac.load_group_mapping(str(path))
    assert set(out) == {"ipam-rw", "admins"}
    assert out["admins"]["is_superuser"] is True


@pytest.mark.parametrize(
    "body,fragment",
    [
        ("- not_a_mapping", "top-level must be a mapping"),
        # Top-level falsy non-``None`` values must raise rather than being
        # coerced to ``{}`` (which would bypass the top-level validator and
        # silently disable RBAC).  (Empty file -- which ``safe_load`` returns as
        # ``None`` -- is still a legitimate "no mappings" idiom and is covered by
        # ``test_load_group_mapping_empty_file_returns_empty``.)
        ("false\n", "top-level must be a mapping"),
        ("0\n", "top-level must be a mapping"),
        ("[]\n", "top-level must be a mapping"),
        ("''\n", "top-level must be a mapping"),
        ("groups: not_a_list", "'groups' must be a list"),
        # The key-present-but-falsy cases MUST raise so an operator typo is loud,
        # not silent: a ``groups or []`` idiom would swallow these and disable
        # RBAC.
        ("groups: {}", "'groups' must be a list"),
        ("groups: ''", "'groups' must be a list"),
        ("groups: false", "'groups' must be a list"),
        ("groups: 0", "'groups' must be a list"),
        ("groups:\n  - 'a string'", "must be a mapping"),
        ("groups:\n  - {}", "must have a non-empty string 'name'"),
        ("groups:\n  - name: 42", "must have a non-empty string 'name'"),
        ("groups:\n  - name: ''", "must have a non-empty string 'name'"),
        # ``is_superuser`` is a privilege boundary; a quoted "true" is a
        # truthy string that would silently promote everyone in a role.
        ("groups:\n  - name: g\n    is_superuser: 'true'", "'is_superuser' must be a YAML bool"),
        ("groups:\n  - name: g\n    is_superuser: 1", "'is_superuser' must be a YAML bool"),
        ("groups:\n  - name: g\n    is_superuser: yes-please", "'is_superuser' must be a YAML bool"),
        # ``nautobot_permissions`` must be a mapping; a list or string would
        # blow up later with an opaque TypeError when iterated as a dict.
        ("groups:\n  - name: g\n    nautobot_permissions: not-a-mapping", "'nautobot_permissions' must be a mapping"),
        ("groups:\n  - name: g\n    nautobot_permissions:\n      - view", "'nautobot_permissions' must be a mapping"),
    ],
)
def test_load_group_mapping_validation_errors(rbac, tmp_path, body, fragment):
    path = tmp_path / "m.yaml"
    path.write_text(body)
    with pytest.raises(rbac.GroupMappingParseError) as exc:
        rbac.load_group_mapping(str(path))
    assert fragment in str(exc.value)


@pytest.mark.parametrize(
    "body",
    [
        # Key absent entirely.
        "other_key: foo\n",
        # Explicit empty list.
        "groups: []\n",
        # Explicit YAML null (idiomatic "key present, no value").
        "groups: null\n",
        "groups:\n",  # bare key with no value also parses to null
    ],
)
def test_load_group_mapping_unconfigured_returns_empty(rbac, tmp_path, body):
    """The "feature unconfigured" idioms must return ``{}`` without raising.

    These are distinct from ``groups: {}`` / ``groups: ""`` which DO raise
    (see ``test_load_group_mapping_validation_errors``): absent / null /
    empty-list are all "no entries, RBAC stays off", but any other shape
    is an operator typo and must surface.
    """
    path = tmp_path / "m.yaml"
    path.write_text(body)
    assert rbac.load_group_mapping(str(path)) == {}


def test_load_group_mapping_accepts_explicit_is_superuser_false(rbac, tmp_path):
    """Real ``false`` (not ``"false"``) is valid -- only quoted booleans fail."""
    path = tmp_path / "m.yaml"
    path.write_text("groups:\n  - name: g\n    is_superuser: false\n")
    out = rbac.load_group_mapping(str(path))
    assert out["g"]["is_superuser"] is False


def test_load_group_mapping_accepts_empty_nautobot_permissions_mapping(rbac, tmp_path):
    """An empty ``nautobot_permissions: {}`` is valid -- just no perms applied."""
    path = tmp_path / "m.yaml"
    path.write_text("groups:\n  - name: g\n    nautobot_permissions: {}\n")
    out = rbac.load_group_mapping(str(path))
    assert out["g"]["nautobot_permissions"] == {}


def test_load_group_mapping_yaml_parse_error_wrapped(rbac, tmp_path):
    path = tmp_path / "m.yaml"
    path.write_text(":\n :: bogus")  # invalid YAML
    with pytest.raises(rbac.GroupMappingParseError):
        rbac.load_group_mapping(str(path))


def test_load_group_mapping_invalid_utf8_wrapped_as_read_error(rbac, tmp_path):
    """Non-UTF8 bytes must surface as ``GroupMappingReadError`` so the
    caller's fail-closed path runs.  A bare ``open(...)`` would let
    ``UnicodeDecodeError`` propagate past ``except GroupMappingError`` in
    ``_get_or_create_user_from_claims`` and crash the login.
    """
    path = tmp_path / "m.yaml"
    # 0xff is invalid as a leading byte in UTF-8.
    path.write_bytes(b"groups:\n  - name: g\n    \xff invalid utf8\n")
    with pytest.raises(rbac.GroupMappingReadError) as exc:
        rbac.load_group_mapping(str(path))
    # ``GroupMappingReadError`` derives from ``GroupMappingError`` so the
    # existing caller catches it without changes.
    assert isinstance(exc.value, rbac.GroupMappingError)


def test_load_group_mapping_directory_at_path_wrapped_as_read_error(rbac, tmp_path):
    """A directory at the mapping path -- e.g. an operator mistake with
    ``mountPath`` -- must not crash with a raw ``IsADirectoryError``.
    """
    target = tmp_path / "m.yaml"
    target.mkdir()
    with pytest.raises(rbac.GroupMappingReadError):
        rbac.load_group_mapping(str(target))


def test_load_group_mapping_permission_denied_wrapped_as_read_error(rbac, tmp_path):
    """An unreadable file (e.g. mode 000) must wrap ``PermissionError``."""
    path = tmp_path / "m.yaml"
    path.write_text("groups: []\n")
    path.chmod(0o000)
    try:
        # Skip the test if the runner is root (chmod is a no-op for uid 0).
        if os.access(str(path), os.R_OK):
            pytest.skip("running as root; permission bits are ignored")
        with pytest.raises(rbac.GroupMappingReadError):
            rbac.load_group_mapping(str(path))
    finally:
        # Restore so pytest can clean tmp_path up.
        path.chmod(0o600)


def test_load_group_mapping_toctou_file_vanishes_returns_empty(rbac, tmp_path, monkeypatch):
    """If the file is deleted between an external ``isfile()``-style check
    and ``open()`` -- e.g. a ConfigMap remount race during ``helm upgrade``
    -- the loader treats it identically to "file never existed" and
    returns ``{}``.  ``mapping_is_configured()`` will already have
    reported True (env-var set or file-was-present), so the caller still
    runs the empty-mapping revocation/demotion path.
    """
    path = tmp_path / "race.yaml"
    real_open = open

    def _open_then_vanish(*args, **kwargs):
        raise FileNotFoundError(2, "No such file or directory", str(path))

    monkeypatch.setattr("builtins.open", _open_then_vanish)
    assert rbac.load_group_mapping(str(path)) == {}
    # restore so subsequent tests aren't affected by the monkeypatch
    monkeypatch.setattr("builtins.open", real_open)


def test_load_group_mapping_path_defaults_to_env_var(rbac, tmp_path, monkeypatch):
    path = tmp_path / "via-env.yaml"
    path.write_text("groups:\n  - name: from-env\n")
    monkeypatch.setenv("NV_CONFIG_MANAGER_GROUP_MAPPING_PATH", str(path))
    assert "from-env" in rbac.load_group_mapping()


# ── is_superuser_per_mapping ───────────────────────────────────────────────


def test_is_superuser_per_mapping_true_when_any_matched_group_is_super(rbac):
    mapping = {
        "ipam-rw": {"name": "ipam-rw"},
        "admins": {"name": "admins", "is_superuser": True},
    }
    assert rbac.is_superuser_per_mapping({"ipam-rw", "admins"}, mapping) is True


def test_is_superuser_per_mapping_false_when_no_matched_super_group(rbac):
    mapping = {
        "ipam-rw": {"name": "ipam-rw"},
        "admins": {"name": "admins", "is_superuser": True},
    }
    # only the non-super group matches
    assert rbac.is_superuser_per_mapping({"ipam-rw"}, mapping) is False


def test_is_superuser_per_mapping_ignores_unmapped_token_groups(rbac):
    mapping = {"admins": {"name": "admins", "is_superuser": True}}
    # token has 'admins' AND something else; only 'admins' is in mapping → True
    assert rbac.is_superuser_per_mapping({"admins", "other"}, mapping) is True
    # token doesn't have 'admins' at all
    assert rbac.is_superuser_per_mapping({"other"}, mapping) is False


def test_is_superuser_per_mapping_empty_mapping_returns_false(rbac):
    assert rbac.is_superuser_per_mapping({"admins"}, {}) is False


# ── mapping_is_configured ──────────────────────────────────────────────────


def test_mapping_is_configured_false_when_no_env_var_and_no_file(rbac, monkeypatch, tmp_path):
    """Unconfigured: env var unset AND default path absent -> feature is off."""
    monkeypatch.delenv("NV_CONFIG_MANAGER_GROUP_MAPPING_PATH", raising=False)
    # Point the helper at a path that definitely doesn't exist.
    assert rbac.mapping_is_configured(str(tmp_path / "does-not-exist.yaml")) is False


def test_mapping_is_configured_true_when_file_exists(rbac, monkeypatch, tmp_path):
    """The Helm chart mounts the ConfigMap whenever groupMapping is set.
    File existence at the standard path is the operator's opt-in signal."""
    monkeypatch.delenv("NV_CONFIG_MANAGER_GROUP_MAPPING_PATH", raising=False)
    path = tmp_path / "m.yaml"
    path.write_text("groups: []\n")
    assert rbac.mapping_is_configured(str(path)) is True


def test_mapping_is_configured_true_when_env_var_set_even_if_file_missing(rbac, monkeypatch, tmp_path):
    """Explicit env var = operator opt-in.  Don't let a transient mount gap
    silently disable the feature -- the caller will see an empty load and
    run the revocation path, which is the safer behavior."""
    monkeypatch.setenv("NV_CONFIG_MANAGER_GROUP_MAPPING_PATH", str(tmp_path / "absent.yaml"))
    assert rbac.mapping_is_configured() is True


def test_mapping_is_configured_true_when_file_exists_but_empty(rbac, monkeypatch, tmp_path):
    """The "configured + empty content" state: groupMapping: [] is the explicit
    revoke-everyone idiom.  Configuration intent != current content."""
    monkeypatch.delenv("NV_CONFIG_MANAGER_GROUP_MAPPING_PATH", raising=False)
    path = tmp_path / "m.yaml"
    path.write_text("")  # empty file
    assert rbac.mapping_is_configured(str(path)) is True


# ── _resolve_content_types ─────────────────────────────────────────────────


def _ct(app_label: str, model: str) -> _FakeCT:
    """Shape a hashable ContentType-like object for the mocked manager."""
    return _FakeCT(app_label=app_label, model=model)


@pytest.fixture
def patched_content_type_manager(rbac, monkeypatch):
    """Stub :class:`ContentType.objects` with deterministic responses."""
    universe = [
        _ct("ipam", "ipaddress"),
        _ct("ipam", "prefix"),
        _ct("dcim", "device"),
        _ct("sessions", "session"),  # excluded from "all"
        _ct("admin", "logentry"),  # excluded from "all"
    ]

    objects = MagicMock()
    objects.all.return_value = list(universe)

    def _filter(**kw):
        return [ct for ct in universe if ct.app_label == kw["app_label"]]

    objects.filter = MagicMock(side_effect=_filter)

    def _get(*, app_label, model):
        for ct in universe:
            if ct.app_label == app_label and ct.model == model:
                return ct
        raise rbac.ContentType.DoesNotExist

    objects.get = MagicMock(side_effect=_get)
    monkeypatch.setattr(rbac.ContentType, "objects", objects)
    return objects


def test_resolve_content_types_empty(rbac, patched_content_type_manager):
    assert rbac._resolve_content_types([]) == []


def test_resolve_content_types_all_excludes_internal_models(rbac, patched_content_type_manager):
    resolved = rbac._resolve_content_types(["all"])
    labels = {f"{ct.app_label}.{ct.model}" for ct in resolved}
    assert "ipam.ipaddress" in labels
    assert "dcim.device" in labels
    # the internal models are filtered out
    assert "sessions.session" not in labels
    assert "admin.logentry" not in labels


def test_resolve_content_types_app_wildcard(rbac, patched_content_type_manager):
    resolved = rbac._resolve_content_types(["ipam.*"])
    assert {f"{ct.app_label}.{ct.model}" for ct in resolved} == {
        "ipam.ipaddress",
        "ipam.prefix",
    }


def test_resolve_content_types_exact_model(rbac, patched_content_type_manager):
    resolved = rbac._resolve_content_types(["dcim.device"])
    assert [(ct.app_label, ct.model) for ct in resolved] == [("dcim", "device")]


def test_resolve_content_types_unknown_model_is_skipped_not_raised(rbac, patched_content_type_manager, caplog):
    with caplog.at_level("WARNING", logger="nv_config_manager_auth.rbac"):
        out = rbac._resolve_content_types(["dcim.device", "ipam.nope"])
    assert [(c.app_label, c.model) for c in out] == [("dcim", "device")]
    assert any("ipam.nope" in r.message for r in caplog.records)


def test_resolve_content_types_malformed_entry_is_skipped(rbac, patched_content_type_manager, caplog):
    with caplog.at_level("WARNING", logger="nv_config_manager_auth.rbac"):
        out = rbac._resolve_content_types(["dcim.device", "not_a_model", 42])
    assert [(c.app_label, c.model) for c in out] == [("dcim", "device")]
    # both malformed entries produce a warning
    assert sum("malformed content_type" in r.message for r in caplog.records) == 2


@pytest.mark.parametrize(
    "bad_entry",
    [
        "ipam.prefix.*",  # multi-dot: would otherwise silently widen to ipam.*
        "ipam.foo.bar",  # multi-dot: not a valid app.model name
        "ipam.",  # empty model
        ".prefix",  # empty app
        "..",  # both empty
        ".",  # both empty, different shape
    ],
)
def test_resolve_content_types_rejects_multi_dot_and_empty_halves(
    rbac, patched_content_type_manager, caplog, bad_entry
):
    """Tightened parser: only ``app.model`` or ``app.*`` are accepted.

    A naive parser that split on the first ``.`` and accepted any ``model``
    ending in ``.*`` would let a typo like ``"ipam.prefix.*"`` silently widen
    access to the entire ``ipam`` app.  These shapes now log a
    warning and contribute zero content types, never reaching the DB filter.
    """
    filter_calls_before = patched_content_type_manager.filter.call_count
    with caplog.at_level("WARNING", logger="nv_config_manager_auth.rbac"):
        out = rbac._resolve_content_types([bad_entry])
    assert out == []
    assert any("malformed content_type" in r.message and bad_entry in r.message for r in caplog.records)
    # Critical: the malformed entry must not have triggered any app-wide
    # ContentType.objects.filter(app_label=...) -- that is the exact silent-
    # widening regression we are guarding against.
    assert patched_content_type_manager.filter.call_count == filter_calls_before


def test_resolve_content_types_does_not_widen_on_prefix_wildcard_typo(rbac, patched_content_type_manager):
    """Guard: ``"ipam.prefix.*"`` must resolve to nothing (not all of ipam),
    while the valid entries are still resolved."""
    out = rbac._resolve_content_types(["dcim.device", "ipam.prefix.*", "ipam.ipaddress"])
    resolved = {(c.app_label, c.model) for c in out}
    assert resolved == {("dcim", "device"), ("ipam", "ipaddress")}
    # In particular, the ipam.prefix model is NOT present -- the typo gave
    # back zero ipam types from the bad entry; ipam.prefix only enters if
    # the operator explicitly lists it or uses "ipam.*".
    assert ("ipam", "prefix") not in resolved


# ── sync_groups_and_permissions (high-level wiring) ────────────────────────


def test_sync_runs_revocation_when_mapping_empty(rbac, monkeypatch):
    """Caller is responsible for the "feature configured" gate -- this
    function deliberately does NOT short-circuit on an empty mapping.

    An empty mapping is the explicit "operator wrote groupMapping: [] to
    revoke everyone" idiom (and the load-failed fail-closed fallback).
    Passes 1+2 become no-ops (no entries to add/keep), but pass 3 still
    runs so previously-managed Django Group memberships and managed
    ObjectPermissions are pruned -- which is the whole point of allowing
    revocation by removing entries.
    """
    monkeypatch.setattr(rbac, "_sync_group_permissions", MagicMock())
    monkeypatch.setattr(rbac, "_sync_group_memberships", MagicMock())
    monkeypatch.setattr(rbac, "_revoke_removed_mapping_groups", MagicMock())

    user = MagicMock()
    rbac.sync_groups_and_permissions(user, {"any-group"}, mapping={})

    # Passes 1+2 still get called but with empty intersections -- no-ops.
    assert rbac._sync_group_permissions.call_args.args[0] == set()
    assert rbac._sync_group_memberships.call_args.args[1] == set()
    # Pass 3 is the active revoke path on an empty mapping.
    rbac._revoke_removed_mapping_groups.assert_called_once_with(user, set())


def test_sync_ignores_groups_not_in_mapping(rbac, monkeypatch):
    """Token roles outside the mapping never reach the per-mapping sync paths."""
    monkeypatch.setattr(rbac, "_sync_group_permissions", MagicMock())
    monkeypatch.setattr(rbac, "_sync_group_memberships", MagicMock())
    monkeypatch.setattr(rbac, "_revoke_removed_mapping_groups", MagicMock())

    mapping = {"managed": {"name": "managed"}}
    user = MagicMock()
    rbac.sync_groups_and_permissions(user, {"managed", "ignored"}, mapping=mapping)

    # The promote/keep paths see only the intersection.
    assert rbac._sync_group_permissions.call_args.args[0] == {"managed"}
    assert rbac._sync_group_memberships.call_args.args[1] == {"managed"}
    # The revoke pass gets the full set of managed names so it can detect
    # Django groups the user is in that are NOT in the current mapping.
    assert rbac._revoke_removed_mapping_groups.call_args.args == (user, {"managed"})


def test_sync_group_memberships_only_touches_managed_groups(rbac, monkeypatch):
    """Manual groups outside the mapping must not be removed."""
    mapping = {"managed": {"name": "managed"}}
    # user is already in "managed" (per mapping) and "manual-admin" (NOT in mapping)
    user = MagicMock()
    managed_filter = MagicMock()
    managed_filter.values_list = MagicMock(return_value=["managed"])
    user.groups.filter = MagicMock(return_value=managed_filter)

    monkeypatch.setattr(rbac.Group, "objects", MagicMock())
    rbac._sync_group_memberships(user, set(), mapping)

    # user has "managed" but token no longer carries it → remove from "managed"
    rbac.Group.objects.filter.assert_called_with(name__in={"managed"})
    user.groups.remove.assert_called_once()
    user.groups.add.assert_not_called()
    # The filter call we issued to read current state was restricted to
    # managed_names -- this is what guarantees we don't touch manual groups.
    user.groups.filter.assert_called_with(name__in={"managed"})


def test_sync_group_memberships_warns_when_group_missing_in_django(rbac, monkeypatch, caplog):
    """Operator-managed group lifecycle: we never create groups, only add
    users to ones that already exist.  A mapping entry without a corresponding
    Django Group should produce a WARNING, not an error."""
    mapping = {"new-role": {"name": "new-role"}}
    user = MagicMock()
    user.username = "alice"
    # User isn't currently in any managed groups...
    current_filter = MagicMock()
    current_filter.values_list = MagicMock(return_value=[])
    user.groups.filter = MagicMock(return_value=current_filter)
    # ...and the Django Group doesn't exist yet.
    addable_qs = MagicMock()
    addable_qs.values_list = MagicMock(return_value=[])
    addable_qs.__bool__ = lambda self: False
    monkeypatch.setattr(
        rbac.Group,
        "objects",
        MagicMock(filter=MagicMock(return_value=addable_qs)),
    )

    with caplog.at_level("WARNING", logger="nv_config_manager_auth.rbac"):
        rbac._sync_group_memberships(user, {"new-role"}, mapping)

    user.groups.add.assert_not_called()
    assert any("non-existent Django groups" in r.message and "new-role" in r.message for r in caplog.records)


def test_sync_group_permissions_applies_perms_to_existing_group(rbac, monkeypatch, patched_content_type_manager):
    """Per-action ObjectPermissions are created and attached to the operator-
    managed Django Group that already exists in Nautobot."""
    mapping = {
        "ipam-rw": {
            "name": "ipam-rw",
            "nautobot_permissions": {
                "view": {"content_types": ["all"]},
                "change": {"content_types": ["ipam.*"], "constraints": {"status__name": "Active"}},
            },
        }
    }
    group = MagicMock()
    group.name = "ipam-rw"
    group.object_permissions.all.return_value = []
    monkeypatch.setattr(
        rbac.Group,
        "objects",
        MagicMock(get=MagicMock(return_value=group)),
    )

    created_perms: list[MagicMock] = []

    def _make_perm(**kw):
        perm = MagicMock()
        perm.name = kw["name"]
        perm.actions = list(kw["defaults"].get("actions", []))
        perm.constraints = dict(kw["defaults"].get("constraints", {}))
        perm.object_types.all.return_value = []
        perm.groups.all.return_value = []
        created_perms.append(perm)
        return (perm, True)

    monkeypatch.setattr(
        rbac.ObjectPermission,
        "objects",
        MagicMock(update_or_create=MagicMock(side_effect=_make_perm)),
    )

    rbac._sync_group_permissions({"ipam-rw"}, mapping)

    names = sorted(p.name for p in created_perms)
    assert names == ["ipam-rw_change", "ipam-rw_view"]

    change_perm = next(p for p in created_perms if p.name == "ipam-rw_change")
    assert change_perm.constraints == {"status__name": "Active"}
    change_perm.object_types.set.assert_called_once()
    args = change_perm.object_types.set.call_args.args[0]
    assert {(c.app_label, c.model) for c in args} == {("ipam", "ipaddress"), ("ipam", "prefix")}


def test_sync_group_permissions_skips_with_warning_when_group_missing(rbac, monkeypatch, caplog):
    """Default operator-managed mode: missing groups are logged and skipped."""
    monkeypatch.delenv("NV_CONFIG_MANAGER_AUTO_CREATE_GROUPS", raising=False)
    mapping = {
        "new-role": {
            "name": "new-role",
            "nautobot_permissions": {"view": {"content_types": ["all"]}},
        }
    }
    monkeypatch.setattr(
        rbac.Group,
        "objects",
        MagicMock(get=MagicMock(side_effect=rbac.Group.DoesNotExist)),
    )
    create_mock = MagicMock()
    monkeypatch.setattr(rbac.ObjectPermission, "objects", MagicMock(create=create_mock))

    with caplog.at_level("WARNING", logger="nv_config_manager_auth.rbac"):
        rbac._sync_group_permissions({"new-role"}, mapping)

    create_mock.assert_not_called()
    assert any("does not exist in Nautobot" in r.message and "new-role" in r.message for r in caplog.records)


@pytest.mark.parametrize("truthy", ["true", "True", "1", "yes", "ON"])
def test_auto_create_groups_truthy(rbac, monkeypatch, truthy):
    monkeypatch.setenv("NV_CONFIG_MANAGER_AUTO_CREATE_GROUPS", truthy)
    assert rbac._auto_create_groups() is True


@pytest.mark.parametrize("falsy", ["", "false", "0", "no", "off", "anything-else"])
def test_auto_create_groups_falsy(rbac, monkeypatch, falsy):
    monkeypatch.setenv("NV_CONFIG_MANAGER_AUTO_CREATE_GROUPS", falsy)
    assert rbac._auto_create_groups() is False


def test_auto_create_groups_unset_defaults_false(rbac, monkeypatch):
    monkeypatch.delenv("NV_CONFIG_MANAGER_AUTO_CREATE_GROUPS", raising=False)
    assert rbac._auto_create_groups() is False


def test_sync_group_permissions_auto_creates_when_enabled(rbac, monkeypatch, patched_content_type_manager, caplog):
    """``NV_CONFIG_MANAGER_AUTO_CREATE_GROUPS=true``: missing Django Groups are created."""
    monkeypatch.setenv("NV_CONFIG_MANAGER_AUTO_CREATE_GROUPS", "true")
    mapping = {
        "new-role": {
            "name": "new-role",
            "nautobot_permissions": {"view": {"content_types": ["all"]}},
        }
    }
    created_group = MagicMock()
    created_group.name = "new-role"
    created_group.object_permissions.all.return_value = []

    get_or_create_mock = MagicMock(return_value=(created_group, True))
    monkeypatch.setattr(rbac.Group, "objects", MagicMock(get_or_create=get_or_create_mock))

    new_perm = MagicMock()
    new_perm.actions = ["view"]
    new_perm.constraints = {}
    new_perm.object_types.all.return_value = []
    new_perm.groups.all.return_value = [created_group]
    monkeypatch.setattr(
        rbac.ObjectPermission,
        "objects",
        MagicMock(update_or_create=MagicMock(return_value=(new_perm, True))),
    )

    with caplog.at_level("INFO", logger="nv_config_manager_auth.rbac"):
        rbac._sync_group_permissions({"new-role"}, mapping)

    get_or_create_mock.assert_called_once_with(name="new-role")
    assert any("auto-created Django Group" in r.message and "new-role" in r.message for r in caplog.records)


def test_sync_group_permissions_auto_create_existing_group_no_log(
    rbac, monkeypatch, patched_content_type_manager, caplog
):
    """When auto-create is on but group already exists, no creation log."""
    monkeypatch.setenv("NV_CONFIG_MANAGER_AUTO_CREATE_GROUPS", "true")
    mapping = {
        "ipam-rw": {
            "name": "ipam-rw",
            "nautobot_permissions": {"view": {"content_types": ["all"]}},
        }
    }
    existing_group = MagicMock()
    existing_group.name = "ipam-rw"
    existing_group.object_permissions.all.return_value = []
    monkeypatch.setattr(
        rbac.Group,
        "objects",
        MagicMock(get_or_create=MagicMock(return_value=(existing_group, False))),
    )
    monkeypatch.setattr(
        rbac.ObjectPermission,
        "objects",
        MagicMock(
            update_or_create=MagicMock(
                return_value=(MagicMock(actions=["view"], constraints={}), True),
            )
        ),
    )

    with caplog.at_level("INFO", logger="nv_config_manager_auth.rbac"):
        rbac._sync_group_permissions({"ipam-rw"}, mapping)

    assert not any("auto-created" in r.message for r in caplog.records)


def test_sync_group_permissions_skips_perms_block_for_superuser_group(rbac, monkeypatch):
    """``is_superuser: true`` entries don't need per-action permissions."""
    mapping = {"admins": {"name": "admins", "is_superuser": True}}
    group = MagicMock()
    group.name = "admins"
    group.object_permissions.all.return_value = []
    monkeypatch.setattr(
        rbac.Group,
        "objects",
        MagicMock(get=MagicMock(return_value=group)),
    )

    create_mock = MagicMock()
    monkeypatch.setattr(rbac.ObjectPermission, "objects", MagicMock(create=create_mock))

    rbac._sync_group_permissions({"admins"}, mapping)
    create_mock.assert_not_called()


def test_apply_group_permission_config_uses_update_or_create_for_upsert_safety(
    rbac, monkeypatch, patched_content_type_manager
):
    """Concurrent logins for the same group must not race the create path.

    A naive implementation that snapshotted ``group.object_permissions.all()``
    and then branched on "is this name in the snapshot?" would let two concurrent
    logins both miss the snapshot and both INSERT, one winning, the
    other tripping ``IntegrityError`` and rolling back the whole sync
    transaction.  Even a follow-up ``get_or_create`` fallback left the path
    half-cooked because the snapshot could also hand back a row another
    transaction had already deleted, then we'd ``save()`` a phantom.

    The fix collapses both branches to a single ``update_or_create`` keyed
    by ``name``, which Django wraps in a savepoint with retry-on-conflict.
    The snapshot is then used purely for prune accounting.
    """
    group = MagicMock()
    group.name = "ipam-rw"

    # Whether the snapshot sees the row or not is irrelevant -- the upsert
    # path must always go through update_or_create, never through the
    # snapshot's in-memory perm reference.
    snapshot_perm = MagicMock(name="snapshot_phantom")
    snapshot_perm.name = "ipam-rw_view"
    group.object_permissions.all.return_value = [snapshot_perm]

    fresh = MagicMock()
    fresh.actions = ["view"]
    fresh.constraints = {}
    fresh.object_types.all.return_value = []
    fresh.groups.all.return_value = []  # exercise the .add() reconciliation path

    update_or_create = MagicMock(return_value=(fresh, False))
    get_or_create_mock = MagicMock()
    create_mock = MagicMock()
    monkeypatch.setattr(
        rbac.ObjectPermission,
        "objects",
        MagicMock(
            update_or_create=update_or_create,
            get_or_create=get_or_create_mock,
            create=create_mock,
        ),
    )

    rbac._apply_group_permission_config(group, {"view": {"content_types": ["all"]}})

    update_or_create.assert_called_once()
    kwargs = update_or_create.call_args.kwargs
    assert kwargs["name"] == "ipam-rw_view"
    assert kwargs["defaults"]["actions"] == ["view"]
    assert kwargs["defaults"]["constraints"] == {}

    # Neither the racy plain create() nor the half-baked snapshot+get_or_create
    # fallback should ever be reached.
    create_mock.assert_not_called()
    get_or_create_mock.assert_not_called()

    # And critically: the row returned by update_or_create is what gets
    # reconciled, not the snapshot's possibly-stale in-memory phantom.
    fresh.groups.add.assert_called_once_with(group)
    snapshot_perm.save.assert_not_called()


def test_apply_group_permission_config_ignores_stale_snapshot_phantom(rbac, monkeypatch, patched_content_type_manager):
    """If the snapshot contains a managed perm name but the row was deleted
    by another transaction between snapshot and upsert, we still go through
    ``update_or_create`` and the snapshot's in-memory object is never
    save()'d, never groups.add()'d -- the phantom is invisible to the upsert
    branch entirely.
    """
    group = MagicMock()
    group.name = "ipam-rw"
    phantom = MagicMock()
    phantom.name = "ipam-rw_view"
    phantom.actions = ["view"]
    phantom.constraints = {}
    group.object_permissions.all.return_value = [phantom]

    fresh = MagicMock()
    fresh.actions = ["view"]
    fresh.constraints = {}
    fresh.object_types.all.return_value = []
    fresh.groups.all.return_value = []
    monkeypatch.setattr(
        rbac.ObjectPermission,
        "objects",
        MagicMock(update_or_create=MagicMock(return_value=(fresh, True))),
    )

    rbac._apply_group_permission_config(group, {"view": {"content_types": ["all"]}})

    # All writes target the fresh row from update_or_create.
    fresh.groups.add.assert_called_once_with(group)
    # The phantom is NOT touched -- no save(), no groups.add().
    phantom.save.assert_not_called()
    phantom.groups.add.assert_not_called()


def test_apply_group_permission_config_prunes_stale_managed_perms(rbac, monkeypatch, patched_content_type_manager):
    """ObjectPermissions named "<group>_<action>" but not in current config are removed."""
    group = MagicMock()
    group.name = "ipam-rw"
    keep = MagicMock()
    keep.name = "ipam-rw_view"
    keep.actions = ["view"]
    keep.constraints = {}
    keep.object_types.all.return_value = []
    keep.groups.all.return_value = [group]
    stale = MagicMock()
    stale.name = "ipam-rw_delete"
    stale.groups.exists.return_value = False
    manual = MagicMock()
    manual.name = "my-custom-perm"
    group.object_permissions.all.return_value = [keep, stale, manual]

    monkeypatch.setattr(
        rbac.ObjectPermission,
        "objects",
        MagicMock(update_or_create=MagicMock(return_value=(keep, False))),
    )

    rbac._apply_group_permission_config(group, {"view": {"content_types": ["all"]}})

    stale.groups.remove.assert_called_once_with(group)
    stale.delete.assert_called_once()
    manual.groups.remove.assert_not_called()
    manual.delete.assert_not_called()


def test_apply_group_permission_config_warns_on_bad_action_shape(
    rbac, monkeypatch, patched_content_type_manager, caplog
):
    """A non-mapping action config is logged and skipped, not raised."""
    group = MagicMock()
    group.name = "g"
    group.object_permissions.all.return_value = []
    monkeypatch.setattr(rbac.ObjectPermission, "objects", MagicMock(create=MagicMock()))

    with caplog.at_level("WARNING", logger="nv_config_manager_auth.rbac"):
        rbac._apply_group_permission_config(group, {"view": "not-a-mapping"})

    assert any("must be a mapping" in r.message for r in caplog.records)
    rbac.ObjectPermission.objects.create.assert_not_called()


# ── _revoke_removed_mapping_groups ─────────────────────────────────────────


def _mock_user_with_groups(*groups: MagicMock) -> MagicMock:
    """Return a user whose ``groups.exclude(name__in=...)`` returns the
    supplied groups *minus* those whose names appear in the exclusion list.
    """
    user = MagicMock()
    user.username = "alice"

    def _exclude(name__in):
        return [g for g in groups if g.name not in name__in]

    user.groups.exclude = MagicMock(side_effect=_exclude)
    return user


def _mock_group(name: str, perm_names: list[str]) -> MagicMock:
    """Build a Group mock whose ``object_permissions.all()`` returns mock
    ObjectPermissions with the given names."""
    group = MagicMock()
    group.name = name
    perms = []
    for pname in perm_names:
        perm = MagicMock()
        perm.name = pname
        # By default, after the user is detached, no other group references it.
        perm.groups.exists.return_value = False
        perms.append(perm)
    group.object_permissions.all.return_value = perms
    return group


def test_revoke_removed_mapping_groups_revokes_and_prunes(rbac):
    """User in a Django group not in the mapping, group has managed perms
    matching ``<group>_<action>`` -- the user is removed and the managed
    perms are detached + deleted."""
    retired = _mock_group("retired-net", ["retired-net_view", "retired-net_change"])
    user = _mock_user_with_groups(retired)

    rbac._revoke_removed_mapping_groups(user, current_managed_names={"ipam-rw"})

    user.groups.remove.assert_called_once_with(retired)
    for perm in retired.object_permissions.all():
        perm.groups.remove.assert_called_once_with(retired)
        perm.delete.assert_called_once()


def test_revoke_removed_mapping_groups_leaves_manual_groups_alone(rbac):
    """User in a Django group not in the mapping with NO managed perms is a
    purely-manual group and must not be touched."""
    manual = _mock_group("manual-admin", ["my-custom-perm", "another-thing"])
    user = _mock_user_with_groups(manual)

    rbac._revoke_removed_mapping_groups(user, current_managed_names={"ipam-rw"})

    user.groups.remove.assert_not_called()
    for perm in manual.object_permissions.all():
        perm.groups.remove.assert_not_called()
        perm.delete.assert_not_called()


def test_revoke_removed_mapping_groups_keeps_perm_when_other_groups_reference_it(rbac):
    """If the managed perm is still attached to another group after detaching
    us, it must be left in the database (not deleted)."""
    retired = _mock_group("retired-net", ["retired-net_view"])
    shared_perm = retired.object_permissions.all()[0]
    shared_perm.groups.exists.return_value = True  # someone else still references it
    user = _mock_user_with_groups(retired)

    rbac._revoke_removed_mapping_groups(user, current_managed_names=set())

    shared_perm.groups.remove.assert_called_once_with(retired)
    shared_perm.delete.assert_not_called()


def test_revoke_removed_mapping_groups_keeps_unrelated_perms(rbac):
    """Only perms whose name starts with ``<group>_`` are pruned; manually-
    added perms on the same group survive."""
    retired = MagicMock()
    retired.name = "retired-net"
    managed = MagicMock()
    managed.name = "retired-net_view"
    managed.groups.exists.return_value = False
    manual = MagicMock()
    manual.name = "totally-custom"
    retired.object_permissions.all.return_value = [managed, manual]
    user = _mock_user_with_groups(retired)

    rbac._revoke_removed_mapping_groups(user, current_managed_names=set())

    user.groups.remove.assert_called_once_with(retired)
    managed.groups.remove.assert_called_once_with(retired)
    managed.delete.assert_called_once()
    manual.groups.remove.assert_not_called()
    manual.delete.assert_not_called()


def test_revoke_removed_mapping_groups_skips_groups_still_in_mapping(rbac):
    """Groups currently in the mapping must never reach the revoke pass."""
    kept = _mock_group("ipam-rw", ["ipam-rw_view"])  # still mapped
    user = _mock_user_with_groups(kept)

    rbac._revoke_removed_mapping_groups(user, current_managed_names={"ipam-rw"})

    user.groups.exclude.assert_called_once_with(name__in={"ipam-rw"})
    user.groups.remove.assert_not_called()


def test_revoke_removed_mapping_groups_ignores_bare_group_name_perm(rbac):
    """A perm literally named ``"<group_name>_"`` (action half empty) is not a
    valid managed marker -- defensive guard against weirdly-named perms."""
    retired = MagicMock()
    retired.name = "retired-net"
    odd = MagicMock()
    odd.name = "retired-net_"  # no action suffix
    retired.object_permissions.all.return_value = [odd]
    user = _mock_user_with_groups(retired)

    rbac._revoke_removed_mapping_groups(user, current_managed_names=set())

    user.groups.remove.assert_not_called()
    odd.groups.remove.assert_not_called()
