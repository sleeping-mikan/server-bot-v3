"""
server/control.py — サーバープロセスの起動・停止ロジック

Discord コマンドに依存しない純粋な実装。
Discord ハンドラは bot/commands/server.py から呼び出す。
"""

from __future__ import annotations

from enum import Enum, auto
from typing import Callable

from core.state import ctx


class StartResult(Enum):
    SUCCESS         = auto()
    ALREADY_RUNNING = auto()


class StopResult(Enum):
    SUCCESS         = auto()
    ALREADY_STOPPED = auto()


def start_server(logger_func: Callable) -> StartResult:
    """サーバープロセスを起動する。"""
    if ctx.server_process.is_running():
        return StartResult.ALREADY_RUNNING
    ctx.server_process.start(
        [str(ctx.server_path / ctx.server_name), *ctx.server_args],
        cwd=ctx.server_path,
        char_code=ctx.server_char_code,
        logger_func=logger_func,
    )
    return StartResult.SUCCESS


def stop_server() -> StopResult:
    """サーバープロセスに停止コマンドを送る。"""
    if ctx.server_process.is_stopped():
        return StopResult.ALREADY_STOPPED
    ctx.use_stop = True
    ctx.server_process.write(ctx.STOP)
    return StopResult.SUCCESS
