"""bot/commands/misc.py — /help, /exit Discord command handlers."""

from __future__ import annotations

import discord

from bot.client import shutdown, tree
from bot.embeds import ModifiedEmbeds
from core.log_setup import LogManager
from core.state import ctx
from bot.utils import (
    is_running_server,
    not_enough_permission,
    print_user,
    user_permission,
)


def setup() -> None:
    help_logger = LogManager.cmd.getChild("help")
    exit_logger = LogManager.cmd.getChild("exit")

    @tree.command(name="help", description=ctx.text.command_desc[ctx.text.lang]["help"])
    async def help_cmd(interaction: discord.Interaction) -> None:
        await print_user(help_logger, interaction.user)
        if await user_permission(interaction.user) < ctx.text.command_permission["help"]:
            await not_enough_permission(interaction, help_logger)
            return
        await interaction.response.send_message(embed=ctx.text.send_help)
        help_logger.info("help sent")

    @tree.command(name="exit", description=ctx.text.command_desc[ctx.text.lang]["exit"])
    async def exit_cmd(interaction: discord.Interaction) -> None:
        await print_user(exit_logger, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title="/exit")
        if await user_permission(interaction.user) < ctx.text.command_permission["exit"]:
            await not_enough_permission(interaction, exit_logger)
            return
        if is_running_server(exit_logger):
            embed.add_field(name="", value=ctx.text.response_msg["other"]["is_running"], inline=False)
            await interaction.response.send_message(embed=embed)
            return
        embed.add_field(name="", value=ctx.text.response_msg["exit"]["success"], inline=False)
        await interaction.response.send_message(embed=embed)
        exit_logger.info("exit")
        await shutdown()
