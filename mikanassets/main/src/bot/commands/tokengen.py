"""bot/commands/tokengen.py — /tokengen Discord command handler."""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from random import choices
from string import ascii_letters, digits

import discord

from bot.client import tree
from bot.embeds import ModifiedEmbeds
from core.log_setup import LogManager
from core.state import ctx
from bot.utils import not_enough_permission, print_user, user_permission


def _generate_token() -> str:
    return "".join(choices(ascii_letters + digits, k=12))


def _save_token(token: str, level: int) -> dict[str, str | int]:
    deadline = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    entry    = {"token": token, "deadline": deadline, "level": level}
    with ctx.paths.web_tokens_file.open("r", encoding="utf-8") as f:
        data = json.load(f)
    data["tokens"].append(entry)
    with ctx.paths.web_tokens_file.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    ctx.web_tokens.append(entry)
    return entry


def setup() -> None:
    token_logger = LogManager.cmd.getChild("tokengen")

    @tree.command(name="tokengen", description=ctx.text.command_desc[ctx.text.lang]["tokengen"])
    async def tokengen_cmd(interaction: discord.Interaction, level: int = 1) -> None:
        await print_user(token_logger, interaction.user)
        embed = ModifiedEmbeds.DefaultEmbed(title=f"/tokengen {level}")
        if await user_permission(interaction.user) < ctx.text.command_permission["tokengen"]:
            await not_enough_permission(interaction, token_logger)
            return
        # 発行者自身の Discord 権限レベルを上限としてクランプする
        # (自分より強い権限のWebトークンを配れないようにする)
        caller_level = await user_permission(interaction.user)
        level = max(0, min(level, caller_level))
        token = _generate_token()
        entry = _save_token(token, level)
        embed.add_field(
            name=ctx.text.response_msg["tokengen"]["success"].format(f" (level {level})"),
            value=token,
            inline=False,
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        token_logger.info(f"token added : {entry}")
