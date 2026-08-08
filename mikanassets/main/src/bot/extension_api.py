"""
bot/extension_api.py — 拡張機能 (mikanassets/extension/*/commands.py) 向け公開API

拡張機能を書くとき、これまでは `bot.client` / `bot.utils` / `core.state` / `server.control` ...
のように使いたいオブジェクトごとに元のモジュールを探して import する必要があった。
このモジュールはそれらの中から拡張機能が使いそうなものを1か所に集めた再エクスポート専用の窓口。
拡張機能側は基本的にこのモジュール1つを import すればよい。

    from bot.extension_api import ctx, ModifiedEmbeds, user_permission, append_task

実装はここには置かない (元のモジュール側が正)。新しいオブジェクトを拡張機能に公開したいときは、
実装を書いた元モジュールから import を1行足して __all__ に加える。
"""

from __future__ import annotations

# ── Discord クライアント ──────────────────────────────────────────────────
from bot.client import client, tree

# ── Embed ────────────────────────────────────────────────────────────────
from bot.embeds import ModifiedEmbeds

# ── 拡張機能ロード・ライフサイクル (bot/extensions.py が実装元) ───────────
from bot.extensions import append_task, get_process, write_server_in

# ── 権限・メッセージ・設定関連ユーティリティ (bot/utils.py が実装元) ──────
from bot.utils import (
    get_member_level,
    is_administrator,
    is_force_administrator,
    is_running_server,
    is_stopped_server,
    not_enough_permission,
    print_user,
    rewrite_config,
    set_member_level,
    user_permission,
)

# ── アプリ共有状態・ロギング・パス検証 (ディレクトリトラバーサル対策) ─────
from core.log_setup import LogManager
from core.log_tailer import LogTailer, LogTailerEmptyError
from core.path_utils import is_important_bot_file, is_path_within_scope
from core.state import ctx

# ── サーバープロセス制御・バックアップ ────────────────────────────────────
from server.backup import ProgressCallback, apply_backup, apply_backup_sync, create_backup, create_backup_sync
from server.control import StartResult, StopResult, start_server, stop_server

__all__ = [
    "ModifiedEmbeds",
    "LogManager",
    "LogTailer",
    "LogTailerEmptyError",
    "ProgressCallback",
    "StartResult",
    "StopResult",
    "append_task",
    "apply_backup",
    "apply_backup_sync",
    "client",
    "create_backup",
    "create_backup_sync",
    "ctx",
    "get_member_level",
    "get_process",
    "is_administrator",
    "is_force_administrator",
    "is_important_bot_file",
    "is_path_within_scope",
    "is_running_server",
    "is_stopped_server",
    "not_enough_permission",
    "print_user",
    "rewrite_config",
    "set_member_level",
    "start_server",
    "stop_server",
    "tree",
    "user_permission",
    "write_server_in",
]
