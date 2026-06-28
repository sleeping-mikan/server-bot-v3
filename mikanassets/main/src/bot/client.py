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

    loop_tasks = [t for t in (
        [_update_loop._task] + [e._task for e in ctx.extension_tasks]
    ) if t is not None]
    if loop_tasks:
        await asyncio.gather(*loop_tasks, return_exceptions=True)

    try:
        await client.close()
    except asyncio.CancelledError:
        # ws.close() 中にこのタスクがキャンセルされると http.close() が呼ばれないため
        # 手動で HTTP セッションを閉じて "Unclosed connector" 警告を防ぐ
        await client.http.close()

    # client.close() 後も client.run() が返らない場合（ネットワーク異常等）に備えた安全弁
    os._exit(0)
