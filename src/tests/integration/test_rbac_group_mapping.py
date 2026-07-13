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
"""Live-cluster tests for group-mapping RBAC (opt-in via --rbac).

These exercise the code paths that unit tests structurally cannot: the JWT
authenticator running the rbac sync during ``authenticate()`` against a real
Nautobot, including Nautobot's change-logging signals firing on
``ObjectPermission.delete()`` in the revoke path. That signal path is exactly
where the ``NoneType has no attribute 'pk'`` regression lived -- it needs a real
DB + a real change-context, so 93 green unit tests never caught it.

The suite assumes a ``make kind-up-sec`` deploy in the CONFIGURED state, i.e.
``nautobot.rbac.groupMapping`` set to the mapping in
``scripts/rbac-local-test/values-configured.yaml``:

    nvcm-network -> view: all, change: dcim.* + ipam.*
    nvcm-admin   -> is_superuser: true

and ``nautobot.rbac.autoCreateGroups: true`` so the managed Django Groups are
created on first login. See conftest ``rbac_*`` fixtures for the plumbing.

Run:
    uv run pytest src/tests/integration/test_rbac_group_mapping.py --rbac -v
"""

import json
import subprocess
import uuid
from collections.abc import Callable

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.rbac]

# Users seeded by scripts/create-local-security-nautobot-users, with the roles
# the local Keycloak realm assigns (password == username).
USER_NETWORK = "nvcm-network"  # roles: [nvcm-network]
USER_ADMIN = "nvcm-admin"  # roles: [nvcm-admin, nvcm-network]

_JSON_MARKER = "RBAC_JSON:"


def _nbshell_json(nbshell: Callable[[str], str], body: str) -> dict:
    """Run *body* in the Django shell and return the dict it emits via ``_emit``.

    *body* must call ``_emit(<dict>)`` exactly once. We prepend a tiny ``_emit``
    helper that prints the result on a single ``RBAC_JSON:{...}`` line, then parse
    the last such line out of stdout (robust to any incidental output).
    """
    script = f"import json\ndef _emit(d): print('{_JSON_MARKER}' + json.dumps(d))\n{body}"
    out = nbshell(script)
    for line in reversed(out.splitlines()):
        line = line.strip()
        if line.startswith(_JSON_MARKER):
            return json.loads(line[len(_JSON_MARKER) :])
    raise AssertionError(f"shell did not emit a {_JSON_MARKER} line. Full output:\n{out}")


def _user_state(nbshell: Callable[[str], str], username: str) -> dict:
    """Return ``{exists, is_superuser, is_active, groups: [...]}`` for *username*."""
    body = (
        "from django.contrib.auth import get_user_model\n"
        "U = get_user_model()\n"
        f"u = U.objects.filter(username={username!r}).first()\n"
        "if u is None:\n"
        "    _emit({'exists': False})\n"
        "else:\n"
        "    _emit({\n"
        "        'exists': True,\n"
        "        'is_superuser': u.is_superuser,\n"
        "        'is_active': u.is_active,\n"
        "        'groups': sorted(u.groups.values_list('name', flat=True)),\n"
        "    })\n"
    )
    return _nbshell_json(nbshell, body)


def _managed_perms(nbshell: Callable[[str], str], group_name: str) -> list[str]:
    """Return the ``<group>_<action>`` ObjectPermission names for *group_name*."""
    body = (
        "from nautobot.users.models import ObjectPermission\n"
        f"names = list(ObjectPermission.objects.filter(name__startswith={group_name + '_'!r})"
        ".values_list('name', flat=True))\n"
        "_emit({'perms': sorted(names)})\n"
    )
    return _nbshell_json(nbshell, body)["perms"]


@pytest.fixture(scope="session")
def rbac_require_configured(
    rbac_enabled: bool,
    config_manager_namespace: str,
    rbac_release: str,
) -> str:
    """Skip the suite unless the group-mapping ConfigMap is mounted (CONFIGURED).

    Returns the ConfigMap name. The suite is meaningless in the UNCONFIGURED
    state (no mapping -> nothing to reconcile), so we skip with a pointer to the
    override rather than emit misleading failures.
    """
    if not rbac_enabled:
        pytest.skip("group-mapping RBAC tests require --rbac")
    configmap = f"{rbac_release}-nautobot-group-mapping"
    res = subprocess.run(
        ["kubectl", "get", "configmap", "-n", config_manager_namespace, configmap],
        capture_output=True,
        text=True,
        check=False,
    )
    if res.returncode != 0:
        pytest.skip(
            f"ConfigMap {configmap!r} not found in namespace {config_manager_namespace!r}; "
            "deploy is not in the CONFIGURED state. Apply "
            "scripts/rbac-local-test/values-configured.yaml (helm upgrade --reuse-values) "
            "or run scripts/rbac-local-test/verify.sh state-c first."
        )
    return configmap


def test_group_mapping_configmap_present(rbac_require_configured: str) -> None:
    """Sanity: the group-mapping ConfigMap is rendered and mounted."""
    assert rbac_require_configured.endswith("-nautobot-group-mapping")


