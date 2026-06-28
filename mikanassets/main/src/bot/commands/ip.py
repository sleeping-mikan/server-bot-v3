"""
commands/ip.py — /ip コマンド

実装 (Implementation)
---------------------
_get_public_ip() → str | None
    外部 IP を取得する。失敗時は None。

get_display_ip() → str | None
    config の prefix / suffix / body に基づいて表示用 IP 文字列を返す。
    allow_ip=False または取得失敗時は None。
    bot の /ip コマンドと web の /api/ip の両方から参照する。

表示 (Presentation)
--------------------
setup() 内の @tree.command ハンドラ
"""

from __future__ import annotations

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


def get_display_ip() -> str | None:
    """config に基づいて表示用 IP 文字列 (prefix+raw+suffix) を返す。

    allow_ip=False または IP 取得失敗時は None を返す。
    """
    if not ctx.config["allow"]["ip"]:
        return None
    cfg  = ctx.config["discord_commands"]["ip"]["address"]
    body = cfg["body"]
    raw  = body if body is not None else _get_public_ip()
    if raw is None:
        return None
    return f"{cfg['prefix']}{raw}{cfg['suffix']}"


# ── 表示 (Presentation) ──────────────────────────────────────────────────────

def setup() -> None:
    ip_logger = LogManager.cmd.getChild("ip")

    @tree.command(name="ip", description=ctx.text.command_desc[ctx.text.lang]["ip"])
    async def ip_cmd(interaction: discord.Interaction) -> None:
        await print_user(ip_logger, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title="/ip")
        if await user_permission(interaction.user) < ctx.text.command_permission["ip"]:
            await not_enough_permission(interaction, ip_logger)
            return
        if not ctx.config["allow"]["ip"]:
            embed.add_field(name="", value=ctx.text.response_msg["ip"]["not_allow"], inline=False)
            await interaction.response.send_message(embed=embed)
            ip_logger.error("ip is not allowed")
            return
        display = get_display_ip()
        if display is None:
            ip_logger.error("get ip failed")
            embed.add_field(name="", value=ctx.text.response_msg["ip"]["get_ip_failed"], inline=False)
            await interaction.response.send_message(embed=embed)
            return
        ip_logger.info(f"ip: {display}")
        embed.add_field(name="", value=ctx.text.response_msg["ip"]["msg_startwith"] + display, inline=False)
        await interaction.response.send_message(embed=embed)
