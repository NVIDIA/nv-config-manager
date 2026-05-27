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
"""NVIDIA Config Manager Render functionality."""

from __future__ import annotations

import asyncio
import os
from datetime import UTC, datetime
from typing import Any

import pynautobot
from nv_config_manager_templates.render import Renderer
from nv_config_manager_templates.version import template_version_key

from nv_config_manager.common.client.config_store import ConfigStoreFileNotFound
from nv_config_manager.common.client.render import FileCommit
from nv_config_manager.common.config import (
    LogCategory,
    config_store_client,
    config_store_ui_url,
    get_logger,
    pynautobot_client,
)
from nv_config_manager.render.exceptions import NautobotException, RenderException

logger = get_logger(__name__, category=LogCategory.RENDER)

DEPLOYABLE_FILES = ["startup.yaml", "full-config"]


def _nv_config_manager_intended_config_endpoint(nb: pynautobot.api) -> Any:
    return nb.plugins.nv_config_manager.intendedconfig


async def _update_nautobot_plugin(  # pylint: disable=too-many-arguments
    nb: pynautobot.api,
    device_uuid: str,
    config_store_instance: str,
    commit_id: str,
    paths: list[str],
    user: str,
    commit_message: str,
    updated_at: str | None = None,
) -> None:
    intended_config_endpoint = _nv_config_manager_intended_config_endpoint(nb)
    # Run blocking Nautobot get in thread
    existing_config_entry = await asyncio.to_thread(intended_config_endpoint.get, device_uuid)

    for file in paths:
        # Only full-config changes are relevant to the NB plugin
        if file in DEPLOYABLE_FILES:
            update = {
                "device_id": device_uuid,
                "config_store_instance": config_store_instance,
                "path": file,
                "commit_id": commit_id,
                "updated": updated_at or datetime.now(UTC).isoformat(),
                "updated_by": user,
                "commit_message": commit_message,
                "template_version": template_version_key(),
            }

            try:
                if existing_config_entry:
                    # Run blocking update in thread
                    await asyncio.to_thread(existing_config_entry.update, update)
                else:
                    # Run blocking create in thread
                    await asyncio.to_thread(intended_config_endpoint.create, update)
                return
            except Exception as exc:
                raise NautobotException(
                    f"Failed to update NB with intended configuration: {exc}"
                ) from exc
    # If we got here, no full config file change, just bump the template version
    await _update_template_version(nb, device_uuid)


async def _update_template_version(nb: pynautobot.api, device_uuid: str) -> None:
    """Update the template version for a device."""
    # Run blocking update in thread
    await asyncio.to_thread(
        _nv_config_manager_intended_config_endpoint(nb).update,
        id=device_uuid,
        data={
            "template_version": template_version_key(),
        },
    )


async def execute_render(device_uuid: str, commit_message: str, user: str) -> list[FileCommit]:
    """Execute a render for a device."""
    nb = pynautobot_client()
    logger.info(
        "Rendering configuration for %s with commit message '%s'",
        device_uuid,
        commit_message,
    )
    user_domain = os.getenv("NV_CONFIG_MANAGER_DOMAIN", "local.config-manager.example.com")
    renderer = Renderer(
        nb.base_url.replace("/api", ""),
        nb.token,
    )

    # Run blocking render operation in thread
    try:
        files = await asyncio.to_thread(renderer.render_entrypoints, device_id=device_uuid)
        if not files:
            # If the device doesn't have associated templates,
            # the render will produce an empty dict and nothing further
            # should be done.
            logger.info("No entrypoint templates matched for %s", device_uuid)
            return []
        # Sanitize the files dict to only include the filename
        # without the entrypoint path and extension
        files = {k.split("/")[-1].replace(".j2", ""): v for k, v in files.items()}
    except Exception as exc:
        raise RenderException(f"Failed to render entrypoints for {device_uuid}: {exc}") from exc

    csclient = config_store_client()

    async with csclient:
        updated_files = await csclient.persist_files(
            device_uuid, files, commit_message, user, user_domain
        )

        if updated_files:
            file_commits = [FileCommit(filename=f.filename, commit=f.commit) for f in updated_files]
            deployable_file = next(
                (f for f in file_commits if f.filename in DEPLOYABLE_FILES), None
            )
            logger.info(
                "Produced commits for %s: %s",
                device_uuid,
                {f.filename: f.commit for f in file_commits},
            )
            if deployable_file:
                await _update_nautobot_plugin(
                    nb,
                    device_uuid,
                    config_store_ui_url(),
                    deployable_file.commit,
                    [f.filename for f in file_commits],
                    user,
                    commit_message,
                )
            else:
                await _update_template_version(nb, device_uuid)
            return file_commits

        # No diff — re-sync Nautobot with the latest Config Store version so
        # that re-added devices get the intended config record populated even
        # when the rendered config hasn't changed.  The deployable filename
        # varies by platform (full-config vs startup.yaml), so try each
        # rendered file that qualifies until one is found in the store.
        for candidate in files:
            if candidate not in DEPLOYABLE_FILES:
                continue
            try:
                latest = await csclient.load_file(device_uuid, candidate)
                logger.info(
                    "No config diff for %s, re-syncing Nautobot with latest version %s of %s",
                    device_uuid,
                    latest.commit,
                    candidate,
                )
                await _update_nautobot_plugin(
                    nb,
                    device_uuid,
                    config_store_ui_url(),
                    latest.commit,
                    [candidate],
                    user,
                    commit_message,
                    updated_at=latest.created_at,
                )
                return []
            except ConfigStoreFileNotFound:
                continue

        await _update_template_version(nb, device_uuid)
        return []
