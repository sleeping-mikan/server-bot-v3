"""
commands/ip.py 窶・/ip 繧ｳ繝槭Φ繝・
螳溯｣・(Implementation)
---------------------
_get_public_ip() 竊・str | None     螟夜Κ IP 繧貞叙蠕励☆繧・(螟ｱ謨玲凾縺ｯ None)

陦ｨ遉ｺ (Presentation)
--------------------
setup() 蜀・・ @tree.command 繝上Φ繝峨Λ
"""

from __future__ import annotations

from dataclasses import dataclass

import requests

import discord

from bot.client import tree
from bot.embeds import ModifiedEmbeds
from core.log_setup import LogManager
from core.state import ctx
from bot.utils import not_enough_permission, print_user, user_permission


# 笏笏 螳溯｣・(Implementation) 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏

def _get_public_ip() -> str | None:
    try:
        return requests.get("https://api.ipify.org", timeout=10).text
    except Exception:
        return None


# 笏笏 陦ｨ遉ｺ (Presentation) 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏

def setup(allow_ip: bool, server_port: str | None = None) -> None:
    """
    allow_ip   : config["allow"]["ip"]
    server_port: Minecraft 繧ｵ繝ｼ繝舌・縺ｮ繝昴・繝育分蜿ｷ (mc-server 縺ｮ蝣ｴ蜷医・縺ｿ)
    """
    ip_logger = LogManager.cmd.getChild("ip")

    @tree.command(name="ip", description=ctx.text.command_desc[ctx.text.lang]["ip"])
    async def ip_cmd(interaction: discord.Interaction) -> None:
        await print_user(ip_logger, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title="/ip")
        if await user_permission(interaction.user) < ctx.text.command_permission["ip"]:
            await not_enough_permission(interaction, ip_logger)
            return
        if not allow_ip:
            embed.add_field(name="", value=ctx.text.response_msg["ip"]["not_allow"], inline=False)
            await interaction.response.send_message(embed=embed)
            ip_logger.error("ip is not allowed")
            return
        addr = _get_public_ip()
        if addr is None:
            ip_logger.error("get ip failed")
            embed.add_field(name="", value=ctx.text.response_msg["ip"]["get_ip_failed"], inline=False)
            await interaction.response.send_message(embed=embed)
            return
        if server_port:
            ip_logger.info(f"get ip : {addr}:{server_port}")
            embed.add_field(
                name=ctx.text.response_msg["ip"]["msg_startwith"] + f"{addr}:{server_port}",
                value=f"(ip:{addr} port:{server_port})",
                inline=False,
            )
        else:
            ip_logger.info(f"get ip : {addr}")
            embed.add_field(name="", value=ctx.text.response_msg["ip"]["msg_startwith"] + addr, inline=False)
        await interaction.response.send_message(embed=embed)
