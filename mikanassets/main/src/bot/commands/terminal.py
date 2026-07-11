"""
commands/terminal.py 窶・/terminal set, /terminal del 繧ｳ繝槭Φ繝・
螳溯｣・(Implementation)
---------------------
_set_terminal(channel_id)   ctx.terminal.channel_id 繧呈峩譁ｰ縺励※ config 縺ｫ豌ｸ邯壼喧
_clear_terminal()           霆｢騾√ｒ辟｡蜉ｹ蛹・(where_terminal = False)

陦ｨ遉ｺ (Presentation)
--------------------
setup() 蜀・・ @tree.command 繝上Φ繝峨Λ
"""

from __future__ import annotations

from discord import app_commands
import discord

from bot.client import tree
from bot.embeds import ModifiedEmbeds
from core.log_setup import LogManager
from core.state import ctx
from bot.utils import not_enough_permission, print_user, rewrite_config, user_permission


# 笏笏 螳溯｣・(Implementation) 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏

async def _set_terminal(channel_id: int | bool) -> None:
    ctx.terminal.channel_id = channel_id
    ctx.config["discord_commands"]["terminal"]["discord"] = ctx.terminal.channel_id
    await rewrite_config()


# 笏笏 陦ｨ遉ｺ (Presentation) 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏

def setup() -> None:
    terminal_logger = LogManager.cmd.getChild("terminal")
    set_logger = terminal_logger.getChild("set")
    del_logger = terminal_logger.getChild("delete")

    command_group_terminal = app_commands.Group(name="terminal", description="terminal group")

    @command_group_terminal.command(name="set", description=ctx.text.command_desc[ctx.text.lang]["terminal"]["set"])
    @app_commands.describe(**ctx.text.command_args_desc[ctx.text.lang]["terminal"]["set"])
    async def terminal_set_cmd(interaction: discord.Interaction, channel: discord.TextChannel | None = None) -> None:
        await print_user(set_logger, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title=f"/terminal set {channel}")
        if await user_permission(interaction.user) < ctx.text.command_permission["terminal set"]:
            await not_enough_permission(interaction, set_logger)
            return
        await _set_terminal(channel.id if channel else interaction.channel.id)
        set_logger.info(f"terminal setting -> {ctx.terminal.channel_id}")
        embed.add_field(name="", value=ctx.text.response_msg["terminal"]["success"].format(ctx.terminal.channel_id), inline=False)
        await interaction.response.send_message(embed=embed)

    @command_group_terminal.command(name="del", description=ctx.text.command_desc[ctx.text.lang]["terminal"]["del"])
    async def terminal_del_cmd(interaction: discord.Interaction) -> None:
        await print_user(del_logger, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title="/terminal del")
        if await user_permission(interaction.user) < ctx.text.command_permission["terminal del"]:
            await not_enough_permission(interaction, del_logger)
            return
        await _set_terminal(False)
        del_logger.info("terminal disabled")
        embed.add_field(name="", value=ctx.text.response_msg["terminal"]["success"].format(ctx.terminal.channel_id), inline=False)
        await interaction.response.send_message(embed=embed)

    tree.add_command(command_group_terminal)
