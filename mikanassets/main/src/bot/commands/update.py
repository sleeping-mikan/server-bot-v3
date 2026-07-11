"""bot/commands/update.py — /update Discord コマンドハンドラ"""

from __future__ import annotations

import discord
from discord import app_commands

from bot.client import tree
from bot.embeds import ModifiedEmbeds
from bot.utils import is_running_server, not_enough_permission, print_user, user_permission
from core.log_setup import LogManager
from core.state import ctx
from update.selfupdate import update_self_if_commit_changed


def setup() -> None:
    _update = LogManager.cmd.getChild("update")

    async def _sender(interaction: discord.Interaction, embed: ModifiedEmbeds.DefaultEmbed) -> None:
        try:
            await interaction.edit_original_response(embed=embed)
        except discord.NotFound:
            await interaction.response.send_message(embed=embed)

    @tree.command(
        name="update",
        description=ctx.text.command_desc[ctx.text.lang]["update"],
    )
    @app_commands.describe(**ctx.text.command_args_desc[ctx.text.lang]["update"])
    async def update_cmd(interaction: discord.Interaction, is_force: bool = False) -> None:
        await print_user(_update, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title=f"/update {is_force}")
        if is_running_server(_update):
            embed.add_field(name="", value=ctx.text.response_msg["other"]["is_running"], inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if await user_permission(interaction.user) < ctx.text.command_permission["update"]:
            await not_enough_permission(interaction, _update)
            return
        await interaction.response.send_message(embed=embed)
        await update_self_if_commit_changed(
            interaction=interaction,
            embed=embed,
            text_pack=ctx.text.response_msg["update"],
            sender=_sender,
            is_force=is_force,
        )
