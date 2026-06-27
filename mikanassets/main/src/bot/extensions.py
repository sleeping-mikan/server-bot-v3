"""
bot/extensions.py — 拡張コマンドのロードと拡張機能向け API

load() を呼ぶと mikanassets/extension/ 以下を走査して拡張コマンドを登録する。
拡張機能向けユーティリティ関数もここで定義する。
"""

from __future__ import annotations

import importlib
import os
from collections import deque

from discord import app_commands

from bot.client import tree
from core.log_setup import LogManager
from core.state import ctx

# 拡張コマンドグループを GC から守る参照先
_gc_anchors: deque = deque()


def load() -> None:
    """拡張コマンドディレクトリを走査してコマンドを登録する。"""
    ext_log = LogManager.extension
    sys_log = LogManager.sys
    ext_log.info("search extension commands")

    extension_dir = ctx.paths.extension_dir
    if not os.path.exists(extension_dir.as_posix()):
        return
    if not os.listdir(extension_dir.as_posix()):
        sys_log.info("no extension commands in " + extension_dir.as_posix())
        return

    sys_log.info("read extension commands -> " + extension_dir.as_posix())
    extension_commands_groups: deque = deque()

    for entry in extension_dir.iterdir():
        cmd_file = entry / "commands.py"
        if not entry.is_dir():
            sys_log.info("not directory -> " + entry.as_posix())
            continue
        sys_log.info("read extension commands -> " + entry.as_posix())
        if not cmd_file.exists():
            sys_log.info("not exist extension commands file in " + cmd_file.as_posix())
            continue
        ctx.extension_commands_group = app_commands.Group(
            name="extension-" + entry.name,
            description="This commands group is extension. Use this code at your own risk. " + entry.name,
        )
        extension_commands_groups.append(ctx.extension_commands_group)
        try:
            ctx.extension_logger = ext_log.getChild(entry.name)
            importlib.import_module("mikanassets.extension." + entry.name + ".commands")
            tree.add_command(ctx.extension_commands_group)
            sys_log.info("read extension commands success -> " + cmd_file.as_posix())
        except Exception as e:
            sys_log.info(f"cannot read extension commands {cmd_file.as_posix()} ({e})")

    _gc_anchors.append(extension_commands_groups)
    ctx.extension_commands_group = None


# ── 拡張機能向け API ──────────────────────────────────────────────────────────

def get_process():
    """サーバーの生の Popen オブジェクトを返す。"""
    return ctx.server_process.raw()


def append_task(func) -> None:
    """on_ready 後に start() される discord.ext.tasks 関数を登録する。"""
    ctx.extension_tasks.append(func)


def write_server_in(command: str) -> tuple[bool, str]:
    """サーバーの stdin にコマンドを書き込む。"""
    if ctx.is_write_server_block:
        return False, "write_server_block"
    ctx.is_write_server_block = True
    if ctx.server_process.is_stopped():
        ctx.is_write_server_block = False
        return False, "server_is_not_running"
    ctx.server_process.write(command)
    ctx.is_write_server_block = False
    return True, "success"
