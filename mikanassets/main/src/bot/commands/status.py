"""bot/commands/status.py — /status Discord command handler."""

from __future__ import annotations

import os
import platform
import sys

import discord

from bot.client import tree
from bot.embeds import ModifiedEmbeds
from core.log_setup import LogManager
from core.state import ctx
from server.system_info import (
    check_response,
    get_process_cpu,
    get_process_memory,
    get_thread_cpu_usage,
)
from bot.utils import not_enough_permission, print_user, user_permission
from core.version import get_version


def setup(server_name: str, web_port: int) -> None:
    status_logger = LogManager.cmd.getChild("status")

    @tree.command(name="status", description=ctx.text.command_desc[ctx.text.lang]["status"])
    async def status_cmd(interaction: discord.Interaction) -> None:
        await print_user(status_logger, interaction.user)
        await interaction.response.defer()
        embed = ModifiedEmbeds.DefaultEmbed(title="/status")

        if await user_permission(interaction.user) < ctx.text.command_permission["status"]:
            await not_enough_permission(interaction, status_logger)
            return

        memorys = await get_process_memory(ctx.server_process.raw())
        embed.add_field(
            name=ctx.text.response_msg["status"]["mem_title"],
            value=(
                ctx.text.response_msg["status"]["mem_value"].format(round(memorys["origin_mem"], 2))
                + "\n"
                + ctx.text.response_msg["status"]["mem_server_value"].format(round(memorys["server_mem"], 2))
            ),
        )
        status_logger.info(f"get memory -> process {memorys['origin_mem']}, server {memorys['server_mem']}")

        is_server_online   = "🟢" if ctx.server_process.is_running() else "🔴"
        is_waitress_online = "🟢" if await check_response(f"http://127.0.0.1:{web_port}") else "🔴"
        embed.add_field(
            name=ctx.text.response_msg["status"]["online_title"],
            value=ctx.text.response_msg["status"]["online_value"].format(is_server_online, is_waitress_online, "🟢"),
        )

        cpu_server = {server_name: await get_process_cpu()} if not ctx.server_process.is_stopped() else {"NULL": "NULL"}
        send_str   = ["Server"]
        send_str  += [ctx.text.response_msg["status"]["cpu_value_proc"].format(cpu_server[k], k) for k in cpu_server]

        cpu_self  = await get_thread_cpu_usage(os.getpid(), is_self=True)
        send_str += ["Self"]
        send_str += [ctx.text.response_msg["status"]["cpu_value_thread"].format(cpu_self[k], k) for k in cpu_self]
        embed.add_field(name=ctx.text.response_msg["status"]["cpu_title"], value="\n".join(send_str), inline=False)
        status_logger.info(f"get cpu usage -> {' '.join(send_str)}")

        branch = ctx.config["update"]["branch"] if ctx.config else "main"
        embed.add_field(
            name=ctx.text.response_msg["status"]["base_title"],
            value=ctx.text.response_msg["status"]["base_value"].format(
                platform.system() + " " + platform.release(),
                sys.version,
                f"{get_version()}({branch})",
            ),
            inline=True,
        )
        await interaction.edit_original_response(embed=embed)
        status_logger.info("status command end")
