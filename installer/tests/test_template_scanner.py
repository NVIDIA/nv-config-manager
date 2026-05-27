# SPDX-FileCopyrightText: Copyright (c) 2024-2026 NVIDIA CORPORATION & AFFILIATES.
# SPDX-License-Identifier: Apache-2.0
"""Tests for the template_scanner module."""

from __future__ import annotations

from pathlib import Path

from nv_config_manager_installer.template_scanner import (
    _decompose_key,
    _find_templates_subdir,
    scan_directory,
    scan_file,
    scan_plugins,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    return path


# ---------------------------------------------------------------------------
# _decompose_key
# ---------------------------------------------------------------------------


class TestDecomposeKey:
    def test_with_rotation(self) -> None:
        assert _decompose_key("bgp_password_r1") == ("bgp_password", "r1")

    def test_with_higher_rotation(self) -> None:
        assert _decompose_key("tacacs_key_r42") == ("tacacs_key", "r42")

    def test_no_rotation(self) -> None:
        assert _decompose_key("hash_salt") == ("hash_salt", "")

    def test_single_word_with_rotation(self) -> None:
        assert _decompose_key("password_r1") == ("password", "r1")


# ---------------------------------------------------------------------------
# scan_file — literal load_secret keys
# ---------------------------------------------------------------------------


class TestScanFileLiteralKeys:
    def test_basic_literal_key(self, tmp_path: Path) -> None:
        j2 = _write(
            tmp_path / "test.j2",
            'password: {{ "bgp_password_r1"|load_secret(site=device_data|site_name) }}',
        )
        result = scan_file(j2, root=tmp_path)
        assert len(result.secrets) == 1
        assert result.secrets[0].secret_key == "bgp_password"
        assert result.secrets[0].rotation == "r1"

    def test_single_quoted_key(self, tmp_path: Path) -> None:
        j2 = _write(
            tmp_path / "test.j2",
            "secret: {{ 'tacacs_key_r1'|load_secret(site=site) }}",
        )
        result = scan_file(j2, root=tmp_path)
        assert len(result.secrets) == 1
        assert result.secrets[0].secret_key == "tacacs_key"

    def test_parenthesized_key(self, tmp_path: Path) -> None:
        j2 = _write(
            tmp_path / "test.j2",
            '{{ ("isis_password_r1"|load_secret(site=s))|encrypt("md5", site=s) }}',
        )
        result = scan_file(j2, root=tmp_path)
        assert len(result.secrets) == 1
        assert result.secrets[0].secret_key == "isis_password"

    def test_multiple_keys_in_file(self, tmp_path: Path) -> None:
        j2 = _write(
            tmp_path / "test.j2",
            (
                'password: {{ "bgp_password_r1"|load_secret(site=s) }}\n'
                'key: {{ "tacacs_key_r1"|load_secret(site=s) }}\n'
            ),
        )
        result = scan_file(j2, root=tmp_path)
        keys = {s.secret_key for s in result.secrets}
        assert keys == {"bgp_password", "tacacs_key"}

    def test_duplicate_key_deduplicated(self, tmp_path: Path) -> None:
        j2 = _write(
            tmp_path / "test.j2",
            (
                'a: {{ "bgp_password_r1"|load_secret(site=s) }}\n'
                'b: {{ "bgp_password_r1"|load_secret(site=s) }}\n'
            ),
        )
        result = scan_file(j2, root=tmp_path)
        assert len(result.secrets) == 1
        assert result.secrets[0].secret_key == "bgp_password"

    def test_internal_keys_excluded(self, tmp_path: Path) -> None:
        j2 = _write(
            tmp_path / "test.j2",
            ('{{ "hash_salt"|load_secret(site=s) }}\n{{ "hash_salt_t7"|load_secret(site=s) }}\n'),
        )
        result = scan_file(j2, root=tmp_path)
        assert len(result.secrets) == 0

    def test_source_files_tracked(self, tmp_path: Path) -> None:
        j2 = _write(
            tmp_path / "sub" / "test.j2",
            '{{ "bgp_password_r1"|load_secret(site=s) }}',
        )
        result = scan_file(j2, root=tmp_path)
        assert result.secrets[0].source_files == ["sub/test.j2"]


# ---------------------------------------------------------------------------
# scan_file — dynamic user.password_key
# ---------------------------------------------------------------------------


class TestScanFileDynamicKeys:
    def test_dynamic_key_detected(self, tmp_path: Path) -> None:
        j2 = _write(
            tmp_path / "test.j2",
            '{{ (user.password_key|load_secret(site=s))|encrypt("sha512", site=s) }}',
        )
        result = scan_file(j2, root=tmp_path)
        assert result.dynamic_user_keys_found is True
        assert len(result.secrets) == 0

    def test_no_dynamic_key(self, tmp_path: Path) -> None:
        j2 = _write(
            tmp_path / "test.j2",
            '{{ "bgp_password_r1"|load_secret(site=s) }}',
        )
        result = scan_file(j2, root=tmp_path)
        assert result.dynamic_user_keys_found is False


# ---------------------------------------------------------------------------
# scan_file — encrypt filter detection
# ---------------------------------------------------------------------------


class TestScanFileEncrypt:
    def test_sha512_needs_hash_salt(self, tmp_path: Path) -> None:
        j2 = _write(
            tmp_path / "test.j2",
            '{{ val|encrypt("sha512", site=s) }}',
        )
        result = scan_file(j2, root=tmp_path)
        assert result.needs_hash_salt is True
        assert result.needs_hash_salt_t7 is False

    def test_ciscot7_needs_hash_salt_t7(self, tmp_path: Path) -> None:
        j2 = _write(
            tmp_path / "test.j2",
            '{{ val|encrypt("ciscot7", site=s) }}',
        )
        result = scan_file(j2, root=tmp_path)
        assert result.needs_hash_salt is False
        assert result.needs_hash_salt_t7 is True

    def test_md5_needs_hash_salt(self, tmp_path: Path) -> None:
        j2 = _write(
            tmp_path / "test.j2",
            '{{ val|encrypt("md5", site=s) }}',
        )
        result = scan_file(j2, root=tmp_path)
        assert result.needs_hash_salt is True

    def test_no_encrypt(self, tmp_path: Path) -> None:
        j2 = _write(tmp_path / "test.j2", "just some text")
        result = scan_file(j2, root=tmp_path)
        assert result.needs_hash_salt is False
        assert result.needs_hash_salt_t7 is False


# ---------------------------------------------------------------------------
# scan_file — error handling
# ---------------------------------------------------------------------------


class TestScanFileErrors:
    def test_missing_file(self, tmp_path: Path) -> None:
        result = scan_file(tmp_path / "nonexistent.j2")
        assert len(result.errors) == 1
        assert result.scanned_files == 1


# ---------------------------------------------------------------------------
# scan_directory
# ---------------------------------------------------------------------------


class TestScanDirectory:
    def test_scans_nested_j2_files(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "role_a" / "include" / "bgp.j2",
            '{{ "bgp_password_r1"|load_secret(site=s) }}',
        )
        _write(
            tmp_path / "role_b" / "include" / "mgmt.j2",
            '{{ "tacacs_key_r1"|load_secret(site=s) }}',
        )
        result = scan_directory(tmp_path)
        assert result.scanned_files == 2
        keys = {s.secret_key for s in result.secrets}
        assert keys == {"bgp_password", "tacacs_key"}

    def test_deduplicates_across_files(self, tmp_path: Path) -> None:
        _write(
            tmp_path / "a.j2",
            '{{ "bgp_password_r1"|load_secret(site=s) }}',
        )
        _write(
            tmp_path / "b.j2",
            '{{ "bgp_password_r1"|load_secret(site=s) }}',
        )
        result = scan_directory(tmp_path)
        assert len(result.secrets) == 1
        assert len(result.secrets[0].source_files) == 2

    def test_not_a_directory(self, tmp_path: Path) -> None:
        result = scan_directory(tmp_path / "nope")
        assert len(result.errors) == 1
        assert result.scanned_files == 0

    def test_empty_directory(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty"
        empty.mkdir()
        result = scan_directory(empty)
        assert result.scanned_files == 0
        assert len(result.secrets) == 0

    def test_ignores_non_j2_files(self, tmp_path: Path) -> None:
        _write(tmp_path / "readme.md", '"bgp_password_r1"|load_secret(site=s)')
        _write(tmp_path / "ok.j2", '{{ "tacacs_key_r1"|load_secret(site=s) }}')
        result = scan_directory(tmp_path)
        assert result.scanned_files == 1
        assert result.secrets[0].secret_key == "tacacs_key"

    def test_aggregates_encrypt_flags(self, tmp_path: Path) -> None:
        _write(tmp_path / "a.j2", '{{ val|encrypt("sha512", site=s) }}')
        _write(tmp_path / "b.j2", '{{ val|encrypt("ciscot7", site=s) }}')
        result = scan_directory(tmp_path)
        assert result.needs_hash_salt is True
        assert result.needs_hash_salt_t7 is True


# ---------------------------------------------------------------------------
# _find_templates_subdir
# ---------------------------------------------------------------------------


class TestFindTemplatesSubdir:
    def test_src_package_layout(self, tmp_path: Path) -> None:
        tpl = tmp_path / "src" / "my_plugin" / "templates"
        _write(tpl / "switch" / "base.j2", "content")
        assert _find_templates_subdir(tmp_path) == tpl

    def test_flat_layout(self, tmp_path: Path) -> None:
        tpl = tmp_path / "templates"
        _write(tpl / "base.j2", "content")
        assert _find_templates_subdir(tmp_path) == tpl

    def test_no_templates_dir(self, tmp_path: Path) -> None:
        _write(tmp_path / "readme.md", "hi")
        assert _find_templates_subdir(tmp_path) == tmp_path


# ---------------------------------------------------------------------------
# scan_plugins
# ---------------------------------------------------------------------------


class TestScanPlugins:
    def test_single_plugin(self, tmp_path: Path) -> None:
        plugin = tmp_path / "my-plugin"
        _write(
            plugin / "src" / "my_plugin" / "templates" / "role" / "bgp.j2",
            '{{ "custom_secret_r1"|load_secret(site=s) }}',
        )
        result = scan_plugins([plugin])
        assert len(result.secrets) == 1
        assert result.secrets[0].secret_key == "custom_secret"

    def test_multiple_plugins(self, tmp_path: Path) -> None:
        p1 = tmp_path / "plugin-a"
        p2 = tmp_path / "plugin-b"
        _write(
            p1 / "templates" / "a.j2",
            '{{ "secret_a_r1"|load_secret(site=s) }}',
        )
        _write(
            p2 / "templates" / "b.j2",
            '{{ "secret_b_r1"|load_secret(site=s) }}',
        )
        result = scan_plugins([p1, p2])
        keys = {s.secret_key for s in result.secrets}
        assert keys == {"secret_a", "secret_b"}

    def test_dedup_across_plugins(self, tmp_path: Path) -> None:
        p1 = tmp_path / "plugin-a"
        p2 = tmp_path / "plugin-b"
        _write(p1 / "templates" / "a.j2", '{{ "bgp_password_r1"|load_secret(site=s) }}')
        _write(p2 / "templates" / "b.j2", '{{ "bgp_password_r1"|load_secret(site=s) }}')
        result = scan_plugins([p1, p2])
        assert len([s for s in result.secrets if s.secret_key == "bgp_password"]) == 1

    def test_hash_salt_added_when_encrypt_found(self, tmp_path: Path) -> None:
        plugin = tmp_path / "plugin"
        _write(
            plugin / "templates" / "mgmt.j2",
            '{{ (user.password_key|load_secret(site=s))|encrypt("sha512", site=s) }}',
        )
        result = scan_plugins([plugin])
        keys = {s.secret_key for s in result.secrets}
        assert "hash_salt" in keys
        assert result.dynamic_user_keys_found is True

    def test_hash_salt_t7_added_when_ciscot7(self, tmp_path: Path) -> None:
        plugin = tmp_path / "plugin"
        _write(
            plugin / "templates" / "mgmt.j2",
            '{{ val|encrypt("ciscot7", site=s) }}',
        )
        result = scan_plugins([plugin])
        keys = {s.secret_key for s in result.secrets}
        assert "hash_salt_t7" in keys

    def test_nonexistent_path_produces_error(self, tmp_path: Path) -> None:
        result = scan_plugins([tmp_path / "nope"])
        assert len(result.errors) == 1
        assert result.scanned_files == 0

    def test_empty_list(self) -> None:
        result = scan_plugins([])
        assert result.scanned_files == 0
        assert len(result.secrets) == 0
