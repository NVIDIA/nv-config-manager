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
"""Secrets configuration loading for Temporal services.

Provides shared logic for loading site-specific secrets from the config-secrets
file with fallback to the main nv-config-manager.ini configuration.

The secrets config file path is specified by the NV_CONFIG_MANAGER_CONFIG_SECRET_PATH environment
variable. This file contains site-specific sections like [site.site-name] with
credentials that can be rotated independently of the main configuration.

Lookup order for credentials:
1. Secrets config: [site.{site_slug}] section (if site provided)
2. Main config: [{section}] section (global fallback)
"""

from __future__ import annotations

import os
from configparser import ConfigParser
from typing import Any

from nv_config_manager.common.log import LogCategory, get_logger

logger = get_logger(__name__, category=LogCategory.AUTH)

# Module-level cache for secrets config to avoid repeated file reads
_secrets_config_cache: tuple[ConfigParser, bool] | None = None


def load_secrets_config() -> tuple[ConfigParser, bool]:
    """Load the secrets config file if available.

    Reads from the path specified by NV_CONFIG_MANAGER_CONFIG_SECRET_PATH environment variable.
    Results are cached at the module level to avoid repeated file reads.

    Returns:
        Tuple of (ConfigParser, found) where found indicates if the file exists
    """
    global _secrets_config_cache

    if _secrets_config_cache is not None:
        return _secrets_config_cache

    secrets_path = os.environ.get("NV_CONFIG_MANAGER_CONFIG_SECRET_PATH")
    secrets_config = ConfigParser(interpolation=None)

    if secrets_path and os.path.exists(secrets_path):
        secrets_config.read(secrets_path)
        logger.debug("Loaded secrets config from: %s", secrets_path)
        _secrets_config_cache = (secrets_config, True)
    else:
        if secrets_path:
            logger.debug("Secrets config path set but file not found: %s", secrets_path)
        _secrets_config_cache = (secrets_config, False)

    return _secrets_config_cache


def clear_secrets_cache() -> None:
    """Clear the secrets config cache.

    Useful for testing or when the secrets file has been updated.
    """
    global _secrets_config_cache
    _secrets_config_cache = None


def get_site_slug(site: str) -> str:
    """Convert a site name to a slug format.

    Args:
        site: Site name (e.g., "Site A", "My Data Center")

    Returns:
        Slugified site name (e.g., "site-a", "my-data-center")
    """
    return site.lower().replace(" ", "-")


def resolve_config_section(
    main_config: Any,
    section: str,
    site: str | None = None,
) -> tuple[Any, str]:
    """Determine the config object and section for credential lookup.

    Checks the secrets config file first for site-specific sections,
    then falls back to the main config. Lookup order:
    1. Secrets config: [site.{site_slug}] section (if site provided)
    2. Main config: [{section}] section (global fallback)

    Args:
        main_config: Main configuration object (from load_config())
        section: The section name to look for (e.g., "device", "ufm")
        site: Site name for site-specific lookup (optional)

    Returns:
        Tuple of (config_to_use, section_name) for credential lookup
    """
    secrets_config, secrets_found = load_secrets_config()

    if site and secrets_found:
        site_slug = get_site_slug(site)
        site_section = f"site.{site_slug}"
        if secrets_config.has_section(site_section):
            logger.debug("Using site-specific secrets config section: [%s]", site_section)
            return secrets_config, site_section

    # Fallback: main config section
    logger.debug("Using global [%s] section from main config", section)
    return main_config, section


def get_rotation_passwords(
    config: Any,
    section: str,
    key_prefix: str = "api_user_key_r",
    max_passwords: int = 2,
) -> list[str]:
    """Get rotation passwords from a config section.

    Parses keys matching the pattern {key_prefix}{revision_number} and returns
    the passwords sorted by revision number (newest first).

    Args:
        config: Configuration object
        section: The config section to read from
        key_prefix: Prefix for rotation keys (default: "api_user_key_r")
        max_passwords: Maximum number of passwords to return (default: 2)

    Returns:
        List of passwords sorted by revision (newest first), up to max_passwords
    """
    rotations: list[tuple[int, str]] = []

    if not config.has_section(section):
        return []

    for key in config[section]:
        if not key.startswith(key_prefix):
            continue
        try:
            # Extract revision number from key like "api_user_key_r1" -> 1
            revision_str = key[len(key_prefix) :]
            revision_num = int(revision_str)
            rotations.append((revision_num, config[section][key]))
            logger.debug("Found rotation key: %s (revision %d) in [%s]", key, revision_num, section)
        except (ValueError, IndexError):
            logger.debug("Skipping invalid rotation key: %s", key)

    if rotations:
        # Sort by revision number (highest first = most recent)
        rotations.sort(reverse=True, key=lambda x: x[0])
        return [pw for _, pw in rotations[:max_passwords]]

    return []


def get_credential(
    main_config: Any,
    section: str,
    key: str,
    site: str | None = None,
    default: str = "",
) -> str:
    """Get a single credential value with site-specific fallback.

    Checks secrets config first for site-specific value, then falls back
    through the standard resolution order.

    Args:
        main_config: Main configuration object (from load_config())
        section: The section name to look for (e.g., "device", "ufm")
        key: The key name to retrieve (e.g., "password", "ufm_api_user")
        site: Site name for site-specific lookup (optional)
        default: Default value if key not found

    Returns:
        The credential value or default if not found
    """
    config, resolved_section = resolve_config_section(main_config, section, site)

    if config.has_section(resolved_section):
        value: str = config[resolved_section].get(key, "")
        if value:
            return value

    # If we got a site-specific section but key wasn't there, try global
    if site and resolved_section.startswith("site."):
        config, resolved_section = resolve_config_section(main_config, section, None)
        if config.has_section(resolved_section):
            result: str = config[resolved_section].get(key, default)
            return result

    return default
