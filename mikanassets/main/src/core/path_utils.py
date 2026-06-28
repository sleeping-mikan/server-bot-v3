"""
core/path_utils.py — パス検証ユーティリティ

bot/ と web/ の両方から参照できる中立的な場所に置く。
bot/utils.py に置いていた is_path_within_scope / is_important_bot_file を
ここへ移動した理由: web/ からも同じ検証ロジックを呼びたい場合に
  web → bot.utils のインポートが生まれ循環 import になるのを防ぐ。

依存: core.state (ctx) のみ。discord / flask など外部ライブラリに依存しない。
"""

from __future__ import annotations

import pathlib

from core.state import ctx


def is_path_within_scope(path: str | pathlib.Path) -> bool:
    """path が ctx.server_path 以下に収まっているかを確認する。

    ディレクトリトラバーサル攻撃 ("../../etc/passwd" など) を防ぐためのガード。
    resolve(strict=False) を使うことで、まだ存在しないパスでも評価できる。
    """
    resolved_path   = pathlib.Path(path).resolve(strict=False)
    resolved_server = ctx.server_path.resolve()
    try:
        resolved_path.relative_to(resolved_server)
        return True
    except ValueError:
        return False


async def is_important_bot_file(path: str | pathlib.Path) -> bool:
    """path が sys_files (重要ファイル) に該当するかを確認する。

    sys_files はコンフィグの discord_commands.cmd.stdin.sys_files で定義される。
    src/ 配下と server_path/ 配下の両方に存在するファイルを重要とみなす。
    管理者でない、または enable_advanced_features が無効のユーザーが
    これらファイルに触れるのを防ぐために使う。
    """
    resolved  = pathlib.Path(path).resolve()
    sys_files = ctx.config["discord_commands"]["cmd"]["stdin"]["sys_files"]

    src_dir   = pathlib.Path(__file__).parent

    important = [
        (src_dir / f).resolve()
        for f in sys_files
    ] + [
        (ctx.server_path / f).resolve()
        for f in sys_files
    ]

    return any(resolved == f or resolved.is_relative_to(f) for f in important)
