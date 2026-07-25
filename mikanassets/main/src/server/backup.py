"""
server/backup.py — バックアップ作成・適用ロジック

Discord コマンドに依存しない純粋な実装。
Discord ハンドラは bot/commands/backup.py から呼び出す。

copy_directory     : ファイル/ディレクトリを再帰的に非同期コピーする (マージコピー)。
create_backup      : バックアップを作成し保存先パスを返す (async)。
apply_backup       : バックアップを指定パスに適用する (async)。
create_backup_sync : create_backup の同期ラッパー。Flask など同期コンテキスト用。
apply_backup_sync  : apply_backup の同期ラッパー。Flask など同期コンテキスト用。
ProgressCallback   : (copied_files, total_files, copied_bytes, total_bytes) → None
"""

from __future__ import annotations

import asyncio
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
    """src を dst へ再帰的にコピーする。src がファイルの場合は単体コピーする。

    dst 側は事前に削除せず、src にあるエントリだけを上書き/追加するマージコピーとして動く。
    """
    src_path = Path(src)
    dst_path = Path(dst)

    if src_path.is_file():
        dst_path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(copy2, src_path, dst_path)
        if on_progress is not None:
            size = src_path.stat().st_size
            await on_progress(1, 1, size, size)
        return

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


async def create_backup(
    from_path:   str,
    on_progress: ProgressCallback | None = None,
) -> str:
    """バックアップを作成し、保存先の絶対パスを返す。"""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    dst = str(ctx.backup_path / f"{timestamp}-{Path(from_path).name}")
    ctx.is_backup_in_progress = True
    try:
        await copy_directory(from_path, dst, on_progress=on_progress)
    finally:
        ctx.is_backup_in_progress = False
    return dst


async def apply_backup(
    backup_name: str,
    dest_path:   str,
    on_progress: ProgressCallback | None = None,
) -> None:
    """バックアップを dest_path に適用する。"""
    src = str(ctx.backup_path / backup_name)
    ctx.is_backup_in_progress = True
    try:
        await copy_directory(src, dest_path, on_progress=on_progress)
    finally:
        ctx.is_backup_in_progress = False


def create_backup_sync(from_path: str) -> str:
    """バックアップを同期的に作成し保存先パスを返す。progress 通知なし。

    Flask のような同期コンテキストから呼ぶ用。Flask ルートは discord.py の
    メインイベントループとは別スレッドで動くため、asyncio.run() で新規
    イベントループを立てて create_backup に委譲しても衝突しない。
    """
    return asyncio.run(create_backup(from_path))


def apply_backup_sync(backup_name: str, dest_path: str) -> None:
    """バックアップを同期的に適用する。Flask のような同期コンテキストから呼ぶ用。

    apply_backup と同じくマージコピー (バックアップ側にあるエントリだけを
    上書き/追加、dest_path 側の無関係な既存ファイルは保持) で適用される。
    """
    asyncio.run(apply_backup(backup_name, dest_path))
