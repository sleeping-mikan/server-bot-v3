"""core/path_utils.py のテスト

パス境界チェックはディレクトリトラバーサル等を防ぐセキュリティ境界そのものなので、
リグレッションを早期に検知できるよう境界値を重点的に確認する。
"""

from __future__ import annotations

from pathlib import Path

from core.path_utils import (
    backup_would_overwrite_important_files,
    is_entry_file,
    is_important_bot_file,
    is_path_within_scope,
)

# ── is_entry_file ────────────────────────────────────────────────────────────

def test_is_entry_file_defaults_to_server_py(app_ctx):
    assert is_entry_file(app_ctx.paths.base / "server.py") is True


def test_is_entry_file_rejects_other_files(app_ctx):
    assert is_entry_file(app_ctx.paths.base / "main.py") is False


def test_is_entry_file_respects_env_override(app_ctx, monkeypatch):
    monkeypatch.setenv("MIKAN_ENTRY_FILE", "custom_launcher.py")
    assert is_entry_file(app_ctx.paths.base / "custom_launcher.py") is True
    assert is_entry_file(app_ctx.paths.base / "server.py") is False


# ── is_path_within_scope ─────────────────────────────────────────────────────

def test_is_path_within_scope_accepts_scope_root(app_ctx):
    assert is_path_within_scope(app_ctx.server_path) is True


def test_is_path_within_scope_accepts_existing_nested_path(app_ctx):
    nested = app_ctx.server_path / "world" / "region"
    nested.mkdir(parents=True)
    assert is_path_within_scope(nested) is True


def test_is_path_within_scope_accepts_nonexistent_nested_path(app_ctx):
    # resolve(strict=False) を使うため、まだ作成していないパスでも判定できる想定
    not_yet_created = app_ctx.server_path / "backups" / "2026-08-08.zip"
    assert is_path_within_scope(not_yet_created) is True


def test_is_path_within_scope_rejects_sibling_directory(app_ctx):
    outside = app_ctx.server_path.parent / "outside_dir" / "secret.txt"
    assert is_path_within_scope(outside) is False


def test_is_path_within_scope_rejects_dotdot_traversal(app_ctx):
    traversal = app_ctx.server_path / ".." / ".." / "etc" / "passwd"
    assert is_path_within_scope(traversal) is False


def test_is_path_within_scope_rejects_traversal_disguised_as_nested_string(app_ctx):
    # 文字列結合ではなく Path.resolve() で判定しているため、
    # "scope/../../outside" のような文字列でもすり抜けないことを確認する
    traversal = f"{app_ctx.server_path}/../../outside"
    assert is_path_within_scope(traversal) is False


# ── is_important_bot_file ────────────────────────────────────────────────────

def test_is_important_bot_file_matches_configured_file_under_server_path(app_ctx):
    assert is_important_bot_file(app_ctx.server_path / ".config") is True


def test_is_important_bot_file_matches_file_inside_configured_directory(app_ctx):
    log_file = app_ctx.server_path / "logs" / "latest.log"
    assert is_important_bot_file(log_file) is True


def test_is_important_bot_file_rejects_unrelated_file(app_ctx):
    assert is_important_bot_file(app_ctx.server_path / "world" / "level.dat") is False


def test_is_important_bot_file_rejects_similarly_named_file(app_ctx):
    # "logs" は保護対象だが "logs_backup" のような別名ディレクトリは保護対象に含めない
    assert is_important_bot_file(app_ctx.server_path / "logs_backup" / "a.log") is False


# ── backup_would_overwrite_important_files ───────────────────────────────────

def test_backup_apply_no_conflict_when_dest_unrelated_to_protected_paths(app_ctx, tmp_path):
    src_dir = tmp_path / "backup_src"
    src_dir.mkdir()
    (src_dir / ".config").write_text("dummy")

    dest_dir = tmp_path / "restore" / "unrelated_subdir"
    dest_dir.mkdir(parents=True)

    assert backup_would_overwrite_important_files(src_dir, dest_dir) is None


def test_backup_apply_detects_conflict_on_protected_file(app_ctx, tmp_path):
    src_dir = tmp_path / "backup_src"
    src_dir.mkdir()
    (src_dir / ".config").write_text("dummy")

    # dest_dir == server_path なので、保護ファイル ".config" がそのまま配下に来る
    result = backup_would_overwrite_important_files(src_dir, app_ctx.server_path)

    assert result == Path(".config")


def test_backup_apply_ignores_conflict_when_src_lacks_the_file(app_ctx, tmp_path):
    src_dir = tmp_path / "backup_src"
    src_dir.mkdir()
    # ".config" を含まないバックアップなので上書きは発生しない

    result = backup_would_overwrite_important_files(src_dir, app_ctx.server_path)

    assert result is None


def test_backup_apply_detects_conflict_on_protected_directory(app_ctx, tmp_path):
    src_dir = tmp_path / "backup_src"
    (src_dir / "mikanassets").mkdir(parents=True)

    result = backup_would_overwrite_important_files(src_dir, app_ctx.server_path)

    assert result == Path("mikanassets")
