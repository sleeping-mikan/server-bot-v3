"""
core/path_utils.py — パス検証ユーティリティ

bot/ と web/ の両方から参照できる中立的な場所に置く。
bot/utils.py に置いていた is_path_within_scope / is_important_bot_file を
ここへ移動した理由: web/ からも同じ検証ロジックを呼びたい場合に
  web → bot.utils のインポートが生まれ循環 import になるのを防ぐ。

依存: core.state (ctx) のみ。discord / flask など外部ライブラリに依存しない。
"""

from __future__ import annotations

import os
import pathlib

from core.state import ctx


def is_path_within_scope(path: str) -> bool:
    """path が ctx.server_path 以下に収まっているかを確認する。

    ディレクトリトラバーサル攻撃 ("../../etc/passwd" など) を防ぐためのガード。
    resolve(strict=False) を使うことで、まだ存在しないパスでも評価できる。
    """
    resolved_path   = pathlib.Path(os.path.abspath(path)).resolve(strict=False)
    resolved_server = pathlib.Path(ctx.server_path).resolve()
    try:
        resolved_path.relative_to(resolved_server)
        return True
    except ValueError:
        return False


async def is_important_bot_file(path: str) -> bool:
    """path が sys_files (重要ファイル) に該当するかを確認する。

    sys_files はコンフィグの discord_commands.cmd.stdin.sys_files で定義される。
    src/ 配下と server_path/ 配下の両方に存在するファイルを重要とみなす。
    管理者でない、または enable_advanced_features が無効のユーザーが
    これらファイルに触れるのを防ぐために使う。
    """
    resolved  = pathlib.Path(os.path.abspath(path)).resolve()
    sys_files = ctx.config["discord_commands"]["cmd"]["stdin"]["sys_files"]

    # __file__ は core/path_utils.py なので、その親ディレクトリが src/
    src_dir = pathlib.Path(__file__).parent

    # src/ 配下の重要ファイルと server_path/ 配下の重要ファイルを列挙する
    important = [
        pathlib.Path(os.path.abspath(src_dir / f)).resolve()
        for f in sys_files
    ] + [
        pathlib.Path(os.path.join(ctx.server_path, f)).resolve()
        for f in sys_files
    ]

    return any(resolved == f or resolved.is_relative_to(f) for f in important)
