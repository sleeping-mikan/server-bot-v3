"""
commands/ip.py — /ip コマンド

実装 (Implementation)
---------------------
_get_public_ip() → str | None     外部 IP を取得する。(失敗時は None)

表示 (Presentation)
--------------------
setup() 内の @tree.command ハンドラ
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


# ── 実装 (Implementation) ────────────────────────────────────────────────────

def _get_public_ip() -> str | None:
    try:
        return requests.get("https://api.ipify.org", timeout=10).text
    except Exception:
        return None


# ── 表示 (Presentation) ──────────────────────────────────────────────────────

def setup(allow_ip: bool, ip_address_config: dict) -> None:
    """
    allow_ip        : config["allow"]["ip"]
    ip_address_config: config["discord_commands"]["ip"]["address"]
                       keys: prefix, suffix, body (null → 実 IP を取得)
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

        prefix = ip_address_config.get("prefix", "")
        suffix = ip_address_config.get("suffix", "")
        body = ip_address_config.get("body")

        if body is None:
            raw = _get_public_ip()
            if raw is None:
                ip_logger.error("get ip failed")
                embed.add_field(name="", value=ctx.text.response_msg["ip"]["get_ip_failed"], inline=False)
                await interaction.response.send_message(embed=embed)
                return
            display = f"{prefix}{raw}{suffix}"
        else:
            display = f"{prefix}{body}{suffix}"

        ip_logger.info(f"ip : {display}")
        embed.add_field(name="", value=ctx.text.response_msg["ip"]["msg_startwith"] + display, inline=False)
        await interaction.response.send_message(embed=embed)