def test_login_grants_managed_group_and_permissions(
    rbac_require_configured: str,
    rbac_api_login: Callable[[str], int],
    rbac_nbshell: Callable[[str], str],
) -> None:
    """A mapped user's login creates the managed Group + ObjectPermissions.

    ``nvcm-network`` carries the ``nvcm-network`` role, which maps to view/change
    permissions. After login the user must belong to the ``nvcm-network`` Django
    Group and the ``nvcm-network_view`` / ``nvcm-network_change`` ObjectPermissions
    must exist (auto-created because ``autoCreateGroups: true``).
    """
    status = rbac_api_login(USER_NETWORK)
    assert status == 200, f"expected authorized 200 for {USER_NETWORK}, got {status}"

    state = _user_state(rbac_nbshell, USER_NETWORK)
    assert state["exists"], f"{USER_NETWORK} was not created by the JWT login"
    assert USER_NETWORK in state["groups"], (
        f"{USER_NETWORK} not added to managed group; groups={state['groups']}"
    )

    perms = _managed_perms(rbac_nbshell, USER_NETWORK)
    assert f"{USER_NETWORK}_view" in perms, f"missing view perm; got {perms}"
    assert f"{USER_NETWORK}_change" in perms, f"missing change perm; got {perms}"


def test_login_sets_superuser_from_mapping(
    rbac_require_configured: str,
    rbac_api_login: Callable[[str], int],
    rbac_nbshell: Callable[[str], str],
) -> None:
    """An ``is_superuser: true`` mapping entry promotes the user on login."""
    status = rbac_api_login(USER_ADMIN)
    assert status == 200, f"expected authorized 200 for {USER_ADMIN}, got {status}"

    state = _user_state(rbac_nbshell, USER_ADMIN)
    assert state["exists"], f"{USER_ADMIN} was not created by the JWT login"
    assert state["is_superuser"], f"{USER_ADMIN} was not promoted to superuser: {state}"


def test_revoke_prunes_stale_managed_group_without_crash(
    rbac_require_configured: str,
    rbac_api_login: Callable[[str], int],
    rbac_nbshell: Callable[[str], str],
) -> None:
    """Regression: the revoke path must delete stale managed perms, not crash.

    We plant a Django Group with a ``<group>_<action>`` ObjectPermission (the
    "previously managed" fingerprint) that is NOT in the current mapping, and add
    ``nvcm-network`` to it. On the next login, ``_revoke_removed_mapping_groups``
    must remove the membership and ``ObjectPermission.delete()`` the stale perm.

    That delete fires Nautobot's change-logging signal, which reads the acting
    user from the change context. Before the fix the sync ran with no bound user,
    so the signal hit ``AttributeError: 'NoneType' object has no attribute 'pk'``
    and -- being ``@transaction.atomic`` -- rolled the whole reconcile back
    (membership + perm survived; login errored). The fix wraps the sync in
    ``web_request_context(user)``. This asserts the post-fix outcome: login
    succeeds AND the stale membership/perm are gone.
    """
    stale_group = f"rbac-it-stale-{uuid.uuid4().hex[:8]}"
    stale_perm = f"{stale_group}_view"

    setup_body = (
        "from django.contrib.auth import get_user_model\n"
        "from django.contrib.auth.models import Group\n"
        "from nautobot.users.models import ObjectPermission\n"
        "U = get_user_model()\n"
        # Ensure the user exists even if this test runs before the grant test.
        f"user, _ = U.objects.get_or_create(username={USER_NETWORK!r})\n"
        f"group, _ = Group.objects.get_or_create(name={stale_group!r})\n"
        f"perm, _ = ObjectPermission.objects.get_or_create(name={stale_perm!r}, "
        "defaults={'actions': ['view']})\n"
        "perm.groups.add(group)\n"
        "user.groups.add(group)\n"
        "_emit({\n"
        "    'user_in_group': group.name in user.groups.values_list('name', flat=True),\n"
        f"    'perm_exists': ObjectPermission.objects.filter(name={stale_perm!r}).exists(),\n"
        "})\n"
    )
    try:
        pre = _nbshell_json(rbac_nbshell, setup_body)
        assert pre["user_in_group"], "precondition: user should be in the stale group"
        assert pre["perm_exists"], "precondition: stale perm should exist"

        # Login triggers the reconcile -> revoke path -> ObjectPermission.delete().
        status = rbac_api_login(USER_NETWORK)
        assert status == 200, (
            f"login regressed to {status}: the revoke path likely crashed on "
            "ObjectPermission.delete() (missing web_request_context user)."
        )

        state = _user_state(rbac_nbshell, USER_NETWORK)
        assert stale_group not in state["groups"], (
            f"stale group membership not revoked (rollback?): groups={state['groups']}"
        )
        remaining = _managed_perms(rbac_nbshell, stale_group)
        assert remaining == [], f"stale ObjectPermission not pruned (rollback?): {remaining}"
    finally:
        cleanup_body = (
            "from django.contrib.auth import get_user_model\n"
            "from django.contrib.auth.models import Group\n"
            "from nautobot.extras.context_managers import web_request_context\n"
            "from nautobot.users.models import ObjectPermission\n"
            # Delete inside a web_request_context bound to a real user: the
            # ObjectPermission.delete() here trips the same change-logging signal
            # the test exercises, so a context-less teardown could crash and mask
            # the real assertion failure.
            f"user = get_user_model().objects.get(username={USER_NETWORK!r})\n"
            "with web_request_context(user, context_detail='nv-config-manager-auth: RBAC integration cleanup'):\n"
            f"    ObjectPermission.objects.filter(name={stale_perm!r}).delete()\n"
            f"    Group.objects.filter(name={stale_group!r}).delete()\n"
            "_emit({'cleaned': True})\n"
        )
        _nbshell_json(rbac_nbshell, cleanup_body)
