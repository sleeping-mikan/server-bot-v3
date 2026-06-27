"""
commands/logs.py 窶・/logs 繧ｳ繝槭Φ繝・
螳溯｣・(Implementation)
---------------------
_resolve_log_path(filename, server_path)
  竊・(path: str | None, error_key: str | None)
  繝輔ぃ繧､繝ｫ蜷阪ｒ讀懆ｨｼ縺励※繝輔Ν繝代せ繧定ｿ斐☆縲ゆｸ肴ｭ｣縺ｪ繧・error_key 繧定ｿ斐☆縲・
_trim_to_discord_limit(lines)
  竊・list[str]
  2000 譁・ｭ励ｒ雜・∴縺ｪ縺・ｈ縺・忰蟆ｾ縺九ｉ隧ｰ繧√ｋ縲・
陦ｨ遉ｺ (Presentation)
--------------------
setup() 蜀・・ @tree.command 繝上Φ繝峨Λ
"""

from __future__ import annotations

import os

import discord
from discord import app_commands

from bot.client import tree
from bot.embeds import ModifiedEmbeds
from core.log_setup import LogManager
from core.state import ctx
from bot.utils import not_enough_permission, print_user, user_permission


# 笏笏 螳溯｣・(Implementation) 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏

def _resolve_log_path(filename: str, server_logs_dir: str) -> tuple[str | None, str | None]:
    """
    謌ｻ繧雁､: (full_path, error_key)
    豁｣蟶ｸ: (path, None)
    繧ｨ繝ｩ繝ｼ: (None, error_key)   error_key 縺ｯ RESPONSE_MSG["logs"][error_key]
    """
    if any(c in filename for c in "/\\%"):
        return None, "cant_access_other_dir"
    if not filename.endswith(".log"):
        return None, "not_found"
    candidates = [
        os.path.join(server_logs_dir, filename),
        str(ctx.paths.log_file(filename)),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p, None
    return None, "not_found"


def _trim_to_discord_limit(lines: list[str], limit: int = 1900) -> list[str]:
    result: list[str] = []
    total = 0
    for line in lines:
        total += len(line)
        result.append(line)
        while total > limit and result:
            removed = result.pop(0)
            total -= len(removed)
    return result


# 笏笏 陦ｨ遉ｺ (Presentation) 笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏笏

def setup(server_path: str, log_msg: list) -> None:
    """
    server_path : 繧ｵ繝ｼ繝舌・繝・ぅ繝ｬ繧ｯ繝医Μ縺ｮ繝代せ
    log_msg     : main.py 蛛ｴ縺ｧ繝ｪ繧｢繝ｫ繧ｿ繧､繝譖ｴ譁ｰ縺輔ｌ繧区怙譁ｰ繝ｭ繧ｰ縺ｮ繝ｪ繧ｹ繝・    """
    log_logger = LogManager.cmd.getChild("logs")
    server_logs_dir = server_path + "logs/"

    async def _autocomplete(interaction: discord.Interaction, current: str):
        current = current.translate(str.maketrans("/\\:", "--_"))
        candidates: list[str] = []
        if os.path.isdir(server_logs_dir):
            candidates += os.listdir(server_logs_dir)
        candidates += [p.name for p in ctx.paths.logs_dir.iterdir()]
        filtered = [f for f in candidates if current in f and f.endswith(".log")][-25:]
        return [app_commands.Choice(name=f, value=f) for f in filtered]

    @tree.command(name="logs", description=ctx.text.command_desc[ctx.text.lang]["logs"])
    @app_commands.autocomplete(filename=_autocomplete)
    async def logs_cmd(interaction: discord.Interaction, filename: str = None) -> None:
        await print_user(log_logger, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title=f"/logs {filename}")
        if await user_permission(interaction.user) < ctx.text.command_permission["logs"]:
            await not_enough_permission(interaction, log_logger)
            return
        if filename is None:
            lines = _trim_to_discord_limit(list(log_msg))
            await interaction.response.send_message("```ansi\n" + "\n".join(lines) + "\n```")
            log_logger.info("sended logs -> Server logs")
            return
        path, error_key = _resolve_log_path(filename, server_logs_dir)
        if error_key:
            log_logger.error(f"invalid filename : {filename} ({interaction.user} {interaction.user.id})")
            embed.add_field(name="", value=ctx.text.response_msg["logs"][error_key], inline=False)
            await interaction.response.send_message(embed=embed)
            return
        await interaction.response.send_message(file=discord.File(path))
        log_logger.info(f"sended logs -> {path}")
