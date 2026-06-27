"""
bot/events.py — Discord イベントハンドラ

on_ready / on_message / update_loop / on_error を定義する。
このモジュールを import するだけで各ハンドラが client/tree に登録される。
"""

from __future__ import annotations

import asyncio
import threading
import traceback
from collections import deque

import discord
from discord.ext import tasks

from bot.client import client, tree
from bot.utils import is_administrator, is_force_administrator
from core.log_setup import LogManager
from core.state import ctx

_status_lock = threading.Lock()


@tasks.loop(seconds=10)
async def _update_loop() -> None:
    if ctx.terminal.loop_is_run:
        return
    term     = ctx.terminal
    log_buf  = LogManager.discord_log_msg
    bot_log  = LogManager.bot
    try:
        ctx.terminal.loop_is_run = True
        with _status_lock:
            activity = (
                ctx.text.activity_name["running"].format(ctx.server_name)
                if not ctx.server_process.is_stopped()
                else ctx.text.activity_name["ended"]
            )
            await client.change_presence(activity=discord.Game(name=activity))

            if not term.channel_id:
                log_buf.clear()
                ctx.terminal.loop_is_run = False
                return

            pop_flg = False
            while len(log_buf) > 0:
                while len(log_buf) > ctx.terminal_capacity:
                    log_buf.popleft()
                    pop_flg = True
                if pop_flg:
                    await client.get_channel(term.channel_id).send(
                        f"データ件数が{ctx.terminal_capacity}件を超えたため以前のデータを破棄しました。"
                        "より多くのログを出力するには.config内のterminal.capacityを変更してください。"
                    )
                    pop_flg = False
                if len(log_buf[0]) >= 1900:
                    log_buf.popleft()
                    raise Exception("message is too long(skipped)")
                term.send_length += len(log_buf[0]) + 1
                if term.send_length >= 1900:
                    await client.get_channel(term.channel_id).send(
                        "```ansi\n" + "".join(term.item) + "\n```"
                    )
                    term.item        = deque()
                    term.send_length = len(log_buf[0]) + 1
                    await asyncio.sleep(1)
                term.item.append(log_buf.popleft() + "\n")

            if len(term.item) > 0:
                await client.get_channel(term.channel_id).send(
                    "```ansi\n" + "".join(term.item) + "\n```"
                )
                term.item        = deque()
                term.send_length = 0

        ctx.terminal.loop_is_run = False
    except Exception as e:
        bot_log.getChild("terminal").error(e)
        ctx.terminal.loop_is_run = False


@client.event
async def on_message(message: discord.Message) -> None:
    try:
        if message.author == client.user:
            return
        if message.channel.id != ctx.terminal.channel_id:
            return
        if not await is_administrator(message.author) and not await is_force_administrator(message.author):
            await message.reply("permission denied")
            return
        if not ctx.server_process.is_running():
            await message.reply("server is not running")
            return
        cmd_list = message.content.split(" ")
        if message.author.bot:
            pass
        elif cmd_list[0] not in ctx.allow_cmd:
            LogManager.sys.error("unknown command : " + " ".join(cmd_list))
            await message.reply("this command is not allowed")
            return
        else:
            ctx.server_process.write(message.content)
    except Exception as e:
        LogManager.sys.error(e)


@client.event
async def on_ready() -> None:
    bot_log = LogManager.bot
    bot_log.info("discord bot logging on")
    _update_loop.start()
    for task in ctx.extension_tasks:
        task.start()
    try:
        await client.change_presence(
            activity=discord.Game(ctx.text.activity_name["starting"])
        )
        if ctx.server_process.is_stopped():
            ctx.server_process.start(
                [ctx.server_path + ctx.server_name, *ctx.server_args],
                cwd=ctx.server_path,
                char_code=ctx.server_char_code,
                logger_func=ctx.server_logger,
            )
            bot_log.info("server starting")
        else:
            bot_log.info("skip server starting because server already running")
        await client.change_presence(
            activity=discord.Game(ctx.text.activity_name["running"].format(ctx.server_name))
        )
    except Exception as e:
        LogManager.sys.error(f"error on ready (server start) -> {e}")
    try:
        await tree.sync()
        bot_log.info("slash commands synced")
    except Exception as e:
        LogManager.sys.error(f"error on ready (command sync) -> {e}")


@tree.error
async def on_error(interaction: discord.Interaction, error: Exception) -> None:
    try:
        LogManager.sys.error(error)
        LogManager.sys.error(traceback.format_exc())
        message = ctx.text.response_msg["error"]["error_base"] + str(error)
        if interaction.response.is_done():
            await interaction.followup.send(message)
        else:
            await interaction.response.send_message(message)
    except Exception as e:
        LogManager.sys.error(e)
        LogManager.sys.error(traceback.format_exc())
