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
"""Shared test fixtures for nautobot component tests.

Mocks Django/Nautobot imports so tests can run without a full Django environment.
"""

from __future__ import annotations

import re
import sys
import unicodedata
from contextlib import contextmanager
from types import ModuleType
from unittest.mock import MagicMock

import pytest


def _slugify(value):
    """Minimal reimplementation of django.utils.text.slugify for tests."""
    value = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    value = re.sub(r"[^\w\s-]", "", value).strip().lower()
    return re.sub(r"[-\s]+", "-", value)


def _slugify_dashes_to_underscores(content):
    """Reimplementation of nautobot.core.models.fields.slugify_dashes_to_underscores."""
    if re.fullmatch(r"[_A-Za-z]", content[0]) is None:
        content = "a" + content
    return _slugify(content).replace("-", "_")


# ---------------------------------------------------------------------------
# Stub heavy Django / Nautobot modules before any component code is imported
# ---------------------------------------------------------------------------


def _stub_module(name: str, attrs: dict | None = None) -> ModuleType:
    mod = ModuleType(name)
    for k, v in (attrs or {}).items():
        setattr(mod, k, v)
    sys.modules[name] = mod
    return mod


@pytest.fixture(autouse=True)
def _django_stubs(monkeypatch):
    """Install lightweight stubs for Django and Nautobot modules."""
    stubs: dict[str, ModuleType] = {}

    mock_user_cls = MagicMock()
    mock_user_cls.objects = MagicMock()

    def _get_user_model():
        return mock_user_cls

    stubs["django"] = _stub_module("django")
    stubs["django.conf"] = _stub_module("django.conf", {"settings": MagicMock()})
    stubs["django.contrib"] = _stub_module("django.contrib")
    stubs["django.contrib.auth"] = _stub_module(
        "django.contrib.auth",
        {"get_user_model": _get_user_model, "login": MagicMock()},
    )
    # django.contrib.auth.models.Group + User (for nv_config_manager_auth.rbac)
    mock_group_cls = MagicMock()
    mock_group_cls.DoesNotExist = type("DoesNotExist", (Exception,), {})
    mock_group_cls.objects = MagicMock()
    stubs["django.contrib.auth.models"] = _stub_module(
        "django.contrib.auth.models",
        {"Group": mock_group_cls, "User": mock_user_cls},
    )
    stubs["django.contrib.contenttypes"] = _stub_module("django.contrib.contenttypes")
    mock_ct = MagicMock()
    mock_ct.DoesNotExist = type("DoesNotExist", (Exception,), {})
    stubs["django.contrib.contenttypes.models"] = _stub_module(
        "django.contrib.contenttypes.models",
        {"ContentType": mock_ct},
    )
    # django.db.transaction (nv_config_manager_auth.rbac uses @transaction.atomic as a decorator)
    stubs["django.db"] = _stub_module("django.db")

    def _passthrough_atomic(func=None, *_a, **_kw):
        if callable(func):
            return func
        return lambda f: f

    stubs["django.db.transaction"] = _stub_module(
        "django.db.transaction",
        {"atomic": _passthrough_atomic},
    )
    # nautobot.users.models.ObjectPermission
    mock_obj_perm = MagicMock()
    mock_obj_perm.objects = MagicMock()
    stubs["nautobot.users"] = _stub_module("nautobot.users")
    stubs["nautobot.users.models"] = _stub_module(
        "nautobot.users.models",
        {"ObjectPermission": mock_obj_perm},
    )
    stubs["django.http"] = _stub_module(
        "django.http",
        {"HttpRequest": MagicMock, "HttpResponse": MagicMock},
    )
    stubs["rest_framework"] = _stub_module("rest_framework")
    stubs["rest_framework.authentication"] = _stub_module(
        "rest_framework.authentication",
        {"BaseAuthentication": object},
    )
    stubs["rest_framework.exceptions"] = _stub_module(
        "rest_framework.exceptions",
        {"AuthenticationFailed": Exception},
    )
    stubs["rest_framework.request"] = _stub_module(
        "rest_framework.request",
        {"Request": MagicMock},
    )

    # Nautobot stubs
    for mod_name in [
        "nautobot",
        "nautobot.apps",
        "nautobot.apps.jobs",
        "nautobot.core",
        "nautobot.core.models",
        "nautobot.dcim",
        "nautobot.dcim.models",
        "nautobot.extras",
        "nautobot.extras.models",
        "nautobot.ipam",
        "nautobot.ipam.models",
        "nautobot.tenancy",
        "nautobot.tenancy.models",
    ]:
        stubs[mod_name] = _stub_module(mod_name)

    stubs["nautobot.core.models.fields"] = _stub_module(
        "nautobot.core.models.fields",
        {"slugify_dashes_to_underscores": _slugify_dashes_to_underscores},
    )

    # nautobot.apps.jobs needs Job and register_jobs
    stubs["nautobot.apps.jobs"].Job = type("Job", (), {"__init_subclass__": classmethod(lambda cls, **kw: None)})
    stubs["nautobot.apps.jobs"].register_jobs = MagicMock()

    # dcim models
    for model in ("Manufacturer", "DeviceType", "Platform", "LocationType", "Location"):
        mock = MagicMock()
        mock.DoesNotExist = type("DoesNotExist", (Exception,), {})
        mock.MultipleObjectsReturned = type("MultipleObjectsReturned", (Exception,), {})
        setattr(stubs["nautobot.dcim.models"], model, mock)

    # extras models
    for model in ("Role", "Tag", "Status", "ConfigContext", "ConfigContextSchema", "Relationship", "CustomField"):
        mock = MagicMock()
        mock.DoesNotExist = type("DoesNotExist", (Exception,), {})
        setattr(stubs["nautobot.extras.models"], model, mock)

    # ipam models
    mock_ns = MagicMock()
    mock_ns.DoesNotExist = type("DoesNotExist", (Exception,), {})
    stubs["nautobot.ipam.models"].Namespace = mock_ns

    # tenancy models
    mock_tenant = MagicMock()
    mock_tenant.DoesNotExist = type("DoesNotExist", (Exception,), {})
    stubs["nautobot.tenancy.models"].Tenant = mock_tenant

    # nautobot.extras.context_managers.web_request_context: the real one binds a
    # change-logging user around DB writes; in tests it's a no-op passthrough.
    @contextmanager
    def _web_request_context(*_args, **_kwargs):
        yield

    stubs["nautobot.extras.context_managers"] = _stub_module(
        "nautobot.extras.context_managers",
        {"web_request_context": _web_request_context},
    )

    yield

    # Clean up: remove stubs and any modules imported on top of them
    for name in list(sys.modules):
        if name in stubs or name.startswith(("nv_config_manager_auth", "nv_config_manager_jobs")):
            sys.modules.pop(name, None)


@pytest.fixture()
def mock_user():
    """Return a mock Django User instance."""
    user = MagicMock()
    user.username = "testuser"
    user.email = "testuser@example.com"
    user.is_active = True
    return user


@pytest.fixture()
def mock_service_user():
    """Return a mock service user."""
    user = MagicMock()
    user.username = "nv-config-manager-service"
    user.is_active = True
    user.is_superuser = True
    return user
