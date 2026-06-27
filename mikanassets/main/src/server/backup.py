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
import os
from datetime import datetime
from shutil import Error, copy2, copystat
from typing import Awaitable, Callable

from core.config_loader import normalize_path
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
    src = normalize_path(src)
    dst = normalize_path(dst)

    total_files = 0
    total_bytes = 0
    for root, _, files in os.walk(top=src, topdown=False):
        total_files += len(files)
        for f in files:
            fp = os.path.join(root, f)
            if not os.path.islink(fp):
                try:
                    total_bytes += os.path.getsize(fp)
                except OSError:
                    pass

    copied_files = 0
    copied_bytes = 0

    async def _do_copy(s: str, d: str, syml: bool) -> None:
        nonlocal copied_files, copied_bytes
        if not os.path.exists(d):
            os.makedirs(d)
        errors: list = []
        for name in os.listdir(s):
            sname = os.path.join(s, name)
            dname = os.path.join(d, name)
            try:
                if syml and os.path.islink(sname):
                    os.symlink(os.readlink(sname), dname)
                elif os.path.isdir(sname):
                    await _do_copy(sname, dname, syml)
                else:
                    await asyncio.to_thread(copy2, sname, dname)
                    try:
                        copied_bytes += os.path.getsize(sname)
                    except OSError:
                        pass
                    copied_files += 1
                    if on_progress is not None:
                        await on_progress(copied_files, total_files, copied_bytes, total_bytes)
            except OSError as why:
                errors.append((sname, dname, str(why)))
            except Error as err:
                errors.extend(err.args[0])
        try:
            copystat(s, d)
        except OSError as why:
            if why.winerror is None:  # type: ignore[attr-defined]
                errors.extend((s, d, str(why)))
        if errors:
            raise Error(errors)

    await _do_copy(src, dst, symlinks)


async def create_backup(
    from_path:   str,
    on_progress: ProgressCallback | None = None,
) -> str:
    """バックアップを作成し、保存先の絶対パスを返す。"""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    dst = os.path.join(
        ctx.backup_path,
        f"{timestamp}-{os.path.basename(from_path)}",
    )
    await copy_directory(from_path, dst, on_progress=on_progress)
    return dst


async def apply_backup(
    backup_name: str,
    dest_path:   str,
    on_progress: ProgressCallback | None = None,
) -> None:
    """バックアップを dest_path に適用する。"""
    src = os.path.join(ctx.backup_path, backup_name)
    await copy_directory(src, dest_path, on_progress=on_progress)
