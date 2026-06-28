"""
server/backup.py — バックアップ作成・適用ロジック

Discord コマンドに依存しない純粋な実装。
Discord ハンドラは bot/commands/backup.py から呼び出す。

copy_directory   : ディレクトリを再帰的に非同期コピーする。
create_backup    : バックアップを作成し保存先パスを返す。
apply_backup     : バックアップを指定パスに適用する。
ProgressCallback : (copied_files, total_files, copied_bytes, total_bytes) → None
"""

from __future__ import annotations

import asyncio
import shutil
from datetime import datetime
from pathlib import Path
from shutil import Error, copy2, copystat
from typing import Awaitable, Callable

from core.state import ctx

# (copied_files, total_files, copied_bytes, total_bytes)
ProgressCallback = Callable[[int, int, int, int], Awaitable[None]]


async def copy_directory(
    src:         str,
    dst:         str,
    on_progress: ProgressCallback | None = None,
    symlinks:    bool                    = False,
) -> None:
    """src を dst へ再帰的にコピーする。"""
    src_path = Path(src)
    dst_path = Path(dst)

    total_files = 0
    total_bytes = 0
    for fp in src_path.rglob("*"):
        if fp.is_file() and not fp.is_symlink():
            total_files += 1
            try:
                total_bytes += fp.stat().st_size
            except OSError:
                pass

    copied_files = 0
    copied_bytes = 0

    async def _do_copy(s: Path, d: Path, syml: bool) -> None:
        nonlocal copied_files, copied_bytes
        d.mkdir(parents=True, exist_ok=True)
        errors: list = []
        for sname in s.iterdir():
            dname = d / sname.name
            try:
                if syml and sname.is_symlink():
                    dname.symlink_to(sname.readlink())
                elif sname.is_dir():
                    await _do_copy(sname, dname, syml)
                else:
                    await asyncio.to_thread(copy2, sname, dname)
                    try:
                        copied_bytes += sname.stat().st_size
                    except OSError:
                        pass
                    copied_files += 1
                    if on_progress is not None:
                        await on_progress(copied_files, total_files, copied_bytes, total_bytes)
            except OSError as why:
                errors.append((str(sname), str(dname), str(why)))
            except Error as err:
                errors.extend(err.args[0])
        try:
            copystat(s, d)
        except OSError as why:
            if why.winerror is None:  # type: ignore[attr-defined]
                errors.extend((str(s), str(d), str(why)))
        if errors:
            raise Error(errors)

    await _do_copy(src_path, dst_path, symlinks)


def create_backup_sync(from_path: str) -> str:
    """バックアップを同期的に作成し保存先パスを返す。progress 通知なし。

    Flask のような同期コンテキストから呼ぶ用。非同期ループと干渉しない。
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    dst = str(ctx.backup_path / f"{timestamp}-{Path(from_path).name}")
    if Path(from_path).is_dir():
        shutil.copytree(from_path, dst)
    else:
        shutil.copy2(from_path, dst)
    return dst


def apply_backup_sync(backup_name: str, dest_path: str) -> None:
    """バックアップを同期的に適用する。Flask のような同期コンテキストから呼ぶ用。

    dest_path が既に存在する場合は削除してから上書きする。
    """
    src = ctx.backup_path / backup_name
    dest = Path(dest_path)
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(str(src), str(dest))


async def create_backup(
    from_path:   str,
    on_progress: ProgressCallback | None = None,
) -> str:
    """バックアップを作成し、保存先の絶対パスを返す。"""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    dst = str(ctx.backup_path / f"{timestamp}-{Path(from_path).name}")
    await copy_directory(from_path, dst, on_progress=on_progress)
    return dst


async def apply_backup(
    backup_name: str,
    dest_path:   str,
    on_progress: ProgressCallback | None = None,
) -> None:
    """バックアップを dest_path に適用する。"""
    src = str(ctx.backup_path / backup_name)
    await copy_directory(src, dest_path, on_progress=on_progress)
