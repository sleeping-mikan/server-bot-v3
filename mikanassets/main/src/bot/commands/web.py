"""
bot/commands/web.py — /web url Discord コマンドハンドラ

Web コンソールへの外部アクセスURLを表示する。
"""

from __future__ import annotations

import discord
from discord import app_commands

from bot.client import tree
from bot.embeds import ModifiedEmbeds
from bot.utils import not_enough_permission, print_user, user_permission
from core.log_setup import LogManager
from core.state import ctx
from core.web_url import get_web_base_url


def setup() -> None:
    _url = LogManager.cmd.getChild("web").getChild("url")

    command_group_web = app_commands.Group(name="web", description="web group")

    @command_group_web.command(
        name="url",
        description=ctx.text.command_desc[ctx.text.lang]["web"]["url"],
    )
    async def web_url_cmd(interaction: discord.Interaction) -> None:
        await print_user(_url, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title="/web url")
        if await user_permission(interaction.user) < ctx.text.command_permission["web url"]:
            await not_enough_permission(interaction, _url)
            return
        embed.add_field(name="", value=get_web_base_url(), inline=False)
        await interaction.response.send_message(embed=embed)

    tree.add_command(command_group_web)
