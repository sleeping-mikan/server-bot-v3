"""
client.py — Discord Client と CommandTree のシングルトン

commands/*.py はここから import することで、main.py への循環 import を避けられる。

    from bot.client import client, tree, shutdown
"""

import asyncio
import os

import discord
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


async def shutdown() -> None:
    """実行中のタスクをキャンセルし、Discord クライアントを閉じる。"""
    from bot.events import _update_loop
    from core.state import ctx

    _update_loop.cancel()
    for task in ctx.extension_tasks:
        task.cancel()

    def _running_task(loop):
        # get_task() は discord.py 2.x の公開 API。旧バージョン互換のため _task にフォールバック。
        if hasattr(loop, "get_task"):
            return loop.get_task()
        return getattr(loop, "_task", None)

    loop_tasks = [t for t in [_running_task(_update_loop)] + [_running_task(e) for e in ctx.extension_tasks] if t is not None]
    if loop_tasks:
        await asyncio.gather(*loop_tasks, return_exceptions=True)

    try:
        # /update の同期 HTTP 呼び出しで heartbeat が途切れ再接続中になっている場合、
        # client.close() が再接続コルーチンの終了を待って無限にハングすることがある。
        # タイムアウトを設けることで確実に os._exit(0) へ到達させる。
        await asyncio.wait_for(client.close(), timeout=5.0)
    except (asyncio.CancelledError, Exception):
        # ws.close() が完了しない / タイムアウトした場合でも HTTP セッションを閉じる
        try:
            await client.http.close()
        except Exception:
            pass

    os._exit(0)
