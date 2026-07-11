"""
bot/setup.py — bot 起動時のセットアップ処理

テキストデータ読み込み・コマンド登録・イベント登録・拡張機能ロードをまとめる。
main.py から呼び出すことを想定している。
"""

from __future__ import annotations

import importlib
from collections import deque

from bot import text_data as _text_data
from core.config_types import AppConfig
from bot.commands import (
    announce as announce_cmd,
    backup as backup_cmd,
    cmd as cmd_cmd,
    ip as ip_cmd,
    logs as logs_cmd,
    misc,
    permission as permission_cmd,
    server as server_cmd,
    status as status_cmd,
    terminal as terminal_cmd,
    tokengen as tokengen_cmd,
    update as update_cmd,
)
from bot.embeds import ModifiedEmbeds
from bot.extensions import load as load_extensions
from core.state import ctx


async def load_text() -> None:
    (
        ctx.text.command_desc,
        ctx.text.command_args_desc,
        ctx.text.response_msg,
        ctx.text.activity_name,
        send_help_initial,
    ) = _text_data.load_text_data(ctx.text.lang)
    # コマンドの説明はスラッシュコマンドUIとドキュメントサイトに任せ、
    # /help は環境固有情報 (docsリンク + web URL) のみを返す
    send_help_initial += f"web : http://{ctx.web_ip}:{ctx.web_port}\n"
    embed = ModifiedEmbeds.DefaultEmbed(title="How to use this bot")
    embed.add_field(name="", value=send_help_initial, inline=False)
    ctx.text.send_help = embed


def setup_commands(config: AppConfig, log_msg: deque) -> None:
    misc.setup()
    status_cmd.setup(server_name=ctx.server_name, web_port=ctx.web_port)
    server_cmd.setup(server_logger=ctx.server_logger)
    permission_cmd.setup(get_text_dat=load_text)
    terminal_cmd.setup()
    tokengen_cmd.setup()
    ip_cmd.setup()
    logs_cmd.setup(server_path=str(ctx.server_path), log_msg=log_msg)
    cmd_cmd.setup()
    backup_cmd.setup()
    announce_cmd.setup()
    update_cmd.setup()

    importlib.import_module("bot.events")
    load_extensions()
