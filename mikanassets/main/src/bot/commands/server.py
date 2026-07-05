"""
bot/commands/server.py — /start, /stop Discord コマンドハンドラ

実装は server/control.py を参照。
"""

from __future__ import annotations

import asyncio

import discord

from bot.client import client, tree
from bot.embeds import ModifiedEmbeds
from bot.utils import is_running_server, is_stopped_server, not_enough_permission, print_user, user_permission
from core.log_setup import LogManager
from core.state import ctx
from server.control import StartResult, StopResult, start_server, stop_server


def setup(server_logger: object) -> None:
    _start = LogManager.cmd.getChild("start")
    _stop  = LogManager.cmd.getChild("stop")

    @tree.command(name="start", description=ctx.text.command_desc[ctx.text.lang]["start"])
    async def start_cmd(interaction: discord.Interaction) -> None:
        await print_user(_start, interaction.user)
        if await user_permission(interaction.user) < ctx.text.command_permission["start"]:
            await not_enough_permission(interaction, _start)
            return
        await interaction.response.defer()
        result = start_server(server_logger)
        embed  = ModifiedEmbeds.DefaultEmbed(title="/start")
        if result == StartResult.ALREADY_RUNNING:
            _start.error("server is already running")
            embed.add_field(name="", value=ctx.text.response_msg["other"]["is_running"], inline=False)
            await interaction.followup.send(embed=embed)
            return
        _start.info("server start")
        embed.add_field(name="", value=ctx.text.response_msg["start"]["success"], inline=False)
        await interaction.followup.send(embed=embed)
        await client.change_presence(
            activity=discord.Game(ctx.text.activity_name["running"].format(ctx.server_name))
        )

    @tree.command(name="stop", description=ctx.text.command_desc[ctx.text.lang]["stop"])
    async def stop_cmd(interaction: discord.Interaction) -> None:
        await print_user(_stop, interaction.user)
        if await user_permission(interaction.user) < ctx.text.command_permission["stop"]:
            await not_enough_permission(interaction, _stop)
            return
        await interaction.response.defer()
        result = stop_server()
        embed  = ModifiedEmbeds.DefaultEmbed(title="/stop")
        if result == StopResult.ALREADY_STOPPED:
            _stop.error("server is not running")
            embed.add_field(name="", value=ctx.text.response_msg["other"]["is_not_running"], inline=False)
            await interaction.followup.send(embed=embed)
            return
        _stop.info("server stop")
        embed.add_field(name="", value=ctx.text.response_msg["stop"]["success"], inline=False)
        await interaction.followup.send(embed=embed)
        await client.change_presence(activity=discord.Game(ctx.text.activity_name["ending"]))
        for _ in range(60):
            if ctx.server_process.is_stopped():
                break
            await asyncio.sleep(1)
        await client.change_presence(activity=discord.Game(ctx.text.activity_name["ended"]))
