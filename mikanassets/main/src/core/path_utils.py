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


def is_entry_file(path: str | pathlib.Path) -> bool:
    """path がエントリファイル (通常 server.py、リネーム可能) と一致するかを確認する。

    server.py が run_main() で設定する MIKAN_ENTRY_FILE 環境変数からファイル名を取得する。
    未設定 (main.py 単体起動など) の場合は "server.py" を既定値とする。
    """
    resolved   = pathlib.Path(path).resolve()
    entry_name = os.environ.get("MIKAN_ENTRY_FILE", "server.py")
    entry_path = (ctx.paths.base / entry_name).resolve()
    return resolved == entry_path


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


def is_important_bot_file(path: str | pathlib.Path) -> bool:
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


def backup_would_overwrite_important_files(
    src_dir: str | pathlib.Path, dest_dir: str | pathlib.Path
) -> pathlib.Path | None:
    """src_dir (バックアップの中身) を dest_dir にマージコピー (同名エントリのみ上書き)
    した場合に、sys_files のいずれかを上書きしてしまうかを確認する。

    バックアップ適用は dest_dir を丸ごと削除するのではなく、src_dir にある
    エントリだけを上書き/追加するマージコピーであることが前提。

    src_dir 側 (バックアップの中身。数百〜数千ファイルもあり得る) を列挙して
    保護パスと突き合わせるのではなく、sys_files (数件の固定リスト) 側を起点に
    「その保護パスが dest_dir の下に来る位置にあり、かつ src_dir 側に対応する
    相対パスが実際に存在するか」を直接確認する方が軽く、多段パスの sys_files
    (例: "data/foo") に対しても取りこぼし・誤検知がない。

    衝突する保護パスが見つかった場合は dest_dir から見た相対パスを返す
    (呼び出し側でエラーメッセージに含めて「何が原因で拒否されたか」を示すため)。
    見つからなければ None を返す。
    """
    src_dir   = pathlib.Path(src_dir)
    dest_dir  = pathlib.Path(dest_dir).resolve(strict=False)
    sys_files = ctx.config["discord_commands"]["cmd"]["stdin"]["sys_files"]

    for f in sys_files:
        protected = (ctx.server_path / f).resolve()
        try:
            rel = protected.relative_to(dest_dir)
        except ValueError:
            continue  # dest_dir はこの保護パスの祖先ではない (衝突しようがない)
        if (src_dir / rel).exists():
            return rel
    return None
